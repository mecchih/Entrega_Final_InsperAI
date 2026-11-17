"""Tabela, comparacao pareada e grafico: MARL x comparadores no Cologne8.

Le somente resultados existentes (nao roda SUMO):
  resultados/comparadores_cologne8/teste/<grupo>.json   (este experimento)
  rodadas.csv da analise conferida do MARL (rodada 9f8d757b)
"""
import csv
import json
from pathlib import Path
import sys

import numpy as np

PROJETO = Path(__file__).resolve().parents[1]
SAIDA = PROJETO / "resultados" / "comparadores_cologne8"
RODADAS_MARL = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    PROJETO / "resultados/marl_cologne8/20261113T011843Z_continuo_10seeds_9f8d757b/"
              "analise_detalhada_20261113T132621Z_902ba2/rodadas.csv")

NOMES = {  # ordem de apresentacao
    "marl": "MARL com supervisor (nosso)",
    "atuado_calibrado": "Semáforo atuado (calibrado)",
    "max_pressure_movimento_ajustado": "Max-Pressure por movimento (ajustado)",
    "max_pressure_executor": "Max-Pressure por faixa (já existente)",
    "imitacao_mlp": "Rede neural supervisionada (imita o atuado)",
    "qlearning_tabular": "Q-learning tabular",
    "original_fixo": "Programa original (transições nativas)",
    "webster_calibrado": "Tempo fixo Webster (no executor)",
    "plano_original_no_executor": "Plano original no executor",
}
CAMPOS = ["espera_s", "p95_s", "espera_max_s", "fila_media_rede", "colisoes", "nao_concluidas", "intervencoes", "trocas"]


def carregar():
    grupos = {}
    with RODADAS_MARL.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["grupo"] == "marl":
                grupos.setdefault("marl", []).append(
                    {"semente": int(r["semente_trafego"]), "semente_modelo": int(r["semente_modelo"]),
                     **{k: float(r[k]) for k in CAMPOS}})
    for arq in sorted((SAIDA / "teste").glob("*.json")):
        if arq.stem == "max_pressure_faixa_ajustado":
            continue  # ajuste escolheu os parametros do executor: identico a max_pressure_executor
        grupos[arq.stem] = json.loads(arq.read_text(encoding="utf-8"))
    return {k: grupos[k] for k in NOMES if k in grupos}


def por_semente(linhas, campo):
    d = {}
    for r in linhas:
        d.setdefault(r["semente"], []).append(float(r[campo]))
    return {s: float(np.mean(v)) for s, v in sorted(d.items())}


def main():
    g = carregar()
    marl = g["marl"]
    tab = ["| Controlador | Simulacoes | Espera media (s) | P95 (s) | Fila media | Colisoes/sim | Nao concluidas | Intervencoes/sim |",
           "|---|---:|---:|---:|---:|---:|---:|---:|"]
    resumo = {}
    for k, L in g.items():
        e = [x["espera_s"] for x in L]
        resumo[k] = {c: float(np.mean([x[c] for x in L])) for c in CAMPOS}
        resumo[k]["espera_dp_entre_simulacoes"] = float(np.std(e, ddof=1))
        resumo[k]["simulacoes"] = len(L)
        tab.append(f"| {NOMES[k]} | {len(L)} | {np.mean(e):.2f} ± {np.std(e, ddof=1):.2f} | "
                   f"{resumo[k]['p95_s']:.1f} | {resumo[k]['fila_media_rede']:.2f} | {resumo[k]['colisoes']:.1f} | "
                   f"{int(sum(x['nao_concluidas'] for x in L))} | {resumo[k]['intervencoes']:.1f} |")

    par = ["| Comparador | Espera: MARL - comparador | Variacao | MARL melhor em | P95: MARL - comparador | Colisoes: MARL - comparador |",
           "|---|---:|---:|---:|---:|---:|"]
    pareado = {}
    for k, L in g.items():
        if k == "marl":
            continue
        out = {}
        for c in ("espera_s", "p95_s", "colisoes"):
            a, b = por_semente(marl, c), por_semente(L, c)
            d = np.array([a[s] - b[s] for s in a if s in b])
            out[c] = {"diferenca_media": float(d.mean()), "variacao_pct": float(d.mean() / np.mean(list(b.values())) * 100),
                      "marl_melhor": int((d < 0).sum()), "pares": len(d)}
        pareado[k] = out
        par.append(f"| {NOMES[k]} | {out['espera_s']['diferenca_media']:+.2f} s | {out['espera_s']['variacao_pct']:+.1f}% | "
                   f"{out['espera_s']['marl_melhor']}/{out['espera_s']['pares']} sementes | "
                   f"{out['p95_s']['diferenca_media']:+.1f} s | {out['colisoes']['diferenca_media']:+.1f} |")

    modelos = ["| Grupo | Semente do modelo | Espera media (s) | P95 (s) | Colisoes/sim |", "|---|---:|---:|---:|---:|"]
    for k in ("imitacao_mlp", "qlearning_tabular"):
        for sm in sorted({x["semente_modelo"] for x in g.get(k, [])}):
            L = [x for x in g[k] if x["semente_modelo"] == sm]
            modelos.append(f"| {NOMES[k]} | {sm} | {np.mean([x['espera_s'] for x in L]):.2f} | "
                           f"{np.mean([x['p95_s'] for x in L]):.1f} | {np.mean([x['colisoes'] for x in L]):.1f} |")

    (SAIDA / "tabelas.md").write_text("## Teste final (sementes de trafego 1 a 10)\n\n" + "\n".join(tab)
        + "\n\nMedias por simulacao; ± = desvio padrao entre simulacoes. MARL: 10 modelos x 10 sementes; "
          "grupos aprendidos: 3 modelos x 10 sementes; classicos: 10 sementes.\n\n"
          "## Comparacao pareada por semente de trafego\n\nPara cada semente, media dos modelos de cada grupo. "
          "Negativo = MARL menor (melhor).\n\n" + "\n".join(par)
        + "\n\n## Variacao entre modelos treinados\n\n" + "\n".join(modelos) + "\n", encoding="utf-8")
    (SAIDA / "resumo.json").write_text(json.dumps({"resumo": resumo, "pareado_vs_marl": pareado},
                                                  ensure_ascii=False, indent=2), encoding="utf-8")
    grafico(g, resumo)
    print((SAIDA / "tabelas.md").read_text(encoding="utf-8"))


def grafico(g, resumo):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ordem = sorted(g, key=lambda k: resumo[k]["espera_s"])
    rotulos = [NOMES[k].replace(" (", "\n(") for k in ordem]
    azul, cinza, texto, sec = "#2a78d6", "#b9b8b2", "#0b0b0b", "#52514e"
    cores = [azul if k == "marl" else cinza for k in ordem]
    fig, eixos = plt.subplots(1, 2, figsize=(12, 0.62 * len(ordem) + 1.6), sharey=True, facecolor="#fcfcfb")
    for ax, campo, titulo in ((eixos[0], "espera_s", "Espera média por viagem (s)"),
                              (eixos[1], "p95_s", "P95 da espera (s)")):
        v = [resumo[k][campo] for k in ordem]
        y = np.arange(len(ordem))[::-1]
        ax.barh(y, v, height=0.62, color=cores, edgecolor="#fcfcfb", linewidth=2)
        for yi, vi in zip(y, v):
            ax.text(vi + max(v) * 0.01, yi, f"{vi:.1f}", va="center", fontsize=9, color=texto)
        ax.set_title(titulo, loc="left", fontsize=11, color=texto)
        ax.set_facecolor("#fcfcfb")
        ax.grid(axis="x", color="#e6e5e0", linewidth=0.8)
        ax.set_axisbelow(True)
        for lado in ("top", "right", "left"):
            ax.spines[lado].set_visible(False)
        ax.spines["bottom"].set_color("#c9c8c2")
        ax.tick_params(colors=sec, labelsize=9, length=0)
        ax.set_xlim(0, max(v) * 1.12)
    eixos[0].set_yticks(np.arange(len(ordem))[::-1], rotulos, fontsize=9)
    fig.suptitle("Cologne8 (8 semáforos): teste nas sementes 1–10 — menor é melhor",
                 x=0.01, ha="left", fontsize=12, color=texto)
    fig.text(0.01, 0.005, "Mesmo executor, mesmas proteções e sementes. Colisões ocorrem em todos os controladores (ver tabela).",
             fontsize=8, color=sec)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    fig.savefig(SAIDA / "comparacao_cologne8.png", dpi=160)


if __name__ == "__main__":
    main()
