"""
Recalibra o Max-Pressure para a dinamica C (transicao de 3 s + 2 s de verdade).

Os parametros do Max-Pressure (verde minimo proprio e custo de troca) foram
escolhidos por varredura na dinamica original, em que cada troca custava
4 s e cada verde ganhava 1 s extra. Na dinamica C o custo e outro, entao o
ajuste otimo pode ser outro. Repetimos a varredura na dinamica C:

  - sementes de CALIBRACAO 301-305: separadas das de teste (1-10), das de
    validacao do treino (201-202) e das de treino (1000+);
  - so os 4 cenarios de treino (o girado fica guardado para o teste);
  - "teto": o melhor ajuste de CADA cenario (trapaceia, como o original);
  - "ajuste unico": um ajuste so, o que minimiza a media, nos 4 cenarios, da
    espera relativa ao Webster (para o saturado nao dominar a escolha).

O Webster nao tem o que calibrar: e uma formula, e a formula ja supoe 5 s
perdidos por troca -- que e justamente o que a dinamica C passa a executar.

Saida: resultados/comparacao_C/calibracao_tradicionais_C.json
Uso (de dentro de scripts/):  python calibrar_tradicionais_C.py
"""

import argparse
import itertools
import json
import os
import statistics
import time
from multiprocessing import Pool

import gerar_demanda
import simulacao
from controladores import AJUSTE_POR_CENARIO, MaxPressure, TempoFixo

CENARIOS = ["equilibrado", "assimetrico", "pico", "saturado"]
SEMENTES_CALIBRACAO = [301, 302, 303, 304, 305]
VERDES_MINIMOS = [10, 15, 20, 25, 30, 35, 40]
CUSTOS_TROCA = [0, 1, 2, 3, 5]
PASTA_SAIDA = os.path.join(simulacao.PASTA, "resultados", "comparacao_C")
ARQUIVO = os.path.join(PASTA_SAIDA, "calibracao_tradicionais_C.json")
ORIGINAL_UNICO = {"custo_troca": 0.0, "verde_minimo": 18}  # MaxPressure() padrao


def _rodar(args):
    cenario, seed, params, rotas, dinamica = args
    ctrl = TempoFixo() if params is None else MaxPressure(**params)
    m = simulacao.rodar(ctrl, cenario, rotas, seed=seed,
                        dinamica=simulacao.DINAMICAS[dinamica])
    return cenario, seed, None if params is None else tuple(sorted(params.items())), m["espera_media"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dinamica", default="C")
    ap.add_argument("--processos", type=int, default=6)
    args = ap.parse_args()

    rotas = {c: gerar_demanda.gerar(c) for c in CENARIOS}
    grade = [{"custo_troca": c, "verde_minimo": v}
             for v, c in itertools.product(VERDES_MINIMOS, CUSTOS_TROCA)]
    extras = [ORIGINAL_UNICO] + [dict(p) for p in AJUSTE_POR_CENARIO.values()]
    todos = grade + [p for p in extras if p not in grade]
    tarefas = [(c, s, p, rotas[c], args.dinamica) for c in CENARIOS
               for s in SEMENTES_CALIBRACAO for p in [None] + todos]
    print(f"{len(tarefas)} simulacoes de calibracao (dinamica {args.dinamica})", flush=True)
    t0 = time.time()
    esperas = {}
    with Pool(args.processos) as pool:
        for i, (c, s, chave, e) in enumerate(pool.imap_unordered(_rodar, tarefas), 1):
            esperas.setdefault((c, chave), []).append(e)
            if i % 50 == 0:
                print(f"  {i}/{len(tarefas)} ({time.time() - t0:.0f} s)", flush=True)

    def chave(p):
        return tuple(sorted(p.items()))

    webster = {c: statistics.mean(esperas[(c, None)]) for c in CENARIOS}
    tabela = {}
    for p in todos:
        tabela[chave(p)] = {c: statistics.mean(esperas[(c, chave(p))]) for c in CENARIOS}

    def relativo(p):
        return statistics.mean(tabela[chave(p)][c] / webster[c] for c in CENARIOS)

    teto = {c: min(todos, key=lambda p: tabela[chave(p)][c]) for c in CENARIOS}
    unico = min(grade, key=relativo)

    saida = {
        "dinamica": simulacao.DINAMICAS[args.dinamica].nome,
        "sementes_calibracao": SEMENTES_CALIBRACAO,
        "cenarios": CENARIOS,
        "criterio_ajuste_unico": "menor media da espera relativa ao Webster nos 4 cenarios",
        "webster_espera": webster,
        "ajuste_unico": {**unico, "verde_maximo": 60},
        "ajuste_por_cenario": {c: dict(p) for c, p in teto.items()},
        "original": {
            "ajuste_unico": ORIGINAL_UNICO,
            "ajuste_por_cenario": AJUSTE_POR_CENARIO,
            "espera_ajuste_unico": tabela[chave(ORIGINAL_UNICO)],
            "relativo_ajuste_unico": relativo(ORIGINAL_UNICO),
            "espera_teto": {c: tabela[chave(AJUSTE_POR_CENARIO[c])][c] for c in CENARIOS},
        },
        "recalibrado": {
            "espera_ajuste_unico": tabela[chave(unico)],
            "relativo_ajuste_unico": relativo(unico),
            "espera_teto": {c: tabela[chave(teto[c])][c] for c in CENARIOS},
        },
        "grade": [{**dict(k), **{f"espera_{c}": v for c, v in d.items()},
                   "relativo_webster": statistics.mean(d[c] / webster[c] for c in CENARIOS)}
                  for k, d in tabela.items()],
    }
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    with open(ARQUIVO, "w") as f:
        json.dump(saida, f, indent=2)

    print("\nWebster (sem calibracao):", {c: round(v, 1) for c, v in webster.items()})
    print(f"Ajuste unico original {ORIGINAL_UNICO}: relativo ao Webster "
          f"{relativo(ORIGINAL_UNICO):.3f}  {_fmt(tabela[chave(ORIGINAL_UNICO)])}")
    print(f"Ajuste unico recalibrado {unico}: relativo ao Webster "
          f"{relativo(unico):.3f}  {_fmt(tabela[chave(unico)])}")
    for c in CENARIOS:
        print(f"  teto {c:12s} original {AJUSTE_POR_CENARIO[c]} -> "
              f"{tabela[chave(AJUSTE_POR_CENARIO[c])][c]:6.1f}s | recalibrado {teto[c]} -> "
              f"{tabela[chave(teto[c])][c]:6.1f}s")
    print(f"\nSalvo em {ARQUIVO}")


def _fmt(d):
    return " ".join(f"{c}={v:.1f}" for c, v in d.items())


if __name__ == "__main__":
    main()
