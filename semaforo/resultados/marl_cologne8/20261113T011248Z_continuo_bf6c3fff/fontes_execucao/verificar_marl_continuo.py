"""Conferencia final automatica do protocolo continuo, sem atualizar pesos."""

import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import torch

from ambiente_marl_cologne import PROJETO, json_novo, sha
from verificar_rodada_marl_cologne import verificar_metricas, verificar_decisoes, verificar_fases


def ler_historicos(resumo):
    linhas = []
    for ref in resumo["historicos"]:
        for line in Path(ref["caminho"]).read_text(encoding="utf-8").splitlines():
            x = json.loads(line)
            if x["episodio"] <= ref["ate_episodio"]:
                linhas.append(x)
    return linhas


def verificar(raiz):
    m = json.loads((raiz / "manifesto.json").read_text(encoding="utf-8"))
    cfg = json.loads((raiz / "protocolo.json").read_text(encoding="utf-8"))
    g = json.loads((raiz / "resumo_geral.json").read_text(encoding="utf-8"))
    assert g["status"] == "CONCLUIDO" and m["episodio"]["continuar_apos_colisao"]
    for p, h in m["fontes"].items():
        assert sha(PROJETO / p) == h
    for p, h in cfg["fontes_sha256"].items():
        assert sha(raiz / "fontes_execucao" / p) == h
    antigos = alterados = 0
    if cfg.get("snapshot"):
        antes = json.loads(Path(cfg["snapshot"]).read_text(encoding="utf-8"))
        permitidos = {"semaforo/scripts/ambiente_marl_cologne.py", "semaforo/scripts/testar_marl_cologne.py",
                      "semaforo/scripts/verificar_rodada_marl_cologne.py"}
        for path, h in antes.items():
            normal = path.replace("\\", "/")
            if normal in permitidos:
                alterados += 1
            else:
                assert sha(PROJETO.parent / path) == h, path
                antigos += 1
    n_exec = n_dec = n_fases = 0
    modelos = []
    for resumo in g["treinos"]:
        seed = resumo["semente_modelo"]
        hist = ler_historicos(resumo)
        assert [x["episodio"] for x in hist] == list(range(1, cfg["episodios"] + 1))
        assert len(resumo["teste_final"]) == len(cfg["sementes_teste"])
        for x in hist:
            assert not x["metricas"]["terminado_por_colisao"]
            assert x["metricas"]["fim_sumo"] >= 28800
        pastas = {Path(ref["caminho"]).parent for ref in resumo["historicos"]}
        for pasta in pastas:
            for p in pasta.rglob("metricas.json"):
                met = json.loads(p.read_text(encoding="utf-8"))
                verificar_metricas(p.parent, met, m)
                n_dec += verificar_decisoes(p.parent, m)
                n_fases += verificar_fases(p.parent, m)
                n_exec += 1
        escores = [(v["pontuacao"], v["episodio"]) for v in resumo["validacoes"]]
        assert resumo["melhor_episodio"] == min(escores)[1]
        melhor = PROJETO / resumo["melhor_checkpoint"]
        assert sha(melhor) == resumo["sha256_checkpoint"]
        for path in (melhor, Path(resumo["ultimo_completo"])):
            d = torch.load(path, map_location="cpu", weights_only=True)
            assert d["manifesto"] == m
            assert len(d["agentes"]) == 9
            for i, a in enumerate(d["agentes"]):
                assert a["gradientes"] > 0
                assert all(torch.isfinite(v).all() for v in a["rede"].values())
                if d["completo_para_retomada"]:
                    assert a["gradientes"] == hist[-1]["gradientes"][i]
                    assert a["memoria"]["n"] > 0
        modelos.append({"semente": seed, "episodios": len(hist),
            "episodios_completaram_hora": sum(x["metricas"]["fim_sumo"] >= 28800 for x in hist),
            "episodios_com_ocorrencia_colisao": sum(bool(x["metricas"]["colisoes"]) for x in hist),
            "episodios_terminados_por_colisao": sum(x["metricas"]["terminado_por_colisao"] for x in hist),
            "eventos_colisao_treino": sum(x["metricas"]["colisoes"] for x in hist),
            "exposicao_horas": sum(x["metricas"]["passos_controlados"] for x in hist) / 3600,
            "gradientes_finais": hist[-1]["gradientes"], "melhor_episodio": resumo["melhor_episodio"]})
        print(f"VERIFICADO modelo_seed{seed}", flush=True)
    for modo, resultados in g["comparadores"].items():
        for met in resultados:
            p = raiz / "comparadores" / modo / f"seed{met['semente']}"
            verificar_metricas(p, met, m)
            n_exec += 1
    return {"status": "VERIFICADO", "execucoes_conferidas": n_exec, "decisoes_conferidas": n_dec,
        "eventos_fases_conferidos": n_fases, "arquivos_anteriores_preservados": antigos,
        "scripts_anteriores_alterados_com_backup": alterados, "modelos": modelos,
        "nota": "Conferencia de integridade e protocolo; nao e afirmacao de superioridade ou seguranca"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rodada", type=Path)
    args = ap.parse_args()
    resultado = verificar(args.rodada)
    json_novo(args.rodada / "verificacao_final.json", resultado)
    print(json.dumps({k: v for k, v in resultado.items() if k != "modelos"}, ensure_ascii=False, indent=2))
