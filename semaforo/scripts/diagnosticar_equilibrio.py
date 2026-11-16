"""
Diagnostico antes de treinar uma DQN "mais justa" com as ruas secundarias.

So LE modelos e resultados; tudo que produz vai para
resultados/diagnostico_equilibrio/. Nao treina nada e nao muda a dinamica C.

Partes (de dentro de scripts/):
  python diagnosticar_equilibrio.py --presos     # ETAPA 1: reproduz SO as rodadas com
                                                 #   veiculo nao atendido (lidas de avaliacao.json)
  python diagnosticar_equilibrio.py --automato   # ETAPA 1: "carro sozinho" -- testa as 6 redes
                                                 #   sem simulador (a rede atende um carro isolado?)
  python diagnosticar_equilibrio.py --esperas    # ETAPA 2: esperas por direcao (avaliacao.json)
                                                 #   + rodadas instrumentadas de girado/assimetrico
  python diagnosticar_equilibrio.py --relatorio  # junta tudo em resumo.md
  py diagnosticar_equilibrio.py --so-graficos    # graficos (Python com matplotlib)

Toda rodada reproduzida e conferida contra avaliacao.json: as metricas tem
de ser identicas (a instrumentacao so observa).
"""

import argparse
import json
import os
import statistics
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from multiprocessing import Pool

import gerar_demanda
import simulacao
import analisar_comportamento as ac
from simulacao import APROXIMACOES, DINAMICAS, FAIXAS_ENTRADA, Observacao

DIN = DINAMICAS["C"]
PASTA_COMP = os.path.join(simulacao.PASTA, "resultados", "comparacao_C")
AVALIACAO = os.path.join(PASTA_COMP, "avaliacao.json")
PASTA = os.path.join(simulacao.PASTA, "resultados", "diagnostico_equilibrio")
PASTA_GRAFICOS = os.path.join(PASTA, "graficos")
ARQ = {p: os.path.join(PASTA, f"{p}.json") for p in ("presos", "automato", "esperas")}

DQNS = ["DQN original", "DQN seed1", "DQN seed2", "DQN C seed0", "DQN C seed1", "DQN C seed2"]
MODELO = {"DQN original": "dqn_fila", "DQN seed1": "dqn_fila_seed1",
          "DQN seed2": "dqn_fila_seed2", **{f"DQN C seed{i}": f"dqn_fila_C_seed{i}" for i in range(3)}}
REFERENCIAS = ["Webster", "Max-Pressure teto (recal. C)"]
# qual par e a rua secundaria (menos demanda) em cada cenario
SECUNDARIAS = {"girado": ["L", "O"], "assimetrico": ["N", "S"]}
CHAVES_CONFERIDAS = ["n_carros", "espera_media", "espera_p95", "espera_max", "fila_media",
                     "segundos_escoamento", "veiculos_sem_atendimento",
                     "verde_max_executado_total", "intervencoes_seguranca_hora",
                     "intervencoes_seguranca_escoamento"]
LIMIAR_ESPERA = 120  # s: o que chamamos de "espera extrema" por carro


def _salvas():
    with open(AVALIACAO) as f:
        return {(r["cenario"], r["controlador"], r["seed"]): r for r in json.load(f)["rodadas"]}


def _conferir(m, ref, rotulo):
    dif = {k: (m[k], ref[k]) for k in CHAVES_CONFERIDAS if m[k] != ref[k]}
    if dif:
        raise RuntimeError(f"{rotulo}: rodada difere de avaliacao.json: {dif}")


def _p(v, q):
    if not v:
        return None
    s = sorted(v)
    return s[int(round(q / 100 * (len(s) - 1)))]


def _media(v):
    return statistics.mean(v) if v else None


# =========================================================================
# Instrumentacao (so observa): carros por faixa, tempo sem verde, valores Q
# =========================================================================
class RegistroDetalhado(ac.Registro):
    def __init__(self, agente=None, acompanhar_carros=True):
        self.agente = agente
        self.acompanhar = acompanhar_carros

    def inicio(self, estados_verdes, duracao):
        super().inicio(estados_verdes, duracao)
        self.ultimo_verde = [0] * 4  # ultimo segundo com verde de cada aproximacao
        self.entrada = {}  # carro -> (aprox, primeiro segundo visto na via de entrada)
        self.cruzou = {}  # carro -> segundo em que saiu da via de entrada
        self._na_entrada = set()
        self.fotos_finais = []  # carros na rede no fim (so com poucos carros)

    def passo(self, segundo, estado):
        super().passo(segundo, estado)
        tipo, i = self.classificar(estado)
        if tipo == "verde":
            self.ultimo_verde[i] = segundo
        if not self.acompanhar:
            return
        tr = simulacao.trafego
        agora = {}
        for a, faixas in FAIXAS_ENTRADA.items():
            for f in faixas:
                for v in tr.lane.getLastStepVehicleIDs(f):
                    agora[v] = a
        for v, a in agora.items():
            if v not in self.entrada:
                self.entrada[v] = (a, segundo)
        for v in self._na_entrada - agora.keys():
            self.cruzou[v] = segundo
        self._na_entrada = set(agora)
        if segundo >= self.duracao and segundo % 60 == 0:
            ids = tr.vehicle.getIDList()
            if 0 < len(ids) <= 3:
                self.fotos_finais.append({"t": segundo, "estado": estado, "carros": [
                    {"id": v, "faixa": tr.vehicle.getLaneID(v),
                     "posicao_m": round(tr.vehicle.getLanePosition(v), 1),
                     "comprimento_faixa_m": round(tr.lane.getLength(tr.vehicle.getLaneID(v)), 1),
                     "velocidade": round(tr.vehicle.getSpeed(v), 2),
                     "espera_s": tr.vehicle.getWaitingTime(v)} for v in ids]})

    def decisao(self, obs, escolha):
        super().decisao(obs, escolha)
        d = self.decisoes[-1]
        d["sem_verde"] = [0 if APROXIMACOES[i] == obs.aprox_verde else obs.segundo - self.ultimo_verde[i]
                          for i in range(4)]
        if self.agente is not None:
            import torch
            with torch.no_grad():
                q = self.agente.rede(torch.from_numpy(self.agente.vetor(obs)).unsqueeze(0))[0]
            d["q"] = [round(x, 4) for x in q.tolist()]

    def fim(self, caminho):
        super().fim(caminho)
        self.viagens = {}
        if os.path.exists(caminho):
            for v in ET.parse(caminho).getroot():
                self.viagens[v.get("id")] = {
                    "espera": float(v.get("waitingTime", 0)),
                    "chegou": float(v.get("arrival", -1)) >= 0,
                    "depart": float(v.get("depart", -1))}


def _rodar(cenario, rotulo, seed, rotas, agente_q=False, acompanhar=True):
    import avaliar_C
    ctrl = avaliar_C.fabricar(rotulo)
    reg = RegistroDetalhado(agente=ctrl if agente_q else None, acompanhar_carros=acompanhar)
    m = simulacao.rodar(ctrl, cenario, rotas, seed=seed, instrumentacao=reg, dinamica=DIN)
    return m, reg


# =========================================================================
# ETAPA 1a: as rodadas com veiculo nao atendido
# =========================================================================
def _ciclo(decisoes):
    """Menor sequencia de decisoes que se repete identica ate o fim."""
    chave = [(d["verde"], d["tempo_no_verde"], d["escolha"], tuple(d["filas"]), tuple(d["carros"]))
             for d in decisoes]
    for n in range(1, 13):
        if len(chave) >= 3 * n and all(chave[-i] == chave[-i - n] for i in range(1, 2 * n + 1)):
            return n, chave[-n:]
    return None, None


def _tarefa_preso(args):
    cenario, rotulo, seed, rotas = args
    m, reg = _rodar(cenario, rotulo, seed, rotas, agente_q=True)
    _conferir(m, _salvas()[(cenario, rotulo, seed)]["metricas"], f"{cenario}|{rotulo}|{seed}")
    presos = [v for v, x in reg.viagens.items() if not x["chegou"]]
    carros = []
    for v in presos:
        aprox, t_ent = reg.entrada.get(v, (v.split("_")[1], None))
        carros.append({"id": v, "aprox": aprox, "entrou_na_via_s": t_ent,
                       "espera_registrada_s": reg.viagens[v]["espera"],
                       "ultimo_verde_da_aprox_s": reg.ultimo_verde[APROXIMACOES.index(aprox)]})
    esc = [d for d in reg.decisoes if d["t"] >= reg.duracao]
    # quando o ultimo carro "normal" saiu: a partir dai, so sobram os presos na rede
    n_ciclo, ciclo = _ciclo(esc)
    segs = reg.segmentos()
    verdes_esc = [s for s in segs if s["tipo"] == "verde" and s["inicio"] >= reg.duracao]
    aprox_presas = {APROXIMACOES.index(c["aprox"]) for c in carros}
    # a regra de seguranca so age em "manter verde >= 60 s com carro em outro lado"
    violacoes = [d for d in reg.decisoes if d["escolha"] == d["verde"] and d["tempo_no_verde"] >= 60
                 and any(c > 0 for i, c in enumerate(d["carros"]) if i != d["verde"])]
    return {
        "cenario": cenario, "controlador": rotulo, "seed": seed,
        "metricas_identicas_a_avaliacao": True,
        "carros_presos": carros,
        "fotos_finais": reg.fotos_finais[:3] + reg.fotos_finais[-1:],
        "ultimas_decisoes": [{**d, "verde": APROXIMACOES[d["verde"]],
                              "escolha": APROXIMACOES[d["escolha"]]} for d in esc[-8:]],
        "ciclo_final": {"tamanho_decisoes": n_ciclo,
                        "passos": [{"verde": APROXIMACOES[c[0]], "tempo_no_verde": c[1],
                                    "escolha": APROXIMACOES[c[2]]} for c in ciclo]} if ciclo else None,
        "verdes_no_escoamento_por_aprox": dict(Counter(APROXIMACOES[s["aprox"]] for s in verdes_esc)),
        "aprox_presa_recebeu_verde_depois_de_parar": any(
            s["aprox"] in aprox_presas and s["inicio"] > min(
                (c["entrou_na_via_s"] or 0) for c in carros) + 30 for s in verdes_esc),
        "maior_verde_no_escoamento_s": max((s["dur"] for s in verdes_esc), default=0),
        "intervencoes": len(reg.intervencoes),
        "decisoes_que_deveriam_ter_acionado_a_regra_sem_acionar": [
            d for d in violacoes if d["t"] not in {i["t"] for i in reg.intervencoes}],
        "metricas": {k: m[k] for k in ["n_carros", "veiculos_concluidos", "veiculos_interrompidos",
                                       "veiculos_sem_atendimento", "veiculos_na_rede_no_fim",
                                       "veiculos_aguardando_entrada_no_fim", "escoamento_cortado",
                                       "segundos_escoamento", "espera_media", "espera_media_concluidos",
                                       "espera_max", "espera_max_concluidos", "espera_p95",
                                       "espera_p95_concluidos", "verde_max_executado_total"]},
    }


def presos(processos):
    salvas = _salvas()
    casos = sorted(k for k, r in salvas.items() if r["metricas"]["veiculos_sem_atendimento"] > 0)
    print(f"{len(casos)} rodadas com veiculo nao atendido (de {len(salvas)})")
    rotas = {c: gerar_demanda.gerar(c) for c in {k[0] for k in casos}}
    with Pool(processos) as pool:
        res = pool.map(_tarefa_preso, [(c, r, s, rotas[c]) for c, r, s in casos])
    # conferencia da contabilizacao, sem simular nada: em cada (cenario, semente) o
    # numero de carros e o mesmo para todos os controladores?
    n_por_rodada = defaultdict(set)
    for (c, r, s), x in salvas.items():
        n_por_rodada[(c, s)].add(x["metricas"]["n_carros"])
    contagem = {
        "n_carros_igual_entre_controladores_em_cada_cenario_semente": all(
            len(v) == 1 for v in n_por_rodada.values()),
        "concluidos_mais_interrompidos_igual_n_carros": all(
            x["metricas"]["veiculos_concluidos"] + x["metricas"]["veiculos_interrompidos"]
            == x["metricas"]["n_carros"] for x in salvas.values()),
        "sem_atendimento_igual_interrompidos": all(
            x["metricas"]["veiculos_sem_atendimento"] == x["metricas"]["veiculos_interrompidos"]
            for x in salvas.values()),
        "rodadas_com_escoamento_cortado": sum(x["metricas"]["escoamento_cortado"] for x in salvas.values()),
    }
    saida = {"casos": res, "contagem": contagem,
             "total_carros_nao_atendidos": sum(len(r["carros_presos"]) for r in res)}
    _gravar("presos", saida)
    for r in res:
        cp = r["carros_presos"]
        print(f"  {r['cenario']:12s} {r['controlador']:12s} s{r['seed']:<2d} presos "
              f"{[(c['aprox'], c['espera_registrada_s']) for c in cp]} ciclo "
              f"{[(p['verde'], p['tempo_no_verde'], p['escolha']) for p in (r['ciclo_final'] or {}).get('passos', [])]}")
    print("  contagem:", contagem)


# =========================================================================
# ETAPA 1b: o "carro sozinho", sem simulador
# =========================================================================
def _automato(agente, verde, aprox_carro, carros=1, limite=1200):
    """Um carro parado sozinho em aprox_carro, verde em `verde` com 10 s.
    Repete a politica gulosa da rede, com a mesma regra de seguranca e o
    mesmo relogio da dinamica C (troca = 5 s de transicao + 10 s minimos).
    Devolve ('atende', segundos, via_regra) ou ('ciclo', fases visitadas).

    Redes de 17 entradas tambem veem a maior espera por aproximacao: o carro
    parado ha t segundos (os outros lados, vazios, tem 0). O ciclo e detectado
    pelo vetor de entrada completo repetido (com o teto da normalizacao, a
    espera do carro para de mudar depois de 360 s)."""
    filas = {a: 0 for a in APROXIMACOES}
    filas[aprox_carro] = carros
    zeros = {a: 0 for a in APROXIMACOES}
    v, tv, t, vistos, fases = verde, 10, 0, set(), [verde]
    while t < limite:
        espera = {a: (float(t) if a == aprox_carro else 0.0) for a in APROXIMACOES}
        obs = Observacao(dict(filas), dict(filas), zeros, v, tv, zeros, t,
                         maior_espera=espera if getattr(agente, "observa_espera", False) else None)
        pedido = APROXIMACOES[agente._escolher(obs)]
        escolha, regra = pedido, False
        if pedido == v and tv >= simulacao.VERDE_MAXIMO_PADRAO:
            escolha, regra = aprox_carro, True  # unico lado com carro
        if escolha == aprox_carro:
            return "atende", t + simulacao.AMARELO + simulacao.VERMELHO_GERAL, regra
        if escolha == v:
            tv += simulacao.INTERVALO_DECISAO
            t += simulacao.INTERVALO_DECISAO
        else:
            v, tv = escolha, simulacao.VERDE_MINIMO
            t += simulacao.AMARELO + simulacao.VERMELHO_GERAL + simulacao.VERDE_MINIMO
            fases.append(v)
        espera = {a: (float(t) if a == aprox_carro else 0.0) for a in APROXIMACOES}
        prox = Observacao(dict(filas), dict(filas), zeros, v, tv, zeros, t, maior_espera=espera
                          if getattr(agente, "observa_espera", False) else None)
        chave = (v, tv, agente.vetor(prox).tobytes())
        if chave in vistos:
            return "ciclo", fases, False
        vistos.add(chave)
    return "limite", fases, False


def automato():
    from dqn import AgenteDQN
    saida = {}
    for rotulo in DQNS:
        ag = AgenteDQN(treinando=False).carregar(MODELO[rotulo])
        casos = []
        for n in (1, 2, 3):
            for v in APROXIMACOES:
                for c in APROXIMACOES:
                    if c == v:
                        continue
                    r = _automato(ag, v, c, carros=n)
                    casos.append({"carros": n, "verde": v, "carro_em": c, "resultado": r[0],
                                  "segundos_ate_verde": r[1] if r[0] == "atende" else None,
                                  "via_regra_de_seguranca": r[2],
                                  "fases_do_ciclo": r[1] if r[0] != "atende" else None})
        saida[rotulo] = {
            "casos": casos,
            **{f"presos_com_{n}_carro{'s' if n > 1 else ''}": sum(
                1 for x in casos if x["carros"] == n and x["resultado"] != "atende") for n in (1, 2, 3)},
            "atendidos_so_pela_regra": sum(1 for x in casos if x["via_regra_de_seguranca"]),
        }
        print(f"  {rotulo:12s} presos (de 12) com 1/2/3 carros: "
              f"{saida[rotulo]['presos_com_1_carro']}/{saida[rotulo]['presos_com_2_carros']}/"
              f"{saida[rotulo]['presos_com_3_carros']}  atendidos so pela regra: "
              f"{saida[rotulo]['atendidos_so_pela_regra']}")
    _gravar("automato", saida)


# =========================================================================
# ETAPA 2: esperas por direcao
# =========================================================================
def _tarefa_esperas(args):
    cenario, rotulo, seed, rotas = args
    m, reg = _rodar(cenario, rotulo, seed, rotas)
    _conferir(m, _salvas()[(cenario, rotulo, seed)]["metricas"], f"{cenario}|{rotulo}|{seed}")
    segs = reg.segmentos()
    verdes = defaultdict(list)  # aprox -> [(inicio, fim)]
    for s in segs:
        if s["tipo"] == "verde":
            verdes[s["aprox"]].append((s["inicio"], s["inicio"] + s["dur"]))
    carros = []
    for v, (aprox, t_ent) in reg.entrada.items():
        if v not in reg.viagens:
            continue
        i = APROXIMACOES.index(aprox)
        t_cruz = reg.cruzou.get(v)
        fim = t_cruz if t_cruz is not None else reg.estados[-1][0]
        # verdes da propria aproximacao que TERMINARAM com o carro ja perto da
        # retencao (>= 20 s depois de entrar na via de 240 m, ~17 s a 50 km/h) e
        # antes de ele cruzar: o carro "ficou para o proximo verde"
        perdidos = sum(1 for a, b in verdes[i] if t_ent + 20 < b < fim - 1)
        # maior trecho sem verde da propria aproximacao durante a estadia
        livres = [(a, b) for a, b in verdes[i] if b > t_ent and a < fim]
        maior_vermelho = 0
        cursor = t_ent
        for a, b in sorted(livres):
            maior_vermelho = max(maior_vermelho, max(0, a - cursor))
            cursor = max(cursor, b)
        maior_vermelho = max(maior_vermelho, max(0, fim - cursor))
        carros.append({"aprox": aprox, "hora": t_ent < reg.duracao,
                       "espera": reg.viagens[v]["espera"], "chegou": reg.viagens[v]["chegou"],
                       "verdes_proprios_que_perdeu": perdidos, "maior_vermelho_s": maior_vermelho})
    # decisoes da hora: o que a rede fez com quem estava esperando
    trocas = []
    for d in reg.decisoes:
        if d["t"] >= reg.duracao or d["escolha"] == d["verde"]:
            continue
        trocas.append({"para": d["escolha"], "filas": d["filas"], "sem_verde": d["sem_verde"]})
    fila_ao_encerrar = defaultdict(list)
    for d in reg.decisoes:
        if d["t"] < reg.duracao and d["escolha"] != d["verde"]:
            fila_ao_encerrar[d["verde"]].append(d["filas"][d["verde"]])
    return {"cenario": cenario, "controlador": rotulo, "seed": seed, "carros": carros,
            "trocas": trocas,
            "fila_ao_encerrar_verde": {APROXIMACOES[i]: v for i, v in fila_ao_encerrar.items()},
            "verdes": {APROXIMACOES[i]: [b - a for a, b in v if a < reg.duracao] for i, v in verdes.items()}}


def _resumir_rodadas(rodadas, cenario):
    """Agrega as rodadas instrumentadas de UM cenario por controlador."""
    sec = SECUNDARIAS[cenario]
    out = {}
    for rotulo in sorted({r["controlador"] for r in rodadas}, key=(DQNS + REFERENCIAS).index):
        rs = [r for r in rodadas if r["controlador"] == rotulo]
        carros = [c for r in rs for c in r["carros"] if c["hora"]]
        ext = [c for c in carros if c["espera"] >= LIMIAR_ESPERA]
        por_aprox = {}
        for a in APROXIMACOES:
            ca = [c for c in carros if c["aprox"] == a]
            ea = [c for c in ca if c["espera"] >= LIMIAR_ESPERA]
            por_aprox[a] = {
                "n": len(ca), "espera_media": _media([c["espera"] for c in ca]),
                "espera_p95": _p([c["espera"] for c in ca], 95),
                "pct_extremos": 100 * len(ea) / len(ca) if ca else 0,
                "pct_que_perdeu_ao_menos_um_verde": 100 * sum(
                    c["verdes_proprios_que_perdeu"] > 0 for c in ca) / len(ca) if ca else 0,
                "fila_media_ao_encerrar_seu_verde": _media(
                    [x for r in rs for x in r["fila_ao_encerrar_verde"].get(a, [])]),
                "verde_medio_s": _media([x for r in rs for x in r["verdes"].get(a, [])]),
            }
        # quando a secundaria FINALMENTE recebe verde: quanto esperou e que fila tinha
        recebe = [t for r in rs for t in r["trocas"] if APROXIMACOES[t["para"]] in sec]
        # trocas para a principal enquanto uma secundaria ja tinha fila ha >= 90 s
        para_principal = [t for r in rs for t in r["trocas"] if APROXIMACOES[t["para"]] not in sec]
        preteriu = [t for t in para_principal if any(
            t["filas"][APROXIMACOES.index(a)] > 0 and t["sem_verde"][APROXIMACOES.index(a)] >= 90
            for a in sec)]
        # padrao dos carros extremos
        out[rotulo] = {
            "por_aprox": por_aprox,
            "n_carros_extremos": len(ext),
            "pct_extremos_na_secundaria": 100 * sum(c["aprox"] in sec for c in ext) / len(ext) if ext else 0,
            "extremos_que_nao_perderam_verde_pct": 100 * sum(
                c["verdes_proprios_que_perdeu"] == 0 for c in ext) / len(ext) if ext else 0,
            "extremos_maior_vermelho_medio_s": _media([c["maior_vermelho_s"] for c in ext]),
            "secundaria_recebe_verde": {
                "n": len(recebe),
                "fila_media": _media([t["filas"][t["para"]] for t in recebe]),
                "tempo_sem_verde_medio_s": _media([t["sem_verde"][t["para"]] for t in recebe]),
                "tempo_sem_verde_p95_s": _p([t["sem_verde"][t["para"]] for t in recebe], 95),
                "fila_media_nas_principais_nesse_momento": _media(
                    [sum(t["filas"][i] for i, a in enumerate(APROXIMACOES) if a not in sec) for t in recebe]),
            },
            "pct_trocas_para_principal_com_secundaria_esperando_90s": (
                100 * len(preteriu) / len(para_principal) if para_principal else 0),
            "dessas_fila_media_da_principal_escolhida": _media([t["filas"][t["para"]] for t in preteriu]),
            "dessas_fila_media_da_secundaria_preterida": _media([max(
                t["filas"][APROXIMACOES.index(a)] for a in sec) for t in preteriu]),
        }
    return out


def _resumo_avaliacao():
    """Esperas por direcao direto de avaliacao.json (sem simular)."""
    with open(AVALIACAO) as f:
        d = json.load(f)
    demanda = {c: {a: sum(q[a] * (b - a0) for a0, b, q in gerar_demanda.CENARIOS[c]) / 3600
                   for a in APROXIMACOES} for c in d["cenarios"]}
    g = defaultdict(list)
    for r in d["rodadas"]:
        g[(r["cenario"], r["controlador"])].append(r)
    out = {}
    for cen in d["cenarios"]:
        tot = sum(demanda[cen].values())
        out[cen] = {"demanda_veic_h": demanda[cen],
                    "pct_demanda": {a: 100 * demanda[cen][a] / tot for a in APROXIMACOES}, "controladores": {}}
        for ctrl in d["controladores"]:
            rs = g[(cen, ctrl)]
            out[cen]["controladores"][ctrl] = {a: {
                "espera_media": _media([r["esperas_por_aprox"][a]["espera_media"] for r in rs]),
                "espera_p95": _media([r["esperas_por_aprox"][a]["espera_p95"] for r in rs]),
                "espera_max": max(r["esperas_por_aprox"][a]["espera_max"] for r in rs),
                "sem_verde_medio_s": _media([r["intervalo_sem_verde_hora"][a]["medio"] for r in rs]),
                "sem_verde_max_s": max(r["intervalo_sem_verde_hora"][a]["maximo"] for r in rs),
                "pct_verde": _media([r["hora"]["pct_verde_por_aprox"][a] for r in rs]),
            } for a in APROXIMACOES}
    return out


def esperas(processos):
    salvas = _salvas()
    sementes = sorted({k[2] for k in salvas})
    cenarios = list(SECUNDARIAS)
    rotas = {c: gerar_demanda.gerar(c) for c in cenarios}
    tarefas = [(c, r, s, rotas[c]) for c in cenarios for r in DQNS + REFERENCIAS for s in sementes]
    print(f"{len(tarefas)} rodadas instrumentadas (ja feitas na avaliacao; conferidas uma a uma)")
    with Pool(processos) as pool:
        rodadas = pool.map(_tarefa_esperas, tarefas, chunksize=2)
    saida = {"limiar_espera_extrema_s": LIMIAR_ESPERA, "secundarias": SECUNDARIAS,
             "por_direcao_avaliacao": _resumo_avaliacao(),
             "instrumentado": {c: _resumir_rodadas([r for r in rodadas if r["cenario"] == c], c)
                               for c in cenarios}}
    _gravar("esperas", saida)
    for c in cenarios:
        print(f"== {c}")
        for rot, x in saida["instrumentado"][c].items():
            s = x["secundaria_recebe_verde"]
            print(f"  {rot:28s} extremos {x['n_carros_extremos']:4d} ({x['pct_extremos_na_secundaria']:5.1f}% sec, "
                  f"{x['extremos_que_nao_perderam_verde_pct']:5.1f}% num vermelho so) | sec recebe verde apos "
                  f"{s['tempo_sem_verde_medio_s']:.0f}s (P95 {s['tempo_sem_verde_p95_s']}) fila {s['fila_media']:.1f} "
                  f"| preteriu {x['pct_trocas_para_principal_com_secundaria_esperando_90s']:.0f}%")


# =========================================================================
def _gravar(parte, dados):
    os.makedirs(PASTA, exist_ok=True)
    with open(ARQ[parte], "w") as f:
        json.dump(dados, f, indent=1)
    print(f"Salvo em {ARQ[parte]}")


def _ler(parte):
    with open(ARQ[parte]) as f:
        return json.load(f)


def _f(x, nd=1):
    return "-" if x is None else f"{x:.{nd}f}"


def relatorio():
    pr, au, es = _ler("presos"), _ler("automato"), _ler("esperas")
    L = ["# Diagnostico: veiculos nao atendidos e esperas por direcao", "",
         "Dinamica C, sementes de teste. Toda rodada reproduzida deu metricas identicas a "
         "`comparacao_C/avaliacao.json`.", "",
         "## 1. Veiculos nao atendidos", "",
         f"{len(pr['casos'])} rodadas (de 550) com {pr['total_carros_nao_atendidos']} veiculos nao atendidos. "
         "Em todas o escoamento foi cortado no limite de 1200 s.", "",
         "| cenario | controlador | semente | carro preso (aprox.) | espera registrada (s) | ciclo final (verde, s de verde -> escolha) | maior verde no escoamento (s) | intervencoes |",
         "|---|---|---|---|---|---|---|---|"]
    for r in pr["casos"]:
        ciclo = " ; ".join(f"{p['verde']} {p['tempo_no_verde']}->{p['escolha']}"
                           for p in (r["ciclo_final"] or {}).get("passos", [])) or "-"
        L.append(f"| {r['cenario']} | {r['controlador']} | {r['seed']} | "
                 f"{', '.join(c['aprox'] for c in r['carros_presos'])} | "
                 f"{', '.join(f'{c['espera_registrada_s']:.0f}' for c in r['carros_presos'])} | {ciclo} | "
                 f"{r['maior_verde_no_escoamento_s']} | {r['intervencoes']} |")
    L += ["", "Conferencia da contagem: " + ", ".join(f"{k} = {v}" for k, v in pr["contagem"].items()), "",
          "### Teste do carro sozinho (sem simulador)", "",
          "Um carro parado sozinho numa aproximacao; verde em outra. Quantas das 12 combinacoes "
          "(verde, aproximacao do carro) a rede NUNCA atende (fica num ciclo entre fases vazias)?", "",
          "| rede | presos com 1 carro | com 2 carros | com 3 carros | atendidos so pela regra de seguranca |",
          "|---|---|---|---|---|"]
    for rot, x in au.items():
        L.append(f"| {rot} | {x['presos_com_1_carro']}/12 | {x['presos_com_2_carros']}/12 | "
                 f"{x['presos_com_3_carros']}/12 | {x['atendidos_so_pela_regra']} |")
    L += ["", "## 2. Esperas por direcao", ""]
    for cen in ("girado", "assimetrico"):
        aval = es["por_direcao_avaliacao"][cen]
        sec = es["secundarias"][cen]
        L += [f"### {cen} (secundarias: {', '.join(sec)}; demanda "
              + ", ".join(f"{a} {aval['demanda_veic_h'][a]:.0f}" for a in APROXIMACOES) + " veic/h)", "",
              "| controlador | " + " | ".join(f"{a}: espera media / P95 (s)" for a in APROXIMACOES)
              + " | " + " | ".join(f"{a}: % verde / sem verde medio / max (s)" for a in APROXIMACOES) + " |",
              "|---|" + "---|" * 8]
        for ctrl in REFERENCIAS + ["Max-Pressure"] + DQNS:
            x = aval["controladores"][ctrl]
            L.append(f"| {ctrl} | " + " | ".join(f"{_f(x[a]['espera_media'])} / {_f(x[a]['espera_p95'], 0)}"
                                                 for a in APROXIMACOES) + " | "
                     + " | ".join(f"{_f(x[a]['pct_verde'])} / {_f(x[a]['sem_verde_medio_s'], 0)} / "
                                  f"{x[a]['sem_verde_max_s']}" for a in APROXIMACOES) + " |")
        ins = es["instrumentado"][cen]
        L += ["", f"Rodadas instrumentadas ({cen}, so carros que entraram na primeira hora; extremo = espera >= "
              f"{es['limiar_espera_extrema_s']} s):", "",
              "| controlador | carros extremos | % deles na secundaria | % que esperaram um unico vermelho longo | "
              "secundaria recebe verde apos (s, media / P95) | fila da secundaria nesse momento | "
              "fila nas principais nesse momento | % trocas p/ principal com secundaria esperando >= 90 s | "
              "verde medio secundaria / principal (s) |",
              "|---|---|---|---|---|---|---|---|---|"]
        for rot, x in ins.items():
            s = x["secundaria_recebe_verde"]
            pa = x["por_aprox"]
            vs = _media([pa[a]["verde_medio_s"] for a in sec])
            vp = _media([pa[a]["verde_medio_s"] for a in APROXIMACOES if a not in sec])
            L.append(f"| {rot} | {x['n_carros_extremos']} | {_f(x['pct_extremos_na_secundaria'])} | "
                     f"{_f(x['extremos_que_nao_perderam_verde_pct'])} | {_f(s['tempo_sem_verde_medio_s'], 0)} / "
                     f"{s['tempo_sem_verde_p95_s']} | {_f(s['fila_media'])} | "
                     f"{_f(s['fila_media_nas_principais_nesse_momento'])} | "
                     f"{_f(x['pct_trocas_para_principal_com_secundaria_esperando_90s'])} | {_f(vs)} / {_f(vp)} |")
        L.append("")
    with open(os.path.join(PASTA, "resumo.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"Salvo em {os.path.join(PASTA, 'resumo.md')}")


def graficos():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    es = _ler("esperas")
    os.makedirs(PASTA_GRAFICOS, exist_ok=True)
    ctrls = REFERENCIAS + DQNS
    cor_sec, cor_pri = ac.CORES[1], ac.CORES[0]

    # 1) espera media e P95 por direcao (secundaria x principal), girado e assimetrico
    fig, eixos = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True)
    for ax, cen in zip(eixos, ("girado", "assimetrico")):
        aval = es["por_direcao_avaliacao"][cen]["controladores"]
        sec = es["secundarias"][cen]
        x = np.arange(len(ctrls))
        for k, (grupo, cor, desl) in enumerate([(sec, cor_sec, -0.2), ([a for a in APROXIMACOES if a not in sec], cor_pri, 0.2)]):
            p95 = [statistics.mean(aval[c][a]["espera_p95"] for a in grupo) for c in ctrls]
            med = [statistics.mean(aval[c][a]["espera_media"] for a in grupo) for c in ctrls]
            nome = "secundarias" if k == 0 else "principais"
            ax.bar(x + desl, p95, 0.38, color=cor, alpha=0.35, label=f"P95 {nome}")
            ax.bar(x + desl, med, 0.38, color=cor, label=f"media {nome}")
        ax.set_xticks(x, ctrls, rotation=35, ha="right", fontsize=8)
        ax.set_title(f"{cen}: espera por tipo de via", fontsize=10)
        ax.grid(axis="y", alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)
    eixos[0].set_ylabel("espera (s)")
    eixos[0].legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(PASTA_GRAFICOS, "1_espera_secundaria_x_principal.png"), dpi=130)
    plt.close(fig)

    # 2) % de verde x % de demanda das secundarias
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(ctrls))
    for k, cen in enumerate(("girado", "assimetrico")):
        aval = es["por_direcao_avaliacao"][cen]
        sec = es["secundarias"][cen]
        v = [sum(aval["controladores"][c][a]["pct_verde"] for a in sec) for c in ctrls]
        ax.bar(x + (k - 0.5) * 0.38, v, 0.38, color=ac.CORES[2 + k], label=f"{cen}: % do verde da hora")
        dem = sum(aval["pct_demanda"][a] for a in sec)
        ax.axhline(dem, color=ac.CORES[2 + k], ls="--", lw=1, label=f"{cen}: % da demanda ({dem:.0f}%)")
    ax.set_xticks(x, ctrls, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("% (soma das duas secundarias)")
    ax.set_title("Quanto verde as ruas secundarias recebem", fontsize=10)
    ax.legend(fontsize=7, frameon=False)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(PASTA_GRAFICOS, "2_verde_das_secundarias.png"), dpi=130)
    plt.close(fig)

    # 3) tempo sem verde quando a secundaria finalmente recebe verde
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for k, cen in enumerate(("girado", "assimetrico")):
        ins = es["instrumentado"][cen]
        med = [ins[c]["secundaria_recebe_verde"]["tempo_sem_verde_medio_s"] for c in ctrls]
        p95 = [ins[c]["secundaria_recebe_verde"]["tempo_sem_verde_p95_s"] for c in ctrls]
        ax.bar(x + (k - 0.5) * 0.38, p95, 0.38, color=ac.CORES[2 + k], alpha=0.35, label=f"{cen}: P95")
        ax.bar(x + (k - 0.5) * 0.38, med, 0.38, color=ac.CORES[2 + k], label=f"{cen}: media")
    ax.set_xticks(x, ctrls, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("segundos sem verde")
    ax.set_title("Ha quanto tempo a secundaria estava sem verde quando foi atendida", fontsize=10)
    ax.legend(fontsize=8, frameon=False)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(PASTA_GRAFICOS, "3_espera_da_secundaria_pelo_verde.png"), dpi=130)
    plt.close(fig)
    print(f"Graficos em {PASTA_GRAFICOS}")


def main():
    ap = argparse.ArgumentParser()
    for p in ("presos", "automato", "esperas", "relatorio", "so-graficos"):
        ap.add_argument(f"--{p}", action="store_true")
    ap.add_argument("--processos", type=int, default=6)
    a = ap.parse_args()
    if a.presos:
        presos(a.processos)
    if a.automato:
        automato()
    if a.esperas:
        esperas(a.processos)
    if a.relatorio:
        relatorio()
    if a.so_graficos:
        graficos()


if __name__ == "__main__":
    main()
