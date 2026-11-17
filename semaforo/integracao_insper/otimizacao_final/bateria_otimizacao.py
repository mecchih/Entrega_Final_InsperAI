"""Otimizacao final: experimentos controlados sobre as tres hipoteses.

Bracos (mesmas 5 sementes de modelo 1-5, mesmas demandas de treino 1001-1030 na mesma
ordem, 150 episodios e hiperparametros identicos; so muda o que o nome indica):

  A_v1        independente, v1 (verde 10, colisao global, -)          [bateria anterior, so leitura]
  B_v1        hierarquico, v1 (verde 10, colisao global, sup 30)      [bateria anterior, so leitura]
  A_col       independente, verde 10, colisao ATRIBUIDA               -> efeito da recompensa (vs A_v1)
  A_col_v5    independente, verde 5,  colisao atribuida               -> efeito do verde minimo (vs A_col)
  B_<L>_s30   hierarquico, melhor configuracao local L, sup 30        -> efeito do supervisor (vs A_<L>)
  B_<L>_s15   hierarquico, L, sup 15                                  -> efeito da frequencia (vs B_<L>_s30)
  B_<L>_s10   hierarquico, L, sup 10 (so se 15 superar 30)

Sementes de trafego (conferidas por programa contra tudo o que ja foi usado):
  treino 1001-1030 | validacao 221-225 | TESTE FINAL INEDITO 241-250

uso:
  python -B -X utf8 semaforo/integracao_insper/otimizacao_final/bateria_otimizacao.py demandas
  ... treinar --bracos A_col A_col_v5 --processos 10      (retomavel)
  ... validar --bracos A_v1 A_col A_col_v5 --baselines    (seleciona checkpoints por braco)
  ... testar                                              (uma unica vez, no fim)
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI))
import insper_comum as ic  # noqa: E402

SAIDA = AQUI / "resultados"
ANTERIOR = AQUI.parent / "resultados" / "bateria_principal_20261116" / "treinos"
SEMENTES_MODELO = [1, 2, 3, 4, 5]
EPISODIOS = 150
CHECKPOINTS = [25, 50, 75, 100, 125, 150]
VALIDACAO = [221, 222, 223, 224, 225]
TESTE = list(range(241, 251))
USADAS = {"treino": set(range(1001, 1031)), "calibracao": {9001, 9002} | set(range(9101, 9111)),
          "niveis": set(range(101, 106)) | set(range(201, 206)) | set(range(301, 306)) | set(range(311, 316)),
          "avaliacoes_anteriores": set(range(211, 216)) | set(range(231, 236)) | {221, 222, 223}}
L10 = {"verde_minimo": 10, "colisao": "atribuida"}
L5 = {"verde_minimo": 5, "colisao": "atribuida"}
BRACOS = {
    "A_v1": {"modelo": "independente", "config": {"verde_minimo": 10, "colisao": "global", "supervisor_s": 30},
             "anterior": "independente"},
    "B_v1": {"modelo": "hierarquico", "config": {"verde_minimo": 10, "colisao": "global", "supervisor_s": 30},
             "anterior": "hierarquico"},
    "A_col": {"modelo": "independente", "config": {**L10, "supervisor_s": 30}},
    "A_col_v5": {"modelo": "independente", "config": {**L5, "supervisor_s": 30}},
    "B_col_s30": {"modelo": "hierarquico", "config": {**L10, "supervisor_s": 30}},
    "B_col_s15": {"modelo": "hierarquico", "config": {**L10, "supervisor_s": 15}},
    "B_col_s10": {"modelo": "hierarquico", "config": {**L10, "supervisor_s": 10}},
    "B_col_v5_s30": {"modelo": "hierarquico", "config": {**L5, "supervisor_s": 30}},
    "B_col_v5_s15": {"modelo": "hierarquico", "config": {**L5, "supervisor_s": 15}},
    "B_col_v5_s10": {"modelo": "hierarquico", "config": {**L5, "supervisor_s": 10}},
}
BASELINES = {"original": ("original", {}),
             "atuado_eq_v10": ("atuado_equivalente", {"verde_minimo": 10}),
             "atuado_eq_v5": ("atuado_equivalente", {"verde_minimo": 5}),
             "max_pressure_v10": ("max_pressure", {"verde_minimo": 10})}
CRITERIO = {
    "elegivel": "5/5 episodios de validacao validos, 0 violacoes de seguranca, 0 colisoes nos controlados, "
                ">= 99% de viagens concluidas e no maximo 1 teletransporte por episodio",
    "ordem": "menor espera media no corredor (media das 5 sementes de validacao); empate < 2%: menor P95; "
             "depois menor bloqueio da saida; depois o checkpoint mais antigo",
    "comparacao_de_bracos": "pareada por semente de modelo (mesma inicializacao e mesmas demandas de treino); "
                            "uma mudanca so e considerada melhora com media melhor E melhora em >= 4 de 5 sementes",
}


def pasta_treino(braco, s):
    b = BRACOS[braco]
    if "anterior" in b:
        return ANTERIOR / f"{b['anterior']}_s{s}"
    return SAIDA / "treinos" / f"{braco}_s{s}"


def conferir_sementes():
    novas = {"validacao": set(VALIDACAO), "teste": set(TESTE)}
    proibidas_teste = set().union(*USADAS.values()) | novas["validacao"]
    proibidas_val = USADAS["treino"] | USADAS["calibracao"] | USADAS["niveis"] | {211, 212, 213, 214, 215, 231,
                                                                                 232, 233, 234, 235}
    if novas["teste"] & proibidas_teste or novas["validacao"] & proibidas_val:
        raise RuntimeError("sobreposicao de sementes")
    # tambem confere as pastas de demanda ja existentes (qualquer nivel)
    existentes = {int(p.name.split("_")[1]) for p in (ic.SEMAFORO / "cenarios" / "insper_demanda").glob("*/semente_*")
                  if p.parent.name != "intenso_teste_final" and p.parent.name != "intenso_validacao"}
    if existentes & novas["teste"]:
        raise RuntimeError(f"semente de teste ja existe em outra demanda: {existentes & novas['teste']}")
    return {"teste": sorted(novas["teste"]), "validacao": sorted(novas["validacao"]),
            "conferidas_contra": {k: len(v) for k, v in USADAS.items()}, "pastas_de_demanda_existentes": len(existentes)}


def _gerar(args):
    nivel, s = args
    import gerar_demanda_insper as gd
    if not (gd.DERIVADO / nivel / f"semente_{s}").exists():
        gd.gerar(nivel, 2000, s, 12.0)


def demandas(_):
    SAIDA.mkdir(parents=True, exist_ok=True)
    info = conferir_sementes()
    print(info)
    with ProcessPoolExecutor(8) as ex:
        list(ex.map(_gerar, [("intenso_validacao", s) for s in VALIDACAO]
                    + [("intenso_teste_final", s) for s in TESTE]))
    (SAIDA / "sementes.json").write_text(json.dumps(info, indent=1), encoding="utf-8")


def treinar(args):
    script = AQUI / "treinar_marl_insper_v2.py"
    fila = [(b, s) for s in SEMENTES_MODELO for b in args.bracos]
    logs = SAIDA / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    ativos, inicio = [], time.perf_counter()
    with (SAIDA / "progresso.jsonl").open("a", encoding="utf-8") as prog:
        prog.write(json.dumps({"evento": "inicio_treinar", "bracos": args.bracos, "processos": args.processos,
                               "hora": time.strftime("%Y-%m-%dT%H:%M:%S")}) + "\n")
        while fila or ativos:
            while fila and len(ativos) < args.processos:
                b, s = fila.pop(0)
                p = pasta_treino(b, s)
                if (p / "resumo_treino.json").exists():
                    continue
                c = BRACOS[b]["config"]
                log = (logs / f"{b}_s{s}.log").open("a", encoding="utf-8")
                proc = subprocess.Popen([sys.executable, "-B", "-X", "utf8", str(script), "--modelo", BRACOS[b]["modelo"],
                                         "--episodios", str(EPISODIOS), "--semente", str(s), "--pasta", str(p),
                                         "--verde-minimo", str(c["verde_minimo"]), "--colisao", c["colisao"],
                                         "--supervisor-s", str(c["supervisor_s"])], stdout=log, stderr=subprocess.STDOUT)
                ativos.append((b, s, proc, log))
                prog.write(json.dumps({"evento": "iniciado", "braco": b, "semente": s,
                                       "hora": time.strftime("%Y-%m-%dT%H:%M:%S")}) + "\n")
                prog.flush()
            time.sleep(15)
            for item in list(ativos):
                b, s, proc, log = item
                if proc.poll() is not None:
                    log.close()
                    ativos.remove(item)
                    prog.write(json.dumps({"evento": "terminado", "braco": b, "semente": s, "codigo": proc.returncode,
                                           "hora": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                           "parede_s": round(time.perf_counter() - inicio)}) + "\n")
                    prog.flush()
                    print(f"{b} s{s} terminou com codigo {proc.returncode}", flush=True)


def tarefa(job):
    import torch
    torch.set_num_threads(1)
    import ambiente_marl_insper_v2 as amb
    import treinar_marl_insper_v2 as tr
    cfg = ic.SEMAFORO / "cenarios" / "insper_demanda" / job["nivel"] / f"semente_{job['semente']}" / "cenario.sumocfg"
    if job.get("checkpoint"):
        d, agentes = tr.carregar(job["checkpoint"])
        modo, config = d["modelo"], d["config"]
        if job.get("config_esperada") and config != dict(amb.CONFIG_V1, **job["config_esperada"]):
            raise RuntimeError(f"checkpoint {job['checkpoint']} com config {config}")
    else:
        agentes, modo, config = None, job["modo"], job.get("config", {})
    m = amb.rodar_episodio(cfg, job["pasta"], job["semente"], agentes, modo, treinando=False,
                           monitor_completo=True, rotulo=f"v2_{job['rotulo']}_{job['semente']}", config=config)
    return job["rotulo"], job["semente"], m


def resumo(ms):
    validos = [m for m in ms if m["valido"]]

    def med(f):
        v = [f(m) for m in validos]
        return round(statistics.fmean(v), 3) if v else None
    r = {"episodios": len(ms), "validos": len(validos),
         "invalidos": [{"semente": m["semente_trafego"], "motivo": m["motivo_invalido"]} for m in ms if not m["valido"]],
         "espera_corredor_media": med(lambda m: m["espera_corredor_s"]["media"]),
         "espera_corredor_p95": med(lambda m: m["espera_corredor_s"]["p95"]),
         "espera_rede_media": med(lambda m: m["espera_rede_s"]["media"]),
         "espera_rede_p95": med(lambda m: m["espera_rede_s"]["p95"]),
         "fracao_concluida_min": min(m["fracao_concluida"] for m in ms),
         "bloqueio_saida_corredor_s": med(lambda m: m["bloqueio_saida_corredor_s"]),
         "filas_media": {t: med(lambda m, t=t: m["filas"][t]["media"]) for t in ic.CONTROLADOS},
         "filas_max": {t: med(lambda m, t=t: m["filas"][t]["max"]) for t in ic.CONTROLADOS},
         "entreverdes_s": {t: med(lambda m, t=t: m["entreverdes_s"][t]) for t in ic.CONTROLADOS},
         "trocas": {t: med(lambda m, t=t: m["trocas"].get(t, 0)) for t in ic.CONTROLADOS},
         "teleportes_por_episodio": [m["teleportes"]["total"] for m in ms],
         "colisoes": sum(m["colisoes"]["eventos"] for m in ms),
         "colisoes_nos_controlados": sum(m["colisoes"]["nos_controlados"] for m in ms),
         "colisoes_por_classe": {},
         "violacoes": sum(m["seguranca"]["violacoes"] for m in ms),
         "por_semente": {m["semente_trafego"]: m["espera_corredor_s"].get("media") for m in ms}}
    for m in ms:
        for k, v in m["colisoes"].get("por_classe", {}).items():
            r["colisoes_por_classe"][k] = r["colisoes_por_classe"].get(k, 0) + v
    falhas = []
    if r["validos"] < len(ms):
        falhas.append("episodio_invalido")
    if r["violacoes"]:
        falhas.append("violacao_seguranca")
    if r["colisoes_nos_controlados"]:
        falhas.append("colisao_nos_controlados")
    if r["fracao_concluida_min"] < 0.99:
        falhas.append("conclusao_abaixo_de_99")
    if max(r["teleportes_por_episodio"]) > 1:
        falhas.append("teleportes_acima_do_baseline")
    r["criterios_violados"] = falhas
    return r


def selecionar(cands):
    eleg = {e: r for e, r in cands.items() if not r["criterios_violados"]}
    if eleg:
        melhor = min(r["espera_corredor_media"] for r in eleg.values())
        prox = [e for e, r in eleg.items() if r["espera_corredor_media"] <= 1.02 * melhor]
        return min(prox, key=lambda e: (eleg[e]["espera_corredor_p95"], eleg[e]["bloqueio_saida_corredor_s"], e)), True
    e = min(cands, key=lambda e: (len(cands[e]["criterios_violados"]), cands[e]["espera_corredor_media"] or 1e9, e))
    return e, False


def avaliar(jobs, processos):
    saida = {}
    with ProcessPoolExecutor(processos) as ex:
        for rotulo, s, m in ex.map(tarefa, jobs):
            saida.setdefault(rotulo, []).append(m)
            print(f"  {rotulo:>30} s{s}: valido={m['valido']} corredor {m['espera_corredor_s'].get('media')} "
                  f"tele {m['teleportes']['total']} col {m['colisoes']['eventos']} ({m['duracao_real_s']} s)", flush=True)
    return saida


def validar(args):
    pasta = SAIDA / "validacao"
    pasta.mkdir(parents=True, exist_ok=True)
    jobs = []
    if args.baselines:
        for nome, (modo, config) in BASELINES.items():
            if not (pasta / f"baseline_{nome}.json").exists():
                jobs += [{"rotulo": f"baseline_{nome}", "modo": modo, "config": config, "semente": s,
                          "nivel": "intenso_validacao", "pasta": str(pasta / "episodios" / f"baseline_{nome}" / f"s{s}")}
                         for s in VALIDACAO]
    for b in args.bracos:
        if (pasta / f"braco_{b}.json").exists():
            continue
        for sm in SEMENTES_MODELO:
            for e in CHECKPOINTS:
                ck = pasta_treino(b, sm) / f"politica_ep{e:04d}.pt"
                for s in VALIDACAO:
                    jobs.append({"rotulo": f"{b}|{sm}|{e}", "checkpoint": str(ck), "config_esperada": BRACOS[b]["config"],
                                 "semente": s, "nivel": "intenso_validacao",
                                 "pasta": str(pasta / "episodios" / b / f"s{sm}_ep{e:04d}" / f"s{s}")})
    res = avaliar(jobs, args.processos)
    for nome in BASELINES:
        if f"baseline_{nome}" in res:
            ic.json_novo(pasta / f"baseline_{nome}.json", {"baseline": nome, "resumo": resumo(res[f"baseline_{nome}"])})
    for b in args.bracos:
        if (pasta / f"braco_{b}.json").exists():
            continue
        tab = {sm: {e: resumo(res[f"{b}|{sm}|{e}"]) for e in CHECKPOINTS} for sm in SEMENTES_MODELO}
        sel = {}
        for sm in SEMENTES_MODELO:
            e, eleg = selecionar(tab[sm])
            sel[sm] = {"episodio": e, "elegivel": eleg, "checkpoint": str(pasta_treino(b, sm) / f"politica_ep{e:04d}.pt"),
                       "validacao": tab[sm][e]}
        ic.json_novo(pasta / f"braco_{b}.json", {"braco": b, **BRACOS[b], "criterio": CRITERIO,
                                                 "sementes_validacao": VALIDACAO, "tabela": tab, "selecao": sel})
        print(b, {sm: (v["episodio"], v["validacao"]["espera_corredor_media"]) for sm, v in sel.items()}, flush=True)


def comparar(args):
    """Comparacao pareada de bracos na VALIDACAO (checkpoints selecionados)."""
    pasta = SAIDA / "validacao"
    sel = {b: json.loads((pasta / f"braco_{b}.json").read_text(encoding="utf-8"))["selecao"] for b in args.bracos}
    base = args.bracos[0]
    for b in args.bracos[1:]:
        dif = [sel[b][str(s)]["validacao"]["espera_corredor_media"] - sel[base][str(s)]["validacao"]["espera_corredor_media"]
               for s in SEMENTES_MODELO]
        print(f"{b} - {base}: media {statistics.fmean(dif):+.2f} s, dp {statistics.stdev(dif):.2f}, "
              f"melhor em {sum(d < 0 for d in dif)}/5 sementes, difs {[round(d, 2) for d in dif]}")
    for b in args.bracos:
        v = [sel[b][str(s)]["validacao"]["espera_corredor_media"] for s in SEMENTES_MODELO]
        print(f"{b}: {statistics.fmean(v):.2f} +- {statistics.stdev(v):.2f}")


def testar(args):
    pasta = SAIDA / "teste_final"
    pasta.mkdir(parents=True, exist_ok=False)  # uma unica vez
    conferir_sementes()
    jobs = []
    for nome, (modo, config) in BASELINES.items():
        jobs += [{"rotulo": f"baseline_{nome}", "modo": modo, "config": config, "semente": s, "nivel": "intenso_teste_final",
                  "pasta": str(pasta / "episodios" / f"baseline_{nome}" / f"s{s}")} for s in TESTE]
    selecionados = {}
    for b in args.bracos:
        sel = json.loads((SAIDA / "validacao" / f"braco_{b}.json").read_text(encoding="utf-8"))["selecao"]
        selecionados[b] = {sm: v["checkpoint"] for sm, v in sel.items()}
        for sm, ck in selecionados[b].items():
            jobs += [{"rotulo": f"{b}|{sm}", "checkpoint": ck, "config_esperada": BRACOS[b]["config"], "semente": s,
                      "nivel": "intenso_teste_final", "pasta": str(pasta / "episodios" / b / f"s{sm}" / f"s{s}")}
                     for s in TESTE]
    res = avaliar(jobs, args.processos)
    por_semente = {r: [{"semente": m["semente_trafego"], "valido": m["valido"], "motivo_invalido": m["motivo_invalido"],
                        "espera_corredor_media": m["espera_corredor_s"].get("media"),
                        "espera_corredor_p95": m["espera_corredor_s"].get("p95"),
                        "espera_rede_media": m["espera_rede_s"].get("media"), "espera_rede_p95": m["espera_rede_s"].get("p95"),
                        "filas": {t: m["filas"][t] for t in ic.CONTROLADOS}, "fracao_concluida": m["fracao_concluida"],
                        "teleportes": m["teleportes"]["total"], "colisoes": m["colisoes"]["eventos"],
                        "colisoes_nos_controlados": m["colisoes"]["nos_controlados"],
                        "colisoes_por_classe": m["colisoes"].get("por_classe", {}),
                        "violacoes": m["seguranca"]["violacoes"], "bloqueio_saida_corredor_s": m["bloqueio_saida_corredor_s"],
                        "entreverdes_s": m["entreverdes_s"], "trocas": m["trocas"]}
                       for m in sorted(ms, key=lambda m: m["semente_trafego"])] for r, ms in res.items()}
    ic.json_novo(pasta / "teste_final.json", {"sementes_teste": TESTE, "bracos": {b: BRACOS[b] for b in args.bracos},
                                              "baselines": BASELINES, "checkpoints": selecionados,
                                              "por_semente": por_semente,
                                              "resumo": {r: resumo(ms) for r, ms in res.items()}})
    print("teste final salvo em", pasta)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demandas")
    for nome in ("treinar", "validar", "comparar", "testar"):
        q = sub.add_parser(nome)
        q.add_argument("--bracos", nargs="+", default=[], choices=list(BRACOS))
        q.add_argument("--processos", type=int, default=10)
        q.add_argument("--baselines", action="store_true")
    args = ap.parse_args()
    antes = ic.hashes_cenario()
    {"demandas": demandas, "treinar": treinar, "validar": validar, "comparar": comparar, "testar": testar}[args.cmd](args)
    ic.conferir_cenario(antes)


if __name__ == "__main__":
    main()
