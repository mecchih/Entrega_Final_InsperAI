"""Calibracao progressiva e validacao dos niveis de demanda do cenario Insper.

Sempre com os programas semaforicos ORIGINAIS (sem IA). Dois modos:

  varredura  gera demandas de calibracao (em resultados/, fora do cenario) para
             pontos CORREDOR:DENSIDADE_RESTO e simula cada semente;
  validar    gera os niveis escolhidos em semaforo/cenarios/insper_demanda/<nivel>/
             (sementes independentes por nivel) e os avalia junto do original.

uso (na raiz do repositorio):
    python -B -X utf8 semaforo/integracao_insper/calibrar_demanda_insper.py varredura --pontos 95:12 300:12 --sementes 9001 9002
    python -B -X utf8 semaforo/integracao_insper/calibrar_demanda_insper.py validar --niveis semaforo/cenarios/insper_demanda/niveis.json
"""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import insper_comum as ic  # noqa: E402
import avaliar_demanda_insper as av  # noqa: E402
import gerar_demanda_insper as gd  # noqa: E402

TLS = list(ic.CONTROLADOS)


def tarefa(job):
    """Executada em outro processo: gera (se preciso) e simula uma semente."""
    if job.get("gerar"):
        g = job["gerar"]
        destino, _ = gd.gerar(g["nivel"], g["corredor"], g["semente"], g["densidade_resto"], destino=g["destino"])
        cfg = Path(destino) / "cenario.sumocfg"
    else:
        cfg = Path(job["cfg"])
    r = av.simular(cfg, job["pasta"], job["semente_sumo"], job["rotulo"], job["porta"])
    return {"chave": job["chave"], "semente": job["semente_sumo"], "metricas": r}


def executar(jobs, processos):
    with ProcessPoolExecutor(max_workers=processos) as ex:
        resultados = []
        for r in ex.map(tarefa, jobs):
            m = r["metricas"]
            print(f"  {r['chave']:>22} s{r['semente']:<5} gerados {m['veiculos_gerados']:5d} "
                  f"concl {m['fracao_concluida']:.3f} filas {[m['por_semaforo'][t]['fila']['media'] for t in TLS]} "
                  f"max {[m['por_semaforo'][t]['fila']['max'] for t in TLS]} tele {m['teleportes']['total']} "
                  f"col {m['colisoes']['eventos']} ({m['duracao_real_s']} s)", flush=True)
            resultados.append(r)
    return resultados


def media(v):
    v = [x for x in v if x is not None]
    return round(statistics.fmean(v), 3) if v else None


def faixa(v):
    v = [x for x in v if x is not None]
    return [round(min(v), 3), round(max(v), 3)] if v else None


def extrair(m):
    """Indicadores por rodada usados nas tabelas e nos criterios."""
    p = m["por_semaforo"]
    c = m["corredor"]
    d = {"gerados": m["veiculos_gerados"], "concluidos": m["veiculos_concluidos"],
         "fracao_concluida": m["fracao_concluida"],
         "nao_atendidos_no_fim": m["nao_inseridos_no_fim"] + m["em_rede_no_fim"],
         "presos_gt180s": m["veiculos_presos_espera_continua_gt_180s"],
         "pendentes_insercao_max": m["pendentes_insercao_max"],
         "corredor_veiculos": c["veiculos"], "corredor_2_ou_3": c["veiculos_2_ou_3"],
         "corredor_3": c["por_numero_de_cruzamentos"].get(3, c["por_numero_de_cruzamentos"].get("3", 0)),
         "espera_corredor_media": c["espera_no_corredor_s"].get("media"),
         "espera_corredor_p95": c["espera_no_corredor_s"].get("p95"),
         "espera_rede_media": m["rede"]["espera_todos_s"]["media"], "espera_rede_p95": m["rede"]["espera_todos_s"]["p95"],
         "fracao_parados_rede_max5min": m["rede"]["fracao_parados_max_janela_5min"],
         "fila_seguinte_media": m["seguinte"]["fila_entradas"].get("media"),
         "fila_seguinte_max": m["seguinte"]["fila_entradas"].get("max"),
         "fila_saida_corredor_max": m["seguinte"]["fila_saida_corredor_234368026#1"].get("max"),
         "colisoes": m["colisoes"]["eventos"], "colisoes_por_juncao": m["colisoes"]["por_juncao"],
         "teleportes": m["teleportes"]["total"], "teleportes_por_via": m["teleportes"]["por_via"],
         "teleportes_por_motivo": m["teleportes"]["por_motivo"]}
    for t in TLS:
        f = p[t]["fila"]
        d[f"{t}_veiculos"] = p[t]["veiculos"]
        g = p[t]["por_grupo_verde"]
        d[f"{t}_menor_grupo"] = round(min(g.get("fase_0", 0), g.get("fase_1", 0)) / max(1, p[t]["veiculos"]), 3)
        d[f"{t}_fila_media"] = f.get("media")
        d[f"{t}_fila_p95"] = f.get("p95")
        d[f"{t}_fila_max"] = f.get("max")
        d[f"{t}_tempo_fila_ge1"] = f.get("fracao_tempo_com_fila_ge1")
        d[f"{t}_tempo_fila_ge5"] = f.get("fracao_tempo_com_fila_ge5")
        d[f"{t}_bloqueio_s"] = p[t]["segundos_verde_bloqueado_a_jusante"]
        d[f"{t}_parados_no_cruzamento"] = p[t]["veiculo_segundos_parados_dentro_do_cruzamento"]
    for e in av.TRECHOS:
        d[f"trecho_{e}_cheio_s"] = c["segundos_trecho_com_fila_ge90pct"].get(e, 0)
    return d


def agregar(resultados):
    grupos = {}
    for r in resultados:
        grupos.setdefault(r["chave"], []).append(extrair(r["metricas"]))
    tabela = {}
    for chave, linhas in grupos.items():
        ag = {"sementes": len(linhas)}
        for k in linhas[0]:
            if isinstance(linhas[0][k], dict):
                total = Counter()
                for l in linhas:
                    total.update(l[k])
                ag[k] = dict(total)
            else:
                ag[k] = {"media": media(l[k] for l in linhas), "faixa": faixa(l[k] for l in linhas)}
        tabela[chave] = ag
    return tabela


def varredura(args):
    pasta = ic.nova_pasta("calibracao_demanda")
    jobs = []
    for ponto in args.pontos:
        corredor, dens = ponto.split(":")
        for s in args.sementes:
            chave = f"c{corredor}_r{dens}"
            jobs.append({"chave": chave, "semente_sumo": s, "rotulo": f"{chave}_{s}", "porta": 8800 + len(jobs),
                         "pasta": str(pasta / "simulacoes" / f"{chave}_s{s}"),
                         "gerar": {"nivel": chave, "corredor": int(corredor), "semente": s,
                                   "densidade_resto": float(dens),
                                   "destino": str(pasta / "demandas" / f"{chave}_s{s}")}})
    if args.original:
        cfg = gd.preparar_original()
        for s in args.sementes:
            jobs.append({"chave": "original", "semente_sumo": s, "rotulo": f"orig_{s}", "porta": 8800 + len(jobs),
                         "pasta": str(pasta / "simulacoes" / f"original_s{s}"), "cfg": str(cfg)})
    resultados = executar(jobs, args.processos)
    ic.json_novo(pasta / "varredura.json", {"pontos": args.pontos, "sementes": args.sementes,
                                            "tabela": agregar(resultados)})
    print("varredura salva em", pasta)


def validar(args):
    niveis = json.loads(Path(args.niveis).read_text(encoding="utf-8"))
    pasta = ic.nova_pasta("validacao_niveis")
    jobs = []
    for n in niveis["niveis"]:
        for s in n["sementes"]:
            base = {"chave": n["nivel"], "semente_sumo": s, "rotulo": f"{n['nivel']}_{s}", "porta": 8800 + len(jobs),
                    "pasta": str(pasta / n["nivel"] / f"semente_{s}")}
            if n["nivel"] == "original":
                base["cfg"] = str(gd.preparar_original())
            else:
                destino = gd.DERIVADO / n["nivel"] / f"semente_{s}"
                if destino.exists():
                    base["cfg"] = str(destino / "cenario.sumocfg")
                else:
                    base["gerar"] = {"nivel": n["nivel"], "corredor": n["corredor"], "semente": s,
                                     "densidade_resto": n["densidade_resto"], "destino": str(destino)}
            jobs.append(base)
    resultados = executar(jobs, args.processos)
    tabela = agregar(resultados)
    # colisoes ja existentes = juncoes com colisao na demanda original
    preexistentes = set(tabela.get("original", {}).get("colisoes_por_juncao", {}))
    preexistentes |= set(niveis.get("juncoes_com_colisao_preexistente", []))
    for chave, ag in tabela.items():
        ag["colisoes_em_juncoes_preexistentes"] = sum(n for j, n in ag["colisoes_por_juncao"].items() if j in preexistentes)
        ag["colisoes_em_juncoes_novas"] = {j: n for j, n in ag["colisoes_por_juncao"].items() if j not in preexistentes}
    # consistencia: a ordem dos niveis se mantem semente a semente?
    ordem = [n["nivel"] for n in niveis["niveis"]]
    por_semente = {}
    for r in resultados:
        por_semente.setdefault(r["chave"], []).append(extrair(r["metricas"]))
    consistencia = {}
    for k in ["espera_corredor_media"] + [f"{t}_fila_media" for t in TLS]:
        pares = []
        for a, b in zip(ordem, ordem[1:]):
            va = [x[k] for x in por_semente[a]]
            vb = [x[k] for x in por_semente[b]]
            pares.append({"de": a, "para": b, "max_inferior": max(va), "min_superior": min(vb),
                          "sem_sobreposicao": max(va) < min(vb)})
        consistencia[k] = pares
    ic.json_novo(pasta / "validacao.json", {"niveis": niveis, "juncoes_com_colisao_preexistente": sorted(preexistentes),
                                            "tabela": tabela, "consistencia_entre_sementes": consistencia,
                                            "hashes_cenario_original": ic.hashes_cenario()})
    print("validacao salva em", pasta)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="modo", required=True)
    v = sub.add_parser("varredura")
    v.add_argument("--pontos", nargs="+", required=True, help="CORREDOR:DENSIDADE_RESTO, ex.: 300:12")
    v.add_argument("--sementes", nargs="+", type=int, default=[9001, 9002])
    v.add_argument("--original", action="store_true", help="inclui a demanda original com as mesmas sementes do SUMO")
    v.add_argument("--processos", type=int, default=8)
    w = sub.add_parser("validar")
    w.add_argument("--niveis", required=True)
    w.add_argument("--processos", type=int, default=8)
    args = ap.parse_args()
    antes = ic.hashes_cenario()
    (varredura if args.modo == "varredura" else validar)(args)
    ic.conferir_cenario(antes)


if __name__ == "__main__":
    main()
