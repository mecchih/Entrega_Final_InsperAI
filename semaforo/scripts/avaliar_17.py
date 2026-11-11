"""
Experimento 2: a rede passa a VER a espera (17 entradas). Compara tres geracoes
de DQN na dinamica C, nos mesmos 5 cenarios e nas mesmas 10 sementes de teste:

  A. DQN C, recompensa fila,         13 entradas  (dqn_fila_C_seed*.pt)
  B. DQN C, recompensa fila_excesso, 13 entradas  (dqn_fila_excesso_C_seed*.pt)  <- referencia principal
  C. DQN C, recompensa fila_excesso, 17 entradas  (dqn_fila_excesso_17_C_seed*.pt)

mais Webster e Max-Pressure teto (recal. C).

So as 3 redes C sao simuladas agora (5 x 3 x 10 = 150 rodadas). A, Webster e
Max-Pressure vem de comparacao_C/avaliacao.json e B de
comparacao_excesso_C/avaliacao.json: a avaliacao e deterministica e as mesmas
rodadas continuam reproduziveis (testar_obs17.py confere amostras). Use
--rerodar-referencias para refazer tudo.

Nenhuma metrica esconde veiculo nao atendido: esperas, P95 e maximos incluem quem
nao terminou a viagem (com a espera ate o corte, um limite inferior).

Saida: resultados/comparacao_17_C/ (avaliacao.json, resumo.json, resumo.md, graficos/)
Uso (de dentro de scripts/), depois dos 3 treinos:
  python avaliar_17.py
  py avaliar_17.py --so-graficos            # Python com matplotlib
"""

import argparse
import json
import os
import statistics
import sys
import time
from multiprocessing import Pool

import gerar_demanda
import simulacao
import analisar_comportamento as ac
import avaliar_C
from avaliar_excesso import ROTULOS, SECUNDARIAS, SOMAS, _metricas
from simulacao import APROXIMACOES

PASTA_SAIDA = os.path.join(simulacao.PASTA, "resultados", "comparacao_17_C")
AVALIACAO_C = os.path.join(simulacao.PASTA, "resultados", "comparacao_C", "avaliacao.json")
AVALIACAO_EXCESSO = os.path.join(simulacao.PASTA, "resultados", "comparacao_excesso_C",
                                 "avaliacao.json")

REFERENCIAS = ["Webster", "Max-Pressure teto (recal. C)"]
GERACOES = {
    "A: fila, 13 entradas": [f"DQN C seed{i}" for i in range(3)],
    "B: fila_excesso, 13 entradas": [f"DQN excesso C seed{i}" for i in range(3)],
    "C: fila_excesso, 17 entradas": [f"DQN excesso17 C seed{i}" for i in range(3)],
}
GA, GB, GC = GERACOES
NOVAS = GERACOES[GC]
PARES = [(GC, GB), (GC, GA), (GB, GA)]  # (nova, base): diferenca = nova - base
# metricas em que "menor e melhor" e que entram nas contagens por semente
PRINCIPAIS = ["espera_media", "espera_p95", "p95_secundarias", "pior_p95_aprox",
              "espera_max", "nao_atendidos"]
# limiar para chamar de "deterioracao relevante" no saturado (criterio 7)
DETERIORACAO = {"espera_media": 5.0, "espera_p95": 10.0}


def _ms(v):
    v = [x for x in v if x is not None]
    if not v:
        return None
    return {"media": statistics.mean(v), "dp": statistics.stdev(v) if len(v) > 1 else 0.0,
            "min": min(v), "max": max(v), "total": sum(v)}


def agregar(rodadas, cenarios):
    por = {}
    for r in rodadas:
        por.setdefault((r["cenario"], r["controlador"]), {})[r["seed"]] = _metricas(r)
    resumo = {}
    for cen in cenarios:
        for ctrl in REFERENCIAS + [m for g in GERACOES.values() for m in g]:
            d = por.get((cen, ctrl))
            if d:
                resumo[f"{cen}|{ctrl}"] = {k: _ms([x[k] for x in d.values()]) for k in ROTULOS}
        series = {}
        for g, membros in GERACOES.items():
            if not all((cen, m) in por for m in membros):
                continue
            sementes = sorted(por[(cen, membros[0])])
            serie = {k: [None if any(por[(cen, m)][s][k] is None for m in membros) else
                         statistics.mean(por[(cen, m)][s][k] for m in membros) for s in sementes]
                     for k in ROTULOS}
            item = {k: _ms(v) for k, v in serie.items()}
            # grupo: maximo = o maior entre 3 redes x 10 sementes; somas = das 3 redes
            item["espera_max"] = {**item["espera_max"], "max": max(
                x["espera_max"] for m in membros for x in por[(cen, m)].values())}
            for k in SOMAS:
                item[k] = {**item[k], "total": sum(x[k] for m in membros for x in por[(cen, m)].values())}
            # variabilidade entre as 3 sementes de TREINO: media de cada rede nas 10 sementes
            item["entre_redes"] = {k: _ms([statistics.mean(
                x[k] for x in por[(cen, m)].values()) for m in membros])
                for k in PRINCIPAIS if serie[k][0] is not None}
            series[g] = serie
            resumo[f"{cen}|{g}"] = item
        for nova, base in PARES:
            if nova not in series or base not in series:
                continue
            comp = {}
            for k in ROTULOS:
                a, n = series[base][k], series[nova][k]
                if a[0] is None:
                    continue
                d = [y - x for x, y in zip(a, n)]
                base_media = statistics.mean(a)
                comp[k] = {"diferenca_media": statistics.mean(d),
                           "relativa_pct": 100 * statistics.mean(d) / base_media if base_media else None,
                           "sementes_melhoraram": sum(x < 0 for x in d),
                           "sementes_pioraram": sum(x > 0 for x in d),
                           "sementes_empate": sum(x == 0 for x in d), "n": len(d)}
            resumo[f"{cen}|{nova} vs {base}"] = comp
    return resumo


def carro_sozinho():
    """Teste do carro sozinho (sem simulador) nas 9 redes; None se faltar modelo."""
    import diagnosticar_equilibrio as de
    from dqn import AgenteDQN
    out = {}
    for g, membros in GERACOES.items():
        for rot in membros:
            nome = ac.ROTULO_MODELO[rot]
            if not _existe(nome):
                return None
            ag = AgenteDQN(treinando=False).carregar(nome)
            res = [de._automato(ag, v, c, carros=n) for n in (1, 2, 3)
                   for v in APROXIMACOES for c in APROXIMACOES if c != v]
            out[rot] = {"geracao": g, "n_entradas": ag.n_entradas,
                        "presos": sum(r[0] != "atende" for r in res), "de": len(res),
                        "atendidos_so_pela_regra": sum(1 for r in res if r[0] == "atende" and r[2])}
    return out


def criterios(resumo, cenarios, auto):
    """Criterios definidos ANTES do treino (comparando C com B)."""
    chave = f"{GC} vs {GB}"
    if not all(f"{c}|{chave}" in resumo for c in cenarios):
        return None
    comp = {c: resumo[f"{c}|{chave}"] for c in cenarios}
    out = {
        "1_zero_nao_atendidos": all(resumo[f"{c}|{m}"]["nao_atendidos"]["total"] == 0
                                    for c in cenarios for m in NOVAS),
        "2_zero_ciclos_carro_sozinho": None if auto is None else all(
            auto[m]["presos"] == 0 for m in NOVAS),
    }
    for i, cen in ((3, "assimetrico"), (4, "girado")):
        v = comp[cen]["p95_secundarias"]["relativa_pct"]
        out[f"{i}_p95_secundarias_{cen}_cai_20pct"] = v <= -20
        out[f"{i}_p95_secundarias_{cen}_variacao_pct"] = v
    piora = {c: comp[c]["espera_media"]["relativa_pct"] for c in cenarios}
    out["5_espera_media_aumenta_no_maximo_5pct"] = all(v <= 5 for v in piora.values())
    out["5_espera_media_variacao_pct"] = piora
    out["6_espera_media_abaixo_de_webster_e_mp_teto"] = all(
        resumo[f"{c}|{GC}"]["espera_media"]["media"]
        < min(resumo[f"{c}|{r}"]["espera_media"]["media"] for r in REFERENCIAS) for c in cenarios)
    sat = comp["saturado"]
    out["7_saturado_variacao_pct"] = {k: sat[k]["relativa_pct"] for k in
                                      ("espera_media", "espera_p95", "pior_p95_aprox")}
    out["7_saturado_deterioracao_relevante"] = any(
        sat[k]["relativa_pct"] > lim for k, lim in DETERIORACAO.items())
    out["7_limiar_deterioracao_pct"] = DETERIORACAO
    out["8_sementes_melhoraram_pioraram"] = {
        c: {k: f"{comp[c][k]['sementes_melhoraram']} melhoraram, "
               f"{comp[c][k]['sementes_pioraram']} pioraram, {comp[c][k]['sementes_empate']} empates"
            for k in PRINCIPAIS if k in comp[c]} for c in cenarios}
    out["aviso"] = ("Cumprir estes criterios nas sementes testadas nao e garantia matematica "
                    "de ausencia de starvation.")
    return out


def _existe(nome):
    from dqn import PASTA_MODELOS  # torch so e importado aqui (nao no --so-graficos)
    return os.path.exists(os.path.join(PASTA_MODELOS, f"{nome}.pt"))


def _f(x, nd=1):
    return "-" if x is None else f"{x:.{nd}f}"


def relatorio(resumo, cenarios, crit, auto):
    L = ["# Experimento 2: DQN de 17 entradas (observa a espera) - dinamica C", "",
         "Media de 10 sementes de teste (+- dp). Esperas, P95 e maximos INCLUEM veiculos nao "
         "atendidos. Nao atendidos e intervencoes: total nas 10 sementes (nos grupos, das 3 redes). "
         "Espera max: a maior. Linhas em negrito: media das 3 redes de cada geracao.", ""]
    for cen in cenarios:
        L += [f"## {cen}" + (" (nunca visto no treino)" if cen == "girado" else ""), "",
              "| controlador | " + " | ".join(ROTULOS.values()) + " |",
              "|---|" + "---|" * len(ROTULOS)]
        for ctrl in REFERENCIAS + [m for g in GERACOES.values() for m in g] + list(GERACOES):
            x = resumo.get(f"{cen}|{ctrl}")
            if not x:
                continue
            cel = []
            for k in ROTULOS:
                v = x[k]
                if v is None:
                    cel.append("-")
                elif k in SOMAS:
                    cel.append(_f(v["total"], 0))
                elif k == "espera_max":
                    cel.append(_f(v["max"], 0))
                elif k in ("espera_media", "espera_p95", "pior_p95_aprox", "p95_secundarias"):
                    cel.append(f"{_f(v['media'])} +- {_f(v['dp'])}")
                else:
                    cel.append(_f(v["media"]))
            L.append(f"| {'**' + ctrl + '**' if ctrl in GERACOES else ctrl} | " + " | ".join(cel) + " |")
        L.append("")
        for nova, base in PARES:
            comp = resumo.get(f"{cen}|{nova} vs {base}")
            if comp:
                L.append(f"- **{nova[:1]} - {base[:1]}** (pareado por semente): " + "; ".join(
                    f"{ROTULOS[k]} {comp[k]['diferenca_media']:+.1f}"
                    + (f" ({comp[k]['relativa_pct']:+.1f}%)" if comp[k]["relativa_pct"] is not None else "")
                    + f", melhor/pior em {comp[k]['sementes_melhoraram']}/{comp[k]['sementes_pioraram']}"
                    for k in PRINCIPAIS + ["trocas_por_hora"] if k in comp))
        L += ["", "Variabilidade entre as 3 sementes de treino (media de cada rede; min - max):", ""]
        for g in GERACOES:
            x = resumo.get(f"{cen}|{g}")
            if x:
                L.append(f"- {g}: " + "; ".join(
                    f"{ROTULOS[k]} {_f(v['min'])} - {_f(v['max'])} (dp {_f(v['dp'])})"
                    for k, v in x["entre_redes"].items() if v))
        L.append("")
    if auto:
        L += ["## Teste do carro sozinho", "", "| rede | geracao | entradas | presos | "
              "atendidos so pela regra |", "|---|---|---|---|---|"]
        L += [f"| {k} | {v['geracao']} | {v['n_entradas']} | {v['presos']}/{v['de']} | "
              f"{v['atendidos_so_pela_regra']} |" for k, v in auto.items()]
        L.append("")
    if crit:
        L += ["## Criterios (C comparado com B)", ""]
        for k, v in crit.items():
            if isinstance(v, dict) and k.startswith("8"):
                L.append(f"- {k}:")
                for c, d in v.items():
                    L.append(f"  - {c}: " + "; ".join(f"{ROTULOS[m]}: {s}" for m, s in d.items()))
            else:
                L.append(f"- {k}: {v}")
        L.append("")
    return "\n".join(L)


def graficos(resumo, cenarios, pasta, n_sementes):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    ac._estilo(plt)
    os.makedirs(pasta, exist_ok=True)
    cor_g = {GA: ac.CORES[0], GB: ac.CORES[1], GC: ac.CORES[2]}
    cor_ref = {REFERENCIAS[0]: "#9a9893", REFERENCIAS[1]: "#6d6b66"}
    feitos = []
    for chave, campo, ylabel, arq in [
            ("espera_media", "media", "Espera media (s)", "1_espera_media.png"),
            ("espera_p95", "media", "P95 geral (s)", "2_p95_geral.png"),
            ("p95_secundarias", "media", "P95 das ruas secundarias (s)", "3_p95_secundarias.png"),
            ("pior_p95_aprox", "media", "P95 da pior aproximacao (s)", "4_pior_p95.png"),
            ("espera_max", "max", "Espera maxima, com nao atendidos (s)", "5_espera_max.png")]:
        cens = [c for c in cenarios if resumo.get(f"{c}|{GA}", {}).get(chave)]
        if not cens:
            continue
        fig, axes = plt.subplots(1, len(cens), figsize=(3.3 * len(cens), 4.4), squeeze=False)
        for ax, cen in zip(axes[0], cens):
            x = 0
            ticks, nomes = [], []
            for ref in REFERENCIAS:
                v = resumo[f"{cen}|{ref}"][chave]
                ax.bar(x, v[campo], 0.8, color=cor_ref[ref])
                ticks.append(x); nomes.append(ref.replace(" (recal. C)", " recal."))
                x += 1
            x += 0.4
            for g, membros in GERACOES.items():
                if f"{cen}|{g}" not in resumo:
                    continue
                for j, m in enumerate(membros):  # as 3 redes (sementes de treino 0, 1, 2)
                    ax.bar(x + j * 0.27, resumo[f"{cen}|{m}"][chave][campo], 0.25,
                           color=cor_g[g], alpha=0.45)
                ax.plot([x - 0.15, x + 0.69], [resumo[f"{cen}|{g}"][chave][campo]] * 2,
                        color=cor_g[g], lw=2.2)
                ticks.append(x + 0.27); nomes.append(g.split(":")[0] + ": " + g.split(": ")[1])
                x += 1.3
            ax.set_xticks(ticks)
            ax.set_xticklabels(nomes, rotation=50, ha="right", fontsize=7)
            ax.set_title(cen + (" *" if cen == "girado" else ""), fontsize=10)
        axes[0][0].set_ylabel(ylabel)
        fig.text(0.01, -0.16, f"{n_sementes} sementes de teste, dinamica C. Barras claras = as 3 redes "
                 "(sementes de treino 0, 1, 2); traco = media das 3. * cenario nao visto no treino.",
                 fontsize=8, color=ac.CINZA_TEXTO)
        fig.tight_layout()
        caminho = os.path.join(pasta, arq)
        fig.savefig(caminho, bbox_inches="tight")
        plt.close(fig)
        feitos.append(caminho)
    return feitos


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sementes", type=int, nargs="*", default=None)
    ap.add_argument("--processos", type=int, default=max(1, min(6, (os.cpu_count() or 2) - 1)))
    ap.add_argument("--rerodar-referencias", action="store_true")
    ap.add_argument("--so-graficos", action="store_true")
    ap.add_argument("--saida", default=PASTA_SAIDA, help=argparse.SUPPRESS)  # usado nos testes
    args = ap.parse_args(argv)
    saida, pasta_graf = args.saida, os.path.join(args.saida, "graficos")
    arq = os.path.join(saida, "avaliacao.json")

    if args.so_graficos:
        with open(arq) as f:
            salvo = json.load(f)
        resumo = agregar(salvo["rodadas"], salvo["cenarios"])
        for c in graficos(resumo, salvo["cenarios"], pasta_graf, len(salvo["sementes"])):
            print("  ", c)
        return 0

    with open(AVALIACAO_C) as f:
        aval_c = json.load(f)
    with open(AVALIACAO_EXCESSO) as f:
        aval_exc = json.load(f)
    cenarios = aval_c["cenarios"]
    sementes = args.sementes or aval_c["sementes"]
    novas = [r for r in NOVAS if _existe(ac.ROTULO_MODELO[r])]
    if not novas:
        sys.exit("Nenhum modelo dqn_fila_excesso_17_C_seed*.pt encontrado: treine antes.")
    if len(novas) < 3:
        print(f"AVISO: so {novas} existem; a geracao C nao sera agregada.")
    controladores = REFERENCIAS + GERACOES[GA] + GERACOES[GB] + novas

    reuso = []
    if not args.rerodar_referencias:
        reuso += [dict(r, origem="comparacao_C/avaliacao.json") for r in aval_c["rodadas"]
                  if r["controlador"] in REFERENCIAS + GERACOES[GA] and r["seed"] in sementes]
        reuso += [dict(r, origem="comparacao_excesso_C/avaliacao.json") for r in aval_exc["rodadas"]
                  if r["controlador"] in GERACOES[GB] and r["seed"] in sementes]
    feitas = {(r["cenario"], r["controlador"], r["seed"]) for r in reuso}
    rotas = {c: gerar_demanda.gerar(c) for c in cenarios}
    tarefas = [(c, ctrl, s, rotas[c]) for c in cenarios for ctrl in controladores
               for s in sementes if (c, ctrl, s) not in feitas]
    print(f"{len(reuso)} rodadas reaproveitadas; {len(tarefas)} novas", flush=True)
    t0 = time.time()
    rodadas = list(reuso)
    pool = Pool(args.processos) if args.processos > 1 else None  # 1 = no proprio processo
    try:
        for i, r in enumerate((pool.imap_unordered if pool else map)(avaliar_C._tarefa, tarefas), 1):
            r["origem"] = "rodada agora"
            rodadas.append(r)
            if i % 25 == 0 or i == len(tarefas):
                print(f"  {i}/{len(tarefas)} ({time.time() - t0:.0f} s)", flush=True)
    finally:
        if pool:
            pool.close()
            pool.join()
    rodadas.sort(key=lambda r: (cenarios.index(r["cenario"]),
                                controladores.index(r["controlador"]), r["seed"]))
    os.makedirs(saida, exist_ok=True)
    with open(arq, "w") as f:
        json.dump({"dinamica": avaliar_C.DIN.nome, "cenarios": cenarios, "sementes": sementes,
                   "controladores": controladores, "geracoes": GERACOES, "rodadas": rodadas}, f)

    resumo = agregar(rodadas, cenarios)
    auto = carro_sozinho()
    crit = criterios(resumo, cenarios, auto)
    with open(os.path.join(saida, "resumo.json"), "w") as f:
        json.dump({"resumo": resumo, "carro_sozinho": auto, "criterios": crit}, f, indent=1)
    with open(os.path.join(saida, "resumo.md"), "w", encoding="utf-8") as f:
        f.write(relatorio(resumo, cenarios, crit, auto))
    print(f"Tabelas: {os.path.join(saida, 'resumo.md')}")
    try:
        graficos(resumo, cenarios, pasta_graf, len(sementes))
    except ImportError as e:
        print(f"Sem matplotlib neste Python ({e}). Graficos:  py avaliar_17.py --so-graficos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
