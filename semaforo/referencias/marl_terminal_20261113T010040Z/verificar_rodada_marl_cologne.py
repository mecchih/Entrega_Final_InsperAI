"""Confere evidencias da rodada sem simular, treinar ou modificar checkpoints."""

import argparse
import gzip
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
import numpy as np
import torch

from ambiente_marl_cologne import PROJETO, json_novo, metricas_viagens, sha


def verificar_metricas(pasta, m, manifesto):
    xml = pasta / "tripinfo.xml.gz"
    esperado = metricas_viagens(xml, 28800)
    if esperado != m["viagens"]:
        raise AssertionError(f"Metricas divergem do tripinfo: {pasta}")
    with gzip.open(xml, "rb") as f:
        trips = ET.parse(f).getroot().findall("tripinfo")
    if len({v.get("id") for v in trips}) != len(trips):
        raise AssertionError("IDs de viagem duplicados")
    concluidos = sum(float(v.get("arrival")) >= 0 for v in trips)
    assert len(trips) + m["viagens_nao_inseridas"] == m["demanda_prevista"]
    assert concluidos + m["viagens_nao_concluidas"] == m["demanda_prevista"]
    assert len(trips) - concluidos == m["remanescentes"]
    assert m["pendentes_insercao"] <= m["viagens_nao_inseridas"]
    assert m["passos_controlados"] == m["fim_sumo"] - 25200
    assert m["colisoes"] == len(m["eventos_colisao"])
    assert m["terminado_por_colisao"] == bool(m["colisoes"])
    penalidade = m["colisoes"] * manifesto["recompensa"]["colisao"]
    assert m["penalidade_colisao_por_agente"] == penalidade
    assert all(r <= penalidade + 1e-6 for r in m["recompensas"])
    assert m["teleportes"] == 0


def verificar_decisoes(pasta, manifesto):
    path = pasta / "decisoes.jsonl"
    if not path.exists():
        return 0
    esquemas = {s["id"]: s for s in manifesto["controladores"]}
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        sup = d["agente"] == "supervisor"
        s = None if sup else esquemas[d["agente"]]
        dim = manifesto["entradas_supervisor"] if sup else s["entradas_com_supervisor"]
        ac = len(manifesto["acoes_supervisor"]) if sup else s["n_acoes"]
        assert len(d["estado"]) == dim and len(d["q"]) == ac
        assert np.isfinite(d["estado"]).all() and np.isfinite(d["q"]).all()
        pedida = d["acao"] if sup else d["pedida"]
        assert 0 <= pedida < ac
        if not d["explorou"]:
            assert pedida == int(np.argmax(d["q"]))
        if not sup:
            assert 0 <= d["executada"] < ac
            assert d["fase_alvo"] == s["fases"][d["executada"]]["state"]
            assert d["intervencao"] == (pedida != d["executada"])
            a = len(s["entradas"])
            assert sum(d["estado"][2*a:2*a+ac]) == 1
            assert sum(d["estado"][-len(manifesto["acoes_supervisor"]):]) == 1
        n += 1
    return n


def verificar_fases(pasta, manifesto):
    path = pasta / "fases.jsonl"
    if not path.exists():
        return 0
    ultimos = {}
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        tls = d["tls"]
        anterior = ultimos.get(tls)
        if d["motivo"] == "fim_amarelo" and anterior["motivo"] == "troca_local":
            assert d["tempo"] - anterior["tempo"] == 3
        if d["motivo"] == "fim_vermelho" and anterior["motivo"] == "fim_amarelo":
            assert d["tempo"] - anterior["tempo"] == 2
        if d["estagio"] == "verde":
            s = next(s for s in manifesto["controladores"] if s["id"] == tls)
            assert d["estado"] == s["fases"][d["fase_alvo"]]["state"]
        ultimos[tls] = d
        n += 1
    return n


def verificar(raiz, snapshot):
    manifesto = json.loads((raiz / "manifesto.json").read_text(encoding="utf-8"))
    protocolo = json.loads((raiz / "protocolo.json").read_text(encoding="utf-8"))
    geral = json.loads((raiz / "resumo_geral.json").read_text(encoding="utf-8"))
    assert geral["status"] == "CONCLUIDO"
    for p, h in manifesto["fontes"].items():
        assert sha(PROJETO / p) == h
    for p, h in protocolo["scripts_sha256"].items():
        assert sha(raiz / "fontes_execucao" / Path(p).name) == h
    preservados = 0
    if snapshot:
        dados = json.loads(snapshot.read_text(encoding="utf-8"))
        for p, h in dados.items():
            assert sha(PROJETO.parent / p) == h, p
            preservados += 1
    verificados = decisoes = fases = 0
    modelos = []
    for resumo in geral["treinos"]:
        seed = resumo["semente_modelo"]
        pasta = raiz / f"modelo_seed{seed}"
        historico = [json.loads(l) for l in (pasta / "historico.jsonl").read_text().splitlines()]
        assert [x["episodio"] for x in historico] == list(range(1, resumo["episodios"] + 1))
        for registro in historico:
            ep = pasta / "episodios" / f"ep{registro['episodio']:04d}"
            assert registro["metricas"] == json.loads((ep / "metricas.json").read_text())
        for p in sorted(pasta.rglob("metricas.json")):
            m = json.loads(p.read_text(encoding="utf-8"))
            verificar_metricas(p.parent, m, manifesto)
            decisoes += verificar_decisoes(p.parent, manifesto)
            fases += verificar_fases(p.parent, manifesto)
            verificados += 1
        scores = [(v["pontuacao"], v["episodio"]) for v in resumo["validacoes"]]
        assert resumo["melhor_episodio"] == min(scores)[1]
        peso = PROJETO / resumo["melhor_checkpoint"]
        assert sha(peso) == resumo["sha256_checkpoint"]
        for p in (peso, pasta / "ultimo_completo.pt"):
            d = torch.load(p, map_location="cpu", weights_only=True)
            assert d["manifesto"] == manifesto
            assert len(d["agentes"]) == len(manifesto["controladores"]) + 1
            for i, a in enumerate(d["agentes"]):
                assert a["gradientes"] > 0
                for v in a["rede"].values():
                    assert torch.isfinite(v).all()
                if d["completo_para_retomada"]:
                    assert a["gradientes"] == historico[-1]["gradientes"][i]
                    assert a["memoria"]["n"] > 0
        exposicao = sum(x["metricas"]["passos_controlados"] for x in historico)
        modelos.append({"semente": seed, "episodios": len(historico),
            "episodios_com_colisao": sum(bool(x["metricas"]["colisoes"]) for x in historico),
            "eventos_colisao_treino": sum(x["metricas"]["colisoes"] for x in historico),
            "exposicao_simulada_s": exposicao, "exposicao_horas": exposicao / 3600,
            "episodios_completaram_hora": sum(x["metricas"]["fim_sumo"] >= 28800 for x in historico),
            "ultimo_epsilon": historico[-1]["epsilon"],
            "gradientes_finais": historico[-1]["gradientes"],
            "melhor_episodio": resumo["melhor_episodio"], "teste_final": resumo["teste_final"][0]})
    for modo in geral["comparadores"]:
        pasta = raiz / "comparadores" / modo / "seed1"
        m = json.loads((pasta / "metricas.json").read_text())
        verificar_metricas(pasta, m, manifesto)
        decisoes += verificar_decisoes(pasta, manifesto)
        fases += verificar_fases(pasta, manifesto)
        verificados += 1
    return {"status": "VERIFICADO", "execucoes_conferidas": verificados,
            "decisoes_conferidas": decisoes, "eventos_fases_conferidos": fases,
            "arquivos_preexistentes_preservados": preservados, "modelos": modelos,
            "nota": "VERIFICADO significa integridade do registro; nao significa ausencia de colisoes ou politica aprovada"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rodada", type=Path)
    ap.add_argument("--snapshot", type=Path)
    args = ap.parse_args()
    resultado = verificar(args.rodada, args.snapshot)
    json_novo(args.rodada / "verificacao_final.json", resultado)
    print(json.dumps({k: v for k, v in resultado.items() if k != "modelos"}, ensure_ascii=False, indent=2))
