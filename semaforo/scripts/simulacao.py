"""
O motor do projeto.

Aqui mora a parte que nao muda: abrir o SUMO, perguntar ao controlador qual
aproximacao deve ficar verde, trocar as fases com seguranca (amarelo e
vermelho geral entre fases) e medir o resultado.

Qualquer controlador -- tempo fixo, Max-Pressure ou, mais pra frente, o DQN --
entra pelo mesmo encaixe. Isso e o que torna a comparacao justa: todos
enxergam a mesma coisa, decidem no mesmo ritmo e sao medidos do mesmo jeito.
"""

import os
import xml.etree.ElementTree as ET

# libsumo roda o simulador dentro do proprio Python: ~8x mais rapido que o
# traci normal. Em troca, nao abre a janela grafica -- o que e exatamente o
# que queremos durante os experimentos. Para gravar o video da apresentacao,
# e so rodar depois com o traci + sumo-gui.
try:
    import libsumo as trafego

    USANDO_LIBSUMO = True
except ImportError:  # pragma: no cover
    import traci as trafego

    USANDO_LIBSUMO = False


PASTA = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REDE = os.path.join(PASTA, "rede", "cruzamento.net.xml")

# Regras de seguranca do semaforo (iguais para todos os controladores)
AMARELO = 3  # segundos de amarelo ao trocar de fase
VERMELHO_GERAL = 2  # segundos com tudo vermelho, para limpar o cruzamento
VERDE_MINIMO = 10  # ninguem recebe verde por menos que isso
INTERVALO_DECISAO = 5  # de quantos em quantos segundos o controlador decide

# As quatro aproximacoes e as faixas de entrada de cada uma.
# A ordem e a mesma das fases verdes do semaforo gerado pelo netgenerate.
APROXIMACOES = ["N", "L", "S", "O"]
FAIXAS_ENTRADA = {
    "N": ["top0A0_0", "top0A0_1"],
    "L": ["right0A0_0", "right0A0_1"],
    "S": ["bottom0A0_0", "bottom0A0_1"],
    "O": ["left0A0_0", "left0A0_1"],
}
# Vias de saida, usadas pelo Max-Pressure para medir a fila do outro lado
VIAS_SAIDA = {
    "N": ["A0bottom0_0", "A0bottom0_1", "A0left0_0", "A0left0_1",
          "A0right0_0", "A0right0_1"],
    "L": ["A0left0_0", "A0left0_1", "A0top0_0", "A0top0_1",
          "A0bottom0_0", "A0bottom0_1"],
    "S": ["A0top0_0", "A0top0_1", "A0right0_0", "A0right0_1",
          "A0left0_0", "A0left0_1"],
    "O": ["A0right0_0", "A0right0_1", "A0bottom0_0", "A0bottom0_1",
          "A0top0_0", "A0top0_1"],
}
SEMAFORO = "A0"


class Observacao:
    """O que o controlador ve no momento de decidir.

    Importante: tudo aqui e informacao que um semaforo real conseguiria ter
    com sensores no asfalto. Nada de "espiar" o futuro.
    """

    def __init__(self, filas, carros, espera, aprox_verde, tempo_no_verde,
                 filas_saida, segundo, fila_acumulada=0.0, espera_acumulada=0.0,
                 excesso_acumulado=0.0, maior_espera=None):
        self.filas = filas  # carros parados por aproximacao
        self.carros = carros  # carros presentes por aproximacao
        self.espera = espera  # espera acumulada (s) por aproximacao
        self.aprox_verde = aprox_verde  # qual aproximacao esta com verde
        self.tempo_no_verde = tempo_no_verde  # ha quantos segundos
        self.filas_saida = filas_saida  # filas nas vias de saida
        self.segundo = segundo  # momento da simulacao
        # Soma de (carros parados) a cada segundo desde o inicio da rodada.
        # A diferenca entre duas decisoes = "carros x segundos de fila" no
        # intervalo. E isso que faz o agente SENTIR o custo de trocar de fase:
        # durante o amarelo e o vermelho geral ninguem anda, e a conta sobe.
        self.fila_acumulada = fila_acumulada
        self.espera_acumulada = espera_acumulada
        # (so para controladores com espera_limite, ex.: recompensa
        # fila_excesso) soma, segundo a segundo, dos carros parados nas vias
        # de entrada cuja espera acumulada ja passou do limite W. A
        # diferenca entre duas decisoes = "segundos parados alem de W".
        # Fica 0 para todos os outros controladores.
        self.excesso_acumulado = excesso_acumulado
        # (so para controladores com observa_espera = True, ex.: DQN de 17
        # entradas) por aproximacao, a MAIOR espera acumulada (s) entre os
        # carros presentes nas faixas de entrada -- getAccumulatedWaitingTime,
        # que nao zera quando o carro anda um pouco. 0 se a aproximacao esta
        # vazia. None para todos os outros controladores.
        self.maior_espera = maior_espera


class Controlador:
    """Molde de qualquer semaforo. So precisa responder uma pergunta:
    qual aproximacao deve ficar verde agora?"""

    nome = "generico"

    def preparar(self, cenario):
        """Chamado uma vez antes da simulacao (para calcular tempos, etc.)."""
        pass

    def decidir(self, obs):
        raise NotImplementedError

    def reiniciar(self):
        """Chamado no inicio de cada rodada."""
        pass


def _fases_verdes():
    """Descobre no semaforo quais fases sao de verde (e nao amarelo)."""
    logicas = trafego.trafficlight.getAllProgramLogics(SEMAFORO)
    fases = logicas[0].phases
    verdes, amarelas = [], []
    for i, fase in enumerate(fases):
        estado = fase.state
        if "y" in estado.lower():
            amarelas.append(i)
        elif "g" in estado.lower():
            verdes.append(i)
    return verdes, amarelas


def _estado_amarelo(estado_verde):
    """Transforma um estado de verde no amarelo correspondente."""
    return "".join("y" if c in "Gg" else c for c in estado_verde)


def _estado_tudo_vermelho(tamanho):
    return "r" * tamanho


class Dinamica:
    """Opcoes de dinamica do semaforo. O padrao (tudo desligado) e a dinamica
    ORIGINAL: a usada no treino das DQNs e em avaliacao_final.json.

    transicao_corrigida: na dinamica original, (1) o amarelo so comeca no
        segundo SEGUINTE ao pedido de troca -- o verde ganha 1 s alem do que
        o controlador contou -- e (2) o verde novo e ligado no mesmo segundo
        em que o vermelho geral termina, o que come 1 dos 2 s de vermelho.
        Corrigida: o amarelo comeca no proprio segundo da decisao, o vermelho
        geral dura os 2 s inteiros e tempo_no_verde conta exatamente os
        segundos de verde ja executados.
    verde_maximo: regra de seguranca independente do controlador. Se o
        controlador pedir para MANTER um verde que ja durou verde_maximo
        segundos e houver carro em outra aproximacao, o simulador troca
        mesmo assim, para a aproximacao com carro que esta ha mais tempo sem
        verde. None desliga a regra.
    filas_no_escoamento: na dinamica original, a fila acumulada que o
        controlador recebe na observacao (e da qual sai a recompensa da DQN)
        so e somada durante a hora de demanda. No escoamento ela congela, e
        toda decisao ali tem recompensa ZERO -- mesmo com carro parado.
        Ligado, a soma continua no escoamento. Nao muda nenhuma metrica
        (fila_media continua sendo so da hora) nem o comportamento dos
        controladores tradicionais; muda so o sinal de recompensa do treino.
    """

    def __init__(self, transicao_corrigida=False, verde_maximo=None, nome=None,
                 filas_no_escoamento=False):
        self.transicao_corrigida = transicao_corrigida
        self.verde_maximo = verde_maximo
        self.filas_no_escoamento = filas_no_escoamento
        self.nome = nome or (
            f"transicao {'corrigida' if transicao_corrigida else 'original'}, "
            f"verde maximo {verde_maximo if verde_maximo else 'desligado'}")

    def original(self):
        return (not self.transicao_corrigida and self.verde_maximo is None
                and not self.filas_no_escoamento)


# As tres configuracoes comparadas em avaliar_seguranca.py
VERDE_MAXIMO_PADRAO = 60
DINAMICAS = {
    "A": Dinamica(nome="A: original"),
    "B": Dinamica(verde_maximo=VERDE_MAXIMO_PADRAO,
                  nome="B: original + verde maximo"),
    # C tambem mede a fila acumulada no escoamento (so afeta a recompensa)
    "C": Dinamica(transicao_corrigida=True, verde_maximo=VERDE_MAXIMO_PADRAO,
                  filas_no_escoamento=True,
                  nome="C: transicao corrigida + verde maximo"),
}

VIAS_ENTRADA = {f.rsplit("_", 1)[0] for faixas in FAIXAS_ENTRADA.values() for f in faixas}

# Janela da espera acumulada do SUMO (--waiting-time-memory). O padrao do
# SUMO e 100 s: a espera "esquece" o que passou de 100 s atras, e um carro
# parado ha 150 s apareceria com 100. Com 10000 s (mais que uma rodada
# inteira, 3600 + ate 1200 s), getAccumulatedWaitingTime e o total de
# segundos parado desde que o carro entrou -- o mesmo waitingTime do tripinfo.
MEMORIA_ESPERA = 10000


class MedidorExcesso:
    """Mede, segundo a segundo, o excesso de espera: para cada carro numa via
    de entrada, max(0, espera acumulada - W). Soma so os AUMENTOS desse valor,
    ou seja, cada segundo que um carro ja acima de W passa parado vale 1.

    So le o SUMO (assinatura de variaveis dos veiculos), nao muda nada da
    simulacao. A espera acumulada nao zera quando o carro anda um pouco na
    fila (getWaitingTime zera; getAccumulatedWaitingTime, nao).
    """

    def __init__(self, limite):
        import traci.constants as tc
        self.limite = float(limite)
        self._vars = (tc.VAR_ROAD_ID, tc.VAR_ACCUMULATED_WAITING_TIME)
        self.total = 0.0
        self._por_carro = {}

    def passo(self):
        """Chamar logo depois de cada simulationStep."""
        via_id, espera_id = self._vars
        for v in trafego.simulation.getDepartedIDList():
            trafego.vehicle.subscribe(v, list(self._vars))
        for v, r in trafego.vehicle.getAllSubscriptionResults().items():
            if r.get(via_id) not in VIAS_ENTRADA:
                continue
            novo = max(0.0, r[espera_id] - self.limite)
            antigo = self._por_carro.get(v, 0.0)
            if novo > antigo:
                self.total += novo - antigo
            self._por_carro[v] = novo


def rodar(controlador, cenario, arquivo_rotas, seed, duracao=3600,
          guardar_serie=False, instrumentacao=None, dinamica=None):
    """Roda uma rodada completa e devolve as metricas.

    cenario: nome do cenario (usado pelo controlador para se preparar)
    seed: muda o sorteio de chegada dos carros -- rodadas diferentes,
          mesmo cenario
    instrumentacao: opcional. Objeto que so OBSERVA a rodada (usado pela
          analise de comportamento). Recebe, a cada segundo, o estado do
          semaforo que o SUMO vai de fato executar; cada decisao executada
          (ja com a regra de seguranca aplicada); e o tripinfo antes de ser
          apagado. Nao altera nada da simulacao. Com None (o padrao), a
          rodada e identica a original.
          Metodos esperados: inicio(estados_verdes, duracao),
          passo(segundo, estado), decisao(obs, escolha), fim(caminho_tripinfo).
          Opcional: intervencao(obs, escolha_do_controlador, escolha_final).
    dinamica: opcional, um objeto Dinamica. None = dinamica original e as
          mesmas metricas de sempre. Com um Dinamica (mesmo o original),
          a rodada devolve tambem as metricas extras de seguranca.
    """
    din = dinamica if dinamica is not None else Dinamica()
    corrigida = din.transicao_corrigida
    tripinfo = os.path.join(PASTA, "resultados", f"_tmp_tripinfo_{os.getpid()}.xml")

    comando = [
        "sumo",
        "-n", REDE,
        "-r", arquivo_rotas,
        "--tripinfo-output", tripinfo,
        "--tripinfo-output.write-unfinished",  # conta tambem quem ficou preso
        "--seed", str(seed),
        "--time-to-teleport", "-1",  # desliga o "teletransporte" de carro preso
        "--waiting-time-memory", str(MEMORIA_ESPERA),
        "--no-step-log", "true",
        "--no-warnings", "true",
        "--duration-log.disable", "true",
    ]

    trafego.start(comando)
    controlador.preparar(cenario)
    controlador.reiniciar()

    verdes, _ = _fases_verdes()
    logicas = trafego.trafficlight.getAllProgramLogics(SEMAFORO)
    estados_verdes = [logicas[0].phases[i].state for i in verdes]
    tamanho_estado = len(estados_verdes[0])

    # Estado interno do semaforo
    indice_verde = 0  # qual aproximacao esta com verde (0=N, 1=L, 2=S, 3=O)
    tempo_no_verde = 0
    transicao = []  # fila de (estado, segundos) a executar antes do proximo verde
    proximo_verde = None
    verde_pendente = False  # (corrigida) transicao acabou: verde no proximo segundo
    fim_ultimo_verde = [0] * len(APROXIMACOES)  # para a regra de seguranca
    intervencoes = []  # segundos em que a regra de seguranca trocou a fase

    trafego.trafficlight.setRedYellowGreenState(SEMAFORO, estados_verdes[0])
    if instrumentacao is not None:
        instrumentacao.inicio(estados_verdes, duracao)

    serie_filas = []
    soma_filas = 0
    soma_espera = 0.0
    # (filas_no_escoamento) o que se acumula DEPOIS da hora: entra na
    # observacao, mas nao em fila_media
    filas_escoamento = 0
    espera_escoamento = 0.0
    segundo = 0
    # excesso de espera: so se o controlador pedir (recompensa fila_excesso)
    espera_limite = getattr(controlador, "espera_limite", None)
    excesso = MedidorExcesso(espera_limite) if espera_limite is not None else None
    # maior espera por aproximacao na observacao: so se o controlador pedir
    observa_espera = bool(getattr(controlador, "observa_espera", False))

    def executar_transicao():
        """Executa 1 segundo da transicao pendente (amarelo / vermelho geral)."""
        nonlocal indice_verde, tempo_no_verde, verde_pendente
        estado, resta = transicao[0]
        trafego.trafficlight.setRedYellowGreenState(SEMAFORO, estado)
        resta -= 1
        if resta <= 0:
            transicao.pop(0)
            if not transicao:
                if corrigida:
                    # o ultimo segundo de vermelho geral fica vermelho; o
                    # verde novo so e ligado no segundo seguinte
                    verde_pendente = True
                else:
                    indice_verde = proximo_verde
                    tempo_no_verde = 0
                    trafego.trafficlight.setRedYellowGreenState(
                        SEMAFORO, estados_verdes[indice_verde]
                    )
        else:
            transicao[0] = (estado, resta)

    def protecao(obs, escolha, t):
        """Regra de seguranca: limita o verde quando ha demanda em outro lado."""
        if (din.verde_maximo is None or escolha != indice_verde
                or obs.tempo_no_verde < din.verde_maximo):
            return escolha
        candidatos = [i for i, a in enumerate(APROXIMACOES)
                      if i != indice_verde and obs.carros[a] > 0]
        if not candidatos:
            return escolha
        # quem esta ha mais tempo sem verde; empate: maior fila; depois ordem do ciclo
        return min(candidatos, key=lambda i: (
            fim_ultimo_verde[i], -obs.filas[APROXIMACOES[i]],
            (i - indice_verde) % len(APROXIMACOES)))

    def decidir(t):
        """Pergunta ao controlador; devolve True se uma troca foi iniciada."""
        nonlocal proximo_verde, transicao
        obs = _ler_observacao(indice_verde, tempo_no_verde, t,
                              soma_filas + filas_escoamento,
                              soma_espera + espera_escoamento,
                              excesso.total if excesso is not None else 0.0,
                              observa_espera)
        pedido = controlador.decidir(obs)
        escolha = protecao(obs, pedido, t)
        if escolha != pedido:
            intervencoes.append(t)
            # avisa o controlador de que a acao EXECUTADA nao foi a pedida
            # (um agente que aprende precisa disso para nao atribuir as
            # consequencias da troca forcada a acao que ele pediu)
            if hasattr(controlador, "acao_substituida"):
                controlador.acao_substituida(pedido, escolha)
            if instrumentacao is not None and hasattr(instrumentacao, "intervencao"):
                instrumentacao.intervencao(obs, pedido, escolha)
        if instrumentacao is not None:
            instrumentacao.decisao(obs, escolha)
        if escolha != indice_verde:
            proximo_verde = escolha
            fim_ultimo_verde[indice_verde] = t
            transicao = [
                (_estado_amarelo(estados_verdes[indice_verde]), AMARELO),
                (_estado_tudo_vermelho(tamanho_estado), VERMELHO_GERAL),
            ]
            return True
        return False

    def controlar(t, alinhado):
        """Tudo que acontece antes de simular o segundo t. Devolve True se o
        segundo t sera de verde (usado so na transicao corrigida)."""
        nonlocal indice_verde, tempo_no_verde, verde_pendente
        if not corrigida:
            # --- dinamica original, passo a passo como sempre foi ---
            if transicao:
                executar_transicao()
            else:
                tempo_no_verde += 1
                if tempo_no_verde >= VERDE_MINIMO and alinhado:
                    decidir(t)
            return None
        # --- transicao corrigida ---
        if transicao:
            executar_transicao()
            return False
        if verde_pendente:
            indice_verde = proximo_verde
            tempo_no_verde = 0
            verde_pendente = False
            trafego.trafficlight.setRedYellowGreenState(
                SEMAFORO, estados_verdes[indice_verde])
        # tempo_no_verde = segundos de verde JA executados
        if tempo_no_verde >= VERDE_MINIMO and alinhado and decidir(t):
            executar_transicao()  # o amarelo comeca neste mesmo segundo
            return False
        return True

    # medicao do verde realmente executado (so com dinamica explicita)
    medir = dinamica is not None
    verde_seguido = {"estado": None, "dur": 0, "max_hora": 0, "max_total": 0}

    def medir_estado(t):
        e = trafego.trafficlight.getRedYellowGreenState(SEMAFORO)
        if e in estados_verdes and e == verde_seguido["estado"]:
            verde_seguido["dur"] += 1
        elif e in estados_verdes:
            verde_seguido["estado"], verde_seguido["dur"] = e, 1
        else:
            verde_seguido["estado"], verde_seguido["dur"] = None, 0
        verde_seguido["max_total"] = max(verde_seguido["max_total"], verde_seguido["dur"])
        if t < duracao:
            verde_seguido["max_hora"] = max(verde_seguido["max_hora"], verde_seguido["dur"])

    while segundo < duracao:
        e_verde = controlar(segundo, segundo % INTERVALO_DECISAO == 0)

        if medir:
            medir_estado(segundo)
        if instrumentacao is not None:
            instrumentacao.passo(
                segundo, trafego.trafficlight.getRedYellowGreenState(SEMAFORO))
        trafego.simulationStep()
        segundo += 1
        if e_verde:
            tempo_no_verde += 1
        if excesso is not None:
            excesso.passo()

        fila_total = sum(
            trafego.lane.getLastStepHaltingNumber(f)
            for faixas in FAIXAS_ENTRADA.values()
            for f in faixas
        )
        soma_filas += fila_total
        soma_espera += sum(
            trafego.lane.getWaitingTime(f)
            for faixas in FAIXAS_ENTRADA.values()
            for f in faixas
        )
        if guardar_serie:
            serie_filas.append(fila_total)

    # deixa o transito restante escoar, para nao premiar quem empurrou
    # o problema para o fim da simulacao
    extra = 0
    while trafego.simulation.getMinExpectedNumber() > 0 and extra < 1200:
        e_verde = controlar(duracao + extra, extra % INTERVALO_DECISAO == 0)
        if medir:
            medir_estado(duracao + extra)
        if instrumentacao is not None:
            instrumentacao.passo(
                duracao + extra,
                trafego.trafficlight.getRedYellowGreenState(SEMAFORO))
        trafego.simulationStep()
        extra += 1
        if e_verde:
            tempo_no_verde += 1
        if excesso is not None:  # o excesso continua sendo medido no escoamento
            excesso.passo()
        if din.filas_no_escoamento:
            filas_escoamento += sum(
                trafego.lane.getLastStepHaltingNumber(f)
                for faixas in FAIXAS_ENTRADA.values()
                for f in faixas
            )
            espera_escoamento += sum(
                trafego.lane.getWaitingTime(f)
                for faixas in FAIXAS_ENTRADA.values()
                for f in faixas
            )

    if hasattr(controlador, "encerrar"):
        controlador.encerrar()

    if medir:
        # quem ainda nao terminou: na fila de entrada (nem entrou na rede),
        # dentro da rede antes da linha de retencao, ou ja depois dela
        aguardando_entrada = len(trafego.simulation.getPendingVehicles())
        na_rede = list(trafego.vehicle.getIDList())
        antes_da_retencao = sum(
            1 for v in na_rede if trafego.vehicle.getRoadID(v) in VIAS_ENTRADA)

    trafego.close()

    if instrumentacao is not None:
        instrumentacao.fim(tripinfo)
    metricas = _ler_tripinfo(tripinfo)
    metricas["fila_media"] = soma_filas / duracao
    metricas["segundos_escoamento"] = extra
    if guardar_serie:
        metricas["serie_filas"] = serie_filas
    if medir:
        metricas.update(_ler_tripinfo_concluidas(tripinfo))
        metricas.update({
            "dinamica": din.nome,
            "veiculos_na_rede_no_fim": len(na_rede),
            "veiculos_aguardando_entrada_no_fim": aguardando_entrada,
            # nunca passaram pela linha de retencao = nunca foram atendidos
            "veiculos_sem_atendimento": antes_da_retencao + aguardando_entrada,
            "escoamento_cortado": bool(
                extra >= 1200 and (len(na_rede) + aguardando_entrada) > 0),
            "verde_max_executado_hora": verde_seguido["max_hora"],
            "verde_max_executado_total": verde_seguido["max_total"],
            "intervencoes_seguranca_hora": sum(1 for t in intervencoes if t < duracao),
            "intervencoes_seguranca_escoamento": sum(1 for t in intervencoes if t >= duracao),
        })
    if os.path.exists(tripinfo):
        os.remove(tripinfo)
    return metricas


def _ler_tripinfo_concluidas(caminho):
    """Separa quem terminou a viagem de quem foi interrompido pelo fim da
    simulacao (arrival = -1 no tripinfo). A espera de um interrompido e so
    um limite inferior, entao as estatisticas 'concluidas' nao o incluem."""
    if not os.path.exists(caminho):
        return {"veiculos_concluidos": 0, "veiculos_interrompidos": 0}
    esperas, interrompidos = [], 0
    for viagem in ET.parse(caminho).getroot():
        if float(viagem.get("arrival", -1)) < 0:
            interrompidos += 1
        else:
            esperas.append(float(viagem.get("waitingTime", 0)))
    ordenado = sorted(esperas)

    def pct(p):
        if not ordenado:
            return 0.0
        return ordenado[int(round((p / 100.0) * (len(ordenado) - 1)))]

    return {
        "veiculos_concluidos": len(esperas),
        "veiculos_interrompidos": interrompidos,
        "espera_media_concluidos": sum(esperas) / len(esperas) if esperas else 0.0,
        "espera_p95_concluidos": pct(95),
        "espera_max_concluidos": ordenado[-1] if ordenado else 0.0,
    }


def _ler_observacao(indice_verde, tempo_no_verde, segundo,
                    fila_acumulada=0.0, espera_acumulada=0.0, excesso_acumulado=0.0,
                    observa_espera=False):
    filas, carros, espera = {}, {}, {}
    for aprox, faixas in FAIXAS_ENTRADA.items():
        filas[aprox] = sum(
            trafego.lane.getLastStepHaltingNumber(f) for f in faixas
        )
        carros[aprox] = sum(
            trafego.lane.getLastStepVehicleNumber(f) for f in faixas
        )
        espera[aprox] = sum(
            trafego.lane.getWaitingTime(f) for f in faixas
        )
    filas_saida = {}
    for aprox, faixas in VIAS_SAIDA.items():
        filas_saida[aprox] = sum(
            trafego.lane.getLastStepHaltingNumber(f) for f in faixas
        )
    return Observacao(
        filas, carros, espera, APROXIMACOES[indice_verde],
        tempo_no_verde, filas_saida, segundo,
        fila_acumulada, espera_acumulada, excesso_acumulado,
        _maior_espera() if observa_espera else None,
    )


def _maior_espera():
    """Maior espera acumulada (s) por aproximacao, na ordem N, L, S, O.

    So os carros nas faixas de entrada (as mesmas da fila). Cada carro esta em
    uma faixa so, e o conjunto por aproximacao garante que nenhum e contado
    duas vezes. Aproximacao vazia = 0. Com --waiting-time-memory 10000 a
    espera acumulada e o total de segundos parado desde que o carro entrou."""
    out = {}
    for aprox, faixas in FAIXAS_ENTRADA.items():
        ids = {v for f in faixas for v in trafego.lane.getLastStepVehicleIDs(f)}
        out[aprox] = max((trafego.vehicle.getAccumulatedWaitingTime(v) for v in ids),
                         default=0.0)
    return out


def _ler_tripinfo(caminho):
    """Le o relatorio que o SUMO escreve com a viagem de cada carro."""
    if not os.path.exists(caminho):
        return {"n_carros": 0}

    esperas, duracoes, perdas = [], [], []
    tree = ET.parse(caminho)
    for viagem in tree.getroot():
        esperas.append(float(viagem.get("waitingTime", 0)))
        duracoes.append(float(viagem.get("duration", 0)))
        perdas.append(float(viagem.get("timeLoss", 0)))

    def media(v):
        return sum(v) / len(v) if v else 0.0

    def percentil(v, p):
        if not v:
            return 0.0
        ordenado = sorted(v)
        k = int(round((p / 100.0) * (len(ordenado) - 1)))
        return ordenado[k]

    return {
        "n_carros": len(esperas),
        "espera_media": media(esperas),
        "espera_p95": percentil(esperas, 95),
        "espera_max": max(esperas) if esperas else 0.0,
        "viagem_media": media(duracoes),
        "perda_media": media(perdas),
    }
