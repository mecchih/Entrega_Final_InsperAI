"""Analisa arquivos de uma rodada concluida; nao importa torch nem inicia SUMO.

Saida exclusiva em diretorio novo. Le tripinfo para conferir os agregados,
preserva o pareamento por seed de trafego e separa a variacao entre modelos.
"""

import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import statistics as st
import uuid
import xml.etree.ElementTree as ET

import numpy as np


def ler(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def resumo(xs):
    xs = [float(x) for x in xs if x is not None]
    if not xs:
        return {"n": 0, "media": None, "dp": None, "min": None, "max": None}
    assert all(math.isfinite(x) for x in xs)
    return {"n": len(xs), "media": st.mean(xs), "dp": st.stdev(xs) if len(xs) > 1 else 0,
            "min": min(xs), "max": max(xs)}


def guardar_json(p, obj):
    with Path(p).open("x", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, allow_nan=False, indent=2)


def guardar_csv(p, linhas):
    if not linhas:
        return
    with Path(p).open("x", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)


def mapear_faixas(net):
    """Segue conexoes reais; internal junctions nao substituem a juncao fisica."""
    edges = {e.get("id"): e for e in net.findall("edge")}
    lane_edge = {l.get("id"): e for e in edges.values() for l in e.findall("lane")}
    fisicos = {j.get("id"): j for j in net.findall("junction") if j.get("type") != "internal"}
    dono = {}

    def atribuir(lane, no):
        assert lane in lane_edge and no in fisicos
        if lane in dono:
            assert dono[lane] == no, (lane, dono[lane], no)
            return False
        dono[lane] = no
        return True

    for no, j in fisicos.items():
        for lane in j.get("intLanes", "").split():
            atribuir(lane, no)
    for c in net.findall("connection"):
        e = edges[c.get("from")]
        if e.get("function") != "internal" and c.get("via"):
            atribuir(c.get("via"), e.get("to"))
    mudou = True
    while mudou:
        mudou = False
        for e in edges.values():
            if e.get("function") != "internal":
                continue
            lanes = [l.get("id") for l in e.findall("lane")]
            nos = {dono[l] for l in lanes if l in dono}
            assert len(nos) <= 1
            if nos:
                for l in lanes:
                    mudou |= atribuir(l, next(iter(nos)))
        for c in net.findall("connection"):
            lane = c.get("from") + "_" + c.get("fromLane")
            if lane in dono and c.get("via"):
                mudou |= atribuir(c.get("via"), dono[lane])
    for lane, edge in lane_edge.items():
        if edge.get("function") != "internal":
            dono[lane] = "trecho:" + edge.get("id")
    return dono


def tripinfo(p, met):
    with gzip.open(p, "rb") as f:
        trips = ET.parse(f).getroot().findall("tripinfo")
    waits = np.array([float(t.get("waitingTime")) for t in trips])
    arrived = [t for t in trips if float(t.get("arrival")) >= 0]
    s = met["viagens"]["demanda_janela"]
    assert len(trips) == s["inseridos"] == s["espera_todos_inclui_censura"]["n"]
    assert len(arrived) == s["concluidos"]
    for field, val in (("media", waits.mean()), ("p95", np.percentile(waits, 95)), ("maximo", waits.max())):
        assert math.isclose(float(val), s["espera_todos_inclui_censura"][field], abs_tol=1e-9)
    return {"n_tripinfo": len(trips), "espera_positiva_pct": float(np.mean(waits > 0) * 100),
            "espera_acima_60_pct": float(np.mean(waits > 60) * 100),
            "espera_acima_120_pct": float(np.mean(waits > 120) * 100),
            "espera_acima_300_pct": float(np.mean(waits > 300) * 100),
            "excesso_acima_60_por_veiculo_s": float(np.maximum(waits - 60, 0).mean()),
            "chegadas_ate_fim_da_hora": sum(float(t.get("arrival")) < 28800 for t in arrived),
            "comprimento_rota_m": st.mean(float(t.get("routeLength")) for t in trips),
            "time_loss_s": st.mean(float(t.get("timeLoss")) for t in trips)}


def registro(m, grupo, seed_modelo, pasta):
    v = m["viagens"]["demanda_janela"]
    locais = sum(v for k, v in m["decisoes"].items() if k.startswith("decisoes_"))
    sup = sum(v for k, v in m["decisoes"].items() if k.startswith("supervisor_"))
    areas = [a for no in m["espera_por_entrada"].values() for a in no.values() if a["n"]]
    d = {"grupo": grupo, "semente_modelo": seed_modelo, "semente_trafego": m["semente"],
         "espera_s": v["espera_todos_inclui_censura"]["media"],
         "p95_s": v["espera_todos_inclui_censura"]["p95"],
         "espera_max_s": v["espera_todos_inclui_censura"]["maximo"],
         "duracao_viagem_s": v["duracao_concluidos"]["media"],
         "atraso_insercao_s": v["atraso_insercao"]["media"], "colisoes": m["colisoes"],
         "colisoes_por_1000_viagens_previstas": m["colisoes"] * 1000 / m["demanda_prevista"],
         "colisoes_por_hora_controlada": m["colisoes"] * 3600 / m["passos_controlados"],
         "fila_media_rede": m["fila_media_rede"], "fila_max_rede": m["fila_max_rede"],
         "fila_media_sensores": m["fila_media_sensores_locais"],
         "nao_concluidas": m["viagens_nao_concluidas"], "concluidas": v["concluidos"],
         "nao_inseridas": m["viagens_nao_inseridas"], "interrompidas": v["interrompidos"],
         "teleportes": m["teleportes"], "escoamento_s": m["fim_sumo"] - 28800,
         "terminado_naturalmente": m["terminado_naturalmente"], "passos_controlados": m["passos_controlados"],
         "decisoes_locais": locais, "decisoes_supervisor": sup,
         "intervencoes": m["intervencoes"] if grupo != "original_fixo" else None,
         "intervencoes_pct_decisoes_locais": m["intervencoes"] * 100 / locais if locais else None,
         "trocas": m["trocas"] if grupo != "original_fixo" else None,
         "trocas_por_hora_controlada_rede": m["trocas"] * 3600 / m["passos_controlados"] if locais else None,
         "pior_p95_entrada_s": max(a["p95"] for a in areas) if areas else None,
         "maior_espera_local_s": max(a["maximo"] for a in areas) if areas else None,
         "todos_tls_verdes_pct": m["segundos_todos_tls_verdes"] * 100 / m["passos_controlados"] if locais else None}
    d.update(tripinfo(pasta / "tripinfo.xml.gz", m))
    return d


def parear(a, b):
    assert len(a) == len(b)
    assert [x["semente_trafego"] for x in a] == [x["semente_trafego"] for x in b]
    saida = {}
    for k in ("espera_s", "p95_s", "espera_max_s", "colisoes", "fila_media_rede", "nao_concluidas",
              "pior_p95_entrada_s", "intervencoes", "espera_acima_60_pct", "duracao_viagem_s"):
        pares = [(x[k], y[k]) for x, y in zip(a, b) if x[k] is not None and y[k] is not None]
        if not pares:
            continue
        ds = [x - y for x, y in pares]
        den = st.mean(y for _, y in pares)
        saida[k] = {**resumo(ds), "variacao_pct": st.mean(ds) * 100 / den if den else None,
                    "melhor": sum(d < -1e-9 for d in ds), "pior": sum(d > 1e-9 for d in ds),
                    "empate": sum(abs(d) <= 1e-9 for d in ds)}
    return saida


def grupo_linhas(linhas):
    ignorar = {"grupo", "semente_modelo", "semente_trafego"}
    return {k: resumo(x[k] for x in linhas) for k in linhas[0] if k not in ignorar}


def por_trafego(linhas):
    saida = []
    for s in sorted({r["semente_trafego"] for r in linhas}):
        xs = [r for r in linhas if r["semente_trafego"] == s]
        d = {"semente_trafego": s}
        for k in xs[0]:
            if k not in ("grupo", "semente_modelo", "semente_trafego"):
                vals = [r[k] for r in xs if r[k] is not None]
                d[k] = st.mean(vals) if vals else None
        saida.append(d)
    return saida


def analisar(raiz, saida):
    assert ler(raiz / "CONCLUIDO.json")["status"] == "CONCLUIDO_E_VERIFICADO"
    ver = ler(raiz / "verificacao_final.json")
    assert ver["status"] == "VERIFICADO"
    cfg, manifesto, g = (ler(raiz / n) for n in ("protocolo.json", "manifesto.json", "resumo_geral.json"))
    assert len(g["treinos"]) == 10 and cfg["episodios"] == 500
    assert cfg["sementes_teste"] == list(range(1, 11))
    projeto = Path(__file__).resolve().parents[1]
    proteger = [raiz / n for n in ("CONCLUIDO.json", "verificacao_final.json", "protocolo.json",
                                   "manifesto.json", "resumo_geral.json", "RELATORIO.md")]
    proteger += [projeto / t["melhor_checkpoint"] for t in g["treinos"]]
    proteger += [Path(t["ultimo_completo"]) for t in g["treinos"]]
    antes = {str(p): sha(p) for p in proteger}
    for t in g["treinos"]:
        assert antes[str(projeto / t["melhor_checkpoint"])] == t["sha256_checkpoint"]
    for n, h in cfg["fontes_sha256"].items():
        assert sha(raiz / "fontes_execucao" / n) == h
    for n, h in manifesto["fontes"].items():
        assert sha(projeto / n) == h

    net = projeto / "referencias/cologne8_sumo_rl_1.4.5/sumo_rl/nets/RESCO/cologne8/cologne8.net.xml"
    lane_node = mapear_faixas(ET.parse(net).getroot())
    metricas, locais, colisoes, supervisores, agentes, treino, escolhas = [], [], [], [], [], [], []
    groups = defaultdict(list)
    num_nos = len(manifesto["controladores"])
    ids = [x["id"] for x in manifesto["controladores"]]

    def adicionar(m, grupo, modelseed, pasta):
        r = registro(m, grupo, modelseed, pasta)
        metricas.append(r)
        groups[grupo].append(r)
        for no, areas in m["espera_por_entrada"].items():
            for edge, a in areas.items():
                locais.append({"grupo": grupo, "semente_modelo": modelseed,
                    "semente_trafego": m["semente"], "tls": no, "edge": edge, **a})
        fases = defaultdict(list)
        if grupo == "marl":
            with (pasta / "fases.jsonl").open(encoding="utf-8") as f:
                for l in f:
                    e = json.loads(l)
                    fases[e["tls"]].append(e)
            decs = defaultdict(Counter)
            with (pasta / "decisoes.jsonl").open(encoding="utf-8") as f:
                for l in f:
                    e = json.loads(l)
                    assert not e["explorou"]
                    a = e["agente"]
                    decs[a]["decisoes"] += 1
                    if a != "supervisor":
                        decs[a]["intervencoes"] += int(e["intervencao"])
                        decs[a][f"acao_{e['executada']}"] += 1
            assert sum(v["intervencoes"] for k, v in decs.items() if k != "supervisor") == m["intervencoes"]
            for i, no in enumerate(ids):
                c = decs[no]
                agentes.append({"semente_modelo": modelseed, "semente_trafego": m["semente"], "tls": no,
                    "decisoes": c["decisoes"], "intervencoes": c["intervencoes"],
                    "acoes": dict(c), "trocas": sum(e["motivo"] == "troca_local" for e in fases[no])})
        for ac in range(num_nos + 1):
            if grupo == "marl":
                supervisores.append({"semente_modelo": modelseed, "semente_trafego": m["semente"],
                    "acao": ac, "objetivo": "equilibrado" if ac == 0 else ids[ac - 1],
                    "decisoes": m["decisoes"].get(f"supervisor_{ac}", 0)})
        for ev in m["eventos_colisao"]:
            no = lane_node.get(ev["faixa_evento"], "NAO_MAPEADO")
            estagio, estado, alvo, motivo, idade = None, None, None, None, None
            if no in fases:
                fs = fases[no]
                i = bisect_left([e["tempo"] for e in fs], ev["tempo"]) - 1
                assert i >= 0
                e = fs[i]
                estagio, estado, alvo = e["estagio"], e["estado"], e["fase_alvo"]
                motivo, idade = e["motivo"], ev["tempo"] - e["tempo"]
            colisoes.append({"grupo": grupo, "semente_modelo": modelseed, "semente_trafego": m["semente"],
                "tls_ou_juncao": no, "estagio_anterior_ao_passo": estagio, "estado": estado,
                "fase_alvo": alvo, "ultimo_motivo": motivo, "segundos_desde_evento_fase": idade, **ev})

    print("Conferindo 220 testes/ablacoes/comparadores a partir de tripinfo...", flush=True)
    for t in g["treinos"]:
        seed = t["semente_modelo"]
        for key, group in (("teste_final", "marl"), ("ablacao_orientacao_zero", "orientacao_zero")):
            sub = "teste_final" if group == "marl" else "ablacao_orientacao_zero"
            for m in t[key]:
                adicionar(m, group, seed, raiz / f"modelo_seed{seed}" / sub / f"seed{m['semente']}")
        historicos = []
        for ref in t["historicos"]:
            with Path(ref["caminho"]).open(encoding="utf-8") as f:
                historicos += [v for l in f if (v := json.loads(l))["episodio"] <= ref["ate_episodio"]]
        assert [x["episodio"] for x in historicos] == list(range(1, 501))
        campos = {"colisoes": lambda x: x["metricas"]["colisoes"],
                  "espera_s": lambda x: x["metricas"]["viagens"]["demanda_janela"]["espera_todos_inclui_censura"]["media"],
                  "nao_concluidas": lambda x: x["metricas"]["viagens_nao_concluidas"]}
        windows = {"primeiros_20": historicos[:20], "ultimos_20": historicos[-20:],
                   "primeiros_100": historicos[:100], "ultimos_100": historicos[-100:]}
        cols = sum(x["metricas"]["colisoes"] for x in historicos)
        penal = sum(-x["metricas"]["penalidade_colisao_por_agente"] * 9 for x in historicos)
        custo_total = sum(-sum(x["metricas"]["recompensas"]) for x in historicos)
        treino.append({"semente_modelo": seed, "episodios": len(historicos),
            "janelas": {n: {c: resumo(f(x) for x in xs) for c, f in campos.items()} for n, xs in windows.items()},
            "eventos_colisao": cols, "exposicao_h": sum(x["metricas"]["passos_controlados"] for x in historicos) / 3600,
            "episodios_com_incompletas": sum(bool(x["metricas"]["viagens_nao_concluidas"]) for x in historicos),
            "nao_concluidas_soma": sum(x["metricas"]["viagens_nao_concluidas"] for x in historicos),
            "episodios_com_colisao": sum(bool(x["metricas"]["colisoes"]) for x in historicos),
            "fracao_custo_absoluto_colisao_pct": penal * 100 / custo_total,
            "gradientes_finais": t["gradientes_finais"], "duracao_real_h": t["duracao_s"] / 3600})
        escolhas.append({"semente_modelo": seed, "episodio": t["melhor_episodio"],
            "validacao": t["melhor_validacao"], "checkpoint": t["melhor_checkpoint"],
            "sha256": t["sha256_checkpoint"]})
        print(f"Conferido modelo {seed}", flush=True)
    for grupo, rs in g["comparadores"].items():
        for m in rs:
            adicionar(m, grupo, None, raiz / "comparadores" / grupo / f"seed{m['semente']}")
    assert len(metricas) == 220 and len(colisoes) == sum(r["colisoes"] for r in metricas)
    assert not any(x["tls_ou_juncao"] == "NAO_MAPEADO" for x in colisoes)
    print("Calculando comparacoes pareadas e variacao entre modelos...", flush=True)
    sumarios = {n: grupo_linhas(rs) for n, rs in groups.items()}
    entre = {}
    por_modelo = []
    pareados = []
    for seed in range(10):
        a = sorted([r for r in groups["marl"] if r["semente_modelo"] == seed], key=lambda r: r["semente_trafego"])
        b = sorted([r for r in groups["orientacao_zero"] if r["semente_modelo"] == seed], key=lambda r: r["semente_trafego"])
        por_modelo.append({"semente_modelo": seed, "teste": grupo_linhas(a), "orientacao_zero": grupo_linhas(b)})
        pareados.append({"semente_modelo": seed,
                        "contra_max_pressure": parear(a, groups["max_pressure"]),
                        "contra_original_fixo": parear(a, groups["original_fixo"]),
                        "contra_orientacao_zero": parear(a, b)})
    for k in por_modelo[0]["teste"]:
        entre[k] = resumo(x["teste"][k]["media"] for x in por_modelo)
    pareado_grupo = {n: parear(por_trafego(groups["marl"]), por_trafego(groups[n]))
                     for n in ("max_pressure", "original_fixo", "orientacao_zero")}
    sem6 = {n: [r for r in groups[n] if r["semente_modelo"] != 6] for n in ("marl", "orientacao_zero")}
    sensibilidade = {"exclusao_seed6_apenas_diagnostico": {
        "marl": grupo_linhas(sem6["marl"]), "orientacao_zero": grupo_linhas(sem6["orientacao_zero"]),
        "pareado": parear(por_trafego(sem6["marl"]), por_trafego(sem6["orientacao_zero"]))}}
    medias_locais = []
    for grupo in ("marl", "orientacao_zero", "max_pressure"):
        for no in ids:
            xs = [l for l in locais if l["grupo"] == grupo and l["tls"] == no and l["n"]]
            n = sum(x["n"] for x in xs)
            piores = []
            for seed in sorted({x["semente_modelo"] for x in xs}, key=str):
                for traf in range(1, 11):
                    vs = [x["p95"] for x in xs if x["semente_modelo"] == seed and x["semente_trafego"] == traf]
                    if vs:
                        piores.append(max(vs))
            medias_locais.append({"grupo": grupo, "tls": no, "visitas": n,
                "espera_local_media_ponderada_s": sum(x["media"] * x["n"] for x in xs) / n if n else None,
                "media_pior_p95_entrada_s": st.mean(piores) if piores else None,
                "maior_espera_local_s": max(x["maximo"] for x in xs) if n else None})
    edges = []
    for grupo in ("marl", "max_pressure"):
        for no in ids:
            for edge in next(s["entradas"] for s in manifesto["controladores"] if s["id"] == no):
                edgeid = edge["edge"]
                xs = [l for l in locais if l["grupo"] == grupo and l["tls"] == no and l["edge"] == edgeid and l["n"]]
                n = sum(x["n"] for x in xs)
                edges.append({"grupo": grupo, "tls": no, "edge": edgeid, "visitas": n,
                    "espera_local_media_ponderada_s": sum(x["media"] * x["n"] for x in xs) / n if n else None,
                    "media_p95_s": st.mean(x["p95"] for x in xs) if n else None,
                    "maximo_s": max(x["maximo"] for x in xs) if n else None})
    colisao_sum = {}
    for grupo in groups:
        xs = [x for x in colisoes if x["grupo"] == grupo]
        colisao_sum[grupo] = {"eventos": len(xs),
            "por_juncao": dict(Counter(x["tls_ou_juncao"] for x in xs)),
            "por_tipo": dict(Counter(x["tipo"] for x in xs)),
            "por_estagio": dict(Counter(x["estagio_anterior_ao_passo"] or "NAO_REGISTRADO" for x in xs)),
            "rodadas_zero_colisao": sum(r["colisoes"] == 0 for r in groups[grupo]),
            "rodadas": len(groups[grupo])}
    sup = []
    for seed in range(10):
        xs = [x for x in supervisores if x["semente_modelo"] == seed]
        counts = {str(a): sum(x["decisoes"] for x in xs if x["acao"] == a) for a in range(9)}
        total = sum(counts.values())
        sup.append({"semente_modelo": seed, "contagens": counts,
                    "percentuais": {a: v * 100 / total for a, v in counts.items()}})
    fronteira = []
    for r in por_modelo:
        w, c = r["teste"]["espera_s"]["media"], r["teste"]["colisoes"]["media"]
        if not any(s["teste"]["espera_s"]["media"] <= w and s["teste"]["colisoes"]["media"] <= c
            and (s["teste"]["espera_s"]["media"] < w or s["teste"]["colisoes"]["media"] < c)
            for s in por_modelo):
            fronteira.append(r["semente_modelo"])
    bootstrap = {}
    # Reamostra linhas de modelo e colunas de trafego separadamente. Baseline e
    # compartilhado por todos os modelos da mesma coluna: nao trata 100 pares
    # como 100 demandas independentes. Intervalos condicionais a este conjunto.
    rng = np.random.default_rng(20261113)
    ia, ib = rng.integers(0, 10, (10000, 10)), rng.integers(0, 10, (10000, 10))
    for k in ("espera_s", "p95_s", "colisoes", "fila_media_rede"):
        mat = np.array([[r[k] for r in groups["marl"] if r["semente_modelo"] == s] for s in range(10)])
        for grupo in ("max_pressure", "original_fixo"):
            bas = np.array([r[k] for r in groups[grupo]])
            delta = np.mean(mat[ia[:, :, None], ib[:, None, :]], axis=(1, 2)) - bas[ib].mean(axis=1)
            bootstrap[f"{k}_contra_{grupo}"] = {"delta": float(mat.mean() - bas.mean()),
                "ic_bootstrap_cruzado_95": np.percentile(delta, [2.5, 97.5]).tolist(), "repeticoes": 10000}
    depois = {p: sha(Path(p)) for p in antes}
    assert antes == depois, "Um arquivo protegido mudou durante a analise"
    result = {"rodada": str(raiz), "utc_analise": datetime.now(timezone.utc).isoformat(),
        "resumo_grupos": sumarios, "variacao_entre_modelos": entre, "por_modelo": por_modelo,
        "pareados_por_modelo": pareados, "pareados_media_modelos_por_trafego": pareado_grupo,
        "sensibilidade_supervisor": sensibilidade, "bootstrap_cruzado": bootstrap,
        "treino": treino, "checkpoints": escolhas, "colisoes": colisao_sum,
        "supervisor": sup, "fronteira_observada_espera_colisao": fronteira,
        "esperas_locais_por_no": medias_locais, "esperas_locais_por_edge": edges,
        "verificacao_preexistente": ver,
        "auditoria_analise": {"tripinfos_conferidos": len(metricas),
            "viagens_tripinfo_conferidas": sum(r["n_tripinfo"] for r in metricas),
            "arquivos_protegidos_iguais_antes_depois": len(antes), "sha256": antes,
            "codigo_sha256": sha(Path(__file__))}}
    guardar_json(saida / "estatisticas.json", result)
    guardar_csv(saida / "rodadas.csv", metricas)
    guardar_csv(saida / "esperas_por_entrada.csv", locais)
    guardar_csv(saida / "esperas_por_cruzamento.csv", medias_locais)
    guardar_csv(saida / "eventos_colisao.csv", colisoes)
    guardar_csv(saida / "orientacoes_supervisor.csv", supervisores)
    guardar_json(saida / "decisoes_por_agente.json", agentes)
    guardar_json(saida / "proveniencia.json", {"entrada": str(raiz), "fontes": antes,
        "script": str(Path(__file__).resolve()), "script_sha256": sha(Path(__file__)),
        "garantia": "Nenhum simulador, treino ou atualizacao de pesos executado por este analisador"})
    desenhar(saida, result)
    print(json.dumps({"saida": str(saida), "tripinfos": len(metricas),
                      "marl": sumarios["marl"]["espera_s"], "colisoes": sumarios["marl"]["colisoes"]}, ensure_ascii=False), flush=True)


def desenhar(saida, r):
    os.environ["MPLCONFIGDIR"] = str(saida / "cache_matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10})
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    nomes = ["MARL", "Max-Pressure", "Programa original"]
    grupos = ["marl", "max_pressure", "original_fixo"]
    for ax, (k, titulo, unidade) in zip(axes.flat, [
        ("espera_s", "Espera média da viagem", "segundos"),
        ("p95_s", "Média dos P95 de cada simulação", "segundos"),
        ("fila_media_rede", "Fila média em toda a rede", "veículos"),
        ("colisoes", "Eventos de colisão detectados", "eventos por simulação")]):
        means = [r["resumo_grupos"][g][k]["media"] for g in grupos]
        ax.bar(nomes, means, color=["#187e8b", "#ad7834", "#78828e"])
        for i, v in enumerate(means):
            ax.text(i, v, f"{v:.2f}", ha="center", va="bottom", fontweight="bold")
        ax.set_title(titulo)
        ax.set_ylabel(unidade)
        ax.set_ylim(0, max(means) * 1.2)
        ax.grid(axis="y", alpha=.2)
        ax.set_axisbelow(True)
    fig.suptitle("Cologne8: desempenho dos checkpoints escolhidos pela validação\nMARL: 10 modelos × 10 seeds de tráfego; comparadores: 10 seeds cada")
    fig.text(.5, .015, "Todos os controles apresentaram colisões. Os ganhos de espera são condicionais a esse simulador com collision.action=warn.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .035, 1, .93))
    fig.savefig(saida / "comparacao_controles.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for modelo in r["por_modelo"]:
        s, m = modelo["semente_modelo"], modelo["teste"]
        axes[0].scatter(m["colisoes"]["media"], m["espera_s"]["media"], s=55, color="#187e8b")
        axes[0].annotate(str(s), (m["colisoes"]["media"], m["espera_s"]["media"]), xytext=(5, 4), textcoords="offset points")
    for grupo, cor, nome in (("max_pressure", "#ad7834", "Max-Pressure"), ("original_fixo", "#78828e", "Original")):
        m = r["resumo_grupos"][grupo]
        axes[0].scatter(m["colisoes"]["media"], m["espera_s"]["media"], s=100, color=cor, marker="s", label=nome)
    axes[0].set(xlabel="Colisões por simulação", ylabel="Espera média (s)", title="Espera e colisões por modelo")
    axes[0].legend()
    mx = np.array([[s["percentuais"][str(i)] for i in range(9)] for s in r["supervisor"]])
    im = axes[1].imshow(mx, aspect="auto", cmap="Blues", vmin=0, vmax=100)
    axes[1].set(xticks=range(9), xticklabels=["Eq."] + [str(i) for i in range(8)], yticks=range(10),
                xlabel="Objetivo: equilibrado ou priorizar agente local", ylabel="Semente de treino",
                title="Escolhas do supervisor (% das decisões)")
    fig.colorbar(im, ax=axes[1], label="%")
    for (y, x), v in np.ndenumerate(mx):
        if v >= 10:
            axes[1].text(x, y, f"{v:.0f}", ha="center", va="center", color="white" if v > 60 else "black", fontsize=8)
    axes[0].grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(saida / "modelos_e_supervisor.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rodada", type=Path)
    ap.add_argument("--saida", type=Path)
    args = ap.parse_args()
    raiz = args.rodada.resolve()
    saida = args.saida or raiz / ("analise_detalhada_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:6])
    saida = saida.resolve()
    saida.mkdir(parents=True, exist_ok=False)
    analisar(raiz, saida)
