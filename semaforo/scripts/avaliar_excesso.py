"""
Experimento 1 de equilibrio: DQNs com recompensa fila + excesso de espera
(dqn_fila_excesso_C_seed{0,1,2}.pt) contra as 3 DQN C atuais (recompensa fila).

Mesma dinamica C, mesmos 5 cenarios, mesmas 10 sementes de teste de
avaliar_C.py; o girado nunca entra no treino nem no checkpoint.

As rodadas das DQN C atuais e das referencias (Webster, Max-Pressure teto
recal. C) NAO sao refeitas: sao lidas de resultados/comparacao_C/avaliacao.json
(a avaliacao e deterministica; testar_recompensa_excesso.py confere que
continua reproduzivel). Use --rerodar-referencias para refaze-las mesmo assim.

Saida: resultados/comparacao_excesso_C/ (avaliacao.json, resumo.json, resumo.md, graficos/)

Uso (de dentro de scripts/), depois dos 3 treinos:
  python avaliar_excesso.py
  py avaliar_excesso.py --so-graficos      # Python com matplotlib
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
from simulacao import APROXIMACOES

PASTA_SAIDA = os.path.join(simulacao.PASTA, "resultados", "comparacao_excesso_C")
PASTA_GRAFICOS = os.path.join(PASTA_SAIDA, "graficos")
AVALIACAO_C = os.path.join(simulacao.PASTA, "resultados", "comparacao_C", "avaliacao.json")

DQN_FILA = [f"DQN C seed{i}" for i in range(3)]
DQN_EXCESSO = [f"DQN excesso C seed{i}" for i in range(3)]
REFERENCIAS = ["Webster", "Max-Pressure teto (recal. C)"]
GRUPOS = {"DQN C fila (media das 3)": DQN_FILA,
          "DQN C fila_excesso (media das 3)": DQN_EXCESSO}
# rua secundaria (menos demanda) de cada cenario assimetrico
SECUNDARIAS = {"assimetrico": ["N", "S"], "girado": ["L", "O"]}


def _metricas(r):
    """O que comparamos em cada rodada (todas as esperas incluem quem nao terminou,
    salvo as marcadas 'concluidos')."""
    m, pa = r["metricas"], r["esperas_por_aprox"]
    p95_aprox = {a: pa[a]["espera_p95"] for a in APROXIMACOES}
    sec = SECUNDARIAS.get(r["cenario"])
    return {
        "espera_media": m["espera_media"],
        "espera_media_concluidos": m["espera_media_concluidos"],
        "espera_p95": m["espera_p95"],
        **{f"p95_{a}": p95_aprox[a] for a in APROXIMACOES},
        "pior_p95_aprox": max(p95_aprox.values()),
        "p95_secundarias": statistics.mean(p95_aprox[a] for a in sec) if sec else None,
        "espera_max": m["espera_max"],  # inclui veiculos nao atendidos
        "nao_atendidos": m["veiculos_sem_atendimento"],
        "trocas_por_hora": r["hora"]["trocas_por_hora"],
        "intervencoes_hora": m["intervencoes_seguranca_hora"],
        "intervencoes_escoamento": m["intervencoes_seguranca_escoamento"],
    }


ROTULOS = {
    "espera_media": "espera media (s)", "espera_media_concluidos": "espera media concluidos (s)",
    "espera_p95": "P95 geral (s)", **{f"p95_{a}": f"P95 {a} (s)" for a in APROXIMACOES},
    "pior_p95_aprox": "pior P95 aprox. (s)", "p95_secundarias": "P95 secundarias (s)",
    "espera_max": "espera max c/ nao atendidos (s)", "nao_atendidos": "nao atendidos",
    "trocas_por_hora": "trocas/h", "intervencoes_hora": "intervencoes hora",
    "intervencoes_escoamento": "intervencoes escoamento",
}
SOMAS = {"nao_atendidos", "intervencoes_hora", "intervencoes_escoamento"}


def _ms(v):
    v = [x for x in v if x is not None]
    if not v:
        return None
    return {"media": statistics.mean(v), "dp": statistics.stdev(v) if len(v) > 1 else 0.0,
            "max": max(v), "total": sum(v)}


def agregar(rodadas, cenarios, controladores):
    por = {}
    for r in rodadas:
        por.setdefault((r["cenario"], r["controlador"]), {})[r["seed"]] = _metricas(r)
    resumo = {}
    for cen in cenarios:
        for ctrl in controladores:
            d = por.get((cen, ctrl))
            if d:
                resumo[f"{cen}|{ctrl}"] = {k: _ms([x[k] for x in d.values()]) for k in ROTULOS}
        for g, membros in GRUPOS.items():
            if not all((cen, m) in por for m in membros):
                continue
            sementes = sorted(por[(cen, membros[0])])
            serie = {k: [None if any(por[(cen, m)][s][k] is None for m in membros) else
                         statistics.mean(por[(cen, m)][s][k] for m in membros) for s in sementes]
                     for k in ROTULOS}
            item = {**{k: _ms(v) for k, v in serie.items()}, "_serie": serie}
            # no grupo, a "espera max" mostrada e a maior entre as 3 redes e 10 sementes
            item["espera_max"] = {**item["espera_max"], "max": max(
                x["espera_max"] for m in membros for x in por[(cen, m)].values())}
            for k in SOMAS:  # e os totais somam as 3 redes
                item[k] = {**item[k], "total": sum(
                    x[k] for m in membros for x in por[(cen, m)].values())}
            resumo[f"{cen}|{g}"] = item
        a, n = (resumo.get(f"{cen}|{g}") for g in GRUPOS)
        if a and n:
            comp = {}
            for k in ROTULOS:
                if a["_serie"][k][0] is None:
                    continue
                d = [y - x for x, y in zip(a["_serie"][k], n["_serie"][k])]
                comp[k] = {"diferenca_media": statistics.mean(d),
                           "relativa_pct": 100 * statistics.mean(d) / statistics.mean(a["_serie"][k])
                           if statistics.mean(a["_serie"][k]) else None,
                           "sementes_excesso_menor": sum(x < 0 for x in d),
                           "sementes_empate": sum(x == 0 for x in d), "n": len(d)}
            resumo[f"{cen}|excesso_vs_fila"] = comp
    return resumo


def criterios(resumo, cenarios, automato):
    """Os criterios definidos ANTES de treinar (plano_experimentos.md)."""
    gf, ge = GRUPOS
    out = {}
    if not all(f"{c}|excesso_vs_fila" in resumo for c in cenarios):
        return None
    out["1_zero_nao_atendidos"] = all(
        resumo[f"{c}|{m}"]["nao_atendidos"]["total"] == 0 for c in cenarios for m in DQN_EXCESSO)
    out["1_zero_ciclos_carro_sozinho"] = (
        None if automato is None else all(x["presos"] == 0 for x in automato.values()))
    quedas = {c: resumo[f"{c}|excesso_vs_fila"]["p95_secundarias"]["relativa_pct"]
              for c in SECUNDARIAS if f"{c}|excesso_vs_fila" in resumo}
    out["2_p95_secundarias_cai_20pct"] = all(v <= -20 for v in quedas.values())
    out["2_p95_secundarias_variacao_pct"] = quedas
    out["2_espera_max_cai"] = all(resumo[f"{c}|excesso_vs_fila"]["espera_max"]["diferenca_media"] < 0
                                  for c in cenarios)
    piora = {c: resumo[f"{c}|excesso_vs_fila"]["espera_media"]["relativa_pct"] for c in cenarios}
    out["3_espera_media_piora_no_maximo_5pct"] = all(v <= 5 for v in piora.values())
    out["3_espera_media_variacao_pct"] = piora
    out["3_abaixo_de_webster_e_mp_teto"] = all(
        resumo[f"{c}|{ge}"]["espera_media"]["media"] < min(
            resumo[f"{c}|{r}"]["espera_media"]["media"] for r in REFERENCIAS
            if f"{c}|{r}" in resumo)
        for c in cenarios)
    return out


def _existe(nome):
    from dqn import PASTA_MODELOS  # (torch so e importado aqui, nao no --so-graficos)
    return os.path.exists(os.path.join(PASTA_MODELOS, f"{nome}.pt"))


def _automato():
    """Teste do carro sozinho (sem simulador) nas redes novas."""
    from dqn import AgenteDQN
    import diagnosticar_equilibrio as de
    out = {}
    for rot in DQN_EXCESSO:
        nome = ac.ROTULO_MODELO[rot]
        if not _existe(nome):
            return None
        ag = AgenteDQN(treinando=False).carregar(nome)
        res = [de._automato(ag, v, c, carros=n) for n in (1, 2, 3)
               for v in APROXIMACOES for c in APROXIMACOES if c != v]
        out[rot] = {"presos": sum(r[0] != "atende" for r in res), "de": len(res),
                    "atendidos_so_pela_regra": sum(1 for r in res if r[0] == "atende" and r[2])}
    return out


def _f(x, nd=1):
    return "-" if x is None else f"{x:.{nd}f}"


def relatorio(resumo, cenarios, controladores, crit, automato):
    L = ["# Experimento 1: recompensa fila + excesso de espera (dinamica C)", "",
         "W = 60 s, beta = 1. Media de 10 sementes de teste (+- dp). Esperas incluem os "
         "veiculos nao atendidos (limite inferior), exceto 'concluidos'. Nao atendidos e "
         "intervencoes: total nas 10 sementes. Espera max: maior das 10 sementes.", ""]
    linhas = controladores + list(GRUPOS)
    for cen in cenarios:
        L += [f"## {cen}" + (" (nunca visto no treino)" if cen == "girado" else ""), "",
              "| controlador | " + " | ".join(ROTULOS.values()) + " |",
              "|---|" + "---|" * len(ROTULOS)]
        for ctrl in linhas:
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
            nome = f"**{ctrl}**" if ctrl in GRUPOS else ctrl
            L.append(f"| {nome} | " + " | ".join(cel) + " |")
        comp = resumo.get(f"{cen}|excesso_vs_fila")
        if comp:
            L += ["", "fila_excesso - fila (pareado por semente; media das 3 redes): " + "; ".join(
                f"{ROTULOS[k]}: {v['diferenca_media']:+.2f}"
                + (f" ({v['relativa_pct']:+.1f}%)" if v["relativa_pct"] is not None else "")
                + f", menor em {v['sementes_excesso_menor']}/{v['n']}"
                for k, v in comp.items() if k in (
                    "espera_media", "espera_p95", "pior_p95_aprox", "p95_secundarias",
                    "espera_max", "nao_atendidos", "trocas_por_hora"))]
        L.append("")
    if automato:
        L += ["## Teste do carro sozinho (redes novas)", ""] + [
            f"- {k}: {v['presos']}/{v['de']} combinacoes presas; "
            f"{v['atendidos_so_pela_regra']} atendidas so pela regra de seguranca"
            for k, v in automato.items()] + [""]
    if crit:
        L += ["## Criterios definidos antes do treino", ""] + [
            f"- {k}: {v}" for k, v in crit.items()] + [""]
    return "\n".join(L)


def graficos(resumo, cenarios, controladores, n_sementes=10):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    ac._estilo(plt)
    os.makedirs(PASTA_GRAFICOS, exist_ok=True)
    # mesma cor para o par (DQN C seed i, DQN excesso C seed i); a hachura diferencia
    cores = {c: ac.CORES[i] for i, c in enumerate(REFERENCIAS + DQN_FILA)}
    cores.update({e: cores[f] for f, e in zip(DQN_FILA, DQN_EXCESSO)})
    feitos = []
    for chave, ylabel, arq in [("espera_media", "Espera media (s)", "1_espera_media.png"),
                               ("pior_p95_aprox", "P95 da pior aproximacao (s)", "2_pior_p95.png"),
                               ("espera_max", "Espera maxima, com nao atendidos (s)", "3_espera_max.png")]:
        fig, axes = plt.subplots(1, len(cenarios), figsize=(3.4 * len(cenarios), 4.6))
        axes = np.atleast_1d(axes)
        for ax, cen in zip(axes, cenarios):
            pres = [c for c in controladores if f"{cen}|{c}" in resumo]
            campo = "max" if chave == "espera_max" else "media"
            med = [resumo[f"{cen}|{c}"][chave][campo] for c in pres]
            dp = None if chave == "espera_max" else [resumo[f"{cen}|{c}"][chave]["dp"] for c in pres]
            ax.bar(range(len(pres)), med, 0.75, yerr=dp, capsize=2, color=[cores[c] for c in pres],
                   error_kw={"elinewidth": 0.8, "ecolor": "#52514e"})
            for i, c in enumerate(pres):
                if c in DQN_EXCESSO:
                    ax.patches[i].set_hatch("//")
            ax.set_xticks(range(len(pres)))
            ax.set_xticklabels(pres, rotation=55, ha="right", fontsize=7)
            ax.set_title(cen + (" *" if cen == "girado" else ""), fontsize=10)
        axes[0].set_ylabel(ylabel)
        fig.text(0.01, -0.12, f"{n_sementes} sementes de teste, dinamica C. Mesma cor = mesma semente "
                 "de treino; hachura = recompensa fila_excesso. * cenario nao visto no treino.", fontsize=8, color=ac.CINZA_TEXTO)
        fig.tight_layout()
        caminho = os.path.join(PASTA_GRAFICOS, arq)
        fig.savefig(caminho, bbox_inches="tight")
        plt.close(fig)
        feitos.append(caminho)
    return feitos


def main(argv=None):
    global PASTA_SAIDA, PASTA_GRAFICOS
    ap = argparse.ArgumentParser()
    ap.add_argument("--sementes", type=int, nargs="*", default=None)
    ap.add_argument("--processos", type=int, default=max(1, min(6, (os.cpu_count() or 2) - 1)))
    ap.add_argument("--rerodar-referencias", action="store_true")
    ap.add_argument("--so-graficos", action="store_true")
    ap.add_argument("--saida", default=PASTA_SAIDA, help=argparse.SUPPRESS)  # usado nos testes
    args = ap.parse_args(argv)
    PASTA_SAIDA, PASTA_GRAFICOS = args.saida, os.path.join(args.saida, "graficos")
    arq = os.path.join(PASTA_SAIDA, "avaliacao.json")

    if args.so_graficos:
        with open(arq) as f:
            salvo = json.load(f)
        resumo = agregar(salvo["rodadas"], salvo["cenarios"], salvo["controladores"])
        for c in graficos(resumo, salvo["cenarios"], salvo["controladores"], len(salvo["sementes"])):
            print("  ", c)
        return 0

    with open(AVALIACAO_C) as f:
        antiga = json.load(f)
    cenarios = antiga["cenarios"]
    sementes = args.sementes or antiga["sementes"]
    novas = [r for r in DQN_EXCESSO if _existe(ac.ROTULO_MODELO[r])]
    if not novas:
        sys.exit("Nenhum modelo dqn_fila_excesso_C_seed*.pt encontrado: treine antes.")
    if len(novas) < 3:
        print(f"AVISO: so {novas} existem; os grupos de 3 redes nao serao comparados.")
    controladores = REFERENCIAS + DQN_FILA + novas
    reuso = [] if args.rerodar_referencias else [
        r for r in antiga["rodadas"]
        if r["controlador"] in REFERENCIAS + DQN_FILA and r["seed"] in sementes]
    feitas = {(r["cenario"], r["controlador"], r["seed"]) for r in reuso}
    rotas = {c: gerar_demanda.gerar(c) for c in cenarios}
    tarefas = [(c, ctrl, s, rotas[c]) for c in cenarios for ctrl in controladores
               for s in sementes if (c, ctrl, s) not in feitas]
    print(f"{len(reuso)} rodadas reaproveitadas de comparacao_C; {len(tarefas)} novas", flush=True)
    t0 = time.time()
    rodadas = list(reuso)
    # com --processos 1 roda no proprio processo (sem Pool)
    pool = Pool(args.processos) if args.processos > 1 else None
    executar = pool.imap_unordered if pool else map
    try:
        for i, r in enumerate(executar(avaliar_C._tarefa, tarefas), 1):
            r["origem"] = "rodada agora"
            rodadas.append(r)
            if i % 25 == 0 or i == len(tarefas):
                print(f"  {i}/{len(tarefas)} ({time.time() - t0:.0f} s)", flush=True)
    finally:
        if pool:
            pool.close()
            pool.join()
    for r in reuso:
        r["origem"] = "comparacao_C/avaliacao.json"
    rodadas.sort(key=lambda r: (cenarios.index(r["cenario"]),
                                controladores.index(r["controlador"]), r["seed"]))
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    with open(arq, "w") as f:
        json.dump({"dinamica": avaliar_C.DIN.nome, "cenarios": cenarios, "sementes": sementes,
                   "controladores": controladores, "rodadas": rodadas}, f)

    resumo = agregar(rodadas, cenarios, controladores)
    automato = _automato()
    crit = criterios(resumo, cenarios, automato)
    with open(os.path.join(PASTA_SAIDA, "resumo.json"), "w") as f:
        json.dump({"resumo": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
                              for k, v in resumo.items()},
                   "carro_sozinho": automato, "criterios": crit}, f, indent=1)
    with open(os.path.join(PASTA_SAIDA, "resumo.md"), "w", encoding="utf-8") as f:
        f.write(relatorio(resumo, cenarios, controladores, crit, automato))
    print(f"Tabelas: {os.path.join(PASTA_SAIDA, 'resumo.md')}")
    try:
        graficos(resumo, cenarios, controladores, len(sementes))
    except ImportError as e:
        print(f"Sem matplotlib neste Python ({e}). Graficos:  py avaliar_excesso.py --so-graficos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
