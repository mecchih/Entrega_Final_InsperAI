"""
Avalia os controladores (sem retreinar nada) em tres dinamicas do simulador:

  A. original                              (a do treino e de avaliacao_final.json)
  B. original + verde maximo de 60 s       (regra de seguranca)
  C. transicao corrigida + verde maximo    (3 s amarelo + 2 s vermelho de verdade)

As DQNs foram treinadas na dinamica A. Em B e C elas rodam fora da dinamica
de treino -- e exatamente isso que queremos medir antes de decidir retreinar.

Mesmos cenarios e mesmas 10 sementes de avaliar.py. Cada rodada passa pela
instrumentacao (estados executados segundo a segundo) e pela checagem de
consistencia de analisar_comportamento.py.

Saida: resultados/seguranca_transicao/  (nada anterior e sobrescrito)

Uso (de dentro de scripts/):
  python avaliar_seguranca.py                   # tudo
  python avaliar_seguranca.py --sementes 1 2    # rapido
  python avaliar_seguranca.py --so-graficos     # refaz tabelas/graficos do JSON
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
from simulacao import APROXIMACOES, DINAMICAS
import analisar_comportamento as ac

PASTA_SAIDA = os.path.join(simulacao.PASTA, "resultados", "seguranca_transicao")
PASTA_GRAFICOS = os.path.join(PASTA_SAIDA, "graficos")
CONTROLADORES = ["Webster", "Max-Pressure", "Max-Pressure teto",
                 "DQN original", "DQN seed1", "DQN seed2"]
MODOS = list(DINAMICAS)  # A, B, C

# metricas por rodada (vindas de simulacao.rodar com dinamica explicita)
METRICAS_RODADA = [
    "n_carros", "espera_media", "espera_p95", "espera_max",
    "veiculos_concluidos", "veiculos_interrompidos",
    "espera_media_concluidos", "espera_p95_concluidos", "espera_max_concluidos",
    "veiculos_na_rede_no_fim", "veiculos_aguardando_entrada_no_fim",
    "veiculos_sem_atendimento", "segundos_escoamento",
    "verde_max_executado_hora", "verde_max_executado_total",
    "intervencoes_seguranca_hora", "intervencoes_seguranca_escoamento", "fila_media",
]


def _tarefa(args):
    cenario, rotulo, seed, rotas, modo = args
    t0 = time.time()
    r = ac.rodar_instrumentado(cenario, rotulo, seed, rotas, dinamica=DINAMICAS[modo])
    # nao precisamos das listas internas nem do pico detalhado aqui
    enxuto = {
        "cenario": cenario, "controlador": rotulo, "seed": seed, "modo": modo,
        "metricas": r["metricas_oficiais"],
        "hora": {k: v for k, v in r["hora"].items() if not k.startswith("_")},
        "duracoes_verde_hora": r["hora"]["_duracoes"],
        "esperas_por_aprox": r["esperas_por_aprox"],
        "intervalo_sem_verde_hora": r["intervalo_sem_verde_hora"],
        "vermelho_geral_executado_s": r["duracoes_vermelho_geral_observadas"],
        "intervencoes": r["intervencoes"],
        "segundos_cpu": time.time() - t0,
    }
    return enxuto


# =========================================================================
def agregar(rodadas):
    grupos = {}
    for r in rodadas:
        grupos.setdefault((r["cenario"], r["controlador"], r["modo"]), []).append(r)
    resumo = {}
    for (cen, ctrl, modo), rs in grupos.items():
        rs.sort(key=lambda r: r["seed"])
        item = {"sementes": [r["seed"] for r in rs]}
        for k in METRICAS_RODADA:
            item[k] = ac._ms([r["metricas"][k] for r in rs])
        item["rodadas_com_escoamento_cortado"] = sum(r["metricas"]["escoamento_cortado"] for r in rs)
        item["veiculos_sem_atendimento_total"] = sum(r["metricas"]["veiculos_sem_atendimento"] for r in rs)
        item["veiculos_interrompidos_total"] = sum(r["metricas"]["veiculos_interrompidos"] for r in rs)
        item["verde_max_executado_total_max"] = max(r["metricas"]["verde_max_executado_total"] for r in rs)
        for k in ["trocas_por_hora", "verde_medio", "pct_transicao", "s_vermelho_geral",
                  "s_amarelo"]:
            item[k] = ac._ms([r["hora"][k] for r in rs])
        item["esperas_por_aprox"] = {
            a: {k: ac._ms([r["esperas_por_aprox"][a][k] for r in rs])
                for k in ["n_carros", "nao_chegaram", "espera_media", "espera_p95",
                          "espera_media_so_chegaram", "espera_p95_so_chegaram",
                          "espera_max_so_chegaram"]}
            for a in APROXIMACOES}
        item["maior_tempo_sem_verde_hora"] = {
            a: ac._ms([r["intervalo_sem_verde_hora"][a]["maximo"] for r in rs])
            for a in APROXIMACOES}
        item["vermelho_geral_executado_s"] = sorted(
            {d for r in rs for d in r["vermelho_geral_executado_s"]})
        # para onde a regra mandou o verde, e o que o controlador queria
        item["intervencoes_total"] = sum(len(r["intervencoes"]) for r in rs)
        # comparacao pareada com o modo A (mesma semente)
        resumo[f"{cen}|{ctrl}|{modo}"] = item
    for chave, item in resumo.items():
        cen, ctrl, modo = chave.split("|")
        base = grupos.get((cen, ctrl, "A"))
        if modo == "A" or not base:
            continue
        atual = grupos[(cen, ctrl, modo)]
        pares = [(b["metricas"], a["metricas"]) for b in base for a in atual
                 if b["seed"] == a["seed"]]
        item["vs_A"] = {
            k: {"diferenca_media": statistics.mean(a[k] - b[k] for b, a in pares),
                "sementes_que_melhoraram": sum(1 for b, a in pares if a[k] < b[k]),
                "sementes_que_pioraram": sum(1 for b, a in pares if a[k] > b[k]),
                "n": len(pares)}
            for k in ["espera_media_concluidos", "espera_p95_concluidos", "espera_media"]}
    return resumo


# =========================================================================
def _f(x, nd=1):
    return "-" if x is None else f"{x:.{nd}f}"


def relatorio(resumo, cenarios, controladores):
    L = ["# Seguranca e transicao - resumo\n",
         "Modos: " + "; ".join(d.nome for d in DINAMICAS.values()) + ".",
         "Valores = media de 10 sementes. 'Concluidos' = so carros que terminaram a "
         "viagem. A espera de um carro interrompido e um limite inferior e NAO entra "
         "nas colunas 'concluidos'.\n"]

    L.append("\n## 1. Atendimento e espera\n")
    L.append("| cenario | controlador | modo | espera media concl. (s) | P95 concl. (s) | "
             "max concl. (s) | espera media oficial (s) | concluidos | interrompidos (total) | "
             "sem atendimento (total) | aguardando entrada (total) | rodadas cortadas | "
             "pior aprox.: espera media / P95 (s) |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for cen in cenarios:
        for ctrl in controladores:
            for modo in MODOS:
                x = resumo.get(f"{cen}|{ctrl}|{modo}")
                if not x:
                    continue
                ep = x["esperas_por_aprox"]
                pior = max(APROXIMACOES, key=lambda a: ep[a]["espera_media_so_chegaram"]["media"] or 0)
                ag = x["veiculos_aguardando_entrada_no_fim"]["media"] * len(x["sementes"])
                L.append(
                    f"| {cen} | {ctrl} | {modo} | {_f(x['espera_media_concluidos']['media'])} "
                    f"+- {_f(x['espera_media_concluidos']['dp'])} | "
                    f"{_f(x['espera_p95_concluidos']['media'])} | "
                    f"{_f(x['espera_max_concluidos']['media'])} | {_f(x['espera_media']['media'])} | "
                    f"{_f(x['veiculos_concluidos']['media'], 0)} | {x['veiculos_interrompidos_total']} | "
                    f"{x['veiculos_sem_atendimento_total']} | {_f(ag, 0)} | "
                    f"{x['rodadas_com_escoamento_cortado']}/{len(x['sementes'])} | "
                    f"{pior}: {_f(ep[pior]['espera_media_so_chegaram']['media'])} / "
                    f"{_f(ep[pior]['espera_p95_so_chegaram']['media'])} |")

    L.append("\n## 2. Comportamento do semaforo e regra de seguranca\n")
    L.append("| cenario | controlador | modo | vermelho geral executado (s) | trocas/h | "
             "verde medio (s) | % transicao | verde max hora (s) | verde max total (s) | "
             "intervencoes/rodada hora | intervencoes/rodada escoamento | escoamento (s) |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for cen in cenarios:
        for ctrl in controladores:
            for modo in MODOS:
                x = resumo.get(f"{cen}|{ctrl}|{modo}")
                if not x:
                    continue
                L.append(
                    f"| {cen} | {ctrl} | {modo} | {x['vermelho_geral_executado_s']} | "
                    f"{_f(x['trocas_por_hora']['media'])} | {_f(x['verde_medio']['media'])} | "
                    f"{_f(x['pct_transicao']['media'])} | "
                    f"{_f(x['verde_max_executado_hora']['media'], 0)} | "
                    f"{x['verde_max_executado_total_max']} | "
                    f"{_f(x['intervencoes_seguranca_hora']['media'])} | "
                    f"{_f(x['intervencoes_seguranca_escoamento']['media'])} | "
                    f"{_f(x['segundos_escoamento']['media'], 0)} |")

    L.append("\n## 3. Diferenca pareada contra o modo A (mesma semente)\n")
    L.append("| cenario | controlador | modo | dif. espera media concl. (s) | sementes melhor/pior | "
             "dif. P95 concl. (s) | sementes melhor/pior |")
    L.append("|---|---|---|---|---|---|---|")
    for cen in cenarios:
        for ctrl in controladores:
            for modo in MODOS[1:]:
                x = resumo.get(f"{cen}|{ctrl}|{modo}")
                if not x or "vs_A" not in x:
                    continue
                m, p = x["vs_A"]["espera_media_concluidos"], x["vs_A"]["espera_p95_concluidos"]
                L.append(f"| {cen} | {ctrl} | {modo} | {m['diferenca_media']:+.1f} | "
                         f"{m['sementes_que_melhoraram']}/{m['sementes_que_pioraram']} | "
                         f"{p['diferenca_media']:+.1f} | "
                         f"{p['sementes_que_melhoraram']}/{p['sementes_que_pioraram']} |")

    L.append("\n## 4. Espera por aproximacao (so concluidos): media / P95 (s)\n")
    L.append("| cenario | controlador | modo | " + " | ".join(APROXIMACOES) +
             " | maior tempo sem verde na hora (s, pior aprox.) |")
    L.append("|---|---|---|" + "---|" * 5)
    for cen in cenarios:
        for ctrl in controladores:
            for modo in MODOS:
                x = resumo.get(f"{cen}|{ctrl}|{modo}")
                if not x:
                    continue
                ep = x["esperas_por_aprox"]
                cel = [f"{_f(ep[a]['espera_media_so_chegaram']['media'])} / "
                       f"{_f(ep[a]['espera_p95_so_chegaram']['media'])}" for a in APROXIMACOES]
                gap = max((x["maior_tempo_sem_verde_hora"][a]["media"] or 0) for a in APROXIMACOES)
                L.append(f"| {cen} | {ctrl} | {modo} | " + " | ".join(cel) + f" | {_f(gap)} |")
    return "\n".join(L) + "\n"


# =========================================================================
def graficos(resumo, cenarios, controladores):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    ac._estilo(plt)
    os.makedirs(PASTA_GRAFICOS, exist_ok=True)
    feitos = []
    cores_modo = {"A": ac.CORES[0], "B": ac.CORES[1], "C": ac.CORES[2]}

    def painel_por_cenario(extrator, ylabel, titulo, nome, nota):
        fig, axes = plt.subplots(1, len(cenarios), figsize=(3.6 * len(cenarios), 4.6),
                                 sharey=False)
        axes = np.atleast_1d(axes)
        larg = 0.8 / len(MODOS)
        x = np.arange(len(controladores))
        for ax, cen in zip(axes, cenarios):
            for i, modo in enumerate(MODOS):
                med, dp = [], []
                for ctrl in controladores:
                    v = extrator(resumo[f"{cen}|{ctrl}|{modo}"])
                    med.append(v[0])
                    dp.append(v[1])
                ax.bar(x + (i - 1) * larg, med, larg * 0.92, yerr=dp, capsize=2,
                       color=cores_modo[modo], label=DINAMICAS[modo].nome,
                       error_kw={"elinewidth": 0.8, "ecolor": "#52514e"})
            ax.set_xticks(x)
            ax.set_xticklabels(controladores, rotation=45, ha="right", fontsize=8)
            ax.set_title(cen + (" *" if cen == "girado" else ""), fontsize=10)
        axes[0].set_ylabel(ylabel)
        h, l = axes[0].get_legend_handles_labels()
        fig.legend(h, l, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.1))
        fig.suptitle(titulo, y=1.02)
        fig.text(0.01, -0.15, nota + " * cenario nao visto no treino.", fontsize=8,
                 color=ac.CINZA_TEXTO)
        fig.tight_layout()
        caminho = os.path.join(PASTA_GRAFICOS, nome)
        fig.savefig(caminho, bbox_inches="tight")
        plt.close(fig)
        feitos.append(caminho)

    ms = lambda k: (lambda x: (x[k]["media"], x[k]["dp"]))  # noqa: E731
    nota = "Media de 10 sementes; traco = desvio padrao."
    painel_por_cenario(ms("espera_media_concluidos"), "Espera media (s)",
                       "1. Espera media dos carros que concluiram a viagem",
                       "1_espera_media_concluidos.png", nota)
    painel_por_cenario(ms("espera_p95_concluidos"), "Espera P95 (s)",
                       "2. Espera P95 dos carros que concluiram a viagem",
                       "2_espera_p95_concluidos.png", nota)
    painel_por_cenario(lambda x: (x["veiculos_sem_atendimento_total"], 0),
                       "Carros (soma das 10 sementes)",
                       "3. Carros que nunca foram atendidos (presos ao fim do escoamento)",
                       "3_sem_atendimento.png",
                       "Soma das 10 sementes: carros que nunca passaram da linha de retencao.")
    painel_por_cenario(lambda x: (x["intervencoes_seguranca_hora"]["media"]
                                  + x["intervencoes_seguranca_escoamento"]["media"], 0),
                       "Intervencoes por rodada",
                       "4. Intervencoes da regra de verde maximo (hora + escoamento)",
                       "4_intervencoes.png", "Media por rodada; o modo A nao tem a regra.")
    painel_por_cenario(lambda x: (x["verde_max_executado_total_max"], 0),
                       "Maior verde executado (s)",
                       "5. Maior verde executado em todas as rodadas (inclui escoamento)",
                       "5_verde_maximo.png", "Maximo entre as 10 sementes, medido no estado do SUMO.")

    # 6. pior aproximacao: espera media por aproximacao das DQNs nos modos
    dqns = [c for c in controladores if c.startswith("DQN")]
    fig, axes = plt.subplots(len(dqns), len(cenarios), figsize=(3.3 * len(cenarios), 2.6 * len(dqns)),
                             sharex=True)
    for li, ctrl in enumerate(dqns):
        for ci, cen in enumerate(cenarios):
            ax = axes[li, ci]
            larg = 0.8 / len(MODOS)
            for i, modo in enumerate(MODOS):
                ep = resumo[f"{cen}|{ctrl}|{modo}"]["esperas_por_aprox"]
                ax.bar(np.arange(4) + (i - 1) * larg,
                       [ep[a]["espera_p95_so_chegaram"]["media"] for a in APROXIMACOES],
                       larg * 0.92, color=cores_modo[modo], label=DINAMICAS[modo].nome)
            ax.set_xticks(range(4))
            ax.set_xticklabels(APROXIMACOES)
            if li == 0:
                ax.set_title(cen + (" *" if cen == "girado" else ""), fontsize=10)
            if ci == 0:
                ax.set_ylabel(f"{ctrl}\nP95 (s)")
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.04))
    fig.suptitle("6. Espera P95 por aproximacao de origem (so concluidos), DQNs", y=1.01)
    fig.tight_layout()
    caminho = os.path.join(PASTA_GRAFICOS, "6_p95_por_aproximacao_dqn.png")
    fig.savefig(caminho, bbox_inches="tight")
    plt.close(fig)
    feitos.append(caminho)
    return feitos


# =========================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sementes", type=int, nargs="*", default=None)
    ap.add_argument("--cenarios", nargs="*", default=None)
    ap.add_argument("--processos", type=int, default=max(1, min(6, (os.cpu_count() or 2) - 1)))
    ap.add_argument("--so-graficos", action="store_true")
    args = ap.parse_args()

    os.makedirs(PASTA_SAIDA, exist_ok=True)
    caminho_rodadas = os.path.join(PASTA_SAIDA, "rodadas.json")
    if args.so_graficos:
        with open(caminho_rodadas) as f:
            salvo = json.load(f)
        rodadas, cenarios = salvo["rodadas"], salvo["cenarios"]
    else:
        import avaliar  # mesmos cenarios e sementes da avaliacao oficial
        cenarios = args.cenarios or avaliar.CENARIOS
        sementes = args.sementes or avaliar.SEMENTES
        rotas = {c: gerar_demanda.gerar(c) for c in cenarios}
        tarefas = [(c, ctrl, s, rotas[c], m) for m in MODOS for c in cenarios
                   for ctrl in CONTROLADORES for s in sementes]
        print(f"{len(tarefas)} simulacoes ({len(MODOS)} modos x {len(cenarios)} cenarios x "
              f"{len(CONTROLADORES)} controladores x {len(sementes)} sementes), "
              f"{args.processos} processos", flush=True)
        t0 = time.time()
        rodadas = []
        with Pool(args.processos) as pool:
            for i, r in enumerate(pool.imap_unordered(_tarefa, tarefas), 1):
                rodadas.append(r)
                if i % 25 == 0 or i == len(tarefas):
                    print(f"  {i}/{len(tarefas)}  ({time.time() - t0:.0f} s)", flush=True)
        rodadas.sort(key=lambda r: (r["modo"], cenarios.index(r["cenario"]),
                                    CONTROLADORES.index(r["controlador"]), r["seed"]))
        with open(caminho_rodadas, "w") as f:
            json.dump({"cenarios": cenarios, "sementes": sementes,
                       "modos": {k: d.nome for k, d in DINAMICAS.items()},
                       "rodadas": rodadas}, f)

    resumo = agregar(rodadas)
    with open(os.path.join(PASTA_SAIDA, "resumo.json"), "w") as f:
        json.dump(resumo, f, indent=1)
    with open(os.path.join(PASTA_SAIDA, "resumo.md"), "w", encoding="utf-8") as f:
        f.write(relatorio(resumo, cenarios, CONTROLADORES))
    print(f"\nTabelas: {os.path.join(PASTA_SAIDA, 'resumo.md')}")
    try:
        feitos = graficos(resumo, cenarios, CONTROLADORES)
    except ImportError as e:
        print(f"\nNao consegui importar o matplotlib neste Python ({e}).\n"
              "As simulacoes ja estao salvas. Para gerar so os graficos, rode com\n"
              "um Python que tenha matplotlib funcionando:\n"
              "  py avaliar_seguranca.py --so-graficos")
        return 1
    for c in feitos:
        print("  ", os.path.relpath(c, PASTA_SAIDA))


if __name__ == "__main__":
    sys.exit(main())
