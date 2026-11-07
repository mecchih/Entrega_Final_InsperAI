"""
A medicao final: todos os semaforos, todos os cenarios, as mesmas sementes.

Regras que fazem a comparacao valer:
  - mesmas 10 sementes para todo mundo (ninguem pega transito mais facil)
  - as sementes de teste (1 a 10) nao foram usadas no treino (1000+)
  - o agente roda sem exploracao nenhuma
  - o cenario "girado" nunca apareceu no treino
"""

import json
import os
import statistics
import sys

import gerar_demanda
import simulacao
from controladores import (MaxPressure, MaxPressureAjustado, TempoFixo,
                           VerdeFixoIngenuo)
from dqn import AgenteDQN

CENARIOS = ["equilibrado", "assimetrico", "pico", "saturado", "girado"]
SEMENTES = list(range(1, 11))


def avaliar(modelos=("dqn_fila",)):
    rotas = {c: gerar_demanda.gerar(c) for c in CENARIOS}

    competidores = [
        ("Tempo fixo sem calibrar", lambda: VerdeFixoIngenuo()),
        ("Tempo fixo (Webster)", lambda: TempoFixo()),
        ("Max-Pressure (ajuste unico)", lambda: MaxPressure()),
        ("Max-Pressure por cenario (teto)", lambda: MaxPressureAjustado()),
    ]
    for nome_modelo in modelos:
        agente = AgenteDQN(treinando=False).carregar(nome_modelo)
        rotulo = f"DQN ({nome_modelo.replace('dqn_', 'recompensa de ')})"
        competidores.append((rotulo, lambda a=agente: a))

    resultados = {}
    for cenario in CENARIOS:
        for rotulo, fabrica in competidores:
            amostras = [
                simulacao.rodar(fabrica(), cenario, rotas[cenario], seed=s)
                for s in SEMENTES
            ]
            resultados[(cenario, rotulo)] = amostras

    return resultados, [r for r, _ in competidores]


def tabela(resultados, rotulos):
    def med(cenario, rotulo, metrica):
        v = [a[metrica] for a in resultados[(cenario, rotulo)]]
        return statistics.mean(v), (statistics.stdev(v) if len(v) > 1 else 0.0)

    for cenario in CENARIOS:
        guardado = "  [CENARIO GUARDADO - nunca visto no treino]" if cenario == "girado" else ""
        print()
        print("=" * 92)
        print(f"CENARIO: {cenario}{guardado}")
        print("=" * 92)
        print(f"{'':34s}{'espera media':>18}{'espera p95':>16}"
              f"{'fila media':>14}{'viagem':>12}")
        print("-" * 92)
        base = med(cenario, "Tempo fixo (Webster)", "espera_media")[0]
        for rotulo in rotulos:
            e, de = med(cenario, rotulo, "espera_media")
            p95, dp = med(cenario, rotulo, "espera_p95")
            f, df = med(cenario, rotulo, "fila_media")
            v, _ = med(cenario, rotulo, "viagem_media")
            ganho = 100 * (base - e) / base
            print(f"{rotulo:34s}{e:>10.1f} +-{de:4.1f}{p95:>10.1f} +-{dp:4.1f}"
                  f"{f:>9.1f} +-{df:4.1f}{v:>12.1f}   "
                  f"({ganho:+.0f}% vs tempo fixo)")

    # resumo geral
    print()
    print("=" * 92)
    print("RESUMO - espera media (s), media dos cenarios")
    print("=" * 92)
    treino = [c for c in CENARIOS if c != "girado"]
    for rotulo in rotulos:
        m_treino = statistics.mean(
            med(c, rotulo, "espera_media")[0] for c in treino
        )
        m_girado = med("girado", rotulo, "espera_media")[0]
        print(f"{rotulo:34s} 4 cenarios de treino: {m_treino:6.1f}s"
              f"    |  cenario guardado: {m_girado:6.1f}s")


def salvar(resultados, rotulos):
    saida = {}
    for (cenario, rotulo), amostras in resultados.items():
        saida[f"{cenario}|{rotulo}"] = [
            {k: v for k, v in a.items() if k != "serie_filas"} for a in amostras
        ]
    caminho = os.path.join(simulacao.PASTA, "resultados", "avaliacao_final.json")
    with open(caminho, "w") as f:
        json.dump(saida, f, indent=2)
    return caminho


if __name__ == "__main__":
    modelos = sys.argv[1:] or ["dqn_fila"]
    print(f"Avaliando: {', '.join(modelos)}")
    print(f"{len(CENARIOS)} cenarios x {4 + len(modelos)} controladores x "
          f"{len(SEMENTES)} sementes\n")
    resultados, rotulos = avaliar(modelos)
    tabela(resultados, rotulos)
    print()
    print(f"Numeros brutos: {salvar(resultados, rotulos)}")
