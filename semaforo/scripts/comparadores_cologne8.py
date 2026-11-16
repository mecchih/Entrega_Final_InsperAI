"""Comparadores para o MARL no Cologne8: classicos calibrados e aprendizado simples.

Todos os controladores rodam DENTRO do mesmo executor usado pelo MARL
(`ambiente_marl_cologne.rodar`, copia congelada da rodada 9f8d757b): mesma rede,
demanda, aquecimento, verde minimo de 10 s, decisao a cada 5 s, amarelo 3 s,
vermelho geral 2 s, protecao de verde > 60 s, colisoes em modo `warn` e as
mesmas metricas. So muda QUEM escolhe a fase.

Controladores:
  webster   - tempo fixo com ciclo/verdes de Webster por cruzamento (fluxos
              medidos nas sementes de validacao) e multiplicador de ciclo
              escolhido na validacao.
  atuado    - semaforo atuado por veiculo: estende o verde enquanto ha carros
              chegando nos movimentos verdes; troca para a proxima fase com demanda.
  mp        - Max-Pressure com verde minimo e histerese ajustados na validacao.
  imitacao  - rede neural (MLP 64-64) treinada por aprendizado SUPERVISIONADO
              para imitar o Max-Pressure ajustado (behavior cloning + DAgger),
              usando o mesmo vetor de observacao local do MARL.
  qlearning - Q-learning tabular, um agente por semaforo, estado discretizado.

Sementes: treino 1000+, validacao 201/202, teste 1..10 (iguais ao MARL).
Nenhuma escolha usa as sementes de teste.
"""

from collections import defaultdict
import argparse
import copy
import json
import math
import os
from pathlib import Path
import pickle
import random
import shutil
import time

import numpy as np

AQUI = Path(__file__).resolve().parent
os.environ.setdefault("SMARTFLOW_PROJETO", str(AQUI.parent))

from ambiente_marl_cologne import INICIO, FIM, construir_manifesto, rodar  # noqa: E402

PROJETO = Path(os.environ["SMARTFLOW_PROJETO"]).resolve()
SAIDA = PROJETO / "resultados" / "comparadores_cologne8"
TMP = Path(os.environ.get("COMPARADORES_TMP", "/tmp/comparadores_cologne8"))
VALIDACAO = [201, 202]
TESTE = list(range(1, 11))
MODO = "independente"  # qualquer modo != hierarquico/max_pressure/original_fixo usa agentes[i]


def manifesto():
    return construir_manifesto("cologne8", continuar_apos_colisao=True)


def conn():
    import libsumo
    return libsumo


# ---------------------------------------------------------------- base comum
class Base:
    """Interface do executor: escolher(estado, treinando) e lembrar(...)."""

    def __init__(self, esquema):
        self.esquema = esquema
        self.id = esquema["id"]
        self.E, self.P = len(esquema["entradas"]), esquema["n_acoes"]
        self.verdes = [p["state"] for p in esquema["fases"]]
        self.intervencoes = 0
        # faixas de entrada e saidas de cada fase (mesma conta do Max-Pressure do executor)
        self.faixas_fase = []
        for verde in self.verdes:
            d = defaultdict(set)
            for c in esquema["conexoes"]:
                if verde[int(c["linkIndex"])] in "Gg":
                    d[c["from"] + "_" + c["fromLane"]].add(c["to"] + "_" + c["toLane"])
            self.faixas_fase.append(d)
        self.faixas_entrada = sorted({c["from"] + "_" + c["fromLane"] for c in esquema["conexoes"]})

    def fase_tempo(self, estado):
        E, P = self.E, self.P
        fase = int(np.argmax(estado[2 * E:2 * E + P]))
        return fase, float(estado[2 * E + P]) * 60.0

    def pressoes(self):
        c = conn()
        h = c.lane.getLastStepHaltingNumber
        return [sum(h(l) - np.mean([h(o) for o in outs]) for l, outs in d.items())
                for d in self.faixas_fase]

    def demanda_movimentos(self, distancia=None, so_parados=False):
        """Carros por fase, contados pelo PROXIMO link deste semaforo de cada carro."""
        c = conn()
        por_link = defaultdict(int)
        for faixa in self.faixas_entrada:
            comprimento = c.lane.getLength(faixa)
            for vid in c.lane.getLastStepVehicleIDs(faixa):
                if so_parados and c.vehicle.getSpeed(vid) >= 0.1:
                    continue
                if distancia is not None and comprimento - c.vehicle.getLanePosition(vid) > distancia:
                    continue
                for tls, link, _, _ in c.vehicle.getNextTLS(vid):
                    if tls == self.id:
                        por_link[int(link)] += 1
                        break
        return [sum(n for l, n in por_link.items() if v[l] in "Gg") for v in self.verdes]

    def lembrar(self, *args):
        pass


# ---------------------------------------------------------------- classicos
class MaxPressure(Base):
    def __init__(self, esquema, verde_minimo=10, histerese=None):
        super().__init__(esquema)
        self.verde_minimo, self.histerese = verde_minimo, histerese

    def escolher(self, estado, treinando):
        fase, t = self.fase_tempo(estado)
        q = self.pressoes()
        if self.histerese is None:  # identico ao modo max_pressure do executor
            return int(np.argmax(q)), q, False
        if t < self.verde_minimo - 0.5:
            return fase, q, False
        melhor = int(np.argmax(q))
        return (melhor if q[melhor] > q[fase] + self.histerese else fase), q, False


class MaxPressureMovimento(Base):
    """Max-Pressure por MOVIMENTO (forma da literatura): carros parados em cada
    link (pelo proximo link do carro) menos os parados na faixa de saida.
    O MP do executor soma por FAIXA; fases que liberam as mesmas faixas com
    movimentos diferentes empatam e a primeira sempre vence."""

    def __init__(self, esquema, verde_minimo=10, histerese=0.0):
        super().__init__(esquema)
        self.verde_minimo, self.histerese = verde_minimo, histerese
        self.saida_link = {int(c["linkIndex"]): c["to"] + "_" + c["toLane"] for c in esquema["conexoes"]}

    def escolher(self, estado, treinando):
        c = conn()
        fase, t = self.fase_tempo(estado)
        fila = defaultdict(int)
        for faixa in self.faixas_entrada:
            for vid in c.lane.getLastStepVehicleIDs(faixa):
                if c.vehicle.getSpeed(vid) < 0.1:
                    for tls, link, _, _ in c.vehicle.getNextTLS(vid):
                        if tls == self.id:
                            fila[int(link)] += 1
                            break
        h = c.lane.getLastStepHaltingNumber
        q = [sum(fila[l] - h(self.saida_link[l]) for l, luz in enumerate(v) if luz in "Gg" and l in self.saida_link)
             for v in self.verdes]
        if t < self.verde_minimo - 0.5:
            return fase, q, False
        melhor = int(np.argmax(q))
        return (melhor if q[melhor] > q[fase] + self.histerese else fase), q, False


class TempoFixo(Base):
    def __init__(self, esquema, verdes_s):
        super().__init__(esquema)
        self.verdes_s = [max(10.0, 5.0 * math.ceil(g / 5.0)) for g in verdes_s]

    def escolher(self, estado, treinando):
        fase, t = self.fase_tempo(estado)
        acao = (fase + 1) % self.P if t >= self.verdes_s[fase] - 0.5 else fase
        return acao, [], False


class Atuado(Base):
    def __init__(self, esquema, verde_maximo=40, distancia=40.0):
        super().__init__(esquema)
        self.verde_maximo, self.distancia = verde_maximo, distancia

    def escolher(self, estado, treinando):
        fase, t = self.fase_tempo(estado)
        d = self.demanda_movimentos(self.distancia)
        if t < self.verde_maximo - 0.5 and d[fase] > 0:
            return fase, d, False
        for k in range(1, self.P):
            prox = (fase + k) % self.P
            if d[prox] > 0:
                return prox, d, False
        return fase, d, False


def webster(fluxos_link, ag, multiplicador=1.0, saturacao=1800.0, perdido=5.0):
    """Verdes de Webster por fase, com fluxos medidos por MOVIMENTO (link).

    Fluxo critico da fase k: a faixa de entrada mais carregada, somando os links
    dessa faixa com verde protegido ('G') em k. Um link com 'G' em varias fases
    divide seu fluxo entre elas; links so permissivos ('g') usam o tempo que sobra.
    Tempo perdido: 5 s por fase (3 s amarelo + 2 s vermelho geral do executor)."""
    conexoes = {int(c["linkIndex"]): c["from"] + "_" + c["fromLane"] for c in ag.esquema["conexoes"]}
    fases_G = defaultdict(int)
    for v in ag.verdes:
        for l, luz in enumerate(v):
            if luz == "G" and l in conexoes:
                fases_G[l] += 1
    y = []
    for v in ag.verdes:
        por_faixa = defaultdict(float)
        for l, luz in enumerate(v):
            if luz == "G" and l in conexoes:
                por_faixa[conexoes[l]] += fluxos_link.get(str(l), 0.0) / fases_G[l]
        y.append(max(por_faixa.values() or [0.0]) / saturacao)
    Y = min(sum(y), 0.9)
    L = perdido * ag.P
    ciclo = (1.5 * L + 5.0) / (1.0 - Y)
    ciclo = min(max(ciclo * multiplicador, ag.P * 15.0), 180.0)
    util = ciclo - L
    verdes = [util * yi / sum(y) if sum(y) > 0 else util / ag.P for yi in y]
    return {"y": y, "Y": Y, "ciclo_s": ciclo, "verdes_s": verdes}


def medir_fluxos(m, sementes):
    """Veiculos/h por movimento (link) de cada semaforo, com o programa original.

    Cada veiculo e contado uma vez no link pelo qual ia cruzar o semaforo
    (proximo link informado pelo SUMO enquanto estava na faixa de entrada)."""
    import libsumo as c
    ref = PROJETO / "referencias/cologne8_sumo_rl_1.4.5/sumo_rl/nets/RESCO/cologne8"
    faixas = defaultdict(set)
    for s in m["controladores"]:
        for x in s["conexoes"]:
            faixas[s["id"]].add(x["from"] + "_" + x["fromLane"])
    total = defaultdict(lambda: defaultdict(float))
    for semente in sementes:
        c.start(["sumo", "-n", str(ref / "cologne8.net.xml"), "-r", str(ref / "cologne8.rou.xml"),
                 "--begin", str(m["episodio"]["inicio_aquecimento"]), "--end", str(FIM),
                 "--seed", str(semente), "--no-step-log", "true", "--time-to-teleport", "-1",
                 "--collision.action", "warn", "--no-warnings", "true"])
        vistos = defaultdict(dict)
        while c.simulation.getTime() < FIM:
            c.simulationStep()
            if c.simulation.getTime() < INICIO:
                continue
            for tid, fs in faixas.items():
                for f in fs:
                    for vid in c.lane.getLastStepVehicleIDs(f):
                        if vid in vistos[tid]:
                            continue
                        for tls, link, _, _ in c.vehicle.getNextTLS(vid):
                            if tls == tid:
                                vistos[tid][vid] = int(link)
                                break
        c.close()
        for tid, d in vistos.items():
            for link in d.values():
                total[tid][str(link)] += 1
    horas = (FIM - INICIO) / 3600.0
    return {tid: {l: n / len(sementes) / horas for l, n in d.items()} for tid, d in total.items()}


def verdes_originais(esquema, net_xml):
    """Duracoes de verde do programa original, para rodar o MESMO plano no executor."""
    import xml.etree.ElementTree as ET
    t = next(x for x in ET.parse(net_xml).getroot().findall("tlLogic") if x.get("id") == esquema["id"])
    fases = t.findall("phase")
    return [float(fases[p["indice_xml"]].get("duration")) for p in esquema["fases"]]


def calibrar_webster():
    m = manifesto()
    C = m["controladores"]
    net = PROJETO / "referencias/cologne8_sumo_rl_1.4.5/sumo_rl/nets/RESCO/cologne8/cologne8.net.xml"
    cal = carregar_calibracao()
    cal.pop("fluxos_veic_h_por_faixa", None)
    fluxos = medir_fluxos(m, VALIDACAO)
    grade = []
    for mult in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0):
        planos = [webster(fluxos[s["id"]], Base(s), mult) for s in C]
        res = [executar(m, [TempoFixo(s, p["verdes_s"]) for s, p in zip(C, planos)], sem) for sem in VALIDACAO]
        grade.append({"multiplicador": mult, "espera_s": media(res, "espera_s"),
                      "nao_concluidas": sum(x["nao_concluidas"] for x in res), "colisoes": media(res, "colisoes")})
        print("webster", grade[-1], flush=True)
    melhor = min(grade, key=lambda g: (g["nao_concluidas"], g["espera_s"]))
    orig = [executar(m, [TempoFixo(s, verdes_originais(s, net)) for s in C], sem) for sem in VALIDACAO]
    cal["webster"] = {"versao": "fluxo por movimento (substitui a primeira versao por faixa, descartada por dividir mal os verdes)",
                      "fluxos_veic_h_por_link": fluxos, "grade": grade, "escolhido": melhor["multiplicador"],
                      "planos": {s["id"]: webster(fluxos[s["id"]], Base(s), melhor["multiplicador"]) for s in C},
                      "plano_original_no_executor_validacao": {"espera_s": media(orig, "espera_s"),
                                                               "verdes_s": {s["id"]: verdes_originais(s, net) for s in C}}}
    print("plano original no executor", media(orig, "espera_s"), flush=True)
    json_salvar(SAIDA / "calibracao_classicos.json", cal)


# ---------------------------------------------------------------- aprendizado simples
class Imitacao(Base):
    """MLP supervisionada; com professor, registra (estado, acao do professor)."""

    def __init__(self, esquema, modelo=None, professor=None, dados=None, agir_professor=False):
        super().__init__(esquema)
        self.modelo, self.professor, self.dados = modelo, professor, dados
        self.agir_professor = agir_professor

    def escolher(self, estado, treinando):
        rotulo = None
        if self.professor is not None:
            rotulo, _, _ = self.professor.escolher(estado, False)
            self.dados.append((np.asarray(estado, dtype=np.float32), int(rotulo)))
        if self.agir_professor or self.modelo is None:
            return int(rotulo), [], False
        prob = self.modelo.predict_proba(np.asarray(estado, dtype=np.float32)[None, :])[0]
        cheia = np.zeros(self.P)
        cheia[self.modelo.classes_] = prob
        return int(np.argmax(cheia)), cheia.tolist(), False


def treinar_mlp(dados, semente):
    from sklearn.neural_network import MLPClassifier
    X = np.stack([d[0] for d in dados])
    y = np.array([d[1] for d in dados])
    if len(set(y)) == 1:
        class Constante:  # semaforo cujo professor nunca troca: rede trivial
            classes_ = np.array([y[0]])
            def predict_proba(self, X):
                return np.ones((len(X), 1))
        return Constante(), 1.0
    mlp = MLPClassifier(hidden_layer_sizes=(64, 64), activation="relu", max_iter=300,
                        early_stopping=True, validation_fraction=0.15, n_iter_no_change=15,
                        random_state=semente)
    mlp.fit(X, y)
    return mlp, float(mlp.score(X, y))


def exportar_imitacao_numpy(semente):
    """Converte as MLPs do scikit-learn em pesos NumPy puros (.npz), sem pickle e sem sklearn."""
    pasta = SAIDA / "modelos" / f"imitacao_seed{semente}"
    modelos = pickle.loads((pasta / "mlps.pkl").read_bytes())
    m = manifesto()
    arrays = {}
    for i, (s, mo) in enumerate(zip(m["controladores"], modelos)):
        arrays[f"{i}_classes"] = np.asarray(mo.classes_, dtype=np.int64)
        for k, (W, b) in enumerate(zip(getattr(mo, "coefs_", []), getattr(mo, "intercepts_", []))):
            arrays[f"{i}_W{k}"], arrays[f"{i}_b{k}"] = np.asarray(W, np.float64), np.asarray(b, np.float64)
        arrays[f"{i}_camadas"] = np.array(len(getattr(mo, "coefs_", [])))
        arrays[f"{i}_id"] = np.array(s["id"])
    np.savez(pasta / "mlps_numpy.npz", **arrays)
    return pasta / "mlps_numpy.npz"


class MLPNumpy:
    """Mesma decisao que MLPClassifier.predict (ReLU nas ocultas; saida logistica ou softmax)."""

    def __init__(self, dados, i):
        self.classes_ = dados[f"{i}_classes"]
        n = int(dados[f"{i}_camadas"])
        self.camadas = [(dados[f"{i}_W{k}"], dados[f"{i}_b{k}"]) for k in range(n)]

    def predict_proba(self, X):
        if not self.camadas:
            return np.ones((len(X), 1))
        h = np.asarray(X, np.float64)
        for k, (W, b) in enumerate(self.camadas):
            h = h @ W + b
            if k < len(self.camadas) - 1:
                h = np.maximum(h, 0.0)
        if h.shape[1] == 1:
            p = 1.0 / (1.0 + np.exp(-h[:, 0]))
            return np.stack([1.0 - p, p], axis=1)
        h = h - h.max(axis=1, keepdims=True)
        e = np.exp(h)
        return e / e.sum(axis=1, keepdims=True)


def carregar_imitacao_numpy(arquivo, controladores):
    dados = np.load(arquivo, allow_pickle=False)
    ids = [str(dados[f"{i}_id"]) for i in range(len(controladores))]
    if ids != [s["id"] for s in controladores]:
        raise ValueError("Os pesos foram exportados para outra ordem de semaforos")
    return [MLPNumpy(dados, i) for i in range(len(controladores))]


class QTabular(Base):
    """Q-learning tabular. Estado: fase, faixa de tempo de verde e fila por fase (em baldes)."""
    BALDES = (0, 2, 5, 10)  # 0 | 1-2 | 3-5 | 6-10 | 11+
    TEMPOS = (15, 30, 60)

    def __init__(self, esquema, semente, alfa=0.1, gamma=0.95):
        super().__init__(esquema)
        self.rng = random.Random(semente)
        self.alfa, self.gamma, self.epsilon = alfa, gamma, 0.0
        self.Q = {}
        self.pendente = None
        self.atualizacoes = 0

    def chave(self, estado):
        fase, t = self.fase_tempo(estado)
        d = self.demanda_movimentos(so_parados=True)
        b = tuple(sum(x > lim for lim in self.BALDES) for x in d)
        return (fase, sum(t >= lim for lim in self.TEMPOS)) + b

    def q(self, k):
        if k not in self.Q:
            self.Q[k] = np.zeros(self.P)
        return self.Q[k]

    def escolher(self, estado, treinando):
        k = self.chave(estado)
        qs = self.q(k)
        explorou = treinando and self.rng.random() < self.epsilon
        acao = self.rng.randrange(self.P) if explorou else int(np.flatnonzero(qs == qs.max())[0])
        self.pendente = k
        return acao, qs.tolist(), explorou

    def lembrar(self, s, a, r, s2, dt, fim, treinando):
        if not treinando or self.pendente is None:
            return
        # O executor soma -10000 por colisao a TODOS os agentes. Aqui ela e retirada:
        # numa tabela, um unico contato apagaria todo o resto do aprendizado.
        if r <= -5000:
            r += 10000.0 * round(-r / 10000.0)
        k = self.pendente
        alvo = r if fim else r + self.gamma ** (dt / 5.0) * self.q(self.chave(s2)).max()
        self.q(k)[a] += self.alfa * (alvo - self.q(k)[a])
        self.atualizacoes += 1


# ---------------------------------------------------------------- execucao e metricas
def resumo(r):
    v = r["viagens"]["afetados_pelo_controle"]
    return {"semente": r["semente"], "espera_s": v["espera_concluidos"]["media"],
            "p95_s": v["espera_concluidos"]["p95"], "espera_max_s": v["espera_concluidos"]["maximo"],
            "duracao_viagem_s": v["duracao_concluidos"]["media"], "colisoes": r["colisoes"],
            "nao_concluidas": r["viagens_nao_concluidas"], "fila_media_rede": r["fila_media_rede"],
            "fila_max_rede": r["fila_max_rede"], "intervencoes": r["intervencoes"],
            "trocas": r["trocas"], "terminado_naturalmente": r["terminado_naturalmente"],
            "fim_sumo": r["fim_sumo"]}


def executar(m, agentes, semente, pasta=None, treinando=False, modo=MODO):
    temporaria = pasta is None
    if temporaria:
        pasta = TMP / f"{os.getpid()}_{time.time_ns()}"
        pasta.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = rodar(m, agentes + [None], pasta, semente, treinando=treinando,
                  duracao=3600, escoamento=1200, backend="libsumo", modo=modo)
    finally:
        if temporaria and pasta.exists():
            shutil.rmtree(pasta)
    return resumo(r)


def media(lista, campo):
    return float(np.mean([x[campo] for x in lista]))


def criterio_marl(lista):
    """Mesmo criterio de selecao do MARL: colisoes, depois nao concluidas, depois espera."""
    return (sum(x["colisoes"] for x in lista), sum(x["nao_concluidas"] for x in lista),
            media(lista, "espera_s"))


def json_salvar(path, dados):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


# ---------------------------------------------------------------- etapas
def calibrar_classicos():
    m = manifesto()
    C = m["controladores"]
    saida = {"sementes_validacao": VALIDACAO, "criterio": "menor espera media nas sementes de validacao"}

    grade = []
    for vmax in (20, 30, 40, 55):
        for dist in (20.0, 40.0, 80.0):
            res = [executar(m, [Atuado(s, vmax, dist) for s in C], sem) for sem in VALIDACAO]
            grade.append({"verde_maximo": vmax, "distancia_m": dist, "espera_s": media(res, "espera_s"),
                          "nao_concluidas": sum(x["nao_concluidas"] for x in res), "colisoes": media(res, "colisoes")})
            print("atuado", grade[-1], flush=True)
    melhor = min(grade, key=lambda g: (g["nao_concluidas"], g["espera_s"]))
    saida["atuado"] = {"grade": grade, "escolhido": {"verde_maximo": melhor["verde_maximo"],
                                                    "distancia_m": melhor["distancia_m"]}}

    grade = []
    for vmin in (10, 15, 20, 25, 30):
        for hist in (0.0, 1.0, 2.0, 4.0, 8.0):
            res = [executar(m, [MaxPressure(s, vmin, hist) for s in C], sem) for sem in VALIDACAO]
            grade.append({"verde_minimo": vmin, "histerese": hist, "espera_s": media(res, "espera_s"),
                          "nao_concluidas": sum(x["nao_concluidas"] for x in res), "colisoes": media(res, "colisoes")})
            print("mp", grade[-1], flush=True)
    res = [executar(m, [MaxPressure(s) for s in C], sem) for sem in VALIDACAO]
    saida["mp_sem_ajuste_validacao"] = {"espera_s": media(res, "espera_s"), "rodadas": res}
    grade.append({"verde_minimo": 10, "histerese": None, "espera_s": media(res, "espera_s"),
                  "nao_concluidas": sum(x["nao_concluidas"] for x in res), "colisoes": media(res, "colisoes")})
    melhor = min(grade, key=lambda g: (g["nao_concluidas"], g["espera_s"]))
    saida["mp"] = {"grade": grade, "escolhido": {"verde_minimo": melhor["verde_minimo"],
                                                "histerese": melhor["histerese"]}}
    json_salvar(SAIDA / "calibracao_classicos.json", saida)
    calibrar_webster()
    calibrar_mp_movimento()
    return saida


def calibrar_mp_movimento():
    m = manifesto()
    C = m["controladores"]
    grade = []
    for vmin in (10, 15, 20):
        for hist in (0.0, 1.0, 2.0, 4.0):
            res = [executar(m, [MaxPressureMovimento(s, vmin, hist) for s in C], sem) for sem in VALIDACAO]
            grade.append({"verde_minimo": vmin, "histerese": hist, "espera_s": media(res, "espera_s"),
                          "nao_concluidas": sum(x["nao_concluidas"] for x in res), "colisoes": media(res, "colisoes")})
            print("mp_mov", grade[-1], flush=True)
    melhor = min(grade, key=lambda g: (g["nao_concluidas"], g["espera_s"]))
    cal = carregar_calibracao()
    cal["mp_movimento"] = {"grade": grade, "escolhido": {"verde_minimo": melhor["verde_minimo"],
                                                        "histerese": melhor["histerese"]}}
    json_salvar(SAIDA / "calibracao_classicos.json", cal)


def carregar_calibracao():
    return json.loads((SAIDA / "calibracao_classicos.json").read_text(encoding="utf-8"))


def controladores_classicos(m, cal):
    C = m["controladores"]
    net = PROJETO / "referencias/cologne8_sumo_rl_1.4.5/sumo_rl/nets/RESCO/cologne8/cologne8.net.xml"
    w, a, p = cal["webster"]["planos"], cal["atuado"]["escolhido"], cal["mp"]["escolhido"]
    mv = cal["mp_movimento"]["escolhido"]
    return {"webster_calibrado": lambda: [TempoFixo(s, w[s["id"]]["verdes_s"]) for s in C],
            "plano_original_no_executor": lambda: [TempoFixo(s, verdes_originais(s, net)) for s in C],
            "atuado_calibrado": lambda: [Atuado(s, a["verde_maximo"], a["distancia_m"]) for s in C],
            "max_pressure_faixa_ajustado": lambda: [MaxPressure(s, p["verde_minimo"], p["histerese"]) for s in C],
            "max_pressure_movimento_ajustado": lambda: [MaxPressureMovimento(s, mv["verde_minimo"], mv["histerese"]) for s in C]}


def professor_imitacao(cal, C):
    """O controlador classico adaptativo com menor espera na VALIDACAO vira o professor
    da rede supervisionada (atuado, Max-Pressure por faixa ou por movimento)."""
    def espera_escolhida(chave, campos):
        e = cal[chave]["escolhido"]
        return next(g["espera_s"] for g in cal[chave]["grade"] if all(g[k] == e[k] for k in campos))
    opcoes = {
        "atuado": (espera_escolhida("atuado", ("verde_maximo", "distancia_m")),
                   lambda e: [Atuado(s, e["verde_maximo"], e["distancia_m"]) for s in C]),
        "mp": (espera_escolhida("mp", ("verde_minimo", "histerese")),
               lambda e: [MaxPressure(s, e["verde_minimo"], e["histerese"]) for s in C]),
        "mp_movimento": (espera_escolhida("mp_movimento", ("verde_minimo", "histerese")),
                         lambda e: [MaxPressureMovimento(s, e["verde_minimo"], e["histerese"]) for s in C]),
    }
    nome = min(opcoes, key=lambda k: opcoes[k][0])
    e = cal[nome]["escolhido"]
    return nome, {**e, "espera_validacao_s": opcoes[nome][0]}, opcoes[nome][1](e)

def treinar_imitacao(semente, episodios_bc=20, iteracoes_dagger=3, episodios_dagger=10):
    m = manifesto()
    C = m["controladores"]
    nome_prof, p, professores = professor_imitacao(carregar_calibracao(), C)
    dados = [[] for _ in C]
    historico = []
    rng = random.Random(semente)
    sementes_usadas = set()
    melhor = None

    def nova_semente():
        while True:
            s = 1000 + rng.randrange(0, 5000)
            if s not in sementes_usadas:
                sementes_usadas.add(s)
                return s

    # 1) behavior cloning: o professor dirige e a rede so observa
    for _ in range(episodios_bc):
        ags = [Imitacao(s, professor=pr, dados=d, agir_professor=True) for s, pr, d in zip(C, professores, dados)]
        executar(m, ags, nova_semente(), treinando=True)
    modelos = [treinar_mlp(d, semente)[0] for d in dados]
    # 2) DAgger: a rede dirige, o professor rotula os estados que a rede visitou
    for it in range(iteracoes_dagger):
        for _ in range(episodios_dagger):
            ags = [Imitacao(s, modelo=mo, professor=pr, dados=d) for s, mo, pr, d in zip(C, modelos, professores, dados)]
            executar(m, ags, nova_semente(), treinando=True)
        treinados = [treinar_mlp(d, semente) for d in dados]
        modelos = [t[0] for t in treinados]
        val = [executar(m, [Imitacao(s, modelo=mo) for s, mo in zip(C, modelos)], sem) for sem in VALIDACAO]
        historico.append({"iteracao_dagger": it + 1, "exemplos": [len(d) for d in dados],
                          "acuracia_treino": [t[1] for t in treinados],
                          "validacao_espera_s": media(val, "espera_s"), "criterio": list(criterio_marl(val)),
                          "validacao": val})
        if melhor is None or criterio_marl(val) < melhor[0]:  # mesma regra de selecao do MARL
            melhor = (criterio_marl(val), it + 1, modelos)
        print("imitacao", semente, historico[-1]["iteracao_dagger"], historico[-1]["validacao_espera_s"], flush=True)
    pasta = SAIDA / "modelos" / f"imitacao_seed{semente}"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "mlps.pkl").write_bytes(pickle.dumps(melhor[2]))
    json_salvar(pasta / "treino.json", {"semente": semente, "iteracao_escolhida": melhor[1],
                                        "criterio_selecao": "igual ao MARL: colisoes, nao concluidas, espera (validacao 201/202)", "professor": {"tipo": nome_prof, **p}, "episodios_bc": episodios_bc,
                                        "iteracoes_dagger": iteracoes_dagger, "episodios_por_iteracao": episodios_dagger,
                                        "sementes_trafego_treino": sorted(sementes_usadas), "historico": historico})


def treinar_qlearning(semente, episodios=300, validar_cada=10, eps_fim=0.05, frac_exploracao=0.6):
    m = manifesto()
    C = m["controladores"]
    pasta = SAIDA / "modelos" / f"qlearning_seed{semente}"
    pasta.mkdir(parents=True, exist_ok=True)
    ckpt = pasta / "checkpoint_retomada.pkl"
    ags = [QTabular(s, semente * 100 + i) for i, s in enumerate(C)]
    melhor, historico, curva, inicio = None, [], [], 1
    if ckpt.exists():  # retoma depois de uma interrupcao, sem repetir episodios
        d = pickle.loads(ckpt.read_bytes())
        for a, q, rs in zip(ags, d["Q"], d["rng"]):
            a.Q, _ = q, a.rng.setstate(rs)
        melhor, historico, curva, inicio = d["melhor"], d["historico"], d["curva"], d["episodio"] + 1
        print("retomando", semente, "do episodio", inicio, flush=True)
    for ep in range(inicio, episodios + 1):
        eps = max(eps_fim, 1.0 - (ep - 1) / (frac_exploracao * episodios))
        for a in ags:
            a.epsilon = eps
        r = executar(m, ags, 1000 + ep, treinando=True)
        curva.append({"episodio": ep, "epsilon": eps, "espera_s": r["espera_s"], "colisoes": r["colisoes"],
                      "nao_concluidas": r["nao_concluidas"], "estados_visitados": sum(len(a.Q) for a in ags)})
        if ep % validar_cada == 0:
            val = [executar(m, ags, sem) for sem in VALIDACAO]
            nota = criterio_marl(val)
            historico.append({"episodio": ep, "criterio": list(nota), "validacao": val})
            print("qlearning", semente, ep, round(eps, 2), nota, flush=True)
            if melhor is None or nota < melhor[0]:
                melhor = (nota, ep, [copy.deepcopy(a.Q) for a in ags])
            tmp = ckpt.with_suffix(".tmp")
            tmp.write_bytes(pickle.dumps({"Q": [a.Q for a in ags], "rng": [a.rng.getstate() for a in ags],
                                          "melhor": melhor, "historico": historico, "curva": curva, "episodio": ep}))
            tmp.replace(ckpt)
    (pasta / "tabelas_q.pkl").write_bytes(pickle.dumps(melhor[2]))
    json_salvar(pasta / "treino.json", {"semente": semente, "episodios": episodios, "episodio_escolhido": melhor[1],
                                        "criterio_selecao": "igual ao MARL: colisoes, nao concluidas, espera (validacao 201/202)",
                                        "alfa": 0.1, "gamma": 0.95, "epsilon": f"1 -> {eps_fim} em {frac_exploracao:.0%} dos episodios",
                                        "historico_validacao": historico, "curva_treino": curva})
    ckpt.unlink()

def fabricas_avaliacao(m, sementes_aprendizado=(0, 1, 2)):
    C = m["controladores"]
    grupos = {nome: {"_": f} for nome, f in controladores_classicos(m, carregar_calibracao()).items()}
    grupos["max_pressure_executor"] = {"_": "max_pressure"}
    grupos["original_fixo"] = {"_": "original_fixo"}
    for s in sementes_aprendizado:
        arq = SAIDA / "modelos" / f"imitacao_seed{s}" / "mlps.pkl"
        if arq.exists():
            mo = pickle.loads(arq.read_bytes())
            grupos.setdefault("imitacao_mlp", {})[s] = (lambda mo=mo: [Imitacao(x, modelo=k) for x, k in zip(C, mo)])
        arq = SAIDA / "modelos" / f"qlearning_seed{s}" / "tabelas_q.pkl"
        if arq.exists():
            tabs = pickle.loads(arq.read_bytes())
            def fabrica_q(tabs=tabs, s=s):
                ags = [QTabular(x, s) for x in C]
                for a, t in zip(ags, tabs):
                    a.Q = copy.deepcopy(t)
                return ags
            grupos.setdefault("qlearning_tabular", {})[s] = fabrica_q
    return grupos


def avaliar_grupo(nome):
    """Teste final nas sementes 1..10; tripinfo e metricas completas ficam em teste/<grupo>/."""
    m = manifesto()
    C = m["controladores"]
    linhas = []
    for sm, fabrica in fabricas_avaliacao(m)[nome].items():
        for sem in TESTE:
            pasta = SAIDA / "teste" / nome / (f"modelo{sm}" if sm != "_" else "") / f"seed{sem}"
            if pasta.exists():
                shutil.rmtree(pasta)
            pasta.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(fabrica, str):
                r = executar(m, [Base(x) for x in C], sem, pasta=pasta, modo=fabrica)
            else:
                r = executar(m, fabrica(), sem, pasta=pasta)
            r.update(grupo=nome, semente_modelo=None if sm == "_" else sm)
            linhas.append(r)
            print(nome, sm, sem, round(r["espera_s"], 2), r["colisoes"], flush=True)
    json_salvar(SAIDA / "teste" / f"{nome}.json", linhas)
    return linhas

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("etapa", choices=["exportar_imitacao", "calibrar", "calibrar_webster", "calibrar_mp_movimento", "imitacao", "qlearning", "avaliar"])
    ap.add_argument("--semente", type=int, default=0)
    ap.add_argument("--episodios", type=int, default=200)
    ap.add_argument("--grupo", default=None)
    a = ap.parse_args()
    if a.etapa == "exportar_imitacao":
        print(exportar_imitacao_numpy(a.semente))
    elif a.etapa == "calibrar":
        calibrar_classicos()
    elif a.etapa == "calibrar_webster":
        calibrar_webster()
    elif a.etapa == "calibrar_mp_movimento":
        calibrar_mp_movimento()
    elif a.etapa == "imitacao":
        treinar_imitacao(a.semente)
    elif a.etapa == "qlearning":
        treinar_qlearning(a.semente, a.episodios)
    else:
        avaliar_grupo(a.grupo)
