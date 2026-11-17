"""Experimento zero-shot C3 -> C5: avaliacao (sem treino) com demandas novas.

Controles (mesmas demandas e sementes em todos):
  original    os 14 semaforos no programa original
  C3          Modelo C (5 checkpoints finais) nos 3 do corredor; os outros 11 no original
  C5          o MESMO checkpoint nos 5 (3 do corredor + 300058973 + 302806060); os outros 9 no original
  atuado3/5   diagnostico: controle classico atuado com as MESMAS regras do RL nos 3 / nos 5
              (separa o efeito das regras operacionais do efeito da politica)
Os 5 cruzamentos sao medidos em todos os controles.

Demanda: intensa (2000 veic/h no corredor, mesmo gerador do nivel intenso), sementes NOVAS 291-300
(conferidas contra todas as pastas de demanda e sementes ja usadas). A demanda nao e alterada.

uso (na raiz):
  python -B -X utf8 semaforo/integracao_insper/parameter_sharing/experimento_c5/bateria_c5.py demandas
  ... piloto --processos 8         (1 checkpoint x 2 sementes, para conferir o funcionamento)
  ... avaliar --processos 12       (5 checkpoints x 10 sementes; uma unica vez)
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
import datetime
import json
from pathlib import Path
import sys

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI.parents[1]))
sys.path.insert(0, str(AQUI.parents[1] / "otimizacao_final"))
import adaptador_c5 as ad  # noqa: E402
import insper_comum as ic  # noqa: E402

NIVEL = "intenso_c5_teste"
SEMENTES = list(range(291, 301))
SAIDA = AQUI / "resultados"
CONFIG = {"verde_minimo": 10, "colisao": "atribuida", "supervisor_s": 30}
RAIZ = AQUI.parents[3]


def conferir_sementes():
    import bateria_otimizacao as bo
    import bateria_ps as bps
    usadas = set().union(*bo.USADAS.values()) | set(bo.VALIDACAO) | set(bo.TESTE)
    usadas |= {s for _, ss in bps.TESTES.values() for s in ss} | set(range(1001, 1031))
    existentes = {int(p.name.split("_")[1]) for p in (ic.SEMAFORO / "cenarios" / "insper_demanda").glob("*/semente_*")
                  if p.parent.name != NIVEL}
    if set(SEMENTES) & (usadas | existentes):
        raise RuntimeError(f"sobreposicao: {set(SEMENTES) & (usadas | existentes)}")
    return {"nivel": NIVEL, "sementes": SEMENTES, "conferidas_contra": len(usadas | existentes)}


def _gerar(s):
    import gerar_demanda_insper as gd
    if not (gd.DERIVADO / NIVEL / f"semente_{s}").exists():
        gd.gerar(NIVEL, 2000, s, 12.0)


def demandas(_):
    SAIDA.mkdir(parents=True, exist_ok=True)
    info = conferir_sementes()
    with ProcessPoolExecutor(8) as ex:
        list(ex.map(_gerar, SEMENTES))
    (SAIDA / "sementes.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print(info)


def tarefa(job):
    import torch
    torch.set_num_threads(1)
    import ambiente_c5 as env5
    import politica_compartilhada as pc
    cfg = ic.SEMAFORO / "cenarios" / "insper_demanda" / NIVEL / f"semente_{job['semente']}" / "cenario.sumocfg"
    agentes = None
    if job.get("checkpoint"):
        d, rede = pc.carregar(job["checkpoint"])
        if d["config"] != dict(env5.CONFIG_V1, **CONFIG):
            raise RuntimeError("config do checkpoint diferente")
        agentes = ad.visoes(rede, job["controlados"])
    m = env5.rodar_episodio(cfg, job["pasta"], job["semente"], agentes, job["modo"], treinando=False,
                            monitor_completo=True, config=CONFIG, controlados=job.get("controlados"), medidos=ad.NOVOS,
                            rotulo=f"c5_{job['rotulo'].replace('|', '_')}_{job['semente']}")
    if agentes is not None and rede.gradientes != d["rede"]["gradientes"]:
        raise RuntimeError("a rede mudou durante a avaliacao")
    linha = {"semente": job["semente"], "valido": m["valido"], "motivo_invalido": m["motivo_invalido"],
             "espera_corredor": m["espera_corredor_s"], "espera_rede": m["espera_rede_s"],
             "fracao_concluida": m["fracao_concluida"], "veiculos_gerados": m["veiculos_gerados"],
             "teleportes": m["teleportes"]["total"], "colisoes": m["colisoes"]["eventos"],
             "colisoes_nos_controlados": m["colisoes"]["nos_controlados"], "colisoes_nos_5": m["colisoes"]["nos_medidos"],
             "colisoes_por_classe": m["colisoes"]["por_classe"], "violacoes": m["seguranca"]["violacoes"],
             "cruzamentos": m["cruzamentos"], "bloqueio_saida_corredor_s": m["bloqueio_saida_corredor_s"],
             "trocas": m["trocas"], "outros_monitorados": len(m["outros_semaforos"]),
             "outros_com_erro": sum(o["erros"] > 0 for o in m["outros_semaforos"].values()),
             "presos_gt180s": m["presos_gt180s"]}
    return job["rotulo"], linha


def jobs(pasta, modelos, sementes):
    man = json.loads((AQUI.parent / "modelos_finais" / "manifesto.json").read_text(encoding="utf-8"))
    sel = man["bracos"]["C"]["sementes_modelo"]
    js = []
    for s in sementes:
        js.append({"rotulo": "original", "modo": "original", "semente": s, "pasta": str(pasta / "original" / f"s{s}")})
        js.append({"rotulo": "atuado3", "modo": "atuado_equivalente", "controlados": ad.TLS3, "semente": s,
                   "pasta": str(pasta / "atuado3" / f"s{s}")})
        js.append({"rotulo": "atuado5", "modo": "atuado_equivalente", "controlados": ad.TLS5, "semente": s,
                   "pasta": str(pasta / "atuado5" / f"s{s}")})
        for sm in modelos:
            ck = str(RAIZ / sel[sm]["arquivo"])
            js.append({"rotulo": f"C3|{sm}", "modo": "independente", "controlados": ad.TLS3, "checkpoint": ck,
                       "semente": s, "pasta": str(pasta / "C3" / f"m{sm}" / f"s{s}")})
            js.append({"rotulo": f"C5|{sm}", "modo": "independente", "controlados": ad.TLS5, "checkpoint": ck,
                       "semente": s, "pasta": str(pasta / "C5" / f"m{sm}" / f"s{s}")})
    return js, {sm: sel[sm]["arquivo"] for sm in modelos}


def executar(nome, modelos, sementes, processos):
    antes = ic.hashes_cenario()
    conferir_sementes()
    pasta = SAIDA / nome
    pasta.mkdir(parents=True, exist_ok=False)
    js, cks = jobs(pasta, modelos, sementes)
    res = {}
    with ProcessPoolExecutor(processos) as ex:
        for rot, l in ex.map(tarefa, js):
            res.setdefault(rot, []).append(l)
            c = l["cruzamentos"]
            print(f"{rot:>10} s{l['semente']}: valido={l['valido']} corredor {l['espera_corredor'].get('media')} "
                  f"rede {l['espera_rede'].get('media')} novos {c['300058973']['espera_s'].get('media')}/"
                  f"{c['302806060']['espera_s'].get('media')} viol {l['violacoes']} tele {l['teleportes']}", flush=True)
    ic.json_novo(pasta / "avaliacao_c5.json", {"nivel": NIVEL, "sementes": sementes, "checkpoints_C": cks,
                                               "controlados": {"C3": ad.TLS3, "C5": ad.TLS5}, "config": CONFIG,
                                               "mapeamento": {t: {k: v for k, v in m.items() if k != "acao_real"}
                                                              | {"acao_real": {str(a): f for a, f in m["acao_real"].items()}}
                                                              for t, m in ad.mapeamento(ad.TLS5).items()},
                                               "por_episodio": res})
    ic.conferir_cenario(antes)
    print("salvo em", pasta)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["demandas", "piloto", "avaliar"])
    ap.add_argument("--processos", type=int, default=12)
    a = ap.parse_args()
    if a.cmd == "demandas":
        demandas(a)
    elif a.cmd == "piloto":
        executar(f"{datetime.datetime.now():%Y%m%dT%H%M%S}_piloto", ["1"], SEMENTES[:2], a.processos)
    else:
        executar("avaliacao_final", ["1", "2", "3", "4", "5"], SEMENTES, a.processos)


if __name__ == "__main__":
    main()
