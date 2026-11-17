"""Bateria principal do Multi-Agent Insper: paralelismo, treinos, validacao e teste.

Todas as saidas ficam em uma unica pasta de bateria (BATERIA abaixo).

  python -B -X utf8 semaforo/integracao_insper/bateria_marl_insper.py demandas
  python -B -X utf8 semaforo/integracao_insper/bateria_marl_insper.py paralelismo --n 4 8 12
  python -B -X utf8 semaforo/integracao_insper/bateria_marl_insper.py treinar --processos 8     (retomavel)
  python -B -X utf8 semaforo/integracao_insper/bateria_marl_insper.py validar --processos 8
  python -B -X utf8 semaforo/integracao_insper/bateria_marl_insper.py testar --processos 8

Sementes de trafego (nenhuma reutilizada entre funcoes):
  treino 1001-1030 (intenso_treino), validacao 221-223 (intenso_validacao),
  teste final 231-235 (intenso_teste). Ja usadas antes: calibracao 9001-9002,
  9101-9110, niveis 101-105, 201-205, 211-215, 301-305, 311-315.
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import insper_comum as ic  # noqa: E402

BATERIA = ic.RESULTADOS / "bateria_principal_20261116"
MODELOS = ["independente", "hierarquico"]
SEMENTES_MODELO = [1, 2, 3, 4, 5]
EPISODIOS = 150
CHECKPOINTS = [25, 50, 75, 100, 125, 150]
VALIDACAO = [221, 222, 223]
TESTE = [231, 232, 233, 234, 235]
# Criterio de selecao, fixado ANTES de validar:
CRITERIO = {
    "elegivel": "3/3 episodios de validacao validos, 0 violacoes de seguranca, 0 colisoes nos controlados, "
                ">= 99% de viagens concluidas em cada episodio e no maximo 1 teletransporte por episodio "
                "(o maximo do programa original)",
    "ordem": "menor espera media no corredor (media das 3 sementes); se a diferenca para o melhor for < 2%, "
             "menor P95 da espera no corredor; depois menor bloqueio da saida; depois o episodio mais antigo",
    "sem_elegivel": "o checkpoint com menos criterios violados e, entre eles, menor espera; marcado como nao elegivel",
}


def pasta_treino(modelo, s):
    return BATERIA / "treinos" / f"{modelo}_s{s}"


def _gerar(args):
    nivel, s = args
    import gerar_demanda_insper as gd
    if not (gd.DERIVADO / nivel / f"semente_{s}").exists():
        gd.gerar(nivel, 2000, s, 12.0)
    return nivel, s


def demandas(_):
    usados = set(range(1001, 1031)) | {9001, 9002} | set(range(9101, 9111)) | set(range(101, 106)) \
        | set(range(201, 206)) | set(range(211, 216)) | set(range(301, 306)) | set(range(311, 316))
    if usados & (set(VALIDACAO) | set(TESTE)):
        raise RuntimeError("semente de validacao/teste ja usada")
    jobs = [("intenso_validacao", s) for s in VALIDACAO] + [("intenso_teste", s) for s in TESTE]
    with ProcessPoolExecutor(8) as ex:
        print(list(ex.map(_gerar, jobs)))
    import treinar_marl_insper as tr
    print("demandas de treino geradas agora:", tr.preparar_demandas_treino())


def _episodio_teste(args):
    n, k = args
    import torch
    torch.set_num_threads(1)
    import ambiente_marl_insper as amb
    import treinar_marl_insper as tr
    s = tr.SEMENTES_TREINO[k % len(tr.SEMENTES_TREINO)]
    agentes = amb.criar_agentes("hierarquico", 900 + k)
    m = amb.rodar_episodio(tr.cfg_treino(s), BATERIA / "paralelismo" / f"n{n}_k{k}", s, agentes, "hierarquico",
                           treinando=True, rotulo=f"par_{n}_{k}")
    return m["duracao_real_s"]


def paralelismo(args):
    res = {}
    for n in args.n:
        inicio = time.perf_counter()
        with ProcessPoolExecutor(n) as ex:
            dur = list(ex.map(_episodio_teste, [(n, k) for k in range(n)]))
        parede = time.perf_counter() - inicio
        res[n] = {"processos": n, "parede_s": round(parede, 1), "media_episodio_s": round(statistics.fmean(dur), 1),
                  "episodios_por_hora": round(3600 * n / parede, 1)}
        print(res[n], flush=True)
    (BATERIA / "paralelismo").mkdir(parents=True, exist_ok=True)
    ic.json_novo(BATERIA / "paralelismo" / f"resultado_{int(time.time())}.json", res)


def treinar(args):
    BATERIA.mkdir(parents=True, exist_ok=True)
    fila = [(m, s) for s in SEMENTES_MODELO for m in MODELOS]
    script = Path(__file__).resolve().parent / "treinar_marl_insper.py"
    logs = BATERIA / "logs"
    logs.mkdir(exist_ok=True)
    ativos = []
    inicio = time.perf_counter()
    with (BATERIA / "progresso.jsonl").open("a", encoding="utf-8") as prog:
        prog.write(json.dumps({"evento": "inicio_treinar", "hora": time.strftime("%Y-%m-%dT%H:%M:%S"),
                               "processos": args.processos}) + "\n")
        while fila or ativos:
            while fila and len(ativos) < args.processos:
                m, s = fila.pop(0)
                p = pasta_treino(m, s)
                if (p / "resumo_treino.json").exists():
                    continue
                log = (logs / f"{m}_s{s}.log").open("a", encoding="utf-8")
                proc = subprocess.Popen([sys.executable, "-B", "-X", "utf8", str(script), "--modelo", m,
                                         "--episodios", str(EPISODIOS), "--semente", str(s), "--pasta", str(p)],
                                        stdout=log, stderr=subprocess.STDOUT)
                ativos.append((m, s, proc, log))
                prog.write(json.dumps({"evento": "iniciado", "modelo": m, "semente": s,
                                       "hora": time.strftime("%Y-%m-%dT%H:%M:%S")}) + "\n")
                prog.flush()
            time.sleep(15)
            for item in list(ativos):
                m, s, proc, log = item
                if proc.poll() is not None:
                    log.close()
                    ativos.remove(item)
                    prog.write(json.dumps({"evento": "terminado", "modelo": m, "semente": s, "codigo": proc.returncode,
                                           "hora": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                           "parede_desde_inicio_s": round(time.perf_counter() - inicio)}) + "\n")
                    prog.flush()
                    print(f"{m} s{s} terminou com codigo {proc.returncode}", flush=True)
    print("treinos encerrados em", round(time.perf_counter() - inicio), "s")


def _avaliar(jobs, processos):
    from avaliar_marl_insper import tarefa
    saida = []
    with ProcessPoolExecutor(processos) as ex:
        for rotulo, semente, m in ex.map(tarefa, jobs):
            saida.append((rotulo, semente, m))
            print(f"  {rotulo:>28} s{semente}: valido={m['valido']} corredor {m['espera_corredor_s'].get('media')} "
                  f"rede {m['espera_rede_s'].get('media')} tele {m['teleportes']['total']} ({m['duracao_real_s']} s)",
                  flush=True)
    return saida


def resumo_ckpt(ms):
    from avaliar_marl_insper import agregar
    a = agregar(ms)
    violados = []
    if a["validos"] < len(ms):
        violados.append("episodio_invalido")
    if a["violacoes_seguranca"]:
        violados.append("violacao_seguranca")
    if a["colisoes_nos_controlados"]:
        violados.append("colisao_nos_controlados")
    if any(m["fracao_concluida"] < 0.99 for m in ms):
        violados.append("conclusao_abaixo_de_99")
    if any(m["teleportes"]["total"] > 1 for m in ms):
        violados.append("teleportes_acima_do_baseline")
    a["criterios_violados"] = violados
    return a


def selecionar(cands):
    """cands: {episodio: resumo}. Aplica CRITERIO."""
    eleg = {e: r for e, r in cands.items() if not r["criterios_violados"]}
    if eleg:
        melhor = min(r["espera_corredor_media"] for r in eleg.values())
        proximos = [e for e, r in eleg.items() if r["espera_corredor_media"] <= 1.02 * melhor]
        e = min(proximos, key=lambda e: (eleg[e]["espera_corredor_p95"], eleg[e]["bloqueio_saida_corredor_s"], e))
        return e, True
    e = min(cands, key=lambda e: (len(cands[e]["criterios_violados"]), cands[e]["espera_corredor_media"] or 1e9, e))
    return e, False


def validar(args):
    pasta = BATERIA / "validacao"
    pasta.mkdir(parents=True, exist_ok=False)
    ic.json_novo(pasta / "criterio.json", {"criterio": CRITERIO, "sementes_validacao": VALIDACAO,
                                           "checkpoints": CHECKPOINTS})
    jobs = [{"rotulo": "original", "checkpoint": None, "modo": "original", "semente": s, "nivel": "intenso_validacao",
             "pasta": str(pasta / "original" / f"semente_{s}")} for s in VALIDACAO]
    for m in MODELOS:
        for sm in SEMENTES_MODELO:
            for e in CHECKPOINTS:
                ck = pasta_treino(m, sm) / f"politica_ep{e:04d}.pt"
                for s in VALIDACAO:
                    jobs.append({"rotulo": f"{m}_s{sm}_ep{e:04d}", "checkpoint": str(ck), "semente": s,
                                 "nivel": "intenso_validacao",
                                 "pasta": str(pasta / f"{m}_s{sm}" / f"ep{e:04d}" / f"semente_{s}")})
    saida = _avaliar(jobs, args.processos)
    por = {}
    for r, s, m in saida:
        por.setdefault(r, []).append(m)
    tabela = {r: resumo_ckpt(ms) for r, ms in por.items()}
    selecao = {}
    for m in MODELOS:
        for sm in SEMENTES_MODELO:
            cands = {e: tabela[f"{m}_s{sm}_ep{e:04d}"] for e in CHECKPOINTS}
            e, elegivel = selecionar(cands)
            selecao[f"{m}_s{sm}"] = {"episodio": e, "elegivel": elegivel,
                                     "checkpoint": str(pasta_treino(m, sm) / f"politica_ep{e:04d}.pt"),
                                     "espera_corredor_media_validacao": cands[e]["espera_corredor_media"]}
    ic.json_novo(pasta / "validacao.json", {"criterio": CRITERIO, "tabela": tabela, "selecao": selecao})
    print(json.dumps(selecao, indent=1))


def testar(args):
    pasta = BATERIA / "teste_final"
    pasta.mkdir(parents=True, exist_ok=False)
    selecao = json.loads((BATERIA / "validacao" / "validacao.json").read_text(encoding="utf-8"))["selecao"]
    jobs = [{"rotulo": modo, "checkpoint": None, "modo": modo, "semente": s, "nivel": "intenso_teste",
             "pasta": str(pasta / modo / f"semente_{s}")} for modo in ("original", "max_pressure") for s in TESTE]
    for r, sel in selecao.items():
        for s in TESTE:
            jobs.append({"rotulo": r, "checkpoint": sel["checkpoint"], "semente": s, "nivel": "intenso_teste",
                         "pasta": str(pasta / r / f"semente_{s}")})
    saida = _avaliar(jobs, args.processos)
    from avaliar_marl_insper import agregar
    por = {}
    for r, s, m in saida:
        por.setdefault(r, []).append(m)
    ic.json_novo(pasta / "teste.json", {"sementes_teste": TESTE, "selecao": selecao,
                                        "tabela": {r: agregar(ms) for r, ms in por.items()},
                                        "por_semente": {r: [{"semente": m["semente_trafego"], "valido": m["valido"],
                                                             "motivo_invalido": m["motivo_invalido"],
                                                             "espera_corredor_media": m["espera_corredor_s"].get("media"),
                                                             "espera_corredor_p95": m["espera_corredor_s"].get("p95"),
                                                             "espera_rede_media": m["espera_rede_s"].get("media"),
                                                             "espera_rede_p95": m["espera_rede_s"].get("p95"),
                                                             "filas": {t: m["filas"][t] for t in ic.CONTROLADOS},
                                                             "fracao_concluida": m["fracao_concluida"],
                                                             "teleportes": m["teleportes"]["total"],
                                                             "colisoes": m["colisoes"]["eventos"],
                                                             "colisoes_nos_controlados": m["colisoes"]["nos_controlados"],
                                                             "violacoes": m["seguranca"]["violacoes"],
                                                             "bloqueio_saida_corredor_s": m["bloqueio_saida_corredor_s"]}
                                                            for m in ms] for r, ms in por.items()}})
    print("teste final salvo em", pasta)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demandas")
    p = sub.add_parser("paralelismo")
    p.add_argument("--n", type=int, nargs="+", default=[4, 8, 12])
    for nome in ("treinar", "validar", "testar"):
        q = sub.add_parser(nome)
        q.add_argument("--processos", type=int, default=8)
    args = ap.parse_args()
    antes = ic.hashes_cenario()
    {"demandas": demandas, "paralelismo": paralelismo, "treinar": treinar, "validar": validar,
     "testar": testar}[args.cmd](args)
    ic.conferir_cenario(antes)


if __name__ == "__main__":
    main()
