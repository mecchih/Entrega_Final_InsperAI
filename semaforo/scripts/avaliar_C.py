"""
Comparacao final na dinamica C (transicao correta + verde maximo de 60 s).

Todos na MESMA dinamica, nos mesmos 5 cenarios e nas mesmas 10 sementes de
teste de avaliar.py:

  - Webster
  - Max-Pressure (ajuste unico) e Max-Pressure por cenario (teto), com os
    parametros originais E com os recalibrados para a dinamica C
    (calibrar_tradicionais_C.py, sementes de calibracao 301-305)
  - as 3 DQNs antigas (treinadas na dinamica A)
  - as 3 DQNs novas (treinadas na dinamica C), se os modelos existirem

Saida: resultados/comparacao_C/  (avaliacao.json, resumo.json, resumo.md, graficos/)

Uso (de dentro de scripts/):
  python avaliar_C.py                  # tudo
  python avaliar_C.py --sementes 1 2   # rapido
  python avaliar_C.py --so-graficos    # refaz tabelas e graficos do JSON
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
from simulacao import APROXIMACOES, DINAMICAS

PASTA_SAIDA = os.path.join(simulacao.PASTA, "resultados", "comparacao_C")
PASTA_GRAFICOS = os.path.join(PASTA_SAIDA, "graficos")
CALIBRACAO = os.path.join(PASTA_SAIDA, "calibracao_tradicionais_C.json")
DIN = DINAMICAS["C"]

DQN_ANTIGAS = ["DQN original", "DQN seed1", "DQN seed2"]
DQN_NOVAS = [f"DQN C seed{i}" for i in range(3)]
TRADICIONAIS = ["Webster", "Max-Pressure", "Max-Pressure teto",
                "Max-Pressure (recal. C)", "Max-Pressure teto (recal. C)"]
GRUPOS = {"DQN antigas (media das 3)": DQN_ANTIGAS, "DQN C (media das 3)": DQN_NOVAS}


def _calibracao():
    with open(CALIBRACAO) as f:
        return json.load(f)


def fabricar(rotulo):
    """Controladores desta comparacao (os recalibrados leem o JSON)."""
    from controladores import MaxPressure, MaxPressureAjustado
    if rotulo == "Max-Pressure (recal. C)":
        p = _calibracao()["ajuste_unico"]
        return MaxPressure(custo_troca=p["custo_troca"], verde_maximo=p["verde_maximo"],
                           verde_minimo=p["verde_minimo"])

    if rotulo == "Max-Pressure teto (recal. C)":
        cal = _calibracao()
        unico, tabela = cal["ajuste_unico"], cal["ajuste_por_cenario"]

        class TetoRecalibrado(MaxPressureAjustado):
            def preparar(self, cenario):
                # cenario fora da tabela (girado): fica o ajuste unico recalibrado
                ajuste = tabela.get(cenario, unico)
                self.custo_troca = ajuste["custo_troca"]
                self.verde_minimo = ajuste["verde_minimo"]

        return TetoRecalibrado(custo_troca=unico["custo_troca"],
                               verde_minimo=unico["verde_minimo"])
    return ac.fabricar(rotulo)


def _tarefa(args):
    cenario, rotulo, seed, rotas = args
    r = ac.rodar_instrumentado(cenario, rotulo, seed, rotas, dinamica=DIN,
                               controlador=fabricar(rotulo))
    return {
        "cenario": cenario, "controlador": rotulo, "seed": seed,
        "metricas": r["metricas_oficiais"],
        "hora": {k: v for k, v in r["hora"].items() if not k.startswith("_")},
        "duracoes_verde_hora": r["hora"]["_duracoes"],
        "esperas_por_aprox": r["esperas_por_aprox"],
        "intervalo_sem_verde_hora": r["intervalo_sem_verde_hora"],
        "vermelho_geral_executado_s": r["duracoes_vermelho_geral_observadas"],
        "n_intervencoes": len(r["intervencoes"]),
    }


# =========================================================================
METRICAS = [  # (chave, de onde, rotulo)
    ("espera_media", "metricas", "espera media oficial (s)"),
    ("espera_media_concluidos", "metricas", "espera media concluidos (s)"),
    ("espera_p95_concluidos", "metricas", "P95 concluidos (s)"),
    ("espera_max_concluidos", "metricas", "espera max concluidos (s)"),
    ("fila_media", "metricas", "fila media (carros)"),
    ("viagem_media", "metricas", "viagem media (s)"),
    ("veiculos_concluidos", "metricas", "atendidos"),
    ("veiculos_sem_atendimento", "metricas", "nao atendidos"),
    ("intervencoes_seguranca_hora", "metricas", "intervencoes hora"),
    ("intervencoes_seguranca_escoamento", "metricas", "intervencoes escoamento"),
    ("trocas_por_hora", "hora", "trocas/h"),
    ("verde_medio", "hora", "verde medio (s)"),
    ("pct_transicao", "hora", "% em transicao"),
]


def agregar(rodadas):
    grupos = {}
    for r in rodadas:
        grupos.setdefault((r["cenario"], r["controlador"]), []).append(r)
    resumo = {}
    for (cen, ctrl), rs in grupos.items():
        rs.sort(key=lambda r: r["seed"])
        item = {"sementes": [r["seed"] for r in rs]}
        for k, fonte, _ in METRICAS:
            item[k] = ac._ms([r[fonte][k] for r in rs])
        item["nao_atendidos_total"] = sum(r["metricas"]["veiculos_sem_atendimento"] for r in rs)
        item["intervencoes_total"] = sum(r["n_intervencoes"] for r in rs)
        item["por_aprox"] = {
            a: {k: ac._ms([r["esperas_por_aprox"][a][k] for r in rs])
                for k in ["espera_media_so_chegaram", "espera_p95_so_chegaram"]}
            for a in APROXIMACOES}
        item["vermelho_geral_executado_s"] = sorted(
            {d for r in rs for d in r["vermelho_geral_executado_s"]})
        item["_por_semente"] = {r["seed"]: r for r in rs}
        resumo[f"{cen}|{ctrl}"] = item

    # grupos de DQN: media das 3 redes em cada semente, depois media/dp entre sementes
    cenarios = sorted({c for c, _ in grupos}, key=lambda c: [r["cenario"] for r in rodadas].index(c))
    for nome, membros in GRUPOS.items():
        for cen in cenarios:
            itens = [resumo.get(f"{cen}|{m}") for m in membros]
            if not all(itens):
                continue
            sementes = itens[0]["sementes"]
            g = {"sementes": sementes, "membros": membros}
            for k, fonte, _ in METRICAS:
                por_semente = [statistics.mean(i["_por_semente"][s][fonte][k] for i in itens)
                               for s in sementes]
                g[k] = ac._ms(por_semente)
                g[f"_serie_{k}"] = por_semente
            g["nao_atendidos_total"] = sum(i["nao_atendidos_total"] for i in itens)
            g["intervencoes_total"] = sum(i["intervencoes_total"] for i in itens)
            resumo[f"{cen}|{nome}"] = g

    # novas x antigas, pareado por semente
    a, n = list(GRUPOS)
    for cen in cenarios:
        ga, gn = resumo.get(f"{cen}|{a}"), resumo.get(f"{cen}|{n}")
        if not (ga and gn):
            continue
        comp = {}
        for k in ["espera_media_concluidos", "espera_p95_concluidos", "trocas_por_hora",
                  "verde_medio"]:
            d = [y - x for x, y in zip(ga[f"_serie_{k}"], gn[f"_serie_{k}"])]
            comp[k] = {"diferenca_media": statistics.mean(d),
                       "dp": statistics.stdev(d) if len(d) > 1 else 0.0,
                       "sementes_novas_menor": sum(1 for x in d if x < 0), "n": len(d)}
        resumo[f"{cen}|novas_vs_antigas"] = comp
    return resumo


def _limpo(resumo):
    return {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
            for k, v in resumo.items()}


def _f(x, nd=1):
    return "-" if x is None else f"{x:.{nd}f}"


def relatorio(resumo, cenarios, controladores):
    L = ["# Comparacao final na dinamica C\n",
         f"Dinamica: {DIN.nome}. Media de {len(next(iter(resumo.values()))['sementes'])} "
         "sementes de teste (+- desvio padrao). 'Concluidos' = so carros que terminaram "
         "a viagem. Trocas/verde/% transicao: so a primeira hora.\n"]
    linhas = controladores + [g for g in GRUPOS if any(f"{c}|{g}" in resumo for c in cenarios)]
    for cen in cenarios:
        L.append(f"\n## {cen}" + (" (nunca visto no treino)" if cen == "girado" else "") + "\n")
        L.append("| controlador | " + " | ".join(r for _, _, r in METRICAS) +
                 " | pior aprox. P95 (s) |")
        L.append("|---|" + "---|" * (len(METRICAS) + 1))
        for ctrl in linhas:
            x = resumo.get(f"{cen}|{ctrl}")
            if not x:
                continue
            cel = [f"{_f(x[k]['media'])} +- {_f(x[k]['dp'])}"
                   if k in ("espera_media_concluidos", "espera_p95_concluidos")
                   else _f(x[k]["media"]) for k, _, _ in METRICAS]
            if "por_aprox" in x:
                pa = x["por_aprox"]
                pior = max(APROXIMACOES, key=lambda a: pa[a]["espera_p95_so_chegaram"]["media"] or 0)
                cel.append(f"{pior}: {_f(pa[pior]['espera_p95_so_chegaram']['media'])}")
            else:
                cel.append("-")
            nome = f"**{ctrl}**" if ctrl in GRUPOS else ctrl
            L.append(f"| {nome} | " + " | ".join(cel) + " |")
        comp = resumo.get(f"{cen}|novas_vs_antigas")
        if comp:
            L.append("\nDQN C - DQN antigas (pareado por semente): " + "; ".join(
                f"{k}: {v['diferenca_media']:+.2f} (novas menores em "
                f"{v['sementes_novas_menor']}/{v['n']} sementes)" for k, v in comp.items()))
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
    cores = {c: ac.CORES[i % len(ac.CORES)] for i, c in enumerate(controladores)}
    for chave, ylabel, titulo, arq in [
        ("espera_media_concluidos", "Espera media (s)", "Espera media dos carros atendidos",
         "1_espera_media.png"),
        ("espera_p95_concluidos", "Espera P95 (s)", "Espera P95 dos carros atendidos",
         "2_espera_p95.png"),
        ("trocas_por_hora", "Trocas por hora", "Trocas de fase por hora (primeira hora)",
         "3_trocas_por_hora.png"),
        ("verde_medio", "Verde medio (s)", "Duracao media do verde (primeira hora)",
         "4_verde_medio.png"),
    ]:
        fig, axes = plt.subplots(1, len(cenarios), figsize=(3.6 * len(cenarios), 4.8))
        axes = np.atleast_1d(axes)
        for ax, cen in zip(axes, cenarios):
            presentes = [c for c in controladores if f"{cen}|{c}" in resumo]
            med = [resumo[f"{cen}|{c}"][chave]["media"] for c in presentes]
            dp = [resumo[f"{cen}|{c}"][chave]["dp"] for c in presentes]
            ax.bar(range(len(presentes)), med, 0.75, yerr=dp, capsize=2,
                   color=[cores[c] for c in presentes],
                   hatch=None, error_kw={"elinewidth": 0.8, "ecolor": "#52514e"})
            for i, c in enumerate(presentes):  # DQNs novas com hachura
                if c in DQN_NOVAS:
                    ax.patches[i].set_hatch("//")
            ax.set_xticks(range(len(presentes)))
            ax.set_xticklabels(presentes, rotation=55, ha="right", fontsize=7)
            ax.set_title(cen + (" *" if cen == "girado" else ""), fontsize=10)
        axes[0].set_ylabel(ylabel)
        fig.suptitle(f"{titulo} - dinamica C", y=1.02)
        fig.text(0.01, -0.12, "Media de 10 sementes de teste; traco = desvio padrao. "
                 "Hachura = DQNs treinadas na dinamica C. * cenario nao visto no treino.",
                 fontsize=8, color=ac.CINZA_TEXTO)
        fig.tight_layout()
        caminho = os.path.join(PASTA_GRAFICOS, arq)
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
    caminho_rodadas = os.path.join(PASTA_SAIDA, "avaliacao.json")
    if args.so_graficos:
        with open(caminho_rodadas) as f:
            salvo = json.load(f)
        rodadas, cenarios, controladores = salvo["rodadas"], salvo["cenarios"], salvo["controladores"]
    else:
        if not os.path.exists(CALIBRACAO):
            sys.exit(f"Falta {CALIBRACAO}. Rode antes: python calibrar_tradicionais_C.py")
        import avaliar  # mesmos cenarios e sementes da avaliacao oficial
        cenarios = args.cenarios or avaliar.CENARIOS
        sementes = args.sementes or avaliar.SEMENTES
        novas = [r for r in DQN_NOVAS if os.path.exists(os.path.join(
            simulacao.PASTA, "modelos", f"{ac.ROTULO_MODELO[r]}.pt"))]
        if len(novas) < len(DQN_NOVAS):
            print(f"AVISO: modelos novos encontrados: {novas or 'nenhum'} "
                  f"(os demais ainda nao foram treinados)")
        controladores = TRADICIONAIS + DQN_ANTIGAS + novas
        rotas = {c: gerar_demanda.gerar(c) for c in cenarios}
        tarefas = [(c, ctrl, s, rotas[c]) for c in cenarios for ctrl in controladores
                   for s in sementes]
        print(f"{len(tarefas)} simulacoes na dinamica C ({len(cenarios)} cenarios x "
              f"{len(controladores)} controladores x {len(sementes)} sementes)", flush=True)
        t0 = time.time()
        rodadas = []
        with Pool(args.processos) as pool:
            for i, r in enumerate(pool.imap_unordered(_tarefa, tarefas), 1):
                rodadas.append(r)
                if i % 25 == 0 or i == len(tarefas):
                    print(f"  {i}/{len(tarefas)}  ({time.time() - t0:.0f} s)", flush=True)
        rodadas.sort(key=lambda r: (cenarios.index(r["cenario"]),
                                    controladores.index(r["controlador"]), r["seed"]))
        with open(caminho_rodadas, "w") as f:
            json.dump({"dinamica": DIN.nome, "cenarios": cenarios, "sementes": sementes,
                       "controladores": controladores, "calibracao": _calibracao(),
                       "rodadas": rodadas}, f)

    resumo = agregar(rodadas)
    with open(os.path.join(PASTA_SAIDA, "resumo.json"), "w") as f:
        json.dump(_limpo(resumo), f, indent=1)
    with open(os.path.join(PASTA_SAIDA, "resumo.md"), "w", encoding="utf-8") as f:
        f.write(relatorio(resumo, cenarios, controladores))
    print(f"\nTabelas: {os.path.join(PASTA_SAIDA, 'resumo.md')}")
    try:
        feitos = graficos(resumo, cenarios, controladores)
    except ImportError as e:
        print(f"\nNao consegui importar o matplotlib neste Python ({e}).\n"
              "Para gerar so os graficos:  py avaliar_C.py --so-graficos")
        return 1
    for c in feitos:
        print("  ", os.path.relpath(c, PASTA_SAIDA))


if __name__ == "__main__":
    sys.exit(main())
