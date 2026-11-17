"""Graficos e tabelas da otimizacao final (so le resultados; nao simula).

uso (matplotlib funciona no `py` deste computador):
    py -B semaforo/integracao_insper/otimizacao_final/relatorio_otimizacao.py
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
ANTERIOR = AQUI.parent / "resultados" / "bateria_principal_20261116" / "treinos"
TLS = {"476455095": "Gomes de Carvalho", "40278305": "Casa do Ator", "40278183": "Quatá"}
SEM = ["1", "2", "3", "4", "5"]
ROT = {"baseline_original": "Original atuado (SUMO)",
       "baseline_atuado_eq_v10": "Atuado c/ regras RL (verde 10)",
       "baseline_atuado_eq_v5": "Atuado c/ regras RL (verde 5)",
       "baseline_max_pressure_v10": "Max-Pressure (fila só faixa imediata)",
       "A_v1": "A anterior (v1)", "B_v1": "B anterior (v1)",
       "A_col": "A: colisão atribuída", "A_col_v5": "A: col. atribuída + verde 5",
       "B_col_s30": "B: col. atribuída, sup 30 s", "B_col_s15": "B: col. atribuída, sup 15 s",
       "B_col_s10": "B: col. atribuída, sup 10 s",
       "B_col_v5_s30": "B: col.+verde 5, sup 30 s", "B_col_v5_s15": "B: col.+verde 5, sup 15 s",
       "B_col_v5_s10": "B: col.+verde 5, sup 10 s"}
COR = {"baseline_original": "#333333", "baseline_atuado_eq_v10": "#8c8c8c", "baseline_atuado_eq_v5": "#bdbdbd",
       "baseline_max_pressure_v10": "#e0e0e0"}
PALETA = ["#1f77b4", "#aec7e8", "#ff7f0e", "#2ca02c", "#d62728", "#ff9896", "#9467bd", "#8c564b", "#e377c2",
          "#17becf"]
T95 = {4: 2.776, 9: 2.262}


def ms(v):
    v = [x for x in v if x is not None]
    return (statistics.fmean(v), statistics.stdev(v) if len(v) > 1 else 0.0) if v else (None, None)


def ic95(dif):
    m, s = ms(dif)
    return m, T95.get(len(dif) - 1, 2.0) * s / math.sqrt(len(dif))


def carregar():
    teste = json.loads((RES / "teste_final" / "teste_final.json").read_text(encoding="utf-8"))
    val = {p.stem.replace("braco_", ""): json.loads(p.read_text(encoding="utf-8"))
           for p in (RES / "validacao").glob("braco_*.json")}
    base_val = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (RES / "validacao").glob("baseline_*.json")}
    return teste, val, base_val


def controladores(teste):
    ps = teste["por_semente"]
    bases = [k for k in ROT if k.startswith("baseline_") and k in ps]
    bracos = [k for k in ROT if not k.startswith("baseline_") and any(r.startswith(k + "|") for r in ps)]
    return bases, bracos


def valores(teste, nome, campo):
    """Matriz [semente_modelo][semente_trafego] (baseline: uma linha)."""
    ps = teste["por_semente"]
    f = (lambda x: campo(x)) if callable(campo) else (lambda x: x[campo])
    if nome.startswith("baseline_"):
        return [[f(x) if x["valido"] else None for x in ps[nome]]]
    return [[f(x) if x["valido"] else None for x in ps[f"{nome}|{s}"]] for s in SEM if f"{nome}|{s}" in ps]


def resumo_ctrl(teste, nome, campo):
    mat = valores(teste, nome, campo)
    por_modelo = [ms(l)[0] for l in mat]
    por_trafego = [ms([l[j] for l in mat])[0] for j in range(len(mat[0]))]
    media = ms(por_modelo if len(mat) > 1 else mat[0])[0]
    return {"media": media, "dp_sementes_modelo": ms(por_modelo)[1] if len(mat) > 1 else None,
            "dp_sementes_trafego": ms(por_trafego)[1], "por_trafego": por_trafego, "por_modelo": por_modelo}


def barras(teste, nomes, campos, arq, titulo):
    fig, axs = plt.subplots(1, len(campos), figsize=(7.5 * len(campos), 5.5))
    axs = axs if len(campos) > 1 else [axs]
    for ax, (rot, campo) in zip(axs, campos):
        res = [resumo_ctrl(teste, n, campo) for n in nomes]
        err = [r["dp_sementes_modelo"] if r["dp_sementes_modelo"] is not None else r["dp_sementes_trafego"] for r in res]
        cores = [COR.get(n, PALETA[i % len(PALETA)]) for i, n in enumerate(nomes)]
        y = range(len(nomes))
        ax.barh(list(y), [r["media"] for r in res], xerr=err, color=cores, capsize=4)
        ax.set_yticks(list(y))
        ax.set_yticklabels([ROT[n] for n in nomes])
        ax.invert_yaxis()
        for i, r in enumerate(res):
            ax.text(r["media"], i, f" {r['media']:.1f}", va="center", ha="left", fontsize=9)
        orig = res[nomes.index("baseline_original")]["media"] if "baseline_original" in nomes else None
        if orig:
            ax.axvline(orig, color="#333333", ls="--", lw=1)
        ax.set_title(rot)
        ax.grid(axis="x", alpha=0.3)
    fig.suptitle(titulo + "\nbarras de erro: dp entre 5 sementes de modelo (RL) ou entre 10 sementes de tráfego (baselines)")
    fig.tight_layout()
    fig.savefig(SAIDA / arq, dpi=130)
    plt.close(fig)


def grafico_validacao(val, base_val):
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for i, (b, d) in enumerate(sorted(val.items(), key=lambda kv: list(ROT).index(kv[0]))):
        eps = sorted({int(e) for s in d["tabela"].values() for e in s})
        m, sd = zip(*[ms([d["tabela"][s][str(e)]["espera_corredor_media"] for s in d["tabela"]]) for e in eps])
        ax.errorbar([e + (i - 3) * 0.8 for e in eps], m, yerr=sd, marker="o", capsize=3, label=ROT[b],
                    color=PALETA[list(ROT).index(b) % len(PALETA)])
    for nome, d in base_val.items():
        ax.axhline(d["resumo"]["espera_corredor_media"], color=COR.get(nome, "#999"), ls="--",
                   label=f"{ROT[nome]} ({d['resumo']['espera_corredor_media']:.1f} s)")
    ax.set_xlabel("checkpoint (episódio de treino)")
    ax.set_ylabel("espera média no corredor (s)")
    ax.set_title("Validação (sementes 221-225, cenário intenso): média ± dp entre 5 sementes de modelo")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(SAIDA / "3_validacao_evolucao.png", dpi=130)
    plt.close(fig)


def pareado(teste, a, b, campo="espera_corredor_media"):
    """b - a por semente de modelo (mesma inicializacao e demandas de treino), no teste final."""
    va, vb = resumo_ctrl(teste, a, campo)["por_modelo"], resumo_ctrl(teste, b, campo)["por_modelo"]
    dif = [y - x for x, y in zip(va, vb)]
    m, h = ic95(dif)
    return {"de": a, "para": b, "dif_media": m, "ic95": h, "melhor_em": sum(d < 0 for d in dif), "n": len(dif),
            "difs": dif}


def grafico_pareado(teste, pares, arq, titulo):
    fig, axs = plt.subplots(1, len(pares), figsize=(5 * len(pares), 4.8), sharey=True)
    axs = axs if len(pares) > 1 else [axs]
    for ax, (a, b) in zip(axs, pares):
        va = resumo_ctrl(teste, a, "espera_corredor_media")["por_modelo"]
        vb = resumo_ctrl(teste, b, "espera_corredor_media")["por_modelo"]
        for s, (x, y) in enumerate(zip(va, vb)):
            ax.plot([0, 1], [x, y], marker="o", color="#1f77b4" if y < x else "#d62728")
            ax.text(1.03, y, f"s{s + 1}", fontsize=8, va="center")
        p = pareado(teste, a, b)
        ax.set_xticks([0, 1])
        ax.set_xticklabels([ROT[a], ROT[b]], fontsize=8)
        ax.set_title(f"Δ = {p['dif_media']:+.2f} s (IC95 ±{p['ic95']:.2f}); melhor em {p['melhor_em']}/{p['n']}",
                     fontsize=9)
        ax.grid(alpha=0.3)
    axs[0].set_ylabel("espera média no corredor no teste (s)")
    fig.suptitle(titulo + " (pareado por semente de modelo; azul = melhorou)")
    fig.tight_layout()
    fig.savefig(SAIDA / arq, dpi=130)
    plt.close(fig)


def grafico_filas(teste, nomes):
    fig, ax = plt.subplots(figsize=(12, 5))
    w = 0.85 / len(nomes)
    for j, n in enumerate(nomes):
        vals = [resumo_ctrl(teste, n, lambda x, t=t: x["filas"][t]["media"]) for t in TLS]
        err = [v["dp_sementes_modelo"] if v["dp_sementes_modelo"] is not None else v["dp_sementes_trafego"] for v in vals]
        ax.bar([i + j * w for i in range(3)], [v["media"] for v in vals], w, yerr=err, capsize=2,
               color=COR.get(n, PALETA[j % len(PALETA)]), label=ROT[n])
    ax.set_xticks([i + w * (len(nomes) - 1) / 2 for i in range(3)])
    ax.set_xticklabels([f"{t}\n{n}" for t, n in TLS.items()])
    ax.set_ylabel("fila média (veículos parados até 100 m)")
    ax.set_title("Filas no teste final (sementes 241-250)")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(SAIDA / "6_teste_filas.png", dpi=130)
    plt.close(fig)


def grafico_treino(bracos):
    fig, axs = plt.subplots(1, 2, figsize=(15, 5))
    for i, b in enumerate(bracos):
        pastas = [(ANTERIOR / f"{'independente' if b == 'A_v1' else 'hierarquico'}_s{s}") if b.endswith("_v1")
                  else RES / "treinos" / f"{b}_s{s}" for s in SEM]
        hs = [[json.loads(l) for l in (p / "historico.jsonl").read_text(encoding="utf-8").splitlines()]
              for p in pastas if (p / "historico.jsonl").exists()]
        if not hs:
            continue
        n = min(len(h) for h in hs)
        for ax, f in ((axs[0], lambda x: x["espera_corredor_media"]), (axs[1], lambda x: sum(x["recompensas"][:3]))):
            serie = [statistics.fmean(f(h[e]) for h in hs) for e in range(n)]
            movel = [statistics.fmean(serie[max(0, e - 9):e + 1]) for e in range(n)]
            ax.plot(range(1, n + 1), movel, label=ROT[b], color=PALETA[list(ROT).index(b) % len(PALETA)])
    axs[0].set_title("Espera média no corredor nos episódios de treino (s)")
    axs[1].set_title("Recompensa dos 3 locais por episódio (inclui penalidades de colisão)")
    for ax in axs:
        ax.set_xlabel("episódio (média de 5 sementes, média móvel de 10)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(SAIDA / "7_treino_curvas.png", dpi=130)
    plt.close(fig)


def main():
    SAIDA.mkdir(exist_ok=True)
    teste, val, base_val = carregar()
    bases, bracos = controladores(teste)
    nomes = bases + bracos
    barras(teste, nomes, [("Espera média no corredor (s)", "espera_corredor_media"),
                          ("Espera média na rede inteira (s)", "espera_rede_media")],
           "1_teste_espera_media.png", "Teste final inédito: sementes 241-250, cenário intenso")
    barras(teste, nomes, [("P95 da espera no corredor (s)", "espera_corredor_p95"),
                          ("P95 da espera na rede (s)", "espera_rede_p95")],
           "2_teste_p95.png", "Teste final inédito: P95")
    grafico_validacao(val, base_val)
    sup = [(a, b) for a, b in (("B_col_s30", "B_col_s15"), ("B_col_s30", "B_col_s10"), ("B_col_v5_s30", "B_col_v5_s15"),
                               ("B_col_v5_s30", "B_col_v5_s10")) if a in bracos and b in bracos]
    if sup:
        grafico_pareado(teste, sup, "4_supervisor_30_vs_15.png", "Frequência do supervisor")
    efe = [(a, b) for a, b in (("A_v1", "A_col"), ("A_col", "A_col_v5"), ("A_v1", "B_v1")) if a in bracos and b in bracos]
    if efe:
        grafico_pareado(teste, efe, "5_efeito_recompensa_verde.png", "Efeito da recompensa e do verde mínimo")
    grafico_filas(teste, nomes)
    grafico_treino(bracos)
    # tabela consolidada
    campos = [("Espera média corredor (s)", "espera_corredor_media"), ("P95 corredor (s)", "espera_corredor_p95"),
              ("Espera média rede (s)", "espera_rede_media"), ("P95 rede (s)", "espera_rede_p95")]
    campos += [(f"Fila média {n}", lambda x, t=t: x["filas"][t]["media"]) for t, n in TLS.items()]
    campos += [(f"Fila máx. {n}", lambda x, t=t: x["filas"][t]["max"]) for t, n in TLS.items()]
    campos += [("Concluídas (%)", lambda x: 100 * x["fracao_concluida"]),
               ("Bloqueio saída (s)", "bloqueio_saida_corredor_s"),
               ("Entreverdes 3 TLS (s)", lambda x: sum(x["entreverdes_s"].values())),
               ("Trocas de fase 3 TLS", lambda x: sum(x["trocas"].values()) if x["trocas"] else None)]
    ps = teste["por_semente"]
    linhas = ["| Controlador | " + " | ".join(c for c, _ in campos) + " | Teleportes | Colisões (nos 3) | Violações | Inválidas |",
              "|---|" + "---:|" * (len(campos) + 4)]
    for n in nomes:
        cel = []
        for _, campo in campos:
            r = resumo_ctrl(teste, n, campo)
            if r["media"] is None:
                cel.append("—")
                continue
            dp = r["dp_sementes_modelo"] if r["dp_sementes_modelo"] is not None else r["dp_sementes_trafego"]
            cel.append(f"{r['media']:.2f} ± {dp:.2f}")
        chaves = [n] if n.startswith("baseline_") else [f"{n}|{s}" for s in SEM]
        eps = [x for c in chaves for x in ps.get(c, [])]
        cel += [str(sum(x["teleportes"] for x in eps)),
                f"{sum(x['colisoes'] for x in eps)} ({sum(x['colisoes_nos_controlados'] for x in eps)})",
                str(sum(x["violacoes"] for x in eps)), f"{sum(not x['valido'] for x in eps)}/{len(eps)}"]
        linhas.append(f"| {ROT[n]} | " + " | ".join(cel) + " |")
    # variabilidade por fonte e comparacoes
    var = ["| Controlador | Espera corredor | dp entre sementes de modelo | dp entre sementes de tráfego | vence o original em (sementes de tráfego) |",
           "|---|---:|---:|---:|---:|"]
    orig = resumo_ctrl(teste, "baseline_original", "espera_corredor_media")["por_trafego"]
    for n in nomes:
        r = resumo_ctrl(teste, n, "espera_corredor_media")
        vence = sum(x < o for x, o in zip(r["por_trafego"], orig))
        var.append(f"| {ROT[n]} | {r['media']:.2f} | {r['dp_sementes_modelo'] if r['dp_sementes_modelo'] is None else round(r['dp_sementes_modelo'], 2)} "
                   f"| {r['dp_sementes_trafego']:.2f} | {vence}/{len(orig)} |")
    comps = [(a, b) for a, b in (("A_v1", "A_col"), ("A_col", "A_col_v5"), ("A_v1", "B_v1"), ("A_col", "B_col_s30"),
                                 ("A_col", "B_col_s15"), ("B_v1", "B_col_s30"), ("B_v1", "B_col_s15"),
                                 ("B_col_s30", "B_col_s15"), ("B_col_s30", "B_col_s10"), ("A_col_v5", "B_col_v5_s30"),
                                 ("B_col_v5_s30", "B_col_v5_s15"), ("B_col_v5_s30", "B_col_v5_s10"),
                                 ("A_col_v5", "B_col_v5_s15"), ("A_v1", "A_col_v5"), ("B_v1", "B_col_v5_s15"))
             if a in bracos and b in bracos]
    pares = [pareado(teste, a, b) for a, b in comps]
    cmp_lin = ["| Comparação (B − A, pareada por semente de modelo) | Δ espera corredor (s) | IC95 | melhor em |",
               "|---|---:|---:|---:|"]
    cmp_lin += [f"| {ROT[p['para']]} − {ROT[p['de']]} | {p['dif_media']:+.2f} | ±{p['ic95']:.2f} | {p['melhor_em']}/{p['n']} |"
                for p in pares]
    # modelos vs baselines por semente de trafego (pareado por demanda)
    vs = ["| Controlador | Δ vs original atuado (s) | IC95 (10 demandas) | Δ vs atuado c/ regras RL (mesmo verde) | IC95 |",
          "|---|---:|---:|---:|---:|"]
    for n in bracos:
        r = resumo_ctrl(teste, n, "espera_corredor_media")["por_trafego"]
        d1 = [x - o for x, o in zip(r, orig)]
        m1, h1 = ic95(d1)
        v = 5 if "v5" in n else 10
        eq = resumo_ctrl(teste, f"baseline_atuado_eq_v{v}", "espera_corredor_media")["por_trafego"]
        m2, h2 = ic95([x - o for x, o in zip(r, eq)])
        vs.append(f"| {ROT[n]} | {m1:+.2f} | ±{h1:.2f} | {m2:+.2f} (verde {v}) | ±{h2:.2f} |")
    texto = ("# Teste final inédito (sementes 241-250, cenário intenso)\n\n"
             "RL: média das 5 sementes de modelo (cada uma = média das 10 demandas); ± dp entre sementes de modelo. "
             "Baselines: média ± dp entre as 10 demandas. Só avaliações válidas entram nas médias.\n\n"
             + "\n".join(linhas) + "\n\n## Variabilidade e vitórias por demanda\n\n" + "\n".join(var)
             + "\n\n## Comparações pareadas entre configurações\n\n" + "\n".join(cmp_lin)
             + "\n\n## RL contra baselines, pareado por demanda (média dos 5 modelos em cada demanda)\n\n" + "\n".join(vs) + "\n")
    (SAIDA / "tabela_final.md").write_text(texto, encoding="utf-8")
    (SAIDA / "comparacoes.json").write_text(json.dumps(pares, indent=1, ensure_ascii=False), encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()
