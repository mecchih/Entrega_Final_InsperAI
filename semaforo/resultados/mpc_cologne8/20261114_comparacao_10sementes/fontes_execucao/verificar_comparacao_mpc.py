"""Confere as decisoes, transicoes, QPs e tripinfo do comparador sem RL."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from ambiente_comparacao_mpc import construir_manifesto, metricas_viagens
from comparar_mpc_cologne8 import checar_fontes


def ler(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def linhas(path):
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def verificar(raiz):
    raiz = Path(raiz)
    checar_fontes()
    m = construir_manifesto("cologne8", continuar_apos_colisao=True)
    assert ler(raiz / "manifesto.json") == m
    por_tls = {s["id"]: s for s in m["controladores"]}
    resultados = []
    for pasta in sorted(raiz.iterdir()):
        if not pasta.is_dir() or not (pasta / "metricas.json").exists() or pasta.name.startswith("calibracao"):
            continue
        metrica = ler(pasta / "metricas.json")
        execucao = ler(pasta / "execucao.json")
        assert metrica["modo"] == "mpc_externo" and not metrica["treinando"]
        assert metrica["versao_sumo"][1] == "SUMO 1.28.0"
        assert not metrica["terminado_por_colisao"] and metrica["teleportes"] == 0
        assert metrica["fim_sumo"] >= 25200 + execucao["duracao"]
        assert metrica["viagens"] == metricas_viagens(pasta / "tripinfo.xml.gz", 25200 + execucao["duracao"])
        assert len(metrica["eventos_colisao"]) == metrica["colisoes"]
        qps = linhas(raiz / (pasta.name + "_mpc") / "otimizacoes.jsonl")
        assert qps and len(qps) == metrica["controlador_externo"]["otimizacoes"]
        for j, qp in enumerate(qps):
            assert qp["indice_plano"] == j and qp["tempo"] == 25200 + j * 120
            assert qp["solver"]["valid"]
            for key in ("eq_violation", "ineq_violation", "stationarity", "dual_violation", "complementarity"):
                assert math.isfinite(qp["solver"][key]) and qp["solver"][key] <= 1e-7
            assert not qp["metadata"]["turns_without_green_service"]
            assert set(qp["verdes_quantizados"]) == set(por_tls)
            for tls, valores in qp["verdes_quantizados"].items():
                assert len(valores) == por_tls[tls]["n_acoes"]
                assert sum(valores) == 120 - 5 * len(valores)
                assert all(v % 5 == 0 and 10 <= v <= 60 for v in valores)
        decisoes = linhas(pasta / "decisoes.jsonl")
        fases = linhas(pasta / "fases.jsonl")
        eventos = defaultdict(list)
        for evento in fases:
            eventos[evento["tls"]].append(evento)
        assert set(eventos) == set(por_tls)
        for d in decisoes:
            esquema = por_tls[d["agente"]]
            assert not d["explorou"] and d["q"] == [] and d["orientacao"] == 0
            assert len(d["estado"]) == esquema["entradas_com_supervisor"]
            assert all(math.isfinite(v) and v >= 0 for v in d["estado"])
            assert 0 <= d["pedida"] < esquema["n_acoes"]
            assert 0 <= d["executada"] < esquema["n_acoes"]
            assert d["fase_alvo"] == esquema["fases"][d["executada"]]["state"]
            indice = d["controlador_externo"]["indice_plano"]
            assert qps[indice]["tempo"] <= d["tempo"] < qps[indice]["tempo"] + 120
            assert d["controlador_externo"]["verdes_alvo_s"] == qps[indice]["verdes_quantizados"][d["agente"]]
        assert sum(d["intervencao"] for d in decisoes) == metrica["intervencoes"]
        transicoes = 0
        for tls, es in eventos.items():
            inicio_verde = None
            for j, e in enumerate(es):
                if e["motivo"] == "fim_vermelho":
                    inicio_verde = e["tempo"]
                    assert e["estado"] == por_tls[tls]["fases"][e["fase_alvo"]]["state"]
                if e["motivo"] != "troca_local":
                    continue
                if inicio_verde is not None:
                    assert 10 <= e["tempo"] - inicio_verde <= 60
                assert set(e["estado"]) <= set("yr") and "y" in e["estado"]
                if e["tempo"] + 3 < metrica["fim_sumo"]:
                    assert es[j + 1]["tempo"] == e["tempo"] + 3
                    assert es[j + 1]["motivo"] == "fim_amarelo"
                    assert set(es[j + 1]["estado"]) == {"r"}
                if e["tempo"] + 5 < metrica["fim_sumo"]:
                    assert es[j + 2]["tempo"] == e["tempo"] + 5
                    assert es[j + 2]["motivo"] == "fim_vermelho"
                    assert es[j + 2]["fase_alvo"] == e["fase_alvo"]
                transicoes += 1
        assert transicoes == metrica["trocas"]
        resultados.append({"pasta": pasta.name, "qps_validos": len(qps), "decisoes_validas": len(decisoes),
                           "transicoes_validas": transicoes, "tripinfo_recalculado": True,
                           "colisoes": metrica["colisoes"], "nao_concluidas": metrica["viagens_nao_concluidas"]})
    assert resultados, "Nenhuma simulacao MPC encontrada"
    return {"status": "CONFERIDO", "rodadas": resultados,
            "qps": sum(r["qps_validos"] for r in resultados),
            "decisoes": sum(r["decisoes_validas"] for r in resultados),
            "transicoes": sum(r["transicoes_validas"] for r in resultados)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pasta", type=Path)
    args = ap.parse_args()
    result = verificar(args.pasta)
    nome = "VERIFICACAO_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json"
    with (args.pasta / nome).open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))
