"""Avaliacao (sem treino, politica gulosa) no cenario intenso com sementes de teste.

Compara o programa original com checkpoints dos modelos independente e
hierarquico, sempre com o mesmo ambiente e as mesmas metricas. Episodios
invalidos (travamento) sao listados a parte e NAO entram nas medias.

uso:
    python -B -X utf8 semaforo/integracao_insper/avaliar_marl_insper.py --original \
        --checkpoint indep_s1=<pasta>/politica_ep0020.pt --checkpoint hier_s1=<pasta>/politica_ep0020.pt
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import insper_comum as ic  # noqa: E402

SEMENTES_TESTE = [211, 212, 213, 214, 215]  # demandas 'intenso' validadas; nunca usadas no treino (1001-1030)


def tarefa(job):
    import torch
    torch.set_num_threads(1)
    import ambiente_marl_insper as amb
    import treinar_marl_insper as tr
    nivel = job.get("nivel", "intenso")
    cfg = ic.SEMAFORO / "cenarios" / "insper_demanda" / nivel / f"semente_{job['semente']}" / "cenario.sumocfg"
    if job["checkpoint"]:
        d, agentes = tr.carregar(job["checkpoint"])
        modo = d["modelo"]
    else:
        agentes, modo = None, job.get("modo", "original")
    m = amb.rodar_episodio(cfg, job["pasta"], job["semente"], agentes, modo, treinando=False,
                           monitor_completo=True, rotulo=f"av_{job['rotulo']}_{job['semente']}")
    return job["rotulo"], job["semente"], m


def media(v):
    v = [x for x in v if x is not None]
    return round(statistics.fmean(v), 3) if v else None


def agregar(ms):
    validos = [m for m in ms if m["valido"]]
    a = {"episodios": len(ms), "validos": len(validos),
         "invalidos": [{"semente": m["semente_trafego"], "motivo": m["motivo_invalido"]} for m in ms if not m["valido"]]}
    campos = {
        "espera_corredor_media": lambda m: m["espera_corredor_s"].get("media"),
        "espera_corredor_p95": lambda m: m["espera_corredor_s"].get("p95"),
        "espera_corredor_desde_t0_media": lambda m: m.get("espera_corredor_desde_t0_s", {}).get("media"),
        "espera_rede_media": lambda m: m["espera_rede_s"].get("media"),
        "espera_rede_p95": lambda m: m["espera_rede_s"].get("p95"),
        "fracao_concluida": lambda m: m["fracao_concluida"],
        "presos_gt180s": lambda m: m["presos_gt180s"],
        "bloqueio_saida_corredor_s": lambda m: m["bloqueio_saida_corredor_s"],
    }
    for t in ic.CONTROLADOS:
        campos[f"fila_media_{t}"] = lambda m, t=t: m["filas"][t].get("media")
        campos[f"fila_max_{t}"] = lambda m, t=t: m["filas"][t].get("max")
    for k, f in campos.items():
        a[k] = media(f(m) for m in validos)
        a[k + "_faixa"] = [min(f(m) for m in validos), max(f(m) for m in validos)] if validos else None
    a["colisoes_total"] = sum(m["colisoes"]["eventos"] for m in ms)
    a["colisoes_nos_controlados"] = sum(m["colisoes"]["nos_controlados"] for m in ms)
    a["teleportes_total"] = sum(m["teleportes"]["total"] for m in ms)
    a["teleportes_por_semente"] = [m["teleportes"]["total"] for m in ms]
    a["violacoes_seguranca"] = sum(m["seguranca"]["violacoes"] for m in ms)
    a["duracao_real_media_s"] = media(m["duracao_real_s"] for m in ms)
    return a


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--checkpoint", action="append", default=[], help="ROTULO=caminho.pt")
    ap.add_argument("--original", action="store_true")
    ap.add_argument("--sementes", type=int, nargs="+", default=SEMENTES_TESTE)
    ap.add_argument("--processos", type=int, default=10)
    args = ap.parse_args()
    antes = ic.hashes_cenario()
    pasta = ic.nova_pasta("avaliacao_marl")
    controles = ([("original", None)] if args.original else []) + [tuple(c.split("=", 1)) for c in args.checkpoint]
    jobs = [{"rotulo": r, "checkpoint": ck, "semente": s, "pasta": str(pasta / r / f"semente_{s}")}
            for r, ck in controles for s in args.sementes]
    resultados = {}
    with ProcessPoolExecutor(args.processos) as ex:
        for r, s, m in ex.map(tarefa, jobs):
            resultados.setdefault(r, []).append(m)
            print(f"{r:>12} s{s}: valido={m['valido']} espera corredor {m['espera_corredor_s'].get('media')} "
                  f"rede {m['espera_rede_s'].get('media')} concl {m['fracao_concluida']} tele {m['teleportes']['total']} "
                  f"col {m['colisoes']['eventos']} ({m['duracao_real_s']} s)", flush=True)
    tabela = {r: agregar(ms) for r, ms in resultados.items()}
    ic.json_novo(pasta / "avaliacao.json", {"sementes_teste": args.sementes,
                                            "checkpoints": dict(controles), "tabela": tabela})
    ic.conferir_cenario(antes)
    print(json.dumps(tabela, ensure_ascii=False, indent=1))
    print("avaliacao salva em", pasta)


if __name__ == "__main__":
    main()
