"""Bateria do Modelo C (Parameter Sharing): demandas novas, treino, validacao e testes de generalizacao.

Bracos (mesmas demandas de treino 1001-1030, 150 episodios, config do A_col):
  C        3 agentes, uma DoubleDQN compartilhada, os 3 cruzamentos alimentam o replay
  C_transf idem, mas so Gomes de Carvalho e Quata aprendem; Casa do Ator (40278305) e
           controlado por regra_atuada_obs durante o treino e NUNCA alimenta o replay
Sementes de modelo 1-5. Validacao 221-225 (a mesma usada para escolher o A_col).
Testes NOVOS (conferidos contra todas as sementes ja usadas), executados uma vez:
  moderado_ps_teste 261-270 (1200 veic/h no corredor)   - Experimento A
  intenso_ps_teste  251-260 (2000)                      - Experimento B (e D, transferencia)
  saturado_ps_teste 271-280 (2400)                      - Experimento C (robustez)

uso (na raiz):
  python -B -X utf8 semaforo/integracao_insper/parameter_sharing/bateria_ps.py demandas
  ... treinar --processos 10
  ... validar --processos 12
  ... testar --processos 12        (uma unica vez)
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
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI.parent / "otimizacao_final"))
import insper_comum as ic  # noqa: E402
import bateria_otimizacao as bo  # noqa: E402  (resumo, selecionar e CRITERIO identicos aos do Modelo A)

SAIDA = AQUI / "resultados"
SEMENTES_MODELO = [1, 2, 3, 4, 5]
EPISODIOS, CHECKPOINTS = 150, [25, 50, 75, 100, 125, 150]
VALIDACAO = [221, 222, 223, 224, 225]
TESTES = {"moderado_ps_teste": (1200, list(range(261, 271))), "intenso_ps_teste": (2000, list(range(251, 261))),
          "saturado_ps_teste": (2400, list(range(271, 281)))}
BRACOS = {"C": (0, 1, 2), "C_transf": (0, 2)}
MODELOS_FINAIS = AQUI.parent / "modelos_finais" / "manifesto.json"


def pasta_treino(b, s):
    return SAIDA / "treinos" / f"{b}_s{s}"


def conferir_sementes():
    usadas = set().union(*bo.USADAS.values()) | set(bo.VALIDACAO) | set(bo.TESTE)
    existentes = {int(p.name.split("_")[1]) for p in (ic.SEMAFORO / "cenarios" / "insper_demanda").glob("*/semente_*")
                  if not p.parent.name.endswith("_ps_teste")}
    novas = [s for _, ss in TESTES.values() for s in ss]
    if len(set(novas)) != len(novas) or set(novas) & (usadas | existentes | set(range(1001, 1031))):
        raise RuntimeError("sobreposicao de sementes de teste")
    return {"teste": {n: ss for n, (_, ss) in TESTES.items()}, "validacao": VALIDACAO, "treino": "1001-1030",
            "conferidas_contra_pastas_existentes": len(existentes)}


def _gerar(args):
    nivel, corredor, s = args
    import gerar_demanda_insper as gd
    if not (gd.DERIVADO / nivel / f"semente_{s}").exists():
        gd.gerar(nivel, corredor, s, 12.0)


def demandas(_):
    SAIDA.mkdir(exist_ok=True)
    info = conferir_sementes()
    with ProcessPoolExecutor(8) as ex:
        list(ex.map(_gerar, [(n, c, s) for n, (c, ss) in TESTES.items() for s in ss]))
    (SAIDA / "sementes.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print(info)


def treinar(args):
    fila = [(b, s) for s in SEMENTES_MODELO for b in BRACOS]
    (SAIDA / "logs").mkdir(parents=True, exist_ok=True)
    ativos = []
    while fila or ativos:
        while fila and len(ativos) < args.processos:
            b, s = fila.pop(0)
            p = pasta_treino(b, s)
            if (p / "resumo_treino.json").exists():
                continue
            log = (SAIDA / "logs" / f"{b}_s{s}.log").open("a", encoding="utf-8")
            proc = subprocess.Popen([sys.executable, "-B", "-X", "utf8", str(AQUI / "treinar_ps.py"), "--semente", str(s),
                                     "--pasta", str(p), "--episodios", str(EPISODIOS), "--aprendizes",
                                     *map(str, BRACOS[b])], stdout=log, stderr=subprocess.STDOUT)
            ativos.append((b, s, proc, log))
        time.sleep(15)
        for item in list(ativos):
            if item[2].poll() is not None:
                item[3].close()
                ativos.remove(item)
                print(f"{item[0]} s{item[1]} terminou com codigo {item[2].returncode}", flush=True)


def tarefa(job):
    import torch
    torch.set_num_threads(1)
    import ambiente_marl_insper_v2 as amb
    import politica_compartilhada as pc
    cfg = ic.SEMAFORO / "cenarios" / "insper_demanda" / job["nivel"] / f"semente_{job['semente']}" / "cenario.sumocfg"
    if job.get("ps"):
        d, rede = pc.carregar(job["ps"])
        agentes, modo, config = pc.visoes_avaliacao(rede), "independente", d["config"]
    elif job.get("checkpoint"):
        import treinar_marl_insper_v2 as tr
        d, agentes = tr.carregar(job["checkpoint"])
        modo, config = d["modelo"], d["config"]
    else:
        agentes, modo, config = None, job["modo"], job.get("config", {})
    m = amb.rodar_episodio(cfg, job["pasta"], job["semente"], agentes, modo, treinando=False, monitor_completo=True,
                           rotulo=f"ps_{job['rotulo'].replace('|', '_')}_{job['semente']}", config=config)
    return job["rotulo"], job["semente"], m


def avaliar(jobs, processos):
    saida = {}
    with ProcessPoolExecutor(processos) as ex:
        for rotulo, s, m in ex.map(tarefa, jobs):
            saida.setdefault(rotulo, []).append(m)
            print(f"  {rotulo:>34} s{s}: valido={m['valido']} corredor {m['espera_corredor_s'].get('media')} "
                  f"tele {m['teleportes']['total']} col {m['colisoes']['eventos']} ({m['duracao_real_s']} s)", flush=True)
    return saida


def validar(args):
    pasta = SAIDA / "validacao"
    pasta.mkdir(parents=True, exist_ok=True)
    jobs = [{"rotulo": f"{b}|{sm}|{e}", "ps": str(pasta_treino(b, sm) / f"politica_ep{e:04d}.pt"), "semente": s,
             "nivel": "intenso_validacao", "pasta": str(pasta / "episodios" / b / f"s{sm}_ep{e:04d}" / f"s{s}")}
            for b in BRACOS if not (pasta / f"braco_{b}.json").exists()
            for sm in SEMENTES_MODELO for e in CHECKPOINTS for s in VALIDACAO]
    res = avaliar(jobs, args.processos)
    for b in BRACOS:
        if (pasta / f"braco_{b}.json").exists():
            continue
        tab = {sm: {e: bo.resumo(res[f"{b}|{sm}|{e}"]) for e in CHECKPOINTS} for sm in SEMENTES_MODELO}
        sel = {}
        for sm in SEMENTES_MODELO:
            e, eleg = bo.selecionar(tab[sm])
            sel[sm] = {"episodio": e, "elegivel": eleg, "checkpoint": str(pasta_treino(b, sm) / f"politica_ep{e:04d}.pt"),
                       "validacao": tab[sm][e]}
        ic.json_novo(pasta / f"braco_{b}.json", {"braco": b, "aprendizes": list(BRACOS[b]), "criterio": bo.CRITERIO,
                                                 "sementes_validacao": VALIDACAO, "tabela": tab, "selecao": sel})
        print(b, {sm: (v["episodio"], v["validacao"]["espera_corredor_media"]) for sm, v in sel.items()}, flush=True)


def testar(args):
    pasta = SAIDA / "teste_generalizacao"
    pasta.mkdir(parents=True, exist_ok=False)  # uma unica vez
    conferir_sementes()
    man = json.loads(MODELOS_FINAIS.read_text(encoding="utf-8"))
    raiz = AQUI.parents[2]
    sel = {b: json.loads((SAIDA / "validacao" / f"braco_{b}.json").read_text(encoding="utf-8"))["selecao"] for b in BRACOS}
    jobs = []
    for nivel, (_, sementes) in TESTES.items():
        ctrl = [("original", {"modo": "original"}), ("atuado_eq_v10", {"modo": "atuado_equivalente", "config": {"verde_minimo": 10}})]
        ctrl += [(f"A_col|{sm}", {"checkpoint": str(raiz / v["arquivo"])}) for sm, v in man["bracos"]["A_col"]["sementes_modelo"].items()]
        ctrl += [(f"C|{sm}", {"ps": v["checkpoint"]}) for sm, v in sel["C"].items()]
        if nivel == "intenso_ps_teste":
            ctrl += [(f"C_transf|{sm}", {"ps": v["checkpoint"]}) for sm, v in sel["C_transf"].items()]
            ctrl += [(f"B_col_s15|{sm}", {"checkpoint": str(raiz / v["arquivo"])})
                     for sm, v in man["bracos"]["B_col_s15"]["sementes_modelo"].items()]
        for rot, extra in ctrl:
            jobs += [{"rotulo": f"{nivel}|{rot}", "semente": s, "nivel": nivel, **extra,
                      "pasta": str(pasta / "episodios" / nivel / rot.replace("|", "_s") / f"s{s}")} for s in sementes]
    res = avaliar(jobs, args.processos)
    por_semente = {r: [{"semente": m["semente_trafego"], "valido": m["valido"], "motivo_invalido": m["motivo_invalido"],
                        "espera_corredor_media": m["espera_corredor_s"].get("media"),
                        "espera_corredor_p95": m["espera_corredor_s"].get("p95"),
                        "espera_rede_media": m["espera_rede_s"].get("media"), "espera_rede_p95": m["espera_rede_s"].get("p95"),
                        "filas": {t: m["filas"][t] for t in ic.CONTROLADOS}, "fracao_concluida": m["fracao_concluida"],
                        "teleportes": m["teleportes"]["total"], "colisoes": m["colisoes"]["eventos"],
                        "colisoes_nos_controlados": m["colisoes"]["nos_controlados"],
                        "violacoes": m["seguranca"]["violacoes"], "bloqueio_saida_corredor_s": m["bloqueio_saida_corredor_s"],
                        "trocas": m["trocas"], "presos_gt180s": m["presos_gt180s"]}
                       for m in sorted(ms, key=lambda m: m["semente_trafego"])] for r, ms in res.items()}
    ic.json_novo(pasta / "teste_generalizacao.json", {
        "sementes": {n: ss for n, (_, ss) in TESTES.items()}, "checkpoints_C": {b: {sm: v["checkpoint"] for sm, v in s.items()}
                                                                              for b, s in sel.items()},
        "por_semente": por_semente, "resumo": {r: bo.resumo(ms) for r, ms in res.items()}})
    print("teste salvo em", pasta)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["demandas", "treinar", "validar", "testar"])
    ap.add_argument("--processos", type=int, default=10)
    a = ap.parse_args()
    antes = ic.hashes_cenario()
    {"demandas": demandas, "treinar": treinar, "validar": validar, "testar": testar}[a.cmd](a)
    ic.conferir_cenario(antes)


if __name__ == "__main__":
    main()
