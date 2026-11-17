"""Analise descritiva pareada do MPC e resultados historicos; nao roda SUMO."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics as st

import numpy as np


def ler(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def analisar(raiz):
    raiz = Path(raiz).resolve()
    if ler(raiz / "CONCLUIDO.json")["status"] != "CONCLUIDO":
        raise ValueError("Execucao incompleta")
    resumo = ler(raiz / "resumo.json")
    comparacao = resumo["comparacao"]
    protocolo = ler(raiz / "protocolo.json")
    sementes = protocolo["teste_seeds"]
    projeto = Path(__file__).resolve().parents[1]
    hist = projeto / "resultados/marl_cologne8/20261113T011843Z_continuo_10seeds_9f8d757b"
    # Conferir todas as metricas historicas que fundamentam a comparacao.
    for fonte in comparacao["fontes_historicas"]:
        assert sha(projeto / fonte["arquivo"]) == fonte["sha256"]
    paths = {"MPC": [raiz / f"teste_seed{s}/metricas.json" for s in sementes],
             "MARL": [p / f"teste_final/seed{s}/metricas.json" for p in sorted(hist.glob("modelo_seed*")) for s in sementes],
             "Max-Pressure": [hist / f"comparadores/max_pressure/seed{s}/metricas.json" for s in sementes],
             "Original": [hist / f"comparadores/original_fixo/seed{s}/metricas.json" for s in sementes]}
    raw = {g: [ler(p) for p in ps] for g, ps in paths.items()}
    means = comparacao["medias"]
    rng = np.random.default_rng(74291)
    n = len(sementes)
    trafego = rng.integers(0, n, size=(10000, n))
    modelos = rng.integers(0, 10, size=(10000, 10))
    intervals = {}
    for campo, extract in {
        "espera_s": lambda m: m["viagens"]["demanda_janela"]["espera_todos_inclui_censura"]["media"],
        "p95_s": lambda m: m["viagens"]["demanda_janela"]["espera_todos_inclui_censura"]["p95"],
        "colisoes": lambda m: m["colisoes"]}.items():
        mpc = np.array([extract(m) for m in raw["MPC"]])
        marl = np.array([extract(m) for m in raw["MARL"]]).reshape(10, n)
        samples = np.array([mpc[ss].mean() - marl[mm][:, ss].mean() for mm, ss in zip(modelos, trafego)])
        intervals[campo] = {"delta_MPC_menos_MARL": float(mpc.mean() - marl.mean()),
                            "IC95_bootstrap_cruzado": np.percentile(samples, [2.5, 97.5]).tolist()}
    # Cada media local e a media das medias por execucao, nao espera total da viagem.
    local, amostras = {}, {}
    for grupo in ("MPC", "MARL", "Max-Pressure"):
        values = defaultdict(list)
        counts = defaultdict(int)
        for m in raw[grupo]:
            for tls, entries in m["espera_por_entrada"].items():
                for edge, dado in entries.items():
                    if dado["n"]:
                        values[tls, edge].append(dado["media"])
                        counts[tls, edge] += dado["n"]
        local[grupo] = {key: st.mean(vals) for key, vals in values.items()}
        amostras[grupo] = counts
    entradas = [{"tls": key[0], "edge": key[1], "MPC_s": value,
                 "MARL_s": local["MARL"].get(key), "MaxPressure_s": local["Max-Pressure"].get(key),
                 "veiculos_observados_somados_entre_execucoes": {g: amostras[g][key] for g in amostras}}
                for key, value in sorted(local["MPC"].items())]
    qps, ciclos = [], []
    for seed in sementes:
        pasta = raiz / f"teste_seed{seed}"
        qps.extend(json.loads(l) for l in (raiz / f"teste_seed{seed}_mpc/otimizacoes.jsonl").read_text(encoding="utf-8").splitlines())
        phase0 = defaultdict(list)
        for l in (pasta / "fases.jsonl").read_text(encoding="utf-8").splitlines():
            e = json.loads(l)
            if e["motivo"] == "fim_vermelho" and e["fase_alvo"] == 0:
                phase0[e["tls"]].append(e["tempo"])
        ciclos.extend(b - a for ts in phase0.values() for a, b in zip(ts, ts[1:]))
    latencias = [p["construcao_e_solver_s"] for p in qps]
    rodadas = [{"seed": seed, "espera_s": m["viagens"]["demanda_janela"]["espera_todos_inclui_censura"]["media"],
               "p95_s": m["viagens"]["demanda_janela"]["espera_todos_inclui_censura"]["p95"],
               "fila": m["fila_media_rede"], "colisoes": m["colisoes"],
               "concluidas": m["viagens"]["demanda_janela"]["concluidos"],
               "nao_concluidas": m["viagens_nao_concluidas"], "segundos_reais": m["duracao_real_s"]}
               for seed, m in zip(sementes, raw["MPC"])]
    ganho = {g: 100 * (means[g]["espera_s"] / means["MPC"]["espera_s"] - 1) for g in ("MARL", "Max-Pressure", "Original")}
    dados = {"medias": means, "rodadas_mpc": rodadas, "bootstrap": intervals,
             "bootstrap_semente": 74291, "bootstrap_replicas": 10000,
             "entradas": entradas, "n_qps_completos": len(qps),
             "latencia_construcao_solver_s": {"media": st.mean(latencias), "p95": float(np.percentile(latencias, 95)), "maximo": max(latencias)},
             "ciclos_fisicos_observados_s": {"n": len(ciclos), "minimo": min(ciclos), "maximo": max(ciclos), "media": st.mean(ciclos)},
             "marl_reducao_espera_vs_mpc_pct": -ganho["MARL"],
             "mpc_piora_espera_vs_original_pct": 100 * (means["MPC"]["espera_s"] / means["Original"]["espera_s"] - 1),
             "fontes": [{"arquivo": str(p), "sha256": sha(p)} for ps in paths.values() for p in ps]}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    saida = raiz / ("analise_" + stamp)
    saida.mkdir(exist_ok=False)
    with (saida / "estatisticas.json").open("x", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False, allow_nan=False)
    linhas = ["# Resultados do MPC sem RL no Cologne8", "",
        "O MPC externo adaptado foi executado com parametros congelados nas dez sementes 1 a 10. "
        "Esta e uma comparacao exploratoria de controladores completos, com diferencas de observacao e politica. "
        "Nao e reproducao exata do manuscrito externo nem evidencia de superioridade sobre MPC em geral.", "",
        "| Media por simulacao | MARL | Max-Pressure | Original | MPC adaptado |",
        "|---|---:|---:|---:|---:|"]
    for label, key in (("Espera (s)", "espera_s"), ("Media dos P95 (s)", "p95_s"),
                       ("Fila media", "fila"), ("Colisoes", "colisoes"), ("Viagens concluidas", "concluidas"),
                       ("Viagens nao concluidas", "nao_concluidas"), ("Teleportes", "teleportes")):
        linhas.append("| " + label + " | " + " | ".join(f"{means[g][key]:.2f}" for g in ("MARL", "Max-Pressure", "Original", "MPC")) + " |")
    linhas += ["", f"Nos mesmos testes, a espera do MARL foi {dados['marl_reducao_espera_vs_mpc_pct']:.2f}% menor que a deste MPC. "
        f"O MPC teve espera {dados['mpc_piora_espera_vs_original_pct']:.2f}% maior que o programa original. "
        "Assim, a configuracao testada nao se mostrou uma referencia forte de eficiencia. Nao ajustar seus parametros nestas sementes e reapresentar o mesmo teste como independente.", "",
        "## Resultados por semente", "", "| Seed | Espera (s) | P95 (s) | Fila | Colisoes | Concluidas | Nao concluidas |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for r in rodadas:
        linhas.append(f"| {r['seed']} | {r['espera_s']:.2f} | {r['p95_s']:.2f} | {r['fila']:.2f} | {r['colisoes']} | {r['concluidas']} | {r['nao_concluidas']} |")
    linhas += ["", "## Verificacoes e custo computacional", "",
        f"Os testes completos tiveram {len(qps)} QPs validos. Construcao e solucao: media {st.mean(latencias):.3f}s, "
        f"P95 {np.percentile(latencias, 95):.3f}s, maximo {max(latencias):.3f}s por atualizacao global. "
        "Incluem verificacao numerica do solver, nao a simulacao inteira. Nao medimos comunicacao de rede nem operacao em tempo real.", "",
        f"O ciclo configurado e de 120s; os ciclos fisicos medidos entre retornos a fase zero tiveram minimo {min(ciclos)}s e maximo {max(ciclos)}s. "
        "Nesta rodada coincidiram com o ciclo planejado. O adaptador aplica alvos por idade de verde e preserva relogios locais; outras inicializacoes ou offsets precisam ser auditados novamente, sem presumir essa coincidencia.", "",
        "Colisoes permanecem relevantes mesmo com transicoes legais. A funcao objetivo deste MPC e de eficiencia; "
        "nao aprende a penalidade de -10000 e nao modela conflitos microscopicos ou acidentes. A contagem segue o mesmo protocolo historico, com collision.action=warn.", "",
        "## Incerteza e limites", "",
        "Bootstrap cruzado de 10 mil replicas (seed 74291), reamostrando inicializacoes do MARL e sementes de trafego. "
        "O mesmo MPC e reutilizado para cada inicializacao pareada; nao sao cem demandas independentes. Delta positivo significa MPC maior que MARL.", "",
        "| Medida | Delta MPC menos MARL | IC95 |", "|---|---:|---:|"]
    for k, v in intervals.items():
        lo, hi = v["IC95_bootstrap_cruzado"]
        linhas.append(f"| {k} | {v['delta_MPC_menos_MARL']:.3f} | [{lo:.3f}, {hi:.3f}] |")
    linhas += ["", "O perfil OD e os horarios sao os mesmos entre sementes. As diferencas incluem controle ciclico versus selecao livre "
        "de fase, sensoriamento global das 149 vias no MPC, estimacao de giros e destinos e modelo fluido com capacidade fixa. "
        "Os resultados nao isolam a contribuicao do supervisor nem demonstram generalizacao para outra demanda ou seguranca fisica.", "",
        "As medias locais por entrada e seus tamanhos amostrais sao diagnosticos diferentes da espera total da viagem. "
        "Os valores por entrada estao em estatisticas.json. O P95 da tabela e media dos percentis por execucao, nao um percentil agrupado.", "",
        "## O que manter e o proximo experimento", "",
        "Manter fontes externas intactas com licenca e commit, estado causal, saidas novas, verificacao das fases e transicoes, "
        "rastros do otimizador, parametros congelados e comparacao pareada. Preservar inclusive esta configuracao com resultado desfavoravel.", "",
        "Antes de propor um MPC mais forte: verificar previsoes versus filas observadas, adequar a execucao ao modelo de ciclos, "
        "calibrar saturacao e comprimentos de ciclo somente no conjunto de treino/validacao e auditar G/g, prioridades e colisoes. "
        "Depois reservar novas demandas de teste. Reusar as sementes 1 a 10 apos ajustar olhando estes resultados seria uma analise exploratoria, nao novo teste independente.", ""]
    with (saida / "RELATORIO.md").open("x", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(linhas))
    print(saida)
    print(json.dumps({"medias": means, "qps": len(qps), "bootstrap": intervals}, ensure_ascii=False))
    return saida


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pasta", type=Path)
    analisar(ap.parse_args().pasta)
