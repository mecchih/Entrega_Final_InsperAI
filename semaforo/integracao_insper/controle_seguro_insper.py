"""Controle seguro de fases para os semaforos escolhidos do cenario Insper.

O SUMO nao insere amarelo nem vermelho quando o TraCI define um estado com
setRedYellowGreenState: o semaforo passa a um programa "online" e exibe
exatamente a string enviada. Por isso este modulo faz toda a transicao:

    verde atual --(verde minimo)--> amarelo do programa --> vermelho geral --> verde pedido

O amarelo vem do proprio programa do SUMO e e conferido: todo link verde da
fase atual vira 'y' e todo o resto fica 'r'. Se o programa nao tiver essa
forma (por exemplo, link verde em duas fases seguidas, verdes 'G' conflitantes
na mesma fase ou caracteres desconhecidos), o controlador recusa assumir o
semaforo: a duvida deve ser resolvida antes de controlar.

O controlador nao escreve em nenhum outro semaforo.
"""

import math

VERDE, AMARELO, VERMELHO = "verde", "amarelo", "vermelho_geral"
CORES = set("Ggyr")


class ErroSeguranca(RuntimeError):
    pass


def eh_verde(c):
    return c in "Gg"


def amarelo_de(verde):
    return "".join("y" if eh_verde(c) else "r" for c in verde)


def analisar_programa(fases, foes):
    """fases: [(state, duration, minDur, maxDur)]; foes: {link: {links conflitantes}}.

    Devolve os verdes, o amarelo (estado e duracao) depois de cada verde e o
    vermelho geral que ja existe no programa. Levanta ErroSeguranca se algo nao
    for seguro ou nao for compreendido.
    """
    if not fases:
        raise ErroSeguranca("programa sem fases")
    n = len(fases[0][0])
    for state, *_ in fases:
        if len(state) != n or set(state) - CORES:
            raise ErroSeguranca(f"estado inesperado no programa: {state}")
    verdes = [i for i, (s, *_) in enumerate(fases) if any(eh_verde(c) for c in s) and "y" not in s]
    if len(verdes) < 2:
        raise ErroSeguranca("programa com menos de duas fases verdes")
    if {i for i, (s, *_) in enumerate(fases) if any(eh_verde(c) for c in s)} != set(verdes):
        raise ErroSeguranca("fase com verde e amarelo ao mesmo tempo")
    for i in verdes:
        s = fases[i][0]
        for a in range(n):
            for b in foes.get(a, ()):
                if s[a] == "G" and s[b] == "G":
                    raise ErroSeguranca(f"verdes prioritarios conflitantes na fase {i}: links {a} e {b}")
    for a in range(n):
        if not any(eh_verde(fases[i][0][a]) for i in verdes):
            raise ErroSeguranca(f"link {a} nunca recebe verde")
    transicoes = {}
    for k, i in enumerate(verdes):
        j = verdes[(k + 1) % len(verdes)]
        meio = [(i + d) % len(fases) for d in range(1, (j - i) % len(fases))]
        if not meio:
            raise ErroSeguranca(f"verde {i} seguido de verde {j} sem amarelo")
        if any(eh_verde(x) and eh_verde(y) for x, y in zip(fases[i][0], fases[j][0])):
            raise ErroSeguranca(f"link verde nas fases seguidas {i} e {j}: transicao exige revisao")
        amarelo, dur = fases[meio[0]][0], fases[meio[0]][1]
        if amarelo != amarelo_de(fases[i][0]):
            raise ErroSeguranca(f"amarelo do programa depois da fase {i} nao corresponde ao verde")
        if dur < 3:
            raise ErroSeguranca(f"amarelo de {dur} s depois da fase {i}")
        resto = meio[1:]
        if any(set(fases[m][0]) != {"r"} for m in resto):
            raise ErroSeguranca(f"fases intermediarias inesperadas depois da fase {i}")
        transicoes[i] = {"amarelo": amarelo, "duracao_amarelo": int(dur),
                         "vermelho_geral_programa": int(sum(fases[m][1] for m in resto))}
    duracoes = {t["duracao_amarelo"] for t in transicoes.values()}
    if len(duracoes) != 1:
        raise ErroSeguranca("amarelos com duracoes diferentes")
    return {"verdes": [fases[i][0] for i in verdes], "indices_xml": verdes, "transicoes": transicoes,
            "amarelo": duracoes.pop(),
            "vermelho_geral_programa": max(t["vermelho_geral_programa"] for t in transicoes.values())}


class SemaforosProtegidos:
    """Envolve conn.trafficlight: leituras livres, escritas so nos semaforos permitidos."""

    def __init__(self, tl, permitidos):
        self._tl, self._permitidos = tl, frozenset(permitidos)
        self.escritas = {t: 0 for t in self._permitidos}

    def __getattr__(self, nome):
        if not nome.startswith("set"):
            return getattr(self._tl, nome)

        def protegida(tls, *args, **kwargs):
            if tls not in self._permitidos:
                raise PermissionError(f"escrita {nome} recusada no semaforo nao controlado {tls}")
            self.escritas[tls] += 1
            return getattr(self._tl, nome)(tls, *args, **kwargs)
        return protegida


class ControladorFasesSeguro:
    """Maquina de estados de UM semaforo. Tempo em segundos inteiros (passo de 1 s).

    `tl` e o modulo trafficlight do TraCI (de preferencia protegido para so
    escrever neste semaforo). `foes` vem de insper_comum.foes_traci. A acao e o
    indice da fase verde (0..n_fases-1), como no Cologne8.
    """

    def __init__(self, tl, tls, agora, foes, registrar=None, verde_minimo=10,
                 vermelho_geral=2, intervalo_decisao=5, verde_maximo=60, conflitantes_ocupados=None):
        self.tl, self.id = tl, tls
        self.registrar = registrar or (lambda evento: None)
        self.conflitantes_ocupados = conflitantes_ocupados
        programa = tl.getProgram(tls)
        logica = next(l for l in tl.getAllProgramLogics(tls) if l.programID == programa)
        self.fases_programa = [(p.state, p.duration, p.minDur, p.maxDur) for p in logica.phases]
        self.plano = analisar_programa(self.fases_programa, foes)
        self.verdes = self.plano["verdes"]
        self.n_links = len(self.verdes[0])
        self.amarelo = self.plano["amarelo"]
        self.vermelho_geral = max(int(vermelho_geral), self.plano["vermelho_geral_programa"])
        self.verde_minimo, self.intervalo = int(verde_minimo), int(intervalo_decisao)
        self.verde_maximo = int(verde_maximo)
        if self.verde_minimo < 1 or self.intervalo < 1 or self.verde_maximo < self.verde_minimo:
            raise ErroSeguranca("tempos invalidos")
        self.trocas = self.recusas = self.intervencoes = 0
        self.ultimo_servico = [agora] * len(self.verdes[0])
        self.historico_verdes = []
        estado = tl.getRedYellowGreenState(tls)
        if len(estado) != self.n_links:
            raise ErroSeguranca("numero de links diferente do programa")
        if estado in self.verdes:
            self.fase = self.verdes.index(estado)
            self.estagio = VERDE
            gasto = int(round(tl.getSpentDuration(tls)))
            self.inicio_verde = agora - gasto
            self.proxima = max(agora, self.inicio_verde + self.verde_minimo)
            self.limite = math.inf
            self._aplicar(agora, estado, "assumir_verde_em_curso", gasto_s=gasto)
        else:
            indice = tl.getPhase(tls)
            if self.fases_programa[indice][0] != estado or "y" not in estado:
                raise ErroSeguranca(f"estado ao assumir nao e verde nem amarelo do programa: {estado}")
            anterior = max(i for i in self.plano["indices_xml"] if i < indice) if any(
                i < indice for i in self.plano["indices_xml"]) else self.plano["indices_xml"][-1]
            if self.plano["transicoes"][anterior]["amarelo"] != estado:
                raise ErroSeguranca("amarelo em curso nao corresponde ao verde anterior")
            k = self.plano["indices_xml"].index(anterior)
            self.fase = (k + 1) % len(self.verdes)  # o mesmo verde que o programa abriria
            self.estagio = AMARELO
            restante = int(math.ceil(tl.getNextSwitch(tls) - agora))
            gasto = int(round(tl.getSpentDuration(tls)))
            # getSpentDuration ja conta o segundo atual; se o amarelo ja completou, o
            # vermelho geral comeca agora (atualizar e chamado logo em seguida)
            self.limite = agora + max(0, self.amarelo - gasto, restante)
            self.proxima = math.inf
            self.inicio_verde = None
            self._aplicar(agora, estado, "assumir_amarelo_em_curso", gasto_s=gasto,
                          restante_s=self.limite - agora)

    # ------------------------------------------------------------------ escrita
    def _aplicar(self, agora, estado, motivo, **extra):
        self.tl.setRedYellowGreenState(self.id, estado)
        lido = self.tl.getRedYellowGreenState(self.id)
        if lido != estado:
            raise ErroSeguranca(f"{self.id}: SUMO exibiu {lido} em vez de {estado}")
        self.esperado = estado
        evento = {"tempo": agora, "tls": self.id, "estagio": self.estagio, "fase_alvo": self.fase,
                  "estado": estado, "motivo": motivo, **extra}
        if self.estagio == VERDE and motivo == "fim_vermelho_geral" and self.conflitantes_ocupados:
            evento["veiculos_em_conflitantes_ao_abrir"] = self.conflitantes_ocupados(self.id, estado)
        self.registrar(evento)

    # ------------------------------------------------------------------ relogio
    def atualizar(self, agora):
        """Chamar uma vez por segundo, ANTES do passo da simulacao."""
        if self.estagio == AMARELO and agora >= self.limite:
            if self.vermelho_geral > 0:
                self.estagio = VERMELHO
                self.limite = agora + self.vermelho_geral
                self._aplicar(agora, "r" * self.n_links, "fim_amarelo")
            else:
                self._abrir(agora)
        elif self.estagio == VERMELHO and agora >= self.limite:
            self._abrir(agora)
        if self.estagio == VERDE:
            for link, c in enumerate(self.verdes[self.fase]):
                if eh_verde(c):
                    self.ultimo_servico[link] = agora

    def _abrir(self, agora):
        self.estagio = VERDE
        self.inicio_verde = agora
        self.proxima = agora + self.verde_minimo
        self.limite = math.inf
        self._aplicar(agora, self.verdes[self.fase], "fim_vermelho_geral")

    def pode_decidir(self, agora):
        return self.estagio == VERDE and agora >= self.proxima

    def proteger(self, pedida, agora, demanda_por_link):
        """Mesma protecao do Cologne8 (RelogioLocal.proteger): depois de `verde_maximo` s,
        manter o verde com veiculos esperando em links vermelhos e substituido pela fase
        que atende o link ha mais tempo sem verde (desempate: mais veiculos, menor indice).
        Devolve (acao executada, houve_intervencao)."""
        if not self.pode_decidir(agora) or pedida != self.fase or agora - self.inicio_verde < self.verde_maximo:
            return pedida, False
        verde = self.verdes[self.fase]
        nao_atendidos = {l: n for l, n in demanda_por_link.items() if n and not eh_verde(verde[l])}
        candidatos = []
        for i, outro in enumerate(self.verdes):
            links = [l for l in nao_atendidos if eh_verde(outro[l])]
            if i != self.fase and links:
                candidatos.append((max(agora - self.ultimo_servico[l] for l in links),
                                   sum(nao_atendidos[l] for l in links), -i, i))
        if not candidatos:
            return pedida, False
        self.intervencoes += 1
        return max(candidatos)[-1], True

    def pedir(self, acao, agora):
        """Pedido da politica. Devolve o motivo; nunca viola os tempos de seguranca."""
        if not isinstance(acao, int) or not 0 <= acao < len(self.verdes):
            self.recusas += 1
            return "recusada_acao_invalida"
        if self.estagio != VERDE:
            self.recusas += 1
            return "recusada_em_transicao"
        if agora - self.inicio_verde < self.verde_minimo:
            self.recusas += 1
            return "recusada_verde_minimo"
        if agora < self.proxima:
            self.recusas += 1
            return "recusada_fora_do_intervalo"
        if acao == self.fase:
            self.proxima = agora + self.intervalo
            return "mantida"
        self.historico_verdes.append(agora - self.inicio_verde)
        antigo = self.verdes[self.fase]
        self.fase = acao
        self.estagio = AMARELO
        self.limite = agora + self.amarelo
        self.proxima = math.inf
        self.trocas += 1
        self._aplicar(agora, amarelo_de(antigo), "troca_pedida", verde_anterior_s=self.historico_verdes[-1])
        return "troca_iniciada"

    def conferir(self, agora):
        """Chamar DEPOIS do passo: o SUMO deve continuar exibindo o estado aplicado."""
        lido = self.tl.getRedYellowGreenState(self.id)
        if lido != self.esperado:
            raise ErroSeguranca(f"{self.id} em {agora}: SUMO exibe {lido}, esperado {self.esperado}")
        return lido

    def idade_verde(self, agora):
        return agora - self.inicio_verde if self.estagio == VERDE else 0
