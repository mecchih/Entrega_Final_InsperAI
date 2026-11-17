"""Graficos e tabelas do C5 treinado (C5-A). So le resultados; nao simula.

uso: py -B -X utf8 semaforo/integracao_insper/parameter_sharing/treinamento_c5/relatorio_treino_c5.py
"""

import json
import math
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

AQUI = Path(__file__).resolve().parent
RES = AQUI / "resultados"
SAIDA = RES / "relatorio"
C3_TREINOS = AQUI.parent / "resultados" / "treinos"
TLS5 = ["476455095", "40278305", "40278183", "300058973", "302806060"]
NOVOS = TLS5[3:]
NOME = {"476455095": "Gomes de Carvalho", "40278305": "Casa do Ator", "40278183": "Quatá",
        "300058973": "Fiandeiras × Clodomiro", "302806060": "Fiandeiras × Atílio Innocenti"}
CTRL = [("original", "Original (14 no programa)", "#4a4a48", None), ("atuado3", "Atuado c/ regras RL nos 3", "#b5b5b0", None),
        ("C3", "C3 (nos 3)", "#2a78d6", None), ("C3_C5", "C3→C5 sem retreino", "#eda100", None),
        ("atuado5", "Atuado c/ regras RL nos 5", "#b5b5b0", "//"), ("C5", "C5 treinado (5 agentes)", "#1baf7a", None)]
ROT = {k: r for k, r, _, _ in CTRL}
COR = {k: c for k, _, c, _ in CTRL}
NIVEIS = {"intenso_c5t_teste": "intensa (2000 veíc/h no corredor), sementes 331-340",
          "moderado_c5t_teste": "moderada (1200 veíc/h), sementes 341-350"}
PALETA_TLS = {"476455095": "#2a78d6", "40278305": "#eda100", "40278183": "#1baf7a", "300058973": "#eb6834", "302806060": "#6250d6"}
T95 = {4: 2.776, 9: 2.262}
TINTA, TINTA2, SUP = "#1f1f1e", "#5f5f5c", "#fcfcfb"


def ms(v):
    v = [x for x in v if x is not None]
    return (statistics.fmean(v), statistics.stdev(v) if len(v) > 1 else 0.0) if v else (None, None)


def ic95(d):
    m, s = ms(d)
    return m, T95.get(len(d) - 1, 2.0) * s / math.sqrt(len(d))


def estilo(ax):
    ax.set_facecolor(SUP)
    ax.grid(axis="y", color="#e6e6e3", linewidth=0.8, zorder=0)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#bdbdb8")
    ax.tick_params(colors=TINTA2)


def pond(l, tls):
    n = sum(l["cruzamentos"][t]["veiculos"] for t in tls)
    return sum(l["cruzamentos"][t]["espera_s"].get("media", 0) * l["cruzamentos"][t]["veiculos"] for t in tls) / n if n else None


CAMPOS = {"corredor": ("Espera média na Ribeirão Claro (s/veículo)", lambda l: l["espera_corredor"].get("media")),
          "rede": ("Espera média na rede inteira (s/viagem)", lambda l: l["espera_rede"].get("media")),
          "p95_corredor": ("P95 da espera no corredor (s)", lambda l: l["espera_corredor"].get("p95")),
          "p95_rede": ("P95 da espera na rede (s)", lambda l: l["espera_rede"].get("p95")),
          "novos": ("Espera nos 2 cruzamentos novos (s/veículo)", lambda l: pond(l, NOVOS)),
          "cinco": ("Espera nos 5 cruzamentos (s/veículo)", lambda l: pond(l, TLS5))}
for t in TLS5:
    CAMPOS[f"esp_{t}"] = (f"Espera em {NOME[t]} (s/veículo)", lambda l, t=t: l["cruzamentos"][t]["espera_s"].get("media"))
    CAMPOS[f"fila_{t}"] = (f"Fila média em {NOME[t]}", lambda l, t=t: l["cruzamentos"][t]["fila"].get("media"))
for t in NOVOS:
    CAMPOS[f"trocas_{t}"] = (f"Trocas de fase/episódio em {NOME[t]}", lambda l, t=t: l["trocas"].get(t))


def carregar(nivel):
    pe = dict(json.loads((RES / "teste" / nivel / "comparadores.json").read_text(encoding="utf-8"))["por_episodio"])
    pe.update(json.loads((RES / "teste" / nivel / "c5.json").read_text(encoding="utf-8"))["por_episodio"])
    return pe


def matriz(pe, c, f):
    if c in pe:
        return [[f(l) if l["valido"] else None for l in sorted(pe[c], key=lambda l: l["semente"])]]
    return [[f(l) if l["valido"] else None for l in sorted(pe[k], key=lambda l: l["semente"])]
            for k in sorted(pe) if k.startswith(c + "|")]


def resumo(pe, c, f):
    m = matriz(pe, c, f)
    if not m:
        return None
    pm = [ms(l)[0] for l in m]
    pd = [ms([l[j] for l in m])[0] for j in range(len(m[0]))]
    return {"media": ms(pm)[0] if len(m) > 1 else ms(m[0])[0], "dp": ms(pm)[1] if len(m) > 1 else ms(pd)[1],
            "por_modelo": pm, "por_demanda": pd}


def eps_de(pe, c):
    return [l for k in pe if k == c or k.startswith(c + "|") for l in pe[k]]


def tabela(nivel, pe):
    ordem = [c for c, *_ in CTRL]
    L = [f"## Demanda {NIVEIS[nivel]}", "", "RL: média de 5 modelos ± dp entre modelos; baselines: ± dp entre 10 demandas. "
         "Só episódios válidos entram nas médias; os inválidos estão contados abaixo.", "",
         "| Métrica | " + " | ".join(ROT[c] for c in ordem) + " |", "|---|" + "---:|" * len(ordem)]
    for campo in ["corredor", "novos", "cinco", "rede", "p95_corredor", "p95_rede"] + [f"esp_{t}" for t in TLS5] + \
            [f"fila_{t}" for t in TLS5] + [f"trocas_{t}" for t in NOVOS]:
        cel = []
        for c in ordem:
            r = resumo(pe, c, CAMPOS[campo][1])
            cel.append("—" if r is None or r["media"] is None else f"{r['media']:.2f} ± {r['dp']:.2f}")
        L.append(f"| {CAMPOS[campo][0]} | " + " | ".join(cel) + " |")
    for nome, f in [("Viagens concluídas (mín.)", lambda e: f"{min(l['fracao_concluida'] for l in e):.3f}"),
                    ("Colisões totais (nos 5 cruzamentos)", lambda e: f"{sum(l['colisoes'] for l in e)} ({sum(l['colisoes_nos_5'] for l in e)})"),
                    ("Teletransportes", lambda e: str(sum(l["teleportes"] for l in e))),
                    ("Episódios travados", lambda e: f"{sum(not l['valido'] for l in e)}/{len(e)}"),
                    ("Violações de segurança", lambda e: str(sum(l["violacoes"] for l in e))),
                    ("Semáforos não controlados fora do programa", lambda e: str(sum(l["outros_com_erro"] for l in e)))]:
        L.append(f"| {nome} | " + " | ".join(f(eps_de(pe, c)) for c in ordem) + " |")
    L += ["", "Comparações pareadas por demanda (média dos 5 modelos em cada demanda; Δ = C5 − referência):", "",
          "| Métrica | C5 − C3→C5 | IC95 | melhora em | C5 − C3 | IC95 | C5 − original | IC95 | C5 − atuado5 | IC95 |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    comps = {}
    for campo in ["corredor", "novos", "cinco", "rede", "p95_corredor"] + [f"esp_{t}" for t in TLS5] + [f"trocas_{t}" for t in NOVOS]:
        f = CAMPOS[campo][1]
        c5 = resumo(pe, "C5", f)["por_demanda"]
        cel, comps[campo] = [], {}
        for ref in ("C3_C5", "C3", "original", "atuado5"):
            r = resumo(pe, ref, f)["por_demanda"]
            d = [b - a for a, b in zip(r, c5) if a is not None and b is not None]
            if not d:
                cel += ["—", "—"] + (["—"] if ref == "C3_C5" else [])
                continue
            m, h = ic95(d)
            comps[campo][ref] = [m, h, sum(x < 0 for x in d), len(d)]
            cel += [f"{m:+.2f}", f"±{h:.2f}"] + ([f"{sum(x < 0 for x in d)}/{len(d)}"] if ref == "C3_C5" else [])
        L.append(f"| {CAMPOS[campo][0]} | " + " | ".join(cel) + " |")
    L += ["", "Consistência entre sementes de modelo (média das 10 demandas por modelo):", "",
          "| Métrica | " + " | ".join(f"C5 s{k}" for k in range(1, 6)) + " | " + " | ".join(f"C3→C5 s{k}" for k in range(1, 6)) + " |",
          "|---|" + "---:|" * 10]
    for campo in ("corredor", "novos", "rede", "trocas_300058973", "trocas_302806060"):
        a = resumo(pe, "C5", CAMPOS[campo][1])["por_modelo"]
        b = resumo(pe, "C3_C5", CAMPOS[campo][1])["por_modelo"]
        L.append(f"| {CAMPOS[campo][0]} | " + " | ".join(f"{x:.2f}" if x is not None else "—" for x in a + b) + " |")
    return L, comps


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    pes = {n: carregar(n) for n in NIVEIS}
    sel = json.loads((RES / "validacao" / "selecao_c5.json").read_text(encoding="utf-8"))
    L = ["# C5 treinado (C5-A) — testes finais com pesos congelados", ""]
    L += ["## Seleção na validação (sementes 221-225)", "", "| Semente | checkpoint | elegível | espera nos 5 (s/veíc.) | corredor | rede |",
          "|---|---:|---|---:|---:|---:|"]
    for sm, v in sel["selecao"].items():
        r = v["validacao"]
        L.append(f"| C5 s{sm} | ep{v['episodio']} | {v['elegivel']} | {r['espera5']:.2f} | {r['espera_corredor']:.2f} | {r['espera_rede']:.2f} |")
    for ref, r in sel["referencias"].items():
        L.append(f"| {ref} | — | — | {r['espera5']:.2f} | {r['espera_corredor']:.2f} | {r['espera_rede']:.2f} |")
    L.append("")
    comps = {}
    for nivel, pe in pes.items():
        l, comps[nivel] = tabela(nivel, pe)
        L += l + [""]
    (SAIDA / "tabela_treino_c5.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (SAIDA / "comparacoes_treino_c5.json").write_text(json.dumps(comps, indent=1), encoding="utf-8")
    print("\n".join(L))

    # G1: evolucao do treino
    hs5 = [[json.loads(l) for l in (RES / "treinos" / f"C5_s{s}" / "historico.jsonl").read_text(encoding="utf-8").splitlines()]
           for s in range(1, 6)]
    hs3 = [[json.loads(l) for l in (C3_TREINOS / f"C_s{s}" / "historico.jsonl").read_text(encoding="utf-8").splitlines()]
           for s in range(1, 6)]

    def mm(hs, f):
        n = min(len(h) for h in hs)
        serie = [statistics.fmean(f(h[e]) for h in hs) for e in range(n)]
        return [statistics.fmean(serie[max(0, e - 9):e + 1]) for e in range(n)]
    fig, axs = plt.subplots(2, 2, figsize=(15, 9), facecolor=SUP)
    axs[0, 0].plot(mm(hs3, lambda h: h["espera_corredor_media"]), color=COR["C3"], lw=2, label="C3 (3 agentes)")
    axs[0, 0].plot(mm(hs5, lambda h: h["espera_corredor_media"]), color=COR["C5"], lw=2, label="C5 (5 agentes)")
    axs[0, 0].set_title("Espera média na Ribeirão Claro por episódio de treino (s)", color=TINTA, loc="left", fontsize=10)
    for t in TLS5:
        axs[0, 1].plot(mm(hs5, lambda h, t=t: h["espera_cruzamentos"][t]), color=PALETA_TLS[t], lw=2, label=NOME[t])
    axs[0, 1].set_title("C5: espera média por cruzamento no treino (s/veículo)", color=TINTA, loc="left", fontsize=10)
    for t in TLS5:
        axs[1, 0].plot(mm(hs5, lambda h, t=t: h["trocas"][t]), color=PALETA_TLS[t], lw=2, label=NOME[t])
    axs[1, 0].set_title("C5: trocas de fase por episódio de treino", color=TINTA, loc="left", fontsize=10)
    tab = sel["tabela"]
    eps = sorted({int(e) for s in tab.values() for e in s})
    m, sd = zip(*[ms([tab[s][str(e)]["espera5"] for s in tab]) for e in eps])
    axs[1, 1].errorbar(eps, m, yerr=sd, marker="o", capsize=3, lw=2, color=COR["C5"], label="C5 (média ± dp de 5 sementes)")
    for ref, cor in (("original", COR["original"]), ("atuado5", "#8c8c88")):
        axs[1, 1].axhline(sel["referencias"][ref]["espera5"], color=cor, ls="--", lw=1.2,
                          label=f"{ROT[ref]} ({sel['referencias'][ref]['espera5']:.1f})")
    axs[1, 1].set_title("Validação (221-225): espera nos 5 cruzamentos por checkpoint (s/veículo)", color=TINTA, loc="left", fontsize=10)
    for ax in axs.flat:
        estilo(ax)
        ax.legend(fontsize=8, frameon=False)
    axs[1, 0].set_xlabel("episódio (média de 5 sementes; média móvel de 10)", color=TINTA2)
    axs[0, 0].set_xlabel("episódio (média de 5 sementes; média móvel de 10)", color=TINTA2)
    fig.tight_layout()
    fig.savefig(SAIDA / "g1_evolucao_treino_c5.png", dpi=140, facecolor=SUP)
    plt.close(fig)

    # G2: comparacao principal (intensa) + moderada
    fig, axs = plt.subplots(2, 4, figsize=(19, 9), facecolor=SUP)
    for row, (nivel, pe) in enumerate(pes.items()):
        for ax, campo in zip(axs[row], ("corredor", "novos", "rede", "p95_corredor")):
            rs = [resumo(pe, c, CAMPOS[campo][1]) for c, *_ in CTRL]
            topo = max(r["media"] + r["dp"] for r in rs)
            ax.set_ylim(0, topo * 1.15)
            for j, ((c, rot, cor, hach), r) in enumerate(zip(CTRL, rs)):
                ax.bar(j, r["media"], 0.75, yerr=r["dp"], capsize=3, color=cor, hatch=hach, zorder=3,
                       edgecolor=SUP if not hach else "#7a7a75", linewidth=1.3, label=rot)
                ax.text(j, r["media"] + r["dp"] + topo * 0.015, f"{r['media']:.1f}", ha="center", va="bottom", fontsize=8,
                        color=TINTA)
                inv = sum(not l["valido"] for l in eps_de(pe, c))
                if inv:
                    ax.text(j, 0.5, f"{inv} trav.", ha="center", va="bottom", fontsize=7, color=TINTA, rotation=90)
            ax.set_xticks([])
            ax.set_title(f"{CAMPOS[campo][0]}\n{NIVEIS[nivel]}", color=TINTA, loc="left", fontsize=9)
            estilo(ax)
    fig.legend(*axs[0, 0].get_legend_handles_labels(), loc="upper right", ncol=6, fontsize=8.5, frameon=False,
               bbox_to_anchor=(1, 0.975))
    fig.suptitle("Original × C3 × C3→C5 × C5 treinado (mesmas demandas; pesos congelados no teste)", color=TINTA, x=0.01,
                 ha="left", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(SAIDA / "g2_original_c3_c3c5_c5.png", dpi=140, facecolor=SUP)
    plt.close(fig)

    # G3: cinco cruzamentos (intensa)
    pe = pes["intenso_c5t_teste"]
    fig, ax = plt.subplots(figsize=(15, 5.5), facecolor=SUP)
    w = 0.8 / len(CTRL)
    for j, (c, rot, cor, hach) in enumerate(CTRL):
        for i, t in enumerate(TLS5):
            r = resumo(pe, c, CAMPOS[f"esp_{t}"][1])
            x = i + (j - (len(CTRL) - 1) / 2) * w
            ax.bar(x, r["media"], w, yerr=r["dp"], capsize=2, color=cor, hatch=hach, zorder=3,
                   edgecolor=SUP if not hach else "#7a7a75", linewidth=1.2, label=rot if i == 0 else None)
    veic = [statistics.fmean(l["cruzamentos"][t]["veiculos"] for l in pe["original"]) for t in TLS5]
    ax.set_xticks(range(5))
    ax.set_xticklabels([f"{NOME[t]}\n{t} · {v:.0f} veíc./episódio" for t, v in zip(TLS5, veic)], color=TINTA, fontsize=8.5)
    ax.axvline(2.5, color="#bdbdb8", lw=1, ls=":")
    ax.set_title("Espera média por veículo em cada cruzamento (s) — demanda intensa, sementes 331-340", color=TINTA, loc="left", fontsize=11)
    estilo(ax)
    ax.legend(fontsize=8, frameon=False, ncol=3)
    fig.tight_layout()
    fig.savefig(SAIDA / "g3_cinco_cruzamentos.png", dpi=140, facecolor=SUP)
    plt.close(fig)

    # G4: trocas de fase nos 2 novos
    fig, axs = plt.subplots(1, 2, figsize=(14, 5), facecolor=SUP)
    for ax, (nivel, pe) in zip(axs, pes.items()):
        ctrls = [("C3_C5", ROT["C3_C5"]), ("atuado5", ROT["atuado5"]), ("C5", ROT["C5"])]
        w = 0.8 / len(ctrls)
        ax.set_ylim(0, 1.3 * max(resumo(pe, c, CAMPOS[f"trocas_{t}"][1])["media"] + resumo(pe, c, CAMPOS[f"trocas_{t}"][1])["dp"]
                                 for c, _ in ctrls for t in NOVOS))
        for j, (c, rot) in enumerate(ctrls):
            for i, t in enumerate(NOVOS):
                r = resumo(pe, c, CAMPOS[f"trocas_{t}"][1])
                x = i + (j - (len(ctrls) - 1) / 2) * w
                hach = "//" if c == "atuado5" else None
                ax.bar(x, r["media"], w, yerr=r["dp"], capsize=3, color=COR[c], hatch=hach, zorder=3,
                       edgecolor=SUP if not hach else "#7a7a75", linewidth=1.2, label=rot if i == 0 else None)
                ax.text(x, r["media"] + r["dp"] + 1, f"{r['media']:.0f}", ha="center", va="bottom", fontsize=8, color=TINTA)
        ax.set_xticks(range(2))
        ax.set_xticklabels([NOME[t] for t in NOVOS], color=TINTA)
        ax.set_title(f"Trocas de fase por episódio nos 2 cruzamentos novos\ndemanda {NIVEIS[nivel]}", color=TINTA, loc="left", fontsize=10)
        estilo(ax)
        ax.legend(fontsize=8, frameon=False, ncol=3, loc="upper center")
    fig.tight_layout()
    fig.savefig(SAIDA / "g4_trocas_novos.png", dpi=140, facecolor=SUP)
    plt.close(fig)


if __name__ == "__main__":
    main()
