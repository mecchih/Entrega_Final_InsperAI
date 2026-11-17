"""Investigacao do 4o semaforo (Ribeirao Claro x Av. Helio Pellegrino), sem treino de RL.

uso:
  python -B -X utf8 semaforo/integracao_insper/quarto_semaforo/investigar_quarto.py estatico
  python -B -X utf8 semaforo/integracao_insper/quarto_semaforo/investigar_quarto.py fumaca
  python -B -X utf8 semaforo/integracao_insper/quarto_semaforo/investigar_quarto.py experimento --processos 12

Sementes: validacao exploratoria 221-225 (intenso_validacao). As sementes do teste final
(241-250) e dos testes antigos (211-215, 231-235) NAO sao usadas.
Controle dos 3: original | atuado_equivalente (verde 10) | RL A_col (checkpoints ja
selecionados na validacao da otimizacao final; so avaliacao, sem treino).
4o semaforo: original | atuado | escoamento | prioridade (ver ambiente_quarto.py).
"""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import datetime
import json
from pathlib import Path
import statistics
import sys
import xml.etree.ElementTree as ET

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI.parent / "otimizacao_final"))
sys.path.insert(0, str(AQUI))
import insper_comum as ic  # noqa: E402

SAIDA_RES = AQUI / "resultados"
SEMENTES = [221, 222, 223, 224, 225]
PROIBIDAS = set(range(241, 251)) | set(range(211, 216)) | set(range(231, 236))
OTIM = AQUI.parent / "otimizacao_final" / "resultados"
BASES = {"original": ("original", None), "atuado_eq_v10": ("atuado_equivalente", None), "A_col": ("independente", "A_col")}
QUARTOS = [None, "atuado", "escoamento", "prioridade"]


def cfg(s):
    return ic.SEMAFORO / "cenarios" / "insper_demanda" / "intenso_validacao" / f"semente_{s}" / "cenario.sumocfg"


def estatico(_):
    """Estrutura do 4o semaforo, rotas que passam por ele e bloqueio da saida nos registros existentes."""
    import ambiente_quarto as aq
    ic.sumo_home()
    import sumolib
    net = sumolib.net.readNet(str(ic.REDE), withPrograms=True)
    tl = net.getTLS(aq.QUARTO)
    links = sorted(tl.getConnections(), key=lambda c: c[2])
    entradas = Counter(i.getEdge().getID() for i, o, li in links)
    prog = list(tl.getPrograms().values())[0]
    fases = [(p.state, p.duration, p.minDur, p.maxDur) for p in prog.getPhases()]
    verdes = [f[0] for f in fases if "y" not in f[0]]
    no = net.getNode(aq.QUARTO)
    info = {
        "id": aq.QUARTO, "tipo_programa": prog.getType(), "fases": fases, "n_links": len(links),
        "n_configuracoes_verde": len(verdes), "verdes": verdes,
        "entradas": {e: {"links": n, "nome": net.getEdge(e).getName(), "faixas": net.getEdge(e).getLaneNumber(),
                         "comprimento_m": round(net.getEdge(e).getLength(), 1),
                         "classes": sorted(net.getEdge(e).getLanes()[0].getPermissions() & {"passenger", "bicycle", "bus"})}
                     for e, n in entradas.items()},
        "links_por_classe": dict(Counter("so_bicicleta" if i.getPermissions() <= {"bicycle"} else "veiculos" for i, o, li in links)),
        "nos_fundidos": "cluster de 6 nos do OSM (4 listados no id + '#2more')",
        "vias_que_saem": sorted({e.getName() or e.getID() for e in no.getOutgoing()}),
        "distancia_da_quata_m": round(net.getEdge(aq.SAIDA).getLength(), 1),
    }
    # rotas da validacao: quantos veiculos do corredor passam pelo 4o e para onde vao
    corr = {i.getEdge().getID() for t in ic.CONTROLADOS for i, o, li in net.getTLS(t).getConnections()}
    ent4 = set(entradas)
    tot, destinos = Counter(), Counter()
    for s in SEMENTES:
        for v in ET.parse(cfg(s).parent / "rotas.rou.xml").getroot().iter("vehicle"):
            r = v.find("route").get("edges").split()
            st = set(r)
            c = bool(st & corr)
            tot["veiculos"] += 1
            tot["corredor"] += c
            tot["passam_pelo_4o"] += bool(st & ent4)
            if aq.SAIDA in st:
                tot["corredor_seguem_para_o_4o"] += c
                k = r.index(aq.SAIDA)
                destinos[net.getEdge(r[k + 1]).getName() + f" ({r[k + 1]})" if k + 1 < len(r) else "termina"] += 1
            for e in ent4 - {aq.SAIDA}:
                tot[f"entram_no_4o_por_{e}"] += e in st
    info["rotas_validacao_221_225"] = {k: round(v / len(SEMENTES), 1) for k, v in tot.items()}
    info["rotas_validacao_221_225"]["unidade"] = "veiculos por semente (media)"
    info["destinos_apos_o_4o"] = {k: round(v / len(SEMENTES), 1) for k, v in destinos.most_common()}
    # bloqueio da saida (registros existentes da otimizacao final, validacao 221-225)
    bloq = {}
    for p in sorted((OTIM / "validacao" / "episodios").glob("*")):
        eps = [json.loads(m.read_text(encoding="utf-8")) for m in p.glob("**/metricas.json")]
        if not eps:
            continue
        b = [e["bloqueio_saida_corredor_s"] for e in eps if e["valido"]]
        jan = [e["fim_s"] - 300 for e in eps if e["valido"]]
        bloq[p.name] = {"episodios": len(b), "bloqueio_s_medio": round(statistics.fmean(b), 1),
                        "bloqueio_max_s": max(b), "fracao_do_tempo_de_controle_%": round(100 * sum(b) / sum(jan), 2)}
    info["bloqueio_saida_registros_validacao"] = bloq
    SAIDA_RES.mkdir(exist_ok=True)
    ic.json_novo(SAIDA_RES / f"estatico_{datetime.datetime.now():%Y%m%dT%H%M%S}.json", info)
    print(json.dumps(info, ensure_ascii=False, indent=1))


def _rodar(job):
    import torch
    torch.set_num_threads(1)
    import ambiente_quarto as aq
    import treinar_marl_insper_v2 as tr
    agentes, config = None, {"verde_minimo": 10, "colisao": "atribuida"}
    if job.get("checkpoint"):
        d, agentes = tr.carregar(job["checkpoint"], "independente")
        config = d["config"]
    m = aq.rodar_episodio(cfg(job["semente"]), Path(job["pasta"]), job["semente"], agentes, job["modo"],
                          monitor_completo=job.get("monitor", False), limite=job.get("limite", aq.LIMITE),
                          config=config, quarto=job["quarto"], rotulo=Path(job["pasta"]).as_posix().replace("/", "_")[-60:])
    return job["rotulo"], {"semente": job["semente"], "valido": m["valido"], "motivo": m["motivo_invalido"],
                           "espera_corredor": m["espera_corredor_s"].get("media"),
                           "p95_corredor": m["espera_corredor_s"].get("p95"),
                           "espera_rede": m["espera_rede_s"].get("media"), "p95_rede": m["espera_rede_s"].get("p95"),
                           "bloqueio_saida_s": m["bloqueio_saida_corredor_s"],
                           "filas_3": {t: m["filas"][t]["media"] for t in ic.CONTROLADOS},
                           "filas_4o": {e: v.get("media") for e, v in m["quarto"]["filas_aproximacoes"].items()},
                           "filas_4o_max": {e: v.get("max") for e, v in m["quarto"]["filas_aproximacoes"].items()},
                           "concluidas": m["fracao_concluida"], "teleportes": m["teleportes"]["total"],
                           "colisoes": m["colisoes"]["eventos"], "colisoes_classes": m["colisoes"]["por_classe"],
                           "violacoes": m["seguranca"]["violacoes"], "violacoes_4o": m["quarto"]["violacoes"],
                           "verdes_4o": m["quarto"]["verificacao"]["verdes"],
                           "vermelho_geral_4o": m["quarto"]["verificacao"]["vermelhos_gerais"],
                           "outros_erros": sum(o["erros"] for o in m["outros_semaforos"].values()),
                           "n_outros_monitorados": len(m["outros_semaforos"]), "trocas": m["trocas"]}


def jobs_para(pasta, limite=None, sementes=SEMENTES, monitor=False, so_classicos=False):
    sel = json.loads((OTIM / "validacao" / "braco_A_col.json").read_text(encoding="utf-8"))["selecao"]
    jobs = []
    for nome, (modo, braco) in BASES.items():
        if braco and so_classicos:
            continue
        for q in QUARTOS:
            rot = f"{nome}+{q or 'original'}"
            modelos = [(sm, v["checkpoint"]) for sm, v in sorted(sel.items())] if braco else [(None, None)]
            for sm, ck in modelos:
                for s in sementes:
                    j = {"rotulo": rot + (f"|{sm}" if sm else ""), "modo": modo, "quarto": q, "checkpoint": ck,
                         "semente": s, "monitor": monitor,
                         "pasta": str(pasta / "episodios" / rot.replace("+", "__") / (f"m{sm}" if sm else "") / f"s{s}")}
                    if limite:
                        j["limite"] = limite
                    jobs.append(j)
    return jobs


def executar(jobs, processos):
    res = {}
    with ProcessPoolExecutor(processos) as ex:
        for rot, r in ex.map(_rodar, jobs):
            res.setdefault(rot, []).append(r)
            print(f"{rot:>32} s{r['semente']}: valido={r['valido']} corredor {r['espera_corredor']} rede {r['espera_rede']} "
                  f"bloq {r['bloqueio_saida_s']} viol {r['violacoes']} tele {r['teleportes']}", flush=True)
    return res


def fumaca(args):
    if PROIBIDAS & set(SEMENTES):
        raise RuntimeError("semente proibida")
    antes = ic.hashes_cenario()
    pasta = SAIDA_RES / f"{datetime.datetime.now():%Y%m%dT%H%M%S}_fumaca"
    jobs = [j for j in jobs_para(pasta, limite=1500, sementes=[224], monitor=True, so_classicos=True)]
    res = executar(jobs, args.processos)
    ic.conferir_cenario(antes)
    ok = all(r["violacoes"] == 0 and r["outros_erros"] == 0 for v in res.values() for r in v)
    ok &= all(r["n_outros_monitorados"] == (11 if "+original" in k else 10) for k, v in res.items() for r in v)
    ok &= all(r["verdes_4o"]["min"] >= 10 and r["vermelho_geral_4o"]["min"] == 2 for k, v in res.items()
              for r in v if "+original" not in k)
    ic.json_novo(pasta / "fumaca.json", {"ok": ok, "resultados": res})
    print("FUMACA OK" if ok else "FUMACA FALHOU")
    return 0 if ok else 1


def experimento(args):
    if PROIBIDAS & set(SEMENTES):
        raise RuntimeError("semente proibida")
    antes = ic.hashes_cenario()
    pasta = SAIDA_RES / f"{datetime.datetime.now():%Y%m%dT%H%M%S}_experimento"
    res = executar(jobs_para(pasta), args.processos)
    ic.conferir_cenario(antes)
    resumo = {}
    for rot, v in res.items():
        val = [r for r in v if r["valido"]]
        resumo[rot] = {"n": len(v), "validos": len(val),
                       **{k: round(statistics.fmean(r[k] for r in val), 3) for k in
                          ("espera_corredor", "p95_corredor", "espera_rede", "p95_rede", "bloqueio_saida_s", "teleportes")},
                       "violacoes": sum(r["violacoes"] for r in v), "colisoes": sum(r["colisoes"] for r in v),
                       "concluidas_min": min(r["concluidas"] for r in v),
                       "filas_4o": {e: round(statistics.fmean(r["filas_4o"][e] for r in val), 2) for e in val[0]["filas_4o"]}}
    ic.json_novo(pasta / "experimento.json", {"sementes": SEMENTES, "resumo": resumo, "por_episodio": res})
    print(json.dumps(resumo, indent=1, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["estatico", "fumaca", "experimento"])
    ap.add_argument("--processos", type=int, default=8)
    args = ap.parse_args()
    return {"estatico": estatico, "fumaca": fumaca, "experimento": experimento}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main() or 0)
