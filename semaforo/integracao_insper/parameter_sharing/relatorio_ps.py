"""Graficos e tabelas do Modelo C (Parameter Sharing). So le resultados; nao simula.

uso (matplotlib do `py` 3.14 deste computador): py -B -X utf8 semaforo/integracao_insper/parameter_sharing/relatorio_ps.py
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
OTIM = AQUI.parent / "otimizacao_final" / "resultados"
SAIDA = RES / "relatorio"
NIVEIS = [("moderado_ps_teste", "Moderada\n(1200 veíc/h, 261-270)"), ("intenso_ps_teste", "Intensa não vista\n(2000 veíc/h, 251-260)"),
          ("saturado_ps_teste", "Saturada\n(2400 veíc/h, 271-280)")]
CTRL = [("original", "Original atuado (SUMO)", "#4a4a48"), ("atuado_eq_v10", "Atuado c/ regras do RL", "#b5b5b0"),
        ("A_col", "A: independentes", "#2a78d6"), ("B_col_s15", "B: hierárquico (sup 15 s)", "#eda100"),
        ("C", "C: parameter sharing", "#1baf7a"), ("C_transf", "C transf.: Casa do Ator fora do treino", "#eb6834")]
COR = {k: c for k, _, c in CTRL}
ROT = {k: r for k, r, _ in CTRL}
TLS = {"476455095": "Gomes de Carvalho", "40278305": "Casa do Ator (fora do treino no C transf.)", "40278183": "Quatá"}
T95 = {4: 2.776, 9: 2.262}
TINTA, TINTA2, SUP = "#1f1f1e", "#5f5f5c", "#fcfcfb"


def ms(v):
    v = [x for x in v if x is not None and not (isinstance(x, float) and math.isnan(x))]
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


def series(ps, nivel, ctrl, campo):
    """Matriz [modelo][demanda] so com episodios validos (None nos invalidos)."""
    f = campo if callable(campo) else (lambda x: x[campo])
    if f"{nivel}|{ctrl}" in ps:
        return [[f(x) if x["valido"] else None for x in ps[f"{nivel}|{ctrl}"]]]
    return [[f(x) if x["valido"] else None for x in ps[k]] for k in sorted(ps) if k.startswith(f"{nivel}|{ctrl}|")]


def resumo(ps, nivel, ctrl, campo):
    mat = series(ps, nivel, ctrl, campo)
    if not mat:
        return None
    por_modelo = [ms(l)[0] for l in mat]
    por_demanda = [ms([l[j] for l in mat])[0] for j in range(len(mat[0]))]
    return {"media": ms(por_modelo)[0] if len(mat) > 1 else ms(mat[0])[0],
            "dp_modelos": ms(por_modelo)[1] if len(mat) > 1 else None, "dp_demandas": ms(por_demanda)[1],
            "por_modelo": por_modelo, "por_demanda": por_demanda,
            "invalidos": sum(x is None for l in mat for x in l), "n": sum(len(l) for l in mat)}


def main():
    SAIDA.mkdir(exist_ok=True)
    teste = json.loads((RES / "teste_generalizacao" / "teste_generalizacao.json").read_text(encoding="utf-8"))
    ps = teste["por_semente"]
    val = {b: json.loads((RES / "validacao" / f"braco_{b}.json").read_text(encoding="utf-8")) for b in ("C", "C_transf")}
    val["A_col"] = json.loads((OTIM / "validacao" / "braco_A_col.json").read_text(encoding="utf-8"))
    val["B_col_s15"] = json.loads((OTIM / "validacao" / "braco_B_col_s15.json").read_text(encoding="utf-8"))
    orig_val = json.loads((OTIM / "validacao" / "baseline_original.json").read_text(encoding="utf-8"))["resumo"]
    atu_val = json.loads((OTIM / "validacao" / "baseline_atuado_eq_v10.json").read_text(encoding="utf-8"))["resumo"]

    # 1. eficiencia do aprendizado: validacao por checkpoint e curvas de treino
    fig, axs = plt.subplots(1, 2, figsize=(15, 5.4), facecolor=SUP)
    for b in ("A_col", "B_col_s15", "C", "C_transf"):
        tab = val[b]["tabela"]
        eps = sorted({int(e) for s in tab.values() for e in s})
        m, sd = zip(*[ms([tab[s][str(e)]["espera_corredor_media"] for s in tab]) for e in eps])
        axs[0].errorbar(eps, m, yerr=sd, marker="o", markersize=5, capsize=3, lw=2, color=COR[b], label=ROT[b])
    for nome, r, cor in (("Original atuado", orig_val, COR["original"]), ("Atuado c/ regras do RL", atu_val, COR["atuado_eq_v10"])):
        axs[0].axhline(r["espera_corredor_media"], color=cor, ls="--", lw=1.2, label=f"{nome} ({r['espera_corredor_media']:.1f} s)")
    axs[0].set_xlabel("checkpoint (episódio de treino)", color=TINTA2)
    axs[0].set_title("Validação (sementes 221-225): espera média no corredor (s)\nmédia ± dp entre 5 sementes de modelo",
                     color=TINTA, loc="left", fontsize=11)
    pastas = {"A_col": [OTIM / "treinos" / f"A_col_s{s}" for s in range(1, 6)],
              "C": [RES / "treinos" / f"C_s{s}" for s in range(1, 6)],
              "C_transf": [RES / "treinos" / f"C_transf_s{s}" for s in range(1, 6)]}
    for b, ps_ in pastas.items():
        hs = [[json.loads(l) for l in (p / "historico.jsonl").read_text(encoding="utf-8").splitlines()] for p in ps_]
        n = min(len(h) for h in hs)
        serie = [statistics.fmean(h[e]["espera_corredor_media"] for h in hs) for e in range(n)]
        movel = [statistics.fmean(serie[max(0, e - 9):e + 1]) for e in range(n)]
        axs[1].plot(range(1, n + 1), movel, lw=2, color=COR[b], label=ROT[b])
    axs[1].set_xlabel("episódio de treino (média de 5 sementes; média móvel de 10)", color=TINTA2)
    axs[1].set_title("Treino: espera média no corredor por episódio (s)\n(inclui exploração)", color=TINTA, loc="left", fontsize=11)
    for ax in axs:
        estilo(ax)
        ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(SAIDA / "ps_1_eficiencia_aprendizado.png", dpi=140, facecolor=SUP)
    plt.close(fig)

    # 2. generalizacao: espera no corredor por nivel de demanda
    fig, axs = plt.subplots(1, 2, figsize=(15, 5.6), facecolor=SUP)
    for ax, (campo, titulo) in zip(axs, [("espera_corredor_media", "Espera média no corredor (s)"),
                                         ("espera_corredor_p95", "P95 da espera no corredor (s)")]):
        ctrls = ["original", "atuado_eq_v10", "A_col", "B_col_s15", "C", "C_transf"]
        w = 0.8 / len(ctrls)
        for j, c in enumerate(ctrls):
            for i, (nivel, _) in enumerate(NIVEIS):
                r = resumo(ps, nivel, c, campo)
                if r is None:
                    continue
                err = r["dp_modelos"] if r["dp_modelos"] is not None else r["dp_demandas"]
                x = i + (j - (len(ctrls) - 1) / 2) * w
                ax.bar(x, r["media"], w, yerr=err, capsize=2, color=COR[c], edgecolor=SUP, linewidth=1.5, zorder=3,
                       label=ROT[c] if i == 1 or (c not in ("B_col_s15", "C_transf") and i == 0) else None)
                if c in ("original", "C"):
                    ax.text(x, r["media"] + (err or 0) + 0.5, f"{r['media']:.1f}", ha="center", va="bottom", fontsize=7.5,
                            color=TINTA)
                if r["invalidos"]:
                    ax.text(x, 1, f"{r['invalidos']} inv.", ha="center", va="bottom", fontsize=7, color=TINTA, rotation=90)
        ax.set_xticks(range(len(NIVEIS)))
        ax.set_xticklabels([n for _, n in NIVEIS], color=TINTA)
        ax.set_title(titulo, color=TINTA, loc="left", fontsize=11)
        estilo(ax)
    handles, labels = axs[0].get_legend_handles_labels()
    h2, l2 = axs[1].get_legend_handles_labels()
    vis = dict(zip(labels + l2, handles + h2))
    axs[0].legend(vis.values(), vis.keys(), fontsize=8, frameon=False, loc="upper left")
    fig.suptitle("Generalização com pesos congelados: demandas nunca usadas em treino ou seleção (10 sementes por nível)",
                 color=TINTA, x=0.01, ha="left", fontsize=12)
    fig.text(0.01, 0.005, "RL: média de 5 modelos ± dp entre modelos; baselines: ± dp entre demandas. Só episódios válidos entram "
             "nas médias; 'inv.' = episódios inválidos (travamento/não concluídos). B e C transf. só na demanda intensa.",
             color=TINTA2, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    fig.savefig(SAIDA / "ps_2_generalizacao_demandas.png", dpi=140, facecolor=SUP)
    plt.close(fig)

    # 3. transferencia: fila media por cruzamento na demanda intensa nao vista
    fig, ax = plt.subplots(figsize=(12, 5), facecolor=SUP)
    ctrls = ["original", "atuado_eq_v10", "A_col", "C", "C_transf"]
    w = 0.8 / len(ctrls)
    for j, c in enumerate(ctrls):
        for i, t in enumerate(TLS):
            r = resumo(ps, "intenso_ps_teste", c, lambda x, t=t: x["filas"][t]["media"])
            err = r["dp_modelos"] if r["dp_modelos"] is not None else r["dp_demandas"]
            x = i + (j - (len(ctrls) - 1) / 2) * w
            ax.bar(x, r["media"], w, yerr=err, capsize=2, color=COR[c], edgecolor=SUP, linewidth=1.5, zorder=3,
                   label=ROT[c] if i == 0 else None)
            ax.text(x, r["media"] + (err or 0) + 0.05, f"{r['media']:.2f}", ha="center", va="bottom", fontsize=7.5, color=TINTA)
    ax.set_xticks(range(3))
    ax.set_xticklabels(list(TLS.values()), color=TINTA)
    ax.set_title("Transferência: fila média por cruzamento (veículos parados até 100 m), demanda intensa não vista 251-260",
                 color=TINTA, loc="left", fontsize=11)
    estilo(ax)
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(SAIDA / "ps_3_transferencia.png", dpi=140, facecolor=SUP)
    plt.close(fig)

    # tabelas
    campos = [("Espera corredor (s)", "espera_corredor_media"), ("P95 corredor (s)", "espera_corredor_p95"),
              ("Espera rede (s)", "espera_rede_media"), ("Bloqueio saída (s)", "bloqueio_saida_corredor_s")]
    linhas = ["# Modelo C (Parameter Sharing): testes de generalização com pesos congelados", "",
              "RL: média de 5 modelos ± dp entre modelos (cada modelo = média das demandas válidas). Baselines: ± dp entre "
              "demandas. Inválidos = episódios com travamento ou < 95% das viagens concluídas (fora das médias).", ""]
    comparacoes = {}
    for nivel, rot in NIVEIS:
        linhas += [f"## {rot.replace(chr(10), ' ')}", "",
                   "| Controlador | " + " | ".join(c for c, _ in campos) + " | Concluídas mín. | Teleportes | Colisões (nos 3) | Violações | Inválidos |",
                   "|---|" + "---:|" * (len(campos) + 5)]
        for c, nome, _ in CTRL:
            if resumo(ps, nivel, c, "espera_corredor_media") is None:
                continue
            cel = []
            for _, campo in campos:
                r = resumo(ps, nivel, c, campo)
                dp = r["dp_modelos"] if r["dp_modelos"] is not None else r["dp_demandas"]
                cel.append(f"{r['media']:.2f} ± {dp:.2f}" if r["media"] is not None else "—")
            chaves = [k for k in ps if k == f"{nivel}|{c}" or k.startswith(f"{nivel}|{c}|")]
            eps = [x for k in chaves for x in ps[k]]
            cel += [f"{min(x['fracao_concluida'] for x in eps):.3f}", str(sum(x["teleportes"] for x in eps)),
                    f"{sum(x['colisoes'] for x in eps)} ({sum(x['colisoes_nos_controlados'] for x in eps)})",
                    str(sum(x["violacoes"] for x in eps)), f"{sum(not x['valido'] for x in eps)}/{len(eps)}"]
            linhas.append(f"| {nome} | " + " | ".join(cel) + " |")
        # pareado por demanda (media dos modelos em cada demanda)
        orig = resumo(ps, nivel, "original", "espera_corredor_media")["por_demanda"]
        a = resumo(ps, nivel, "A_col", "espera_corredor_media")
        linhas += ["", "| Comparação pareada por demanda (Δ espera corredor, s) | Δ médio | IC95 | demandas em que melhora |",
                   "|---|---:|---:|---:|"]
        for c in ("C", "C_transf", "B_col_s15"):
            r = resumo(ps, nivel, c, "espera_corredor_media")
            if r is None:
                continue
            for base_nome, base in (("A independentes", a["por_demanda"]), ("original atuado", orig)):
                d = [x - y for x, y in zip(r["por_demanda"], base) if x is not None and y is not None]
                m, h = ic95(d)
                comparacoes[f"{nivel}|{c}-{base_nome}"] = {"dif": m, "ic95": h, "melhora_em": sum(x < 0 for x in d), "n": len(d)}
                linhas.append(f"| {ROT[c]} − {base_nome} | {m:+.2f} | ±{h:.2f} | {sum(x < 0 for x in d)}/{len(d)} |")
        linhas.append("")
    # transferencia
    linhas += ["## Transferência (demanda intensa não vista): fila média por cruzamento", "",
               "| Controlador | " + " | ".join(TLS.values()) + " |", "|---|---:|---:|---:|"]
    for c in ("original", "atuado_eq_v10", "A_col", "C", "C_transf"):
        cel = []
        for t in TLS:
            r = resumo(ps, "intenso_ps_teste", c, lambda x, t=t: x["filas"][t]["media"])
            dp = r["dp_modelos"] if r["dp_modelos"] is not None else r["dp_demandas"]
            cel.append(f"{r['media']:.2f} ± {dp:.2f}")
        linhas.append(f"| {ROT[c]} | " + " | ".join(cel) + " |")
    # validacao
    linhas += ["", "## Validação (sementes 221-225; checkpoints escolhidos só aqui)", "",
               "| Braço | s1 | s2 | s3 | s4 | s5 | média ± dp |", "|---|---|---|---|---|---|---|"]
    for b in ("A_col", "B_col_s15", "C", "C_transf"):
        sel = val[b]["selecao"]
        v = [sel[str(s)]["validacao"]["espera_corredor_media"] for s in range(1, 6)]
        linhas.append(f"| {ROT[b]} | " + " | ".join(f"{sel[str(s)]['validacao']['espera_corredor_media']:.2f} "
                                                      f"(ep{sel[str(s)]['episodio']})" for s in range(1, 6))
                      + f" | {statistics.fmean(v):.2f} ± {statistics.stdev(v):.2f} |")
    (SAIDA / "tabela_ps.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    (SAIDA / "comparacoes_ps.json").write_text(json.dumps(comparacoes, indent=1, ensure_ascii=False), encoding="utf-8")
    print("\n".join(linhas))


if __name__ == "__main__":
    main()
