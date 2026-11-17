"""Bateria do C5 treinado (C5-A, demanda intensa atual): demandas de teste novas, comparadores, validacao e teste.

Sementes:
  treino     1001-1030 (as mesmas do C3 e do Modelo A)
  validacao  221-225 (intenso_validacao; selecao de checkpoint SO aqui)
  teste      intenso_c5t_teste 331-340 (2000 veic/h)  e  moderado_c5t_teste 341-350 (1200 veic/h, robustez)
             novas, conferidas contra todas as ja usadas (inclusive 291-300 do zero-shot)
Criterio de selecao (definido antes de ver qualquer resultado): checkpoint elegivel (5/5 validos, 0 violacoes,
0 colisoes nos controlados, >= 99% concluidas, <= 1 teletransporte por episodio) com a menor espera media por
veiculo nos 5 cruzamentos controlados (ponderada pelo n. de veiculos de cada); empate < 2%: menor P95 da rede;
depois o checkpoint mais antigo.

uso (na raiz):
  python -B -X utf8 semaforo/integracao_insper/parameter_sharing/treinamento_c5/bateria_treino_c5.py demandas
  ... comparadores --processos 6     (Original, atuado3, atuado5, C3, C3->C5 nas demandas de teste)
  ... validar --processos 12
  ... testar --processos 12          (C5 selecionado, uma unica vez)
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import statistics
import sys

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import politica_c5 as p5  # noqa: E402
import insper_comum as ic  # noqa: E402

ad = p5.ad
SAIDA = AQUI / "resultados"
RAIZ = AQUI.parents[3]
SEMENTES_MODELO = ["1", "2", "3", "4", "5"]
CHECKPOINTS = [25, 50, 75, 100, 125, 150]
VALIDACAO = [221, 222, 223, 224, 225]
TESTES = {"intenso_c5t_teste": (2000, list(range(331, 341))), "moderado_c5t_teste": (1200, list(range(341, 351)))}
CONFIG = {"verde_minimo": 10, "colisao": "atribuida", "supervisor_s": 30}


def conferir_sementes():
    sys.path.insert(0, str(AQUI.parent / "experimento_c5"))
    import bateria_otimizacao as bo
    import bateria_ps as bps
    import bateria_c5 as bc5
    usadas = set().union(*bo.USADAS.values()) | set(bo.VALIDACAO) | set(bo.TESTE) | set(bc5.SEMENTES)
    usadas |= {s for _, ss in bps.TESTES.values() for s in ss} | set(range(1001, 1031))
    existentes = {int(p.name.split("_")[1]) for p in (ic.SEMAFORO / "cenarios" / "insper_demanda").glob("*/semente_*")
                  if p.parent.name not in TESTES}
    novas = [s for _, ss in TESTES.values() for s in ss]
    if set(novas) & (usadas | existentes):
        raise RuntimeError(f"sobreposicao {set(novas) & (usadas | existentes)}")
    return {"teste": {n: ss for n, (_, ss) in TESTES.items()}, "validacao": VALIDACAO, "treino": "1001-1030",
            "conferidas_contra": len(usadas | existentes)}


def _gerar(a):
    nivel, corredor, s = a
    import gerar_demanda_insper as gd
    if not (gd.DERIVADO / nivel / f"semente_{s}").exists():
        gd.gerar(nivel, corredor, s, 12.0)


def demandas(_):
    info = conferir_sementes()
    with ProcessPoolExecutor(8) as ex:
        list(ex.map(_gerar, [(n, c, s) for n, (c, ss) in TESTES.items() for s in ss]))
    (SAIDA / "sementes.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print(info)


def tarefa(job):
    import torch
    torch.set_num_threads(1)
    import ambiente_c5 as env5
    cfg = ic.SEMAFORO / "cenarios" / "insper_demanda" / job["nivel"] / f"semente_{job['semente']}" / "cenario.sumocfg"
    agentes, g0 = None, None
    if job.get("c5"):
        d, rede = p5.carregar(RAIZ / job["c5"])
        agentes, g0 = p5.visoes_avaliacao(rede), rede.gradientes
    elif job.get("c3"):
        import politica_compartilhada as pc
        d, rede = pc.carregar(job["c3"])
        agentes, g0 = ad.visoes(rede, job["controlados"]), rede.gradientes
    m = env5.rodar_episodio(cfg, job["pasta"], job["semente"], agentes, job["modo"], treinando=False, monitor_completo=True,
                            config=CONFIG, controlados=job.get("controlados"), medidos=ad.NOVOS,
                            rotulo=f"t5_{job['rotulo'].replace('|', '_')}_{job['nivel'][:4]}_{job['semente']}")
    if g0 is not None and rede.gradientes != g0:
        raise RuntimeError("a rede mudou durante a avaliacao")
    return job["rotulo"], {
        "semente": job["semente"], "valido": m["valido"], "motivo_invalido": m["motivo_invalido"],
        "espera_corredor": m["espera_corredor_s"], "espera_rede": m["espera_rede_s"],
        "fracao_concluida": m["fracao_concluida"], "teleportes": m["teleportes"]["total"], "colisoes": m["colisoes"]["eventos"],
        "colisoes_nos_controlados": m["colisoes"]["nos_controlados"], "colisoes_nos_5": m["colisoes"]["nos_medidos"],
        "violacoes": m["seguranca"]["violacoes"], "cruzamentos": m["cruzamentos"],
        "bloqueio_saida_corredor_s": m["bloqueio_saida_corredor_s"], "trocas": m["trocas"],
        "outros_com_erro": sum(o["erros"] > 0 for o in m["outros_semaforos"].values())}


def avaliar(jobs, processos):
    res = {}
    with ProcessPoolExecutor(processos) as ex:
        for rot, l in ex.map(tarefa, jobs):
            res.setdefault(rot, []).append(l)
            print(f"{rot:>28} s{l['semente']}: valido={l['valido']} corredor {l['espera_corredor'].get('media')} "
                  f"rede {l['espera_rede'].get('media')} viol {l['violacoes']} tele {l['teleportes']}", flush=True)
    return res


def espera5(l):
    c = [l["cruzamentos"][t] for t in ad.TLS5]
    n = sum(x["veiculos"] for x in c)
    return sum(x["espera_s"].get("media", 0) * x["veiculos"] for x in c) / n if n else None


def resumo(eps):
    val = [l for l in eps if l["valido"]]

    def med(f):
        v = [f(l) for l in val]
        return statistics.fmean(v) if v else None
    r = {"episodios": len(eps), "validos": len(val), "espera5": med(espera5),
         "espera_corredor": med(lambda l: l["espera_corredor"]["media"]), "espera_rede": med(lambda l: l["espera_rede"]["media"]),
         "p95_rede": med(lambda l: l["espera_rede"]["p95"]), "concluidas_min": min(l["fracao_concluida"] for l in eps),
         "teleportes_max": max(l["teleportes"] for l in eps), "violacoes": sum(l["violacoes"] for l in eps),
         "colisoes_nos_controlados": sum(l["colisoes_nos_controlados"] for l in eps),
         "trocas": {t: med(lambda l, t=t: l["trocas"].get(t, 0)) for t in ad.TLS5}}
    r["elegivel"] = (r["validos"] == len(eps) and not r["violacoes"] and not r["colisoes_nos_controlados"]
                     and r["concluidas_min"] >= 0.99 and r["teleportes_max"] <= 1)
    return r


def comparadores(args):
    man3 = json.loads((AQUI.parent / "modelos_finais" / "manifesto.json").read_text(encoding="utf-8"))
    sel3 = man3["bracos"]["C"]["sementes_modelo"]
    for nivel, (_, sementes) in TESTES.items():
        pasta = SAIDA / "teste" / nivel
        pasta.mkdir(parents=True, exist_ok=True)
        if (pasta / "comparadores.json").exists():
            continue
        js = []
        for s in sementes:
            js += [{"rotulo": "original", "modo": "original", "nivel": nivel, "semente": s, "pasta": str(pasta / "original" / f"s{s}")},
                   {"rotulo": "atuado3", "modo": "atuado_equivalente", "controlados": ad.TLS3, "nivel": nivel, "semente": s,
                    "pasta": str(pasta / "atuado3" / f"s{s}")},
                   {"rotulo": "atuado5", "modo": "atuado_equivalente", "controlados": ad.TLS5, "nivel": nivel, "semente": s,
                    "pasta": str(pasta / "atuado5" / f"s{s}")}]
            for sm in SEMENTES_MODELO:
                ck = str(RAIZ / sel3[sm]["arquivo"])
                js += [{"rotulo": f"C3|{sm}", "modo": "independente", "controlados": ad.TLS3, "c3": ck, "nivel": nivel,
                        "semente": s, "pasta": str(pasta / "C3" / f"m{sm}" / f"s{s}")},
                       {"rotulo": f"C3_C5|{sm}", "modo": "independente", "controlados": ad.TLS5, "c3": ck, "nivel": nivel,
                        "semente": s, "pasta": str(pasta / "C3_C5" / f"m{sm}" / f"s{s}")}]
        res = avaliar(js, args.processos)
        ic.json_novo(pasta / "comparadores.json", {"nivel": nivel, "sementes": sementes,
                                                   "checkpoints_C3": {sm: v["arquivo"] for sm, v in sel3.items()},
                                                   "por_episodio": res})


def validar(args):
    pasta = SAIDA / "validacao"
    pasta.mkdir(parents=True, exist_ok=False)
    js = [{"rotulo": f"C5|{sm}|{e}", "modo": "independente", "controlados": ad.TLS5, "nivel": "intenso_validacao",
           "c5": str(SAIDA / "treinos" / f"C5_s{sm}" / f"politica_ep{e:04d}.pt"), "semente": s,
           "pasta": str(pasta / "episodios" / f"s{sm}_ep{e:04d}" / f"s{s}")}
          for sm in SEMENTES_MODELO for e in CHECKPOINTS for s in VALIDACAO]
    js += [{"rotulo": r, "modo": m, "controlados": c, "nivel": "intenso_validacao", "semente": s,
            "pasta": str(pasta / "episodios" / r / f"s{s}")}
           for r, m, c in (("original", "original", None), ("atuado5", "atuado_equivalente", ad.TLS5)) for s in VALIDACAO]
    res = avaliar(js, args.processos)
    tab = {sm: {e: resumo(res[f"C5|{sm}|{e}"]) for e in CHECKPOINTS} for sm in SEMENTES_MODELO}
    sel = {}
    for sm in SEMENTES_MODELO:
        eleg = {e: r for e, r in tab[sm].items() if r["elegivel"]}
        if eleg:
            melhor = min(r["espera5"] for r in eleg.values())
            prox = [e for e, r in eleg.items() if r["espera5"] <= 1.02 * melhor]
            e = min(prox, key=lambda e: (eleg[e]["p95_rede"], e))
        else:
            e = min(tab[sm], key=lambda e: (tab[sm][e]["episodios"] - tab[sm][e]["validos"], tab[sm][e]["espera5"] or 1e9, e))
        sel[sm] = {"episodio": e, "elegivel": bool(eleg), "checkpoint": (SAIDA / "treinos" / f"C5_s{sm}" / f"politica_ep{e:04d}.pt").relative_to(RAIZ).as_posix(),
                   "validacao": tab[sm][e]}
    ic.json_novo(pasta / "selecao_c5.json", {"criterio": __doc__.split("Criterio de selecao")[1].split("uso")[0].strip(),
                                             "sementes_validacao": VALIDACAO, "tabela": tab, "selecao": sel,
                                             "referencias": {r: resumo(res[r]) for r in ("original", "atuado5")}, "por_episodio": res})
    print({sm: (v["episodio"], round(v["validacao"]["espera5"], 3), v["elegivel"]) for sm, v in sel.items()})


def testar(args):
    sel = json.loads((SAIDA / "validacao" / "selecao_c5.json").read_text(encoding="utf-8"))["selecao"]
    for nivel, (_, sementes) in TESTES.items():
        pasta = SAIDA / "teste" / nivel
        if (pasta / "c5.json").exists():
            raise RuntimeError("teste do C5 ja executado")
        js = [{"rotulo": f"C5|{sm}", "modo": "independente", "controlados": ad.TLS5, "c5": v["checkpoint"], "nivel": nivel,
               "semente": s, "pasta": str(pasta / "C5" / f"m{sm}" / f"s{s}")} for sm, v in sel.items() for s in sementes]
        res = avaliar(js, args.processos)
        ic.json_novo(pasta / "c5.json", {"nivel": nivel, "sementes": sementes,
                                         "checkpoints_C5": {sm: v["checkpoint"] for sm, v in sel.items()}, "por_episodio": res})


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["demandas", "comparadores", "validar", "testar"])
    ap.add_argument("--processos", type=int, default=12)
    a = ap.parse_args()
    antes = ic.hashes_cenario()
    {"demandas": demandas, "comparadores": comparadores, "validar": validar, "testar": testar}[a.cmd](a)
    ic.conferir_cenario(antes)


if __name__ == "__main__":
    main()
