"""Graficos e tabela consolidada da bateria principal do Multi-Agent Insper.

So le os arquivos da bateria (historico, validacao, teste); nao simula nada.
uso (precisa de matplotlib; no Windows deste projeto use o `py`):
    py -B semaforo/integracao_insper/relatorio_marl_insper.py
"""

import json
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

AQUI = Path(__file__).resolve().parent
BATERIA = AQUI / "resultados" / "bateria_principal_20261116"
SAIDA = BATERIA / "relatorio"
MODELOS = {"independente": "Independente (A)", "hierarquico": "Hierárquico (B)"}
SEMENTES = [1, 2, 3, 4, 5]
TLS = {"476455095": "Gomes de Carvalho", "40278305": "Casa do Ator", "40278183": "Quatá"}
CORES = {"original": "#555555", "max_pressure": "#999999", "independente": "#1f77b4", "hierarquico": "#d62728"}


def m_sd(v):
    v = [x for x in v if x is not None]
    if not v:
        return None, None
    return statistics.fmean(v), (statistics.stdev(v) if len(v) > 1 else 0.0)


def movel(v, k=10):
    return [statistics.fmean(v[max(0, i - k + 1):i + 1]) for i in range(len(v))]


def historicos():
    h = {}
    for m in MODELOS:
        for s in SEMENTES:
            p = BATERIA / "treinos" / f"{m}_s{s}" / "historico.jsonl"
            if p.exists():
                h[(m, s)] = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()]
    return h


def grafico_treino(h):
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.5))
    for m, nome in MODELOS.items():
        series_loc = [movel([sum(x["recompensas"][:3]) for x in h[(m, s)]]) for s in SEMENTES if (m, s) in h]
        series_esp = [movel([x["espera_corredor_media"] for x in h[(m, s)]]) for s in SEMENTES if (m, s) in h]
        for a, series in ((ax[0], series_loc), (ax[2], series_esp)):
            n = min(len(x) for x in series)
            med = [statistics.fmean(x[i] for x in series) for i in range(n)]
            sd = [statistics.stdev([x[i] for x in series]) if len(series) > 1 else 0 for i in range(n)]
            eps = range(1, n + 1)
            a.plot(eps, med, color=CORES[m], label=nome)
            a.fill_between(eps, [a_ - b for a_, b in zip(med, sd)], [a_ + b for a_, b in zip(med, sd)],
                           color=CORES[m], alpha=0.2)
    series_sup = [movel([x["recompensas"][3] for x in h[("hierarquico", s)]]) for s in SEMENTES if ("hierarquico", s) in h]
    if series_sup:
        n = min(len(x) for x in series_sup)
        med = [statistics.fmean(x[i] for x in series_sup) for i in range(n)]
        sd = [statistics.stdev([x[i] for x in series_sup]) if len(series_sup) > 1 else 0 for i in range(n)]
        ax[1].plot(range(1, n + 1), med, color=CORES["hierarquico"], label="Supervisor (B)")
        ax[1].fill_between(range(1, n + 1), [a - b for a, b in zip(med, sd)], [a + b for a, b in zip(med, sd)],
                           color=CORES["hierarquico"], alpha=0.2)
    ax[0].set_title("Recompensa dos 3 agentes locais (soma)\nB inclui o termo de prioridade: escalas não comparáveis")
    ax[1].set_title("Recompensa do supervisor (B)")
    ax[2].set_title("Espera média no corredor nos episódios de treino (s)")
    for a in ax:
        a.set_xlabel("episódio (média móvel de 10; faixa = ±1 dp entre 5 sementes)")
        a.legend()
        a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(SAIDA / "1_treino_recompensas.png", dpi=120)
    plt.close(fig)


def grafico_validacao(val):
    tab = val["tabela"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ref = tab["original"]["espera_corredor_media"]
    ax.axhline(ref, color=CORES["original"], ls="--", label=f"Programa original ({ref:.1f} s)")
    for m, nome in MODELOS.items():
        eps = sorted({int(k.split("_ep")[1]) for k in tab if k.startswith(m + "_s")})
        med, sd = zip(*[m_sd([tab[f"{m}_s{s}_ep{e:04d}"]["espera_corredor_media"] for s in SEMENTES
                              if f"{m}_s{s}_ep{e:04d}" in tab]) for e in eps])
        ax.errorbar(eps, med, yerr=sd, color=CORES[m], marker="o", capsize=4, label=nome)
    ax.set_xlabel("checkpoint (episódio de treino)")
    ax.set_ylabel("espera média no corredor (s)")
    ax.set_title("Validação (sementes 221-223): média ± dp entre 5 sementes de treino")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(SAIDA / "2_validacao_checkpoints.png", dpi=120)
    plt.close(fig)


def agregados_teste(teste):
    """Por controlador: lista de medias por 'unidade' (semente de treino para modelos, semente de trafego para baselines)."""
    ps = teste["por_semente"]
    out = {}
    for base in ("original", "max_pressure"):
        if base in ps:
            out[base] = [[x] for x in ps[base] if x["valido"]]
    for m in MODELOS:
        out[m] = [[x for x in ps[f"{m}_s{s}"] if x["valido"]] for s in SEMENTES if f"{m}_s{s}" in ps]
    return out


def valor(grupos, f):
    medias = [statistics.fmean(f(x) for x in g) for g in grupos if g]
    return m_sd(medias)


def grafico_barras(ag, nome_arq, titulo, campos):
    fig, ax = plt.subplots(1, len(campos), figsize=(6 * len(campos), 4.5))
    ax = ax if len(campos) > 1 else [ax]
    rot = {"original": "Original", "max_pressure": "Max-Pressure", **MODELOS}
    for a, (rotulo, f) in zip(ax, campos):
        nomes = [k for k in ("original", "max_pressure", "independente", "hierarquico") if k in ag]
        vals = [valor(ag[k], f) for k in nomes]
        a.bar([rot[k] for k in nomes], [v[0] for v in vals], yerr=[v[1] for v in vals], capsize=5,
              color=[CORES[k] for k in nomes])
        for i, v in enumerate(vals):
            a.text(i, v[0], f"{v[0]:.1f}", ha="center", va="bottom")
        a.set_title(rotulo)
        a.grid(axis="y", alpha=0.3)
    fig.suptitle(titulo)
    fig.tight_layout()
    fig.savefig(SAIDA / nome_arq, dpi=120)
    plt.close(fig)


def grafico_filas(ag):
    fig, ax = plt.subplots(figsize=(10, 4.5))
    nomes = [k for k in ("original", "max_pressure", "independente", "hierarquico") if k in ag]
    rot = {"original": "Original", "max_pressure": "Max-Pressure", **MODELOS}
    w = 0.8 / len(nomes)
    for j, k in enumerate(nomes):
        vals = [valor(ag[k], lambda x, t=t: x["filas"][t]["media"]) for t in TLS]
        ax.bar([i + j * w for i in range(3)], [v[0] for v in vals], w, yerr=[v[1] for v in vals], capsize=3,
               color=CORES[k], label=rot[k])
    ax.set_xticks([i + w * (len(nomes) - 1) / 2 for i in range(3)])
    ax.set_xticklabels([f"{t}\n{n}" for t, n in TLS.items()])
    ax.set_ylabel("fila média (veículos parados até 100 m)")
    ax.set_title("Filas no teste final (sementes 231-235)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(SAIDA / "5_teste_filas.png", dpi=120)
    plt.close(fig)


def main():
    SAIDA.mkdir(exist_ok=True)
    h = historicos()
    val = json.loads((BATERIA / "validacao" / "validacao.json").read_text(encoding="utf-8"))
    teste = json.loads((BATERIA / "teste_final" / "teste.json").read_text(encoding="utf-8"))
    grafico_treino(h)
    grafico_validacao(val)
    ag = agregados_teste(teste)
    grafico_barras(ag, "3_teste_espera_media.png", "Espera média no teste final (média ± dp)",
                   [("Corredor (s)", lambda x: x["espera_corredor_media"]),
                    ("Rede inteira (s)", lambda x: x["espera_rede_media"])])
    grafico_barras(ag, "4_teste_p95.png", "P95 da espera no teste final (média ± dp)",
                   [("Corredor (s)", lambda x: x["espera_corredor_p95"]),
                    ("Rede inteira (s)", lambda x: x["espera_rede_p95"])])
    grafico_filas(ag)
    # tabela consolidada
    campos = [("Espera média no corredor (s)", lambda x: x["espera_corredor_media"]),
              ("P95 corredor (s)", lambda x: x["espera_corredor_p95"]),
              ("Espera média na rede (s)", lambda x: x["espera_rede_media"]),
              ("P95 rede (s)", lambda x: x["espera_rede_p95"])]
    campos += [(f"Fila média {n}", lambda x, t=t: x["filas"][t]["media"]) for t, n in TLS.items()]
    campos += [(f"Fila máx. {n}", lambda x, t=t: x["filas"][t]["max"]) for t, n in TLS.items()]
    campos += [("Viagens concluídas (%)", lambda x: 100 * x["fracao_concluida"]),
               ("Bloqueio da saída (s)", lambda x: x["bloqueio_saida_corredor_s"])]
    rot = {"original": "Original", "max_pressure": "Max-Pressure", **MODELOS}
    nomes = [k for k in ("original", "max_pressure", "independente", "hierarquico") if k in ag]
    linhas = ["| Métrica | " + " | ".join(rot[k] for k in nomes) + " |", "|---|" + "---:|" * len(nomes)]
    for rotulo, f in campos:
        cel = []
        for k in nomes:
            mu, sd = valor(ag[k], f)
            cel.append(f"{mu:.2f} ± {sd:.2f}" if mu is not None else "—")
        linhas.append(f"| {rotulo} | " + " | ".join(cel) + " |")
    ps = teste["por_semente"]
    def soma(chaves, campo):
        return sum(x[campo] for c in chaves for x in ps.get(c, []))
    grupos = {"original": ["original"], "max_pressure": ["max_pressure"],
              **{m: [f"{m}_s{s}" for s in SEMENTES] for m in MODELOS}}
    for rotulo, campo in (("Teletransportes (total)", "teleportes"), ("Colisões (total)", "colisoes"),
                          ("Colisões nos controlados", "colisoes_nos_controlados"),
                          ("Violações de segurança", "violacoes")):
        linhas.append(f"| {rotulo} | " + " | ".join(str(soma(grupos[k], campo)) for k in nomes) + " |")
    linhas.append("| Avaliações inválidas | " + " | ".join(
        str(sum(not x["valido"] for c in grupos[k] for x in ps.get(c, []))) + f"/{sum(len(ps.get(c, [])) for c in grupos[k])}"
        for k in nomes) + " |")
    # comparacao pareada B - A por semente de treino (mesmas demandas de teste)
    pares = []
    for s in SEMENTES:
        a, b = ps.get(f"independente_s{s}"), ps.get(f"hierarquico_s{s}")
        if a and b:
            va = [x["espera_corredor_media"] for x in a if x["valido"]]
            vb = [x["espera_corredor_media"] for x in b if x["valido"]]
            if va and vb:
                pares.append({"semente": s, "independente": round(statistics.fmean(va), 2),
                              "hierarquico": round(statistics.fmean(vb), 2),
                              "diferenca_B_menos_A": round(statistics.fmean(vb) - statistics.fmean(va), 2)})
    treino = {f"{m}_s{s}": {"episodios": len(h[(m, s)]), "invalidos": sum(not x["valido"] for x in h[(m, s)]),
                            "motivos": sorted({x["motivo_invalido"] for x in h[(m, s)] if not x["valido"]}),
                            "teleportes": sum(x["teleportes"] for x in h[(m, s)]),
                            "colisoes": sum(x["colisoes"] for x in h[(m, s)]),
                            "duracao_total_s": round(sum(x["duracao_real_s"] for x in h[(m, s)]), 1)}
              for (m, s) in h}
    (SAIDA / "tabela_final.md").write_text(
        "# Teste final: sementes 231-235 (cenario intenso)\n\n"
        "Modelos: média ± dp entre 5 sementes de treino (cada uma = média das 5 sementes de teste). "
        "Original e Max-Pressure: média ± dp entre as 5 sementes de teste. Só episódios válidos entram nas médias.\n\n"
        + "\n".join(linhas) + "\n\n## Hierárquico − independente, pareado por semente de treino (espera no corredor, s)\n\n"
        + "\n".join(f"- semente {p['semente']}: A {p['independente']} | B {p['hierarquico']} | B−A {p['diferenca_B_menos_A']:+.2f}"
                    for p in pares) + "\n", encoding="utf-8")
    (SAIDA / "resumo.json").write_text(json.dumps({"treino": treino, "pareado_B_menos_A": pares,
                                                   "selecao": val["selecao"]}, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    print("\n".join(linhas))
    print(json.dumps(pares, indent=1))


if __name__ == "__main__":
    main()
