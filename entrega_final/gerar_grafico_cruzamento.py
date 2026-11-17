"""Grafico unico da Etapa A (cruzamento sintetico, dinamica C corrigida): geracoes A/B/C da DQN
contra Webster e o teto Max-Pressure, espera media e P95 por cenario. So le
semaforo/resultados/comparacao_17_C/resumo.json; nao simula.

uso (na raiz do repositorio; precisa de matplotlib): python -B entrega_final/gerar_grafico_cruzamento.py
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
FONTE = RAIZ / "semaforo" / "resultados" / "comparacao_17_C" / "resumo.json"
SAIDA = Path(__file__).resolve().parent / "graficos" / "A1_cruzamento_geracoes_dqn.png"
CENARIOS = ["equilibrado", "assimetrico", "pico", "saturado", "girado"]
ROTULO_CEN = ["equilibrado", "assimétrico", "pico", "saturado", "girado\n(nunca visto)"]
SERIES = [  # (chave no resumo.json, rotulo, cor) - referencias em cinza, geracoes em ordem categorica fixa
    ("Webster", "Tempo fixo (Webster)", "#8c8c8c"),
    ("Max-Pressure teto (recal. C)", "Max-Pressure teto por cenário", "#c4c4c4"),
    ("A: fila, 13 entradas", "DQN geração A (fila, 13 entradas)", "#2a78d6"),
    ("B: fila_excesso, 13 entradas", "DQN geração B (fila+excesso, 13)", "#eb6834"),
    ("C: fila_excesso, 17 entradas", "DQN geração C (fila+excesso, 17)", "#1baf7a"),
]
TINTA, TINTA_2, SUPERFICIE = "#1f1f1e", "#5f5f5c", "#fcfcfb"


def main():
    r = json.loads(FONTE.read_text(encoding="utf-8"))["resumo"]
    fig, eixos = plt.subplots(1, 2, figsize=(15, 5.6), facecolor=SUPERFICIE)
    largura = 0.16
    for ax, (campo, titulo) in zip(eixos, [("espera_media", "Espera média (s)"), ("espera_p95", "P95 da espera (s)")]):
        ax.set_facecolor(SUPERFICIE)
        for j, (chave, rotulo, cor) in enumerate(SERIES):
            xs = [i + (j - 2) * largura for i in range(len(CENARIOS))]
            ys = [r[f"{c}|{chave}"][campo]["media"] for c in CENARIOS]
            ax.bar(xs, ys, largura, color=cor, edgecolor=SUPERFICIE, linewidth=2, label=rotulo, zorder=3)
            if j == len(SERIES) - 1:  # rotulo direto so na geracao C (a final)
                for x, y in zip(xs, ys):
                    ax.text(x, y + 1, f"{y:.0f}", ha="center", va="bottom", fontsize=8, color=TINTA)
        ax.set_xticks(range(len(CENARIOS)))
        ax.set_xticklabels(ROTULO_CEN, color=TINTA)
        ax.set_title(titulo, color=TINTA, loc="left", fontsize=12)
        ax.grid(axis="y", color="#e6e6e3", linewidth=0.8, zorder=0)
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)
        for lado in ("left", "bottom"):
            ax.spines[lado].set_color("#bdbdb8")
        ax.tick_params(colors=TINTA_2)
    eixos[0].legend(loc="upper left", fontsize=8.5, frameon=False, labelcolor=TINTA)
    fig.suptitle("Cruzamento sintético (SUMO, dinâmica corrigida C): DQN contra controladores tradicionais",
                 color=TINTA, x=0.01, ha="left", fontsize=13)
    fig.text(0.01, 0.005, "Média de 10 sementes de teste (1-10); cada geração = média de 3 redes. Menor é melhor. "
             "Fonte: semaforo/resultados/comparacao_17_C/resumo.json", color=TINTA_2, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SAIDA, dpi=150, facecolor=SUPERFICIE)
    print(SAIDA.relative_to(RAIZ).as_posix())


if __name__ == "__main__":
    main()
