"""
Analise de comportamento: COMO as DQNs controlam o cruzamento?

Este script nao treina nada e nao mexe nos modelos. Ele roda as mesmas
simulacoes de avaliar.py (mesmos cenarios, mesmas 10 sementes de teste), mas
com a instrumentacao opcional de simulacao.rodar() ligada. A instrumentacao
so OBSERVA: registra, segundo a segundo, o estado do semaforo que o SUMO de
fato executou, cada decisao do controlador e a viagem de cada carro.

Com isso medimos:
  A. frequencia de trocas e tempo gasto em amarelo / vermelho geral
  B. duracao dos verdes (geral, por aproximacao, distribuicao)
  C. adaptacao ao transito (equilibrado x saturado, e os 3 tercos do pico)
  D. espera por aproximacao (media, P95, maxima, n de carros)

Regras de medicao (para nao misturar as coisas):
  - "hora" = os 3600 s de demanda; "escoamento" = o tempo extra depois disso.
    Trocas e verdes sao contados separadamente em cada periodo.
  - Um verde so entra na estatistica de duracao se comecar E terminar dentro
    do periodo e for encerrado por um amarelo (verde completo). Verdes
    cortados pela fronteira de 3600 s sao contados a parte ("censurados").
  - O verde inicial (imposto pelo simulador no segundo 0, com o cruzamento
    vazio) fica fora da estatistica de duracao.
  - Espera de cada carro = waitingTime do tripinfo do SUMO (a mesma fonte de
    espera_media em simulacao.py). A aproximacao de origem vem da faixa onde o
    carro entrou (departLane), conferida com o id do fluxo.

Uso (de dentro de scripts/):
  python analisar_comportamento.py                 # tudo (5 cenarios x 10 sementes)
  python analisar_comportamento.py --sementes 1 2  # rapido, para testar
  python analisar_comportamento.py --so-graficos   # refaz graficos do JSON salvo
  python analisar_comportamento.py --todos         # inclui tambem os outros 2 tradicionais
"""

import argparse
import json
import os
import statistics
import sys
import time
import xml.etree.ElementTree as ET
from multiprocessing import Pool

import gerar_demanda
import simulacao
from simulacao import (AMARELO, APROXIMACOES, FAIXAS_ENTRADA, INTERVALO_DECISAO,
                       VERDE_MINIMO, VERMELHO_GERAL)

PASTA_SAIDA = os.path.join(simulacao.PASTA, "resultados", "analise_comportamento")
PASTA_GRAFICOS = os.path.join(PASTA_SAIDA, "graficos")

MODELOS_DQN = ["dqn_fila", "dqn_fila_seed1", "dqn_fila_seed2"]
CONTROLADORES_PADRAO = ["Webster", "Max-Pressure"] + [
    f"DQN {m.replace('dqn_fila', 'original').replace('original_', '')}"
    for m in MODELOS_DQN
]
# rotulo -> nome do modelo
ROTULO_MODELO = dict(zip(CONTROLADORES_PADRAO[2:], MODELOS_DQN))
# DQNs treinadas na dinamica C (treinar_dqn.py --dinamica C)
MODELOS_DQN_C = [f"dqn_fila_C_seed{i}" for i in range(3)]
ROTULO_MODELO.update({f"DQN C seed{i}": m for i, m in enumerate(MODELOS_DQN_C)})
# DQNs com recompensa fila + excesso de espera (treinar_dqn.py fila_excesso --dinamica C).
# Na avaliacao a recompensa nao e usada: carregam como qualquer outra DQN.
MODELOS_DQN_EXCESSO = [f"dqn_fila_excesso_C_seed{i}" for i in range(3)]
ROTULO_MODELO.update({f"DQN excesso C seed{i}": m for i, m in enumerate(MODELOS_DQN_EXCESSO)})
# Experimento 2: mesma recompensa, 17 entradas (+ maior espera por aproximacao).
# O numero de entradas e lido do proprio checkpoint ao carregar.
MODELOS_DQN_EXCESSO_17 = [f"dqn_fila_excesso_17_C_seed{i}" for i in range(3)]
ROTULO_MODELO.update({f"DQN excesso17 C seed{i}": m for i, m in enumerate(MODELOS_DQN_EXCESSO_17)})
EXTRAS = ["Max-Pressure teto", "Tempo fixo 30s"]

# Periodos do cenario pico (os mesmos blocos de gerar_demanda.py)
PERIODOS_PICO = [(ini, fim) for ini, fim, _ in gerar_demanda.CENARIOS["pico"]]

FAIXA_PARA_APROX = {f: a for a, faixas in FAIXAS_ENTRADA.items() for f in faixas}


# =========================================================================
# Registro: o objeto que a instrumentacao de simulacao.rodar() alimenta
# =========================================================================
class Registro:
    """Guarda o que aconteceu de verdade numa rodada (so observa)."""

    def inicio(self, estados_verdes, duracao):
        self.estados_verdes = list(estados_verdes)
        self.estados_amarelos = [
            "".join("y" if c in "Gg" else c for c in e) for e in estados_verdes
        ]
        self.duracao = duracao
        self.estados = []  # (segundo, estado executado nesse segundo)
        self.decisoes = []  # dicts (escolha = o que foi EXECUTADO)
        self.intervencoes = []  # quando a regra de seguranca mudou a escolha
        self.veiculos = []

    def passo(self, segundo, estado):
        self.estados.append((segundo, estado))

    def decisao(self, obs, escolha):
        self.decisoes.append({
            "t": obs.segundo,
            "verde": APROXIMACOES.index(obs.aprox_verde),
            "tempo_no_verde": obs.tempo_no_verde,
            "escolha": int(escolha),
            "filas": [obs.filas[a] for a in APROXIMACOES],
            "carros": [obs.carros[a] for a in APROXIMACOES],
        })

    def intervencao(self, obs, pedido, escolha):
        self.intervencoes.append({
            "t": obs.segundo,
            "verde": APROXIMACOES.index(obs.aprox_verde),
            "tempo_no_verde": obs.tempo_no_verde,
            "pedido_controlador": int(pedido),
            "escolha_executada": int(escolha),
            "filas": [obs.filas[a] for a in APROXIMACOES],
            "carros": [obs.carros[a] for a in APROXIMACOES],
        })

    def fim(self, caminho_tripinfo):
        if not os.path.exists(caminho_tripinfo):
            return
        for v in ET.parse(caminho_tripinfo).getroot():
            faixa = v.get("departLane", "")
            aprox = FAIXA_PARA_APROX.get(faixa)
            # id do fluxo: f{bloco}_{aprox}_{movimento}.{n}
            aprox_id = v.get("id").split("_")[1]
            if aprox is None:  # carro que nunca entrou na rede
                aprox = aprox_id
            if aprox != aprox_id:
                raise RuntimeError(f"aproximacao inconsistente: {v.attrib}")
            self.veiculos.append({
                "aprox": aprox,
                "depart": float(v.get("depart", -1)),
                "espera": float(v.get("waitingTime", 0)),
                "atraso_entrada": float(v.get("departDelay", 0)),
                "chegou": float(v.get("arrival", -1)) >= 0,
            })

    # ---------------------------------------------------------------------
    def classificar(self, estado):
        """-> ('verde', i) | ('amarelo', i) | ('vermelho', None)"""
        if estado in self.estados_verdes:
            return "verde", self.estados_verdes.index(estado)
        if estado in self.estados_amarelos:
            return "amarelo", self.estados_amarelos.index(estado)
        if set(estado) == {"r"}:
            return "vermelho", None
        raise RuntimeError(f"estado de semaforo desconhecido: {estado}")

    def segmentos(self):
        """Trechos continuos de mesmo estado: dicts tipo/aprox/inicio/dur."""
        segs = []
        for t, estado in self.estados:
            tipo, aprox = self.classificar(estado)
            if segs and segs[-1]["tipo"] == tipo and segs[-1]["aprox"] == aprox \
                    and segs[-1]["inicio"] + segs[-1]["dur"] == t:
                segs[-1]["dur"] += 1
            else:
                segs.append({"tipo": tipo, "aprox": aprox, "inicio": t, "dur": 1})
        # um verde so esta "completo" se foi encerrado por um amarelo
        for i, s in enumerate(segs):
            s["completo"] = i + 1 < len(segs) and segs[i + 1]["tipo"] == "amarelo"
            s["inicial"] = i == 0
        return segs


# =========================================================================
# Metricas de uma rodada
# =========================================================================
def percentil(v, p):
    """Mesma definicao de simulacao._ler_tripinfo (vizinho mais proximo)."""
    if not v:
        return 0.0
    ordenado = sorted(v)
    k = int(round((p / 100.0) * (len(ordenado) - 1)))
    return ordenado[k]


def media(v):
    return sum(v) / len(v) if v else None


def metricas_periodo(segs, decisoes, ini, fim):
    """Comportamento do semaforo na janela [ini, fim)."""
    dur_janela = fim - ini
    segundos = {"verde": 0, "amarelo": 0, "vermelho": 0}
    verde_por_aprox = [0] * 4
    for s in segs:
        a, b = max(s["inicio"], ini), min(s["inicio"] + s["dur"], fim)
        if b > a:
            segundos[s["tipo"]] += b - a
            if s["tipo"] == "verde":
                verde_por_aprox[s["aprox"]] += b - a
    total = sum(segundos.values())

    trocas = sum(1 for s in segs if s["tipo"] == "amarelo" and ini <= s["inicio"] < fim)

    # verdes completos que COMECAM na janela e terminam ate o fim dela
    verdes = [s for s in segs if s["tipo"] == "verde" and not s["inicial"]
              and s["completo"] and ini <= s["inicio"]
              and s["inicio"] + s["dur"] <= fim]
    censurados = sum(1 for s in segs if s["tipo"] == "verde"
                     and s["inicio"] < fim < s["inicio"] + s["dur"])
    duracoes = [s["dur"] for s in verdes]
    dur_por_aprox = [[s["dur"] for s in verdes if s["aprox"] == i] for i in range(4)]

    # decisoes de troca nesta janela: o que o controlador olhou ao trocar
    trocas_dec = [d for d in decisoes if ini <= d["t"] < fim and d["escolha"] != d["verde"]]
    fila_ao_encerrar = [d["filas"][d["verde"]] for d in trocas_dec]
    escolheu_maior_fila = [
        d["filas"][d["escolha"]] >= max(d["filas"][j] for j in range(4) if j != d["verde"])
        for d in trocas_dec
    ]
    ordem_ciclica = [d["escolha"] == (d["verde"] + 1) % 4 for d in trocas_dec]

    # "verde ocioso": decisao de MANTER o verde numa aproximacao sem fila
    # enquanto outra tem carro parado. Cada decisao vale INTERVALO_DECISAO s.
    ocioso = [ini <= d["t"] < fim and d["escolha"] == d["verde"]
              and d["filas"][d["verde"]] == 0
              and max(d["filas"][j] for j in range(4) if j != d["verde"]) > 0
              for d in decisoes]
    seq, maior_seq = 0, 0
    for o in ocioso:
        seq = seq + 1 if o else 0
        maior_seq = max(maior_seq, seq)

    return {
        "duracao_janela_s": dur_janela,
        "segundos_simulados": total,
        "trocas": trocas,
        "trocas_por_hora": trocas * 3600.0 / dur_janela,
        "s_verde": segundos["verde"],
        "s_amarelo": segundos["amarelo"],
        "s_vermelho_geral": segundos["vermelho"],
        "pct_amarelo": 100.0 * segundos["amarelo"] / total if total else None,
        "pct_vermelho_geral": 100.0 * segundos["vermelho"] / total if total else None,
        "pct_transicao": 100.0 * (segundos["amarelo"] + segundos["vermelho"]) / total
        if total else None,
        "s_verde_por_aprox": dict(zip(APROXIMACOES, verde_por_aprox)),
        "pct_verde_por_aprox": {
            a: (100.0 * verde_por_aprox[i] / segundos["verde"] if segundos["verde"] else None)
            for i, a in enumerate(APROXIMACOES)
        },
        "n_verdes_completos": len(duracoes),
        "n_verdes_censurados": censurados,
        "verde_medio": media(duracoes),
        "verde_mediano": statistics.median(duracoes) if duracoes else None,
        "verde_medio_por_aprox": {a: media(dur_por_aprox[i]) for i, a in enumerate(APROXIMACOES)},
        "n_verdes_por_aprox": {a: len(dur_por_aprox[i]) for i, a in enumerate(APROXIMACOES)},
        "fila_media_ao_encerrar_verde": media(fila_ao_encerrar),
        "pct_verde_encerrado_com_fila_zero": (
            100.0 * sum(1 for f in fila_ao_encerrar if f == 0) / len(fila_ao_encerrar)
            if fila_ao_encerrar else None),
        "pct_troca_para_maior_fila": (
            100.0 * sum(escolheu_maior_fila) / len(escolheu_maior_fila)
            if escolheu_maior_fila else None),
        "pct_troca_em_ordem_ciclica": (
            100.0 * sum(ordem_ciclica) / len(ordem_ciclica) if ordem_ciclica else None),
        "s_verde_ocioso_com_fila_esperando": sum(ocioso) * INTERVALO_DECISAO,
        "maior_verde_ocioso_seguido_s": maior_seq * INTERVALO_DECISAO,
        "_duracoes": duracoes,
        "_duracoes_por_aprox": dict(zip(APROXIMACOES, dur_por_aprox)),
    }


def intervalos_sem_verde(segs, fim):
    """Maior e media do tempo que cada aproximacao passa SEM verde entre dois
    verdes seus (so dentro da hora, entre verdes que terminam antes de 'fim')."""
    saida = {}
    for i, a in enumerate(APROXIMACOES):
        verdes = [s for s in segs if s["tipo"] == "verde" and s["aprox"] == i]
        gaps = []
        for v1, v2 in zip(verdes, verdes[1:]):
            fim_v1 = v1["inicio"] + v1["dur"]
            if v2["inicio"] <= fim:
                gaps.append(v2["inicio"] - fim_v1)
        saida[a] = {"medio": media(gaps), "maximo": max(gaps) if gaps else None}
    return saida


def metricas_esperas(veiculos, filtro=None):
    saida = {}
    for a in APROXIMACOES:
        vs = [v for v in veiculos if v["aprox"] == a and (filtro is None or filtro(v))]
        esperas = [v["espera"] for v in vs]
        # so quem completou a viagem: a espera de quem ficou preso ate o fim
        # do escoamento e um limite inferior (a viagem foi cortada)
        esperas_ok = [v["espera"] for v in vs if v["chegou"]]
        saida[a] = {
            "n_carros": len(vs),
            "espera_media": media(esperas),
            "espera_p95": percentil(esperas, 95) if esperas else None,
            "espera_max": max(esperas) if esperas else None,
            "atraso_entrada_medio": media([v["atraso_entrada"] for v in vs]),
            "nao_chegaram": sum(1 for v in vs if not v["chegou"]),
            "espera_media_so_chegaram": media(esperas_ok),
            "espera_max_so_chegaram": max(esperas_ok) if esperas_ok else None,
            "espera_p95_so_chegaram": percentil(esperas_ok, 95) if esperas_ok else None,
        }
    return saida


def checar_consistencia(reg, segs, metricas, dinamica=None):
    """Confere que o registro bate com as regras do simulador. Levanta erro
    se algo nao fecha -- melhor quebrar do que publicar numero errado."""
    erros = []
    # 1) um registro por segundo simulado, sem buracos
    ts = [t for t, _ in reg.estados]
    if ts != list(range(len(ts))):
        erros.append("segundos registrados nao sao 0,1,2,...")
    if len(ts) != reg.duracao + metricas["segundos_escoamento"]:
        erros.append("total de segundos != duracao + escoamento")
    # 2) sequencia verde -> amarelo -> vermelho -> verde (de outra aproximacao)
    for i, s in enumerate(segs):
        if s["tipo"] == "amarelo":
            ant = segs[i - 1]
            if ant["tipo"] != "verde" or ant["aprox"] != s["aprox"]:
                erros.append(f"amarelo sem verde correspondente em t={s['inicio']}")
            if i + 1 < len(segs):
                if s["dur"] != AMARELO:
                    erros.append(f"amarelo de {s['dur']}s em t={s['inicio']}")
                if segs[i + 1]["tipo"] != "vermelho":
                    erros.append(f"amarelo nao seguido de vermelho em t={s['inicio']}")
        if s["tipo"] == "vermelho" and i + 1 < len(segs):
            prox = segs[i + 1]
            if prox["tipo"] != "verde" or prox["aprox"] == segs[i - 2]["aprox"]:
                erros.append(f"vermelho nao seguido de verde novo em t={s['inicio']}")
        if s["tipo"] == "verde" and s["completo"] and not s["inicial"] \
                and s["dur"] < VERDE_MINIMO:
            erros.append(f"verde de {s['dur']}s (< minimo) em t={s['inicio']}")
    # 3) cada pedido de troca vira exatamente um amarelo
    # (o amarelo comeca no segundo seguinte ao pedido; um pedido feito no
    # ultimo segundo do escoamento nunca chega a ser executado)
    # (na transicao corrigida o amarelo comeca no proprio segundo do pedido)
    corrigida = dinamica is not None and dinamica.transicao_corrigida
    atraso = 0 if corrigida else 1
    ultimo = ts[-1] if ts else -1
    pedidos = sum(1 for d in reg.decisoes
                  if d["escolha"] != d["verde"] and d["t"] + atraso <= ultimo)
    amarelos = sum(1 for s in segs if s["tipo"] == "amarelo")
    if pedidos != amarelos:
        erros.append(f"{pedidos} pedidos de troca, mas {amarelos} amarelos")
    # 4) a espera por veiculo reproduz a espera_media oficial
    if reg.veiculos:
        e = sum(v["espera"] for v in reg.veiculos) / len(reg.veiculos)
        if len(reg.veiculos) != metricas["n_carros"] or abs(e - metricas["espera_media"]) > 1e-9:
            erros.append("esperas por veiculo nao reproduzem espera_media")
    if corrigida:
        # vermelho geral inteiro, e verde executado = tempo que o controlador contou
        for i, s in enumerate(segs[:-1]):
            if s["tipo"] == "vermelho" and s["dur"] != VERMELHO_GERAL:
                erros.append(f"vermelho geral de {s['dur']}s em t={s['inicio']}")
        trocas = {d["t"]: d for d in reg.decisoes if d["escolha"] != d["verde"]}
        for s in segs:
            if s["tipo"] == "verde" and s["completo"]:
                d = trocas.get(s["inicio"] + s["dur"])
                if d is None or d["tempo_no_verde"] != s["dur"]:
                    erros.append(f"verde de {s['dur']}s em t={s['inicio']} nao bate "
                                 f"com tempo_no_verde do controlador")
    if erros:
        raise RuntimeError("; ".join(erros[:10]))


# =========================================================================
# Rodar uma simulacao instrumentada (roda em processo separado)
# =========================================================================
_CACHE_AGENTES = {}


def fabricar(rotulo):
    from controladores import MaxPressure, MaxPressureAjustado, TempoFixo, VerdeFixoIngenuo
    if rotulo == "Webster":
        return TempoFixo()
    if rotulo == "Max-Pressure":
        return MaxPressure()
    if rotulo == "Max-Pressure teto":
        return MaxPressureAjustado()
    if rotulo == "Tempo fixo 30s":
        return VerdeFixoIngenuo()
    from dqn import AgenteDQN
    modelo = ROTULO_MODELO[rotulo]
    if modelo not in _CACHE_AGENTES:  # carrega uma vez, igual avaliar.py
        _CACHE_AGENTES[modelo] = AgenteDQN(treinando=False).carregar(modelo)
    return _CACHE_AGENTES[modelo]


def rodar_instrumentado(cenario, rotulo, seed, arquivo_rotas, dinamica=None,
                        controlador=None):
    reg = Registro()
    ctrl = controlador if controlador is not None else fabricar(rotulo)
    m = simulacao.rodar(ctrl, cenario, arquivo_rotas, seed=seed,
                        instrumentacao=reg, dinamica=dinamica)
    segs = reg.segmentos()
    checar_consistencia(reg, segs, m, dinamica)
    fim_total = reg.duracao + m["segundos_escoamento"]
    # o ultimo trecho pode ter sido cortado pelo fim da simulacao
    dur_red = sorted({s["dur"] for s in segs[:-1] if s["tipo"] == "vermelho"})
    r = {
        "cenario": cenario, "controlador": rotulo, "seed": seed,
        "metricas_oficiais": m,
        "hora": metricas_periodo(segs, reg.decisoes, 0, reg.duracao),
        "escoamento": metricas_periodo(segs, reg.decisoes, reg.duracao, fim_total)
        if fim_total > reg.duracao else None,
        "intervalo_sem_verde_hora": intervalos_sem_verde(segs, reg.duracao),
        "duracoes_vermelho_geral_observadas": dur_red,
        "esperas_por_aprox": metricas_esperas(reg.veiculos),
        "verdes": [[s["inicio"], s["dur"], APROXIMACOES[s["aprox"]]]
                   for s in segs if s["tipo"] == "verde"],
        "intervencoes": reg.intervencoes,
    }
    if cenario == "pico":
        r["pico_periodos"] = [
            metricas_periodo(segs, reg.decisoes, ini, fim) for ini, fim in PERIODOS_PICO
        ]
        # carros agrupados pelo periodo em que ENTRARAM na rede
        r["pico_esperas_por_periodo"] = [
            metricas_esperas(reg.veiculos, lambda v, a=ini, b=fim: a <= v["depart"] < b)
            for ini, fim in PERIODOS_PICO
        ]
    return r


def _tarefa(args):
    t0 = time.time()
    r = rodar_instrumentado(*args)
    r["segundos_cpu"] = time.time() - t0
    return r


# =========================================================================
# Agregacao entre sementes
# =========================================================================
def _ms(v):
    v = [x for x in v if x is not None]
    if not v:
        return {"media": None, "dp": None}
    return {"media": statistics.mean(v), "dp": statistics.stdev(v) if len(v) > 1 else 0.0}


def agregar_periodo(lista):
    """Media +- desvio entre sementes de cada metrica escalar do periodo."""
    chaves = ["trocas", "trocas_por_hora", "s_amarelo", "s_vermelho_geral",
              "pct_amarelo", "pct_vermelho_geral", "pct_transicao",
              "verde_medio", "verde_mediano", "n_verdes_completos", "n_verdes_censurados",
              "fila_media_ao_encerrar_verde", "pct_verde_encerrado_com_fila_zero",
              "pct_troca_para_maior_fila", "pct_troca_em_ordem_ciclica",
              "s_verde_ocioso_com_fila_esperando", "maior_verde_ocioso_seguido_s",
              "segundos_simulados"]
    out = {k: _ms([p[k] for p in lista]) for k in chaves}
    for k in ["pct_verde_por_aprox", "verde_medio_por_aprox", "s_verde_por_aprox"]:
        out[k] = {a: _ms([p[k][a] for p in lista]) for a in APROXIMACOES}
    # verde medio por aproximacao sobre TODOS os verdes das sementes juntas
    out["verde_medio_por_aprox_agrupado"] = {
        a: media([d for p in lista for d in p["_duracoes_por_aprox"][a]]) for a in APROXIMACOES
    }
    todas = [d for p in lista for d in p["_duracoes"]]
    out["histograma_verdes"] = {str(d): todas.count(d) for d in sorted(set(todas))}
    out["verde_medio_agrupado"] = media(todas)
    return out


def agregar_esperas(lista):
    return {a: {k: _ms([e[a][k] for e in lista])
                for k in ["n_carros", "espera_media", "espera_p95", "espera_max",
                          "atraso_entrada_medio", "nao_chegaram",
                          "espera_media_so_chegaram", "espera_max_so_chegaram"]}
            for a in APROXIMACOES}


def agregar(rodadas):
    resumo = {}
    grupos = {}
    for r in rodadas:
        grupos.setdefault((r["cenario"], r["controlador"]), []).append(r)
    for (cen, ctrl), rs in grupos.items():
        rs.sort(key=lambda r: r["seed"])
        item = {
            "sementes": [r["seed"] for r in rs],
            "oficiais": {k: _ms([r["metricas_oficiais"][k] for r in rs])
                         for k in ["espera_media", "espera_p95", "espera_max",
                                   "fila_media", "n_carros", "segundos_escoamento"]},
            "hora": agregar_periodo([r["hora"] for r in rs]),
            "escoamento": agregar_periodo([r["escoamento"] for r in rs if r["escoamento"]]),
            "esperas_por_aprox": agregar_esperas([r["esperas_por_aprox"] for r in rs]),
            "intervalo_sem_verde_hora": {
                a: {"medio": _ms([r["intervalo_sem_verde_hora"][a]["medio"] for r in rs]),
                    "maximo": _ms([r["intervalo_sem_verde_hora"][a]["maximo"] for r in rs])}
                for a in APROXIMACOES},
            "rodadas_que_bateram_limite_escoamento": sum(
                1 for r in rs if r["metricas_oficiais"]["segundos_escoamento"] >= 1200),
            "carros_presos_no_fim_total": sum(
                e["nao_chegaram"] for r in rs for e in r["esperas_por_aprox"].values()),
            "vermelho_geral_executado_s": sorted(
                {d for r in rs for d in r["duracoes_vermelho_geral_observadas"]}),
        }
        if cen == "pico":
            item["pico_periodos"] = [
                agregar_periodo([r["pico_periodos"][k] for r in rs]) for k in range(3)]
            item["pico_esperas_por_periodo"] = [
                agregar_esperas([r["pico_esperas_por_periodo"][k] for r in rs])
                for k in range(3)]
        resumo[f"{cen}|{ctrl}"] = item
    return resumo


# =========================================================================
# Relatorio em texto
# =========================================================================
def _f(x, nd=1):
    return "-" if x is None else f"{x:.{nd}f}"


def relatorio(resumo, cenarios, controladores):
    L = []
    L.append("# Analise de comportamento - resumo\n")
    L.append("Valores = media entre sementes (+- desvio padrao quando indicado). "
             "'Hora' = 0 a 3600 s; o escoamento fica de fora destas tabelas.\n")

    def g(cen, ctrl):
        return resumo.get(f"{cen}|{ctrl}")

    L.append("\n## A/B. Trocas e verdes (primeira hora)\n")
    L.append("| cenario | controlador | trocas/h | % amarelo | % vermelho geral | "
             "verde medio (s) | verde mediano (s) | fila ao encerrar verde | "
             "% trocas p/ maior fila | % ordem ciclica | espera media (s) |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for cen in cenarios:
        for ctrl in controladores:
            x = g(cen, ctrl)
            if not x:
                continue
            h = x["hora"]
            L.append(
                f"| {cen} | {ctrl} | {_f(h['trocas_por_hora']['media'])} +- "
                f"{_f(h['trocas_por_hora']['dp'])} | {_f(h['pct_amarelo']['media'])} | "
                f"{_f(h['pct_vermelho_geral']['media'])} | "
                f"{_f(h['verde_medio']['media'])} +- {_f(h['verde_medio']['dp'])} | "
                f"{_f(h['verde_mediano']['media'])} | "
                f"{_f(h['fila_media_ao_encerrar_verde']['media'])} | "
                f"{_f(h['pct_troca_para_maior_fila']['media'], 0)} | "
                f"{_f(h['pct_troca_em_ordem_ciclica']['media'], 0)} | "
                f"{_f(x['oficiais']['espera_media']['media'])} |")

    L.append("\n## B. Verde por aproximacao (primeira hora)\n")
    L.append("| cenario | controlador | " + " | ".join(
        f"{a}: % verde / verde medio (s)" for a in APROXIMACOES) + " |")
    L.append("|---|---|" + "---|" * 4)
    for cen in cenarios:
        for ctrl in controladores:
            x = g(cen, ctrl)
            if not x:
                continue
            h = x["hora"]
            cel = [f"{_f(h['pct_verde_por_aprox'][a]['media'])} / "
                   f"{_f(h['verde_medio_por_aprox_agrupado'][a])}" for a in APROXIMACOES]
            L.append(f"| {cen} | {ctrl} | " + " | ".join(cel) + " |")

    L.append("\n## C. Cenario pico, por periodo de 20 min\n")
    L.append("| controlador | periodo | trocas/h | verde medio (s) | "
             "% verde N/L/S/O | espera media dos carros que entraram no periodo (s) |")
    L.append("|---|---|---|---|---|---|")
    nomes = ["0-20 min (calmo)", "20-40 min (pico)", "40-60 min (calmo)"]
    for ctrl in controladores:
        x = g("pico", ctrl)
        if not x:
            continue
        for k, p in enumerate(x["pico_periodos"]):
            esp = x["pico_esperas_por_periodo"][k]
            n = sum(esp[a]["n_carros"]["media"] or 0 for a in APROXIMACOES)
            tot = sum((esp[a]["espera_media"]["media"] or 0) * (esp[a]["n_carros"]["media"] or 0)
                      for a in APROXIMACOES)
            pv = "/".join(_f(p["pct_verde_por_aprox"][a]["media"], 0) for a in APROXIMACOES)
            L.append(f"| {ctrl} | {nomes[k]} | {_f(p['trocas_por_hora']['media'])} | "
                     f"{_f(p['verde_medio']['media'])} | {pv} | {_f(tot / n if n else None)} |")

    L.append("\n## D. Espera por aproximacao (todos os carros da rodada)\n")
    L.append("| cenario | controlador | aprox | carros | espera media (s) | P95 (s) | "
             "max (s) | atraso de entrada (s) | maior tempo sem verde (s) |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for cen in cenarios:
        for ctrl in controladores:
            x = g(cen, ctrl)
            if not x:
                continue
            for a in APROXIMACOES:
                e = x["esperas_por_aprox"][a]
                L.append(
                    f"| {cen} | {ctrl} | {a} | {_f(e['n_carros']['media'], 0)} | "
                    f"{_f(e['espera_media']['media'])} | {_f(e['espera_p95']['media'])} | "
                    f"{_f(e['espera_max']['media'])} | {_f(e['atraso_entrada_medio']['media'])} | "
                    f"{_f(x['intervalo_sem_verde_hora'][a]['maximo']['media'])} |")

    L.append("\n## Escoamento: verde ocioso e carros presos no fim\n")
    L.append("Escoamento = depois dos 3600 s, ate o ultimo carro sair ou 1200 s. "
             "'Verde ocioso' = decisao de manter o verde numa aproximacao sem fila "
             "enquanto outra tem carro parado (5 s por decisao).\n")
    L.append("| cenario | controlador | rodadas que bateram 1200 s | carros presos (total 10 sementes) | "
             "verde ocioso na hora (s) | maior verde ocioso seguido na hora (s) | "
             "verde ocioso no escoamento (s) | escoamento medio (s) | "
             "espera media so de quem chegou (s) |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for cen in cenarios:
        for ctrl in controladores:
            x = g(cen, ctrl)
            if not x:
                continue
            h, e, ep = x["hora"], x["escoamento"], x["esperas_por_aprox"]
            n = sum(ep[a]["n_carros"]["media"] for a in APROXIMACOES)
            presos = sum(ep[a]["nao_chegaram"]["media"] for a in APROXIMACOES)
            ok = sum((ep[a]["espera_media_so_chegaram"]["media"] or 0)
                     * (ep[a]["n_carros"]["media"] - ep[a]["nao_chegaram"]["media"])
                     for a in APROXIMACOES)
            ocioso_esc = e.get("s_verde_ocioso_com_fila_esperando", {}).get("media") if e else None
            L.append(
                f"| {cen} | {ctrl} | {x['rodadas_que_bateram_limite_escoamento']}/"
                f"{len(x['sementes'])} | {x['carros_presos_no_fim_total']} | "
                f"{_f(h['s_verde_ocioso_com_fila_esperando']['media'])} | "
                f"{_f(h['maior_verde_ocioso_seguido_s']['media'])} | "
                f"{_f(ocioso_esc)} | "
                f"{_f(x['oficiais']['segundos_escoamento']['media'], 0)} | "
                f"{_f(ok / (n - presos) if n > presos else None)} |")

    L.append("\n## Transicoes realmente executadas\n")
    for cen in cenarios:
        for ctrl in controladores:
            x = g(cen, ctrl)
            if x:
                L.append(f"- {cen} / {ctrl}: vermelho geral executado com "
                         f"{x['vermelho_geral_executado_s']} s")
    return "\n".join(L) + "\n"


# =========================================================================
# Graficos
# =========================================================================
# Paleta categorica de referencia (ordem fixa, nunca reciclada)
CORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"]
CINZA_TEXTO = "#52514e"


def _estilo(plt):
    plt.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 150, "font.size": 10,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#b9b8b3", "axes.labelcolor": "#0b0b0b",
        "xtick.color": CINZA_TEXTO, "ytick.color": CINZA_TEXTO,
        "axes.grid": True, "grid.color": "#e6e5e1", "grid.linewidth": 0.8,
        "axes.axisbelow": True, "legend.frameon": False,
        "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
    })


def _barras(ax, resumo, cenarios, controladores, extrator, ylabel):
    import numpy as np
    n = len(controladores)
    larg = 0.8 / n
    x = np.arange(len(cenarios))
    for i, ctrl in enumerate(controladores):
        med, dp = [], []
        for cen in cenarios:
            v = extrator(resumo[f"{cen}|{ctrl}"]) if f"{cen}|{ctrl}" in resumo else None
            med.append(v["media"] if v and v["media"] is not None else np.nan)
            dp.append(v["dp"] if v and v["dp"] is not None else 0)
        ax.bar(x + (i - (n - 1) / 2) * larg, med, larg * 0.92, yerr=dp, capsize=2,
               color=CORES[i], label=ctrl, error_kw={"elinewidth": 0.8, "ecolor": "#52514e"})
    ax.set_xticks(x)
    ax.set_xticklabels([c + ("\n(nao visto no treino)" if c == "girado" else "")
                        for c in cenarios])
    ax.set_ylabel(ylabel)


def graficos(resumo, rodadas, cenarios, controladores):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    _estilo(plt)
    os.makedirs(PASTA_GRAFICOS, exist_ok=True)
    feitos = []
    rodape = "Barras = media de 10 sementes; traco = desvio padrao entre sementes. Primeira hora (0-3600 s), sem o escoamento."

    def salvar(fig, nome):
        caminho = os.path.join(PASTA_GRAFICOS, nome)
        fig.savefig(caminho, bbox_inches="tight")
        plt.close(fig)
        feitos.append(caminho)

    # 1. trocas por hora
    fig, ax = plt.subplots(figsize=(10, 4.8))
    _barras(ax, resumo, cenarios, controladores,
            lambda x: x["hora"]["trocas_por_hora"], "Trocas de fase por hora")
    ax.set_title("1. Frequencia de trocas de fase, por controlador e cenario")
    ax.legend(ncol=len(controladores), loc="upper center", bbox_to_anchor=(0.5, -0.15))
    fig.text(0.01, -0.08, rodape, fontsize=8, color=CINZA_TEXTO)
    salvar(fig, "1_trocas_por_hora.png")

    # 1b. tempo em transicao
    fig, ax = plt.subplots(figsize=(10, 4.8))
    _barras(ax, resumo, cenarios, controladores,
            lambda x: x["hora"]["pct_transicao"], "% da hora em amarelo + vermelho geral")
    ax.set_title("1b. Parcela do tempo gasta em transicao (amarelo + vermelho geral)")
    ax.legend(ncol=len(controladores), loc="upper center", bbox_to_anchor=(0.5, -0.15))
    fig.text(0.01, -0.08, rodape, fontsize=8, color=CINZA_TEXTO)
    salvar(fig, "1b_tempo_em_transicao.png")

    # 2. verde medio
    fig, ax = plt.subplots(figsize=(10, 4.8))
    _barras(ax, resumo, cenarios, controladores,
            lambda x: x["hora"]["verde_medio"], "Duracao media do verde (s)")
    ax.axhline(VERDE_MINIMO, color=CINZA_TEXTO, lw=1, ls="--")
    ax.text(-0.5, VERDE_MINIMO - 0.4, f"verde minimo de seguranca ({VERDE_MINIMO} s)",
            ha="left", va="top", fontsize=8, color=CINZA_TEXTO)
    ax.set_title("2. Duracao media do verde, por controlador e cenario")
    ax.legend(ncol=len(controladores), loc="upper center", bbox_to_anchor=(0.5, -0.15))
    fig.text(0.01, -0.08, rodape + " So verdes completos.", fontsize=8, color=CINZA_TEXTO)
    salvar(fig, "2_verde_medio.png")

    # 3. distribuicao dos verdes das DQNs (+ referencias), por cenario
    dqns = [c for c in controladores if c.startswith("DQN")]
    refs = [c for c in controladores if not c.startswith("DQN")]
    fig, axes = plt.subplots(len(cenarios), 1, figsize=(10, 2.3 * len(cenarios)), sharex=True)
    axes = np.atleast_1d(axes)
    maxdur = 1
    for r in rodadas:
        if r["hora"]["_duracoes"]:
            maxdur = max(maxdur, max(r["hora"]["_duracoes"]))
    bins = np.arange(VERDE_MINIMO - 0.5, min(maxdur, 160) + 1.5, 1)
    for ax, cen in zip(axes, cenarios):
        for ctrl in dqns:
            d = [x for r in rodadas if r["cenario"] == cen and r["controlador"] == ctrl
                 for x in r["hora"]["_duracoes"]]
            if d:
                ax.hist(d, bins=bins, histtype="step", lw=1.6,
                        color=CORES[controladores.index(ctrl)],
                        weights=np.full(len(d), 100.0 / len(d)), label=ctrl)
        for ctrl in refs:
            d = [x for r in rodadas if r["cenario"] == cen and r["controlador"] == ctrl
                 for x in r["hora"]["_duracoes"]]
            if d:
                ax.hist(d, bins=bins, histtype="stepfilled", alpha=0.18,
                        color=CORES[controladores.index(ctrl)],
                        weights=np.full(len(d), 100.0 / len(d)), label=f"{ctrl} (ref.)")
        ax.set_ylabel("% dos verdes")
        ax.set_title(cen + (" (nao visto no treino)" if cen == "girado" else ""),
                     loc="left", fontsize=10)
    axes[-1].set_xlabel("Duracao do verde executado (s), em classes de 1 s")
    axes[0].legend(ncol=3, fontsize=8, loc="upper right")
    fig.suptitle("3. Distribuicao das duracoes de verde (DQNs = linhas; tradicionais = area clara)",
                 y=1.0)
    fig.text(0.01, -0.01, "Todas as sementes juntas; primeira hora; so verdes completos.",
             fontsize=8, color=CINZA_TEXTO)
    fig.tight_layout()
    salvar(fig, "3_distribuicao_verdes.png")

    # 4. espera media por aproximacao (e P95), um painel por cenario
    for metrica, nome_m, arq in [("espera_media", "Espera media (s)", "4_espera_media_por_aproximacao.png"),
                                 ("espera_p95", "Espera P95 (s)", "4b_espera_p95_por_aproximacao.png"),
                                 ("espera_max", "Espera maxima (s)", "4c_espera_max_por_aproximacao.png")]:
        fig, axes = plt.subplots(1, len(cenarios), figsize=(3.3 * len(cenarios), 4), sharey=False)
        axes = np.atleast_1d(axes)
        for ax, cen in zip(axes, cenarios):
            _barras(ax, {f"{a}|{c}": resumo[f"{cen}|{c}"]["esperas_por_aprox"][a][metrica]
                         for a in APROXIMACOES for c in controladores if f"{cen}|{c}" in resumo},
                    APROXIMACOES, controladores, lambda v: v, "")
            ax.set_title(cen + (" *" if cen == "girado" else ""), fontsize=10)
            ax.set_xlabel("Aproximacao de origem")
        axes[0].set_ylabel(nome_m)
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, ncol=len(controladores), loc="lower center",
                   bbox_to_anchor=(0.5, -0.08))
        fig.suptitle(f"4. {nome_m} dos carros, por aproximacao de origem", y=1.02)
        fig.text(0.01, -0.13, "Espera = waitingTime do SUMO por carro (inclui o escoamento). "
                 "Media de 10 sementes; traco = desvio padrao. * cenario nao visto no treino.\n"
                 "Inclui carros presos ate o corte do escoamento (ver grafico 7); "
                 "por isso a maxima das DQNs chega a ~1200 s.",
                 fontsize=8, color=CINZA_TEXTO)
        fig.tight_layout()
        salvar(fig, arq)

    # 5. evolucao no pico: 4 paineis
    if "pico" in cenarios:
        x = np.arange(3)
        rot = ["0-20 min\n(calmo)", "20-40 min\n(pico)", "40-60 min\n(calmo)"]
        fig, axes = plt.subplots(2, 2, figsize=(11, 7.5))
        paineis = [
            (axes[0, 0], lambda p, e: p["trocas_por_hora"]["media"], "Trocas por hora"),
            (axes[0, 1], lambda p, e: p["verde_medio"]["media"], "Verde medio (s)"),
            (axes[1, 0], lambda p, e: p["fila_media_ao_encerrar_verde"]["media"],
             "Fila da aproximacao ao encerrar o verde (carros)"),
            (axes[1, 1], lambda p, e: (
                sum((e[a]["espera_media"]["media"] or 0) * (e[a]["n_carros"]["media"] or 0)
                    for a in APROXIMACOES) /
                max(sum(e[a]["n_carros"]["media"] or 0 for a in APROXIMACOES), 1)),
             "Espera media dos carros que entraram no periodo (s)"),
        ]
        for ax, fn, yl in paineis:
            for i, ctrl in enumerate(controladores):
                k = f"pico|{ctrl}"
                if k not in resumo:
                    continue
                y = [fn(resumo[k]["pico_periodos"][j], resumo[k]["pico_esperas_por_periodo"][j])
                     for j in range(3)]
                ls = "-" if ctrl.startswith("DQN") else "--"
                ax.plot(x, y, ls, marker="o", ms=6, lw=2, color=CORES[i], label=ctrl)
            ax.set_xticks(x)
            ax.set_xticklabels(rot)
            ax.set_ylabel(yl)
        axes[0, 0].legend(fontsize=8)
        fig.suptitle("5. Cenario pico: comportamento em cada periodo de 20 minutos "
                     "(DQNs = linha cheia; tradicionais = tracejada)")
        fig.text(0.01, -0.01, "Media de 10 sementes. Verdes atribuidos ao periodo em que comecaram.",
                 fontsize=8, color=CINZA_TEXTO)
        fig.tight_layout()
        salvar(fig, "5_evolucao_pico.png")

    # 7. carros presos no fim do escoamento
    fig, ax = plt.subplots(figsize=(10, 4.5))
    _barras(ax, resumo, cenarios, controladores,
            lambda x: {"media": sum(x["esperas_por_aprox"][a]["nao_chegaram"]["media"]
                                    for a in APROXIMACOES), "dp": 0},
            "Carros que nunca sairam (media por rodada)")
    ax.set_title("7. Carros presos quando o escoamento atinge o limite de 1200 s")
    ax.legend(ncol=len(controladores), loc="upper center", bbox_to_anchor=(0.5, -0.15), fontsize=8)
    fig.text(0.01, -0.08, "Media de 10 sementes. Esses carros ficaram parados ate a simulacao "
             "ser cortada: a espera registrada deles e um limite inferior.",
             fontsize=8, color=CINZA_TEXTO)
    salvar(fig, "7_carros_presos_no_fim.png")

    # 6. parcela do verde por aproximacao (barras empilhadas)
    fig, axes = plt.subplots(1, len(cenarios), figsize=(3.3 * len(cenarios), 4.2), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, cen in zip(axes, cenarios):
        base = np.zeros(len(controladores))
        for j, a in enumerate(APROXIMACOES):
            v = np.array([resumo[f"{cen}|{c}"]["hora"]["pct_verde_por_aprox"][a]["media"]
                          if f"{cen}|{c}" in resumo else np.nan for c in controladores])
            ax.bar(range(len(controladores)), v, 0.75, bottom=base, color=CORES[j],
                   edgecolor="#fcfcfb", lw=1.5, label=a)
            base += v
        ax.set_xticks(range(len(controladores)))
        ax.set_xticklabels(controladores, rotation=45, ha="right", fontsize=8)
        ax.set_title(cen + (" *" if cen == "girado" else ""), fontsize=10)
        ax.set_ylim(0, 100)
    axes[0].set_ylabel("% do tempo de verde da hora")
    axes[-1].legend(title="Aproximacao", loc="upper left", bbox_to_anchor=(1, 1))
    fig.suptitle("6. Como cada controlador reparte o verde entre as aproximacoes", y=1.02)
    fig.tight_layout()
    salvar(fig, "6_parcela_verde_por_aproximacao.png")
    return feitos


# =========================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--sementes", type=int, nargs="*", default=None,
                    help="padrao: as mesmas de avaliar.py")
    ap.add_argument("--cenarios", nargs="*", default=None,
                    help="padrao: os mesmos de avaliar.py")
    ap.add_argument("--processos", type=int, default=max(1, min(6, (os.cpu_count() or 2) - 1)))
    ap.add_argument("--todos", action="store_true",
                    help="inclui Max-Pressure teto e tempo fixo 30s")
    ap.add_argument("--so-graficos", action="store_true",
                    help="nao simula; refaz relatorio e graficos de rodadas.json")
    args = ap.parse_args()

    controladores = CONTROLADORES_PADRAO + (EXTRAS if args.todos else [])
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    caminho_rodadas = os.path.join(PASTA_SAIDA, "rodadas.json")

    if args.so_graficos:
        with open(caminho_rodadas) as f:
            salvo = json.load(f)
        rodadas = salvo["rodadas"]
        controladores = salvo["controladores"]
        cenarios = salvo["cenarios"]
    else:
        import avaliar  # so aqui: puxa o torch, que o modo --so-graficos dispensa
        cenarios = args.cenarios or avaliar.CENARIOS
        args.sementes = args.sementes or avaliar.SEMENTES
        rotas = {c: gerar_demanda.gerar(c) for c in cenarios}
        tarefas = [(c, ctrl, s, rotas[c]) for c in cenarios for ctrl in controladores
                   for s in args.sementes]
        print(f"{len(tarefas)} simulacoes instrumentadas "
              f"({len(cenarios)} cenarios x {len(controladores)} controladores x "
              f"{len(args.sementes)} sementes), {args.processos} processos", flush=True)
        t0 = time.time()
        rodadas = []
        with Pool(args.processos) as pool:
            for i, r in enumerate(pool.imap_unordered(_tarefa, tarefas), 1):
                rodadas.append(r)
                if i % 10 == 0 or i == len(tarefas):
                    print(f"  {i}/{len(tarefas)}  ({time.time() - t0:.0f} s)", flush=True)
        rodadas.sort(key=lambda r: (cenarios.index(r["cenario"]),
                                    controladores.index(r["controlador"]), r["seed"]))
        with open(caminho_rodadas, "w") as f:
            json.dump({"cenarios": cenarios, "controladores": controladores,
                       "sementes": args.sementes, "rodadas": rodadas}, f)

    resumo = agregar(rodadas)
    with open(os.path.join(PASTA_SAIDA, "resumo.json"), "w") as f:
        json.dump(resumo, f, indent=1)
    texto = relatorio(resumo, cenarios, controladores)
    with open(os.path.join(PASTA_SAIDA, "resumo.md"), "w", encoding="utf-8") as f:
        f.write(texto)
    print(f"\nTabelas: {os.path.join(PASTA_SAIDA, 'resumo.md')}")
    try:
        feitos = graficos(resumo, rodadas, cenarios, controladores)
    except ImportError as e:
        print(f"\nNao consegui importar o matplotlib neste Python ({e}).\n"
              "As simulacoes ja estao salvas. Para gerar so os graficos, rode com\n"
              "um Python que tenha matplotlib funcionando:\n"
              "  py analisar_comportamento.py --so-graficos")
        return 1
    print(f"\nResultados em {PASTA_SAIDA}")
    for c in feitos:
        print("  ", os.path.relpath(c, PASTA_SAIDA))


if __name__ == "__main__":
    sys.exit(main())
