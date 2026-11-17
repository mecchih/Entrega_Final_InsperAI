"""Graficos e tabela do experimento zero-shot C3 -> C5. So le resultados/avaliacao_final/avaliacao_c5.json.

uso: py -B -X utf8 semaforo/integracao_insper/parameter_sharing/experimento_c5/relatorio_c5.py
"""

import json
import math
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

AQUI = Path(__file__).resolve().parent
RES = AQUI / "resultados" / "avaliacao_final"
SAIDA = AQUI / "resultados" / "relatorio"
TLS5 = ["476455095", "40278305", "40278183", "300058973", "302806060"]
NOVOS = TLS5[3:]
NOME = {"476455095": "Gomes de Carvalho", "40278305": "Casa do Ator", "40278183": "Quatá",
        "300058973": "Fiandeiras ×\nClodomiro (novo)", "302806060": "Fiandeiras ×\nAtílio Innocenti (novo)"}
CTRL = [("original", "Original (14 no programa)", "#4a4a48", None), ("atuado3", "Atuado c/ regras RL nos 3", "#b5b5b0", None),
        ("C3", "C3: Modelo C nos 3", "#2a78d6", None), ("atuado5", "Atuado c/ regras RL nos 5", "#b5b5b0", "//"),
        ("C5", "C3→C5: mesmo checkpoint nos 5", "#eb6834", None)]
ROT = {k: r for k, r, _, _ in CTRL}
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


def novos_ponderado(l):
    """Espera media por veiculo nos 2 cruzamentos novos juntos (ponderada pelo n. de veiculos de cada)."""
    n = sum(l["cruzamentos"][t]["veiculos"] for t in NOVOS)
    return sum(l["cruzamentos"][t]["espera_s"].get("media", 0) * l["cruzamentos"][t]["veiculos"] for t in NOVOS) / n if n else None


CAMPOS = {
    "corredor": ("Espera média no corredor original (s/veículo)", lambda l: l["espera_corredor"].get("media")),
    "rede": ("Espera média na rede inteira (s/viagem)", lambda l: l["espera_rede"].get("media")),
    "p95_corredor": ("P95 da espera no corredor (s)", lambda l: l["espera_corredor"].get("p95")),
    "p95_rede": ("P95 da espera na rede (s)", lambda l: l["espera_rede"].get("p95")),
    "novos": ("Espera nos 2 cruzamentos novos (s/veículo)", novos_ponderado),
}
for t in TLS5:
    CAMPOS[f"espera_{t}"] = (f"Espera em {t} (s/veículo)", lambda l, t=t: l["cruzamentos"][t]["espera_s"].get("media"))
    CAMPOS[f"fila_{t}"] = (f"Fila média em {t} (veículos)", lambda l, t=t: l["cruzamentos"][t]["fila"].get("media"))
    CAMPOS[f"veic_{t}"] = (f"Veículos em {t}", lambda l, t=t: l["cruzamentos"][t]["veiculos"])


def matriz(pe, ctrl, f):
    """[modelo][semente] com None nos episodios invalidos (baselines: uma linha)."""
    if ctrl in pe:
        return [[f(l) if l["valido"] else None for l in sorted(pe[ctrl], key=lambda l: l["semente"])]]
    return [[f(l) if l["valido"] else None for l in sorted(pe[k], key=lambda l: l["semente"])]
            for k in sorted(pe) if k.startswith(ctrl + "|")]


def resumo(pe, ctrl, f):
    m = matriz(pe, ctrl, f)
    por_modelo = [ms(l)[0] for l in m]
    por_demanda = [ms([l[j] for l in m])[0] for j in range(len(m[0]))]
    return {"media": ms(por_modelo)[0] if len(m) > 1 else ms(m[0])[0], "dp_modelos": ms(por_modelo)[1] if len(m) > 1 else None,
            "dp_demandas": ms(por_demanda)[1], "por_modelo": por_modelo, "por_demanda": por_demanda, "mat": m}


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    d = json.loads((RES / "avaliacao_c5.json").read_text(encoding="utf-8"))
    pe = d["por_episodio"]

    # tabela principal
    def cel(ctrl, campo):
        r = resumo(pe, ctrl, CAMPOS[campo][1])
        dp = r["dp_modelos"] if r["dp_modelos"] is not None else r["dp_demandas"]
        return f"{r['media']:.2f} ± {dp:.2f}" if r["media"] is not None else "—"

    def soma(ctrl, f):
        eps = [l for k in pe if k == ctrl or k.startswith(ctrl + "|") for l in pe[k]]
        return f(eps), len(eps)

    ordem = ["original", "C3", "C5", "atuado3", "atuado5"]
    L = ["# Zero-shot C3 → C5 (intensa, sementes novas 291-300; pesos congelados)", "",
         "RL: média dos 5 checkpoints do Modelo C ± dp entre checkpoints (cada um = média das 10 demandas). Baselines: ± dp "
         "entre demandas. Só episódios válidos entram nas médias.", "",
         "| Métrica | " + " | ".join(ROT[c] for c in ordem) + " |", "|---|" + "---:|" * len(ordem)]
    for campo in ("corredor", "rede", "p95_corredor", "p95_rede", "novos"):
        L.append(f"| {CAMPOS[campo][0]} | " + " | ".join(cel(c, campo) for c in ordem) + " |")
    for t in TLS5:
        L.append(f"| Espera em {NOME[t].replace(chr(10), ' ')} (s/veículo) | " + " | ".join(cel(c, f'espera_{t}') for c in ordem) + " |")
    for t in TLS5:
        L.append(f"| Fila média em {NOME[t].replace(chr(10), ' ')} | " + " | ".join(cel(c, f'fila_{t}') for c in ordem) + " |")
    for t in TLS5:
        L.append(f"| Veículos que passaram por {NOME[t].replace(chr(10), ' ')} (por episódio) | "
                 + " | ".join(cel(c, f'veic_{t}') for c in ordem) + " |")
    linhas_soma = [("Viagens concluídas (mín.)", lambda e: f"{min(l['fracao_concluida'] for l in e):.3f}"),
                   ("Colisões totais", lambda e: str(sum(l["colisoes"] for l in e))),
                   ("Colisões nos 5 cruzamentos", lambda e: str(sum(l["colisoes_nos_5"] for l in e))),
                   ("Colisões nos controlados", lambda e: str(sum(l["colisoes_nos_controlados"] for l in e))),
                   ("Teletransportes", lambda e: str(sum(l["teleportes"] for l in e))),
                   ("Episódios travados/inválidos", lambda e: f"{sum(not l['valido'] for l in e)}/{len(e)}"),
                   ("Violações de segurança", lambda e: str(sum(l["violacoes"] for l in e))),
                   ("Semáforos não controlados fora do programa", lambda e: str(sum(l["outros_com_erro"] for l in e)))]
    for nome, f in linhas_soma:
        L.append(f"| {nome} | " + " | ".join(soma(c, f)[0] for c in ordem) + " |")

    # comparacoes pareadas por demanda (media dos 5 modelos em cada demanda)
    L += ["", "## Comparações pareadas por demanda (10 demandas; Δ = segundo − primeiro)", "",
          "| Métrica | C5 − C3 | IC95 | demandas em que C5 melhora | C5 − original | IC95 | C3 − original | IC95 |",
          "|---|---:|---:|---:|---:|---:|---:|---:|"]
    comps = {}
    for campo in ["corredor", "rede", "p95_corredor", "novos"] + [f"espera_{t}" for t in TLS5]:
        f = CAMPOS[campo][1]
        c3, c5, o = (resumo(pe, c, f)["por_demanda"] for c in ("C3", "C5", "original"))
        d53 = [b - a for a, b in zip(c3, c5) if a is not None and b is not None]
        d5o = [b - a for a, b in zip(o, c5) if a is not None and b is not None]
        d3o = [b - a for a, b in zip(o, c3) if a is not None and b is not None]
        (m1, h1), (m2, h2), (m3, h3) = ic95(d53), ic95(d5o), ic95(d3o)
        comps[campo] = {"C5-C3": [m1, h1, sum(x < 0 for x in d53)], "C5-original": [m2, h2], "C3-original": [m3, h3]}
        L.append(f"| {CAMPOS[campo][0]} | {m1:+.2f} | ±{h1:.2f} | {sum(x < 0 for x in d53)}/{len(d53)} | {m2:+.2f} | ±{h2:.2f} | "
                 f"{m3:+.2f} | ±{h3:.2f} |")
    # consistencia entre checkpoints
    L += ["", "## Consistência entre os 5 checkpoints (C5 − C3 no mesmo checkpoint, média das 10 demandas)", "",
          "| Checkpoint | corredor | rede | novos | Fiandeiras×Clodomiro | Fiandeiras×Atílio |", "|---|---:|---:|---:|---:|---:|"]
    for k, sm in enumerate(sorted({k.split("|")[1] for k in pe if "|" in k})):
        vals = []
        for campo in ("corredor", "rede", "novos", "espera_300058973", "espera_302806060"):
            f = CAMPOS[campo][1]
            a = matriz(pe, "C3", f)[k]
            b = matriz(pe, "C5", f)[k]
            vals.append(ms([y - x for x, y in zip(a, b) if x is not None and y is not None])[0])
        L.append(f"| C s{sm} | " + " | ".join(f"{v:+.2f}" for v in vals) + " |")
    (SAIDA / "tabela_c5.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (SAIDA / "comparacoes_c5.json").write_text(json.dumps(comps, indent=1), encoding="utf-8")
    print("\n".join(L))

    # grafico 1: Original x C3 x C3->C5 (+ diagnosticos)
    fig, axs = plt.subplots(1, 4, figsize=(18, 5.2), facecolor=SUP)
    for ax, campo in zip(axs, ("corredor", "rede", "p95_corredor", "novos")):
        for j, (c, rot, cor, hachura) in enumerate(CTRL):
            r = resumo(pe, c, CAMPOS[campo][1])
            err = r["dp_modelos"] if r["dp_modelos"] is not None else r["dp_demandas"]
            ax.bar(j, r["media"], 0.75, yerr=err, capsize=3, color=cor, hatch=hachura, edgecolor=SUP if not hachura else "#7a7a75",
                   linewidth=1.5, zorder=3, label=rot)
            ax.text(j, r["media"] + (err or 0) + 0.3, f"{r['media']:.1f}", ha="center", va="bottom", fontsize=8.5, color=TINTA)
        ax.set_xticks([])
        ax.set_title(CAMPOS[campo][0], color=TINTA, loc="left", fontsize=10)
        estilo(ax)
    axs[0].legend(fontsize=8, frameon=False, loc="lower left")
    fig.suptitle("Zero-shot C3 → C5: mesma Double DQN compartilhada (pesos congelados) controlando 3 ou 5 cruzamentos "
                 "— demanda intensa nova, sementes 291-300", color=TINTA, x=0.01, ha="left", fontsize=12)
    fig.text(0.01, 0.005, "RL: média de 5 checkpoints ± dp entre checkpoints; baselines: ± dp entre 10 demandas. "
             "Hachurado/cinza = diagnóstico clássico com as mesmas regras de segurança do RL.", color=TINTA2, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.93))
    fig.savefig(SAIDA / "c5_1_original_c3_c5.png", dpi=140, facecolor=SUP)
    plt.close(fig)

    # grafico 2: por cruzamento
    fig, axs = plt.subplots(2, 1, figsize=(14, 9), facecolor=SUP)
    for ax, (pref, titulo) in zip(axs, (("espera_", "Espera média por veículo em cada cruzamento (s)"),
                                       ("fila_", "Fila média em cada cruzamento (veículos parados até 100 m)"))):
        w = 0.8 / len(CTRL)
        for j, (c, rot, cor, hachura) in enumerate(CTRL):
            for i, t in enumerate(TLS5):
                r = resumo(pe, c, CAMPOS[pref + t][1])
                err = r["dp_modelos"] if r["dp_modelos"] is not None else r["dp_demandas"]
                x = i + (j - (len(CTRL) - 1) / 2) * w
                ax.bar(x, r["media"], w, yerr=err, capsize=2, color=cor, hatch=hachura, zorder=3,
                       edgecolor=SUP if not hachura else "#7a7a75", linewidth=1.2, label=rot if i == 0 else None)
        veic = [resumo(pe, "original", CAMPOS["veic_" + t][1])["media"] for t in TLS5]
        ax.set_xticks(range(len(TLS5)))
        ax.set_xticklabels([f"{NOME[t]}\n{t} · {v:.0f} veíc./episódio" for t, v in zip(TLS5, veic)], color=TINTA, fontsize=8.5)
        ax.axvline(2.5, color="#bdbdb8", lw=1, ls=":")
        ax.set_title(titulo, color=TINTA, loc="left", fontsize=11)
        estilo(ax)
    axs[0].legend(fontsize=8, frameon=False, ncol=3)
    fig.tight_layout()
    fig.savefig(SAIDA / "c5_2_por_cruzamento.png", dpi=140, facecolor=SUP)
    plt.close(fig)


if __name__ == "__main__":
    main()
