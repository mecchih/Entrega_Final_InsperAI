"""Modelo C - Parameter Sharing: UMA Double DQN para os tres agentes locais do corredor Insper.

Reaproveita sem alterar:
  - DoubleDQN / Replay de semaforo/scripts/agente_marl_cologne.py (mesma rede 13 -> 64 -> 64 -> 2,
    Adam 5e-4, lote 64, Huber, gamma 0,95^(dt/5), alvo a cada 500 gradientes);
  - o ambiente da otimizacao final (otimizacao_final/ambiente_marl_insper_v2.py) no modo
    "independente": continuam 3 agentes, cada um com sua observacao, sua decisao, sua recompensa
    e o seu controlador seguro. So os PESOS e o REPLAY sao comuns.

Representacao canonica (verificada em orientacao_canonica()):
  no vetor local de 13 entradas, as 2 aproximacoes aparecem na ordem alfabetica do id da via.
  Nos 3 cruzamentos a aproximacao do slot 0 e servida pela fase verde 1 e a do slot 1 pela fase 0
  (relacao slot <-> fase consistente), mas a RUA muda: em Gomes de Carvalho e Quata o slot 0 e a
  Ribeirao Claro; em Casa do Ator o slot 0 e a transversal. Para que a mesma rede veja sempre
  "slot 0 = corredor (Ribeirao Claro), slot 1 = transversal; acao 1 = verde do corredor,
  acao 0 = verde da transversal", a visao de Casa do Ator permuta filas, carros, fase one-hot e
  maior espera e traduz a acao (real = 1 - canonica). E uma bijecao entre as duas fases verdes do
  proprio programa: o controlador seguro, que recebe a acao REAL, continua impondo todas as regras.

Orcamento igual ao de UM agente do Modelo A por rede (para separar o efeito do compartilhamento
do efeito de "mais treino"): com N agentes aprendizes, o replay tem N x 50 mil posicoes, o
aquecimento N x 2000 transicoes, o epsilon decai em N x 40 mil decisoes (o mesmo ritmo por agente)
e ha UM passo de gradiente a cada N transicoes guardadas. Assim a rede compartilhada recebe o
mesmo numero de atualizacoes que cada rede do Modelo A, mas com dados dos N cruzamentos.
"""

from pathlib import Path
import sys

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI.parent / "otimizacao_final"))
sys.path.insert(1, str(AQUI.parents[1] / "scripts"))
import insper_comum as ic  # noqa: E402

FORMATO = "smartflow_marl_insper_parameter_sharing_v1"
TLS = list(ic.CONTROLADOS)
N_LOCAL, ACOES = 13, 2
CORREDOR = "Rua Ribeirão Claro"
PERMUTACAO_OBS = [1, 0, 3, 2, 5, 4, 6, 8, 7, 9, 10, 11, 12]  # troca os slots 0 <-> 1 (filas, carros, fase, espera)
POR_AGENTE = {"replay": 50_000, "aquecimento": 2000, "decaimento": 40_000}


def orientacao_canonica(net=None):
    """{tls: True se a visao precisa permutar}. Confere, pela rede, que em todos os cruzamentos o slot
    da aproximacao j e servido pela fase 1 - j e que existe exatamente uma aproximacao do corredor."""
    if net is None:
        ic.sumo_home()
        import sumolib
        net = sumolib.net.readNet(str(ic.REDE), withPrograms=True)
    saida = {}
    for t in TLS:
        tl = net.getTLS(t)
        con = sorted(tl.getConnections(), key=lambda c: c[2])
        prog = list(tl.getPrograms().values())[0]
        verdes = [p.state for p in prog.getPhases() if "y" not in p.state]
        entradas = sorted({i.getEdge().getID() for i, o, li in con})
        if len(entradas) != 2 or len(verdes) != 2:
            raise RuntimeError(f"{t}: esperadas 2 aproximacoes e 2 fases verdes")
        for j, e in enumerate(entradas):
            links = [li for i, o, li in con if i.getEdge().getID() == e]
            fases = [k for k, v in enumerate(verdes) if any(v[li] in "Gg" for li in links)]
            if fases != [1 - j]:
                raise RuntimeError(f"{t}: slot {j} servido pelas fases {fases}; representacao incompativel")
        corredor = [j for j, e in enumerate(entradas) if net.getEdge(e).getName() == CORREDOR]
        if len(corredor) != 1:
            raise RuntimeError(f"{t}: aproximacao do corredor ambigua {corredor}")
        saida[t] = corredor[0] == 1
    return saida


def criar_rede(semente, n_aprendizes=3):
    import torch  # noqa: F401
    from agente_marl_cologne import DoubleDQN, Replay

    class DoubleDQNCompartilhada(DoubleDQN):
        """A DoubleDQN original com replay e cronogramas escalados por n_aprendizes e um gradiente
        a cada n_aprendizes transicoes. Nenhuma mudanca na rede nem no passo de gradiente."""

        def __init__(self):
            super().__init__(N_LOCAL, ACOES, semente, aquecimento=POR_AGENTE["aquecimento"] * n_aprendizes)
            self.n_aprendizes = n_aprendizes
            self.decaimento = POR_AGENTE["decaimento"] * n_aprendizes
            self.memoria = Replay(N_LOCAL, POR_AGENTE["replay"] * n_aprendizes)
            self.transicoes = 0
            self.transicoes_por_agente = [0] * len(TLS)

        def lembrar_de(self, k, s, a, r, s2, dt, fim, treinando):
            if not treinando:
                return
            self.transicoes += 1
            self.transicoes_por_agente[k] += 1
            if self.transicoes % self.n_aprendizes:
                if not 0 <= a < self.acoes:
                    raise ValueError("Acao fora da rede local")
                self.memoria.adicionar(s, a, r, s2, dt, fim)
                return
            super().lembrar(s, a, r, s2, dt, fim, treinando)  # guarda e faz UM passo de gradiente

        def estado(self, completo=False):
            d = super().estado(completo)
            d.update(n_aprendizes=self.n_aprendizes, transicoes=self.transicoes,
                     transicoes_por_agente=list(self.transicoes_por_agente))
            return d

        def carregar(self, dados, completo=False):
            if dados.get("n_aprendizes") != self.n_aprendizes:
                raise ValueError("checkpoint com outro numero de agentes aprendizes")
            super().carregar(dados, completo)
            self.transicoes = dados["transicoes"]
            self.transicoes_por_agente = list(dados["transicoes_por_agente"])

    return DoubleDQNCompartilhada()


def regra_atuada_obs(estado):
    """Controle classico simples usado SO no cruzamento retirado do treino (experimento de transferencia):
    le a observacao local (em unidades reais) e mantem o verde enquanto a aproximacao servida tem
    veiculos; senao troca se a outra tem. O controlador seguro aplica verde min/max e entreverdes."""
    filas = [estado[0] * 25, estado[1] * 25]
    carros = [estado[2] * 35, estado[3] * 35]
    fase = 0 if estado[4] > 0.5 else 1 if estado[5] > 0.5 else None
    if fase is None:  # em amarelo/vermelho geral nao ha decisao elegivel; mantem a fase 0 por convencao
        return 0
    servido, outro = 1 - fase, fase
    if carros[servido] > 0 or filas[servido] > 0:
        return fase
    return 1 - fase if carros[outro] > 0 else fase


class VisaoAgente:
    """O agente k do corredor. Decide sozinho, com a rede compartilhada, a partir da propria observacao."""

    acoes = ACOES

    def __init__(self, rede, k, permutar, aprende=True, regra=None):
        self.rede, self.k, self.permutar, self.aprende, self.regra = rede, k, permutar, aprende, regra
        self.intervencoes = 0
        self.decisoes_proprias = 0

    # conversoes entre o referencial do cruzamento e o canonico
    def canon(self, v):
        import numpy as np
        v = np.asarray(v, dtype=np.float32)
        return v[PERMUTACAO_OBS] if self.permutar else v

    def acao_real(self, a):
        return 1 - int(a) if self.permutar else int(a)

    acao_canonica = acao_real  # a traducao e uma involucao

    def escolher(self, estado, treinando):
        self.decisoes_proprias += 1
        if self.regra is not None:
            return int(self.regra(list(estado))), [0.0, 0.0], False
        a, q, explorou = self.rede.escolher(self.canon(estado), treinando)
        return self.acao_real(a), (q[::-1] if self.permutar else q), explorou

    def lembrar(self, s, a, r, s2, dt, fim, treinando):
        if not self.aprende:
            return
        # `a` e a acao EXECUTADA (depois da protecao de verde maximo), no referencial do cruzamento
        self.rede.lembrar_de(self.k, self.canon(s), self.acao_canonica(a), r, self.canon(s2), dt, fim, treinando)

    # atributos lidos pelo treino/relatorios
    @property
    def memoria(self):
        return self.rede.memoria

    @property
    def gradientes(self):
        return self.rede.gradientes

    @property
    def perdas(self):
        return self.rede.perdas

    @property
    def epsilon(self):
        return self.rede.epsilon


def criar_agentes(semente, aprendizes=(0, 1, 2), orientacao=None):
    """3 visoes sobre UMA rede. Os cruzamentos fora de `aprendizes` usam regra_atuada_obs e nao
    alimentam o replay (experimento de transferencia)."""
    orientacao = orientacao or orientacao_canonica()
    rede = criar_rede(semente, n_aprendizes=len(aprendizes))
    visoes = [VisaoAgente(rede, k, orientacao[t], aprende=k in aprendizes,
                          regra=None if k in aprendizes else regra_atuada_obs) for k, t in enumerate(TLS)]
    return rede, visoes


def visoes_avaliacao(rede, orientacao=None):
    """Para avaliacao (pesos congelados): os 3 cruzamentos usam a politica compartilhada."""
    orientacao = orientacao or orientacao_canonica()
    return [VisaoAgente(rede, k, orientacao[t], aprende=False) for k, t in enumerate(TLS)]


def salvar(path, rede, semente, episodio, completo, config, aprendizes):
    import torch
    with Path(path).open("xb") as f:
        torch.save({"formato": FORMATO, "config": config, "semente_modelo": semente, "episodio": episodio,
                    "aprendizes": list(aprendizes), "tls": TLS, "orientacao": orientacao_canonica(),
                    "completo_para_retomada": completo, "rede": rede.estado(completo)}, f)


def carregar(path):
    import torch
    d = torch.load(path, map_location="cpu", weights_only=False)
    if d["formato"] != FORMATO:
        raise ValueError("checkpoint de outro formato")
    rede = criar_rede(d["semente_modelo"], n_aprendizes=len(d["aprendizes"]))
    rede.carregar(d["rede"], completo=d["completo_para_retomada"])
    return d, rede
