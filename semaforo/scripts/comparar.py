"""
Roda todos os controladores, em todos os cenarios, com varias sementes,
e monta a tabela comparativa.

Por que varias sementes: cada semente e um transito diferente (os carros
chegam em momentos diferentes). Com uma semente so, uma diferenca de 5%
entre dois semaforos pode ser puro azar. Com 10 sementes e desvio padrao,
da para afirmar algo.

Regra de ouro da comparacao: TODOS os controladores rodam exatamente as
mesmas sementes nos mesmos cenarios. Nenhum deles ve um transito mais facil.
"""

import json
import os
import statistics
import sys

import gerar_demanda
import simulacao
from controladores import (MaxPressure, MaxPressureAjustado, TempoFixo,
                           VerdeFixoIngenuo)

CENARIOS = ["equilibrado", "assimetrico", "pico", "saturado"]
SEMENTES = list(range(1, 11))  # 10 rodadas por combinacao

METRICAS = [
    ("espera_media", "Espera media (s)"),
    ("espera_p95", "Espera p95 (s)"),
    ("fila_media", "Fila media (carros)"),
    ("viagem_media", "Tempo de viagem (s)"),
    ("n_carros", "Carros atendidos"),
]


def fabricas():
    """Um controlador novo por rodada, para ninguem carregar estado da rodada
    anterior."""
    return [
        ("ingenuo", VerdeFixoIngenuo),
        ("webster", TempoFixo),
        ("maxpressure", MaxPressure),
        ("maxpressure_teto", MaxPressureAjustado),
    ]


def rodar_tudo():
    resultados = {}
    for cenario in CENARIOS:
        rotas = gerar_demanda.gerar(cenario)
        for chave, Fabrica in fabricas():
            amostras = []
            for semente in SEMENTES:
                m = simulacao.rodar(Fabrica(), cenario, rotas, seed=semente)
                amostras.append(m)
            resultados[(cenario, chave)] = amostras
            print(
                f"  {cenario:12s} {chave:12s} "
                f"espera {statistics.mean(a['espera_media'] for a in amostras):6.2f}s",
                flush=True,
            )
    return resultados


def resumir(amostras, metrica):
    valores = [a[metrica] for a in amostras]
    return statistics.mean(valores), (
        statistics.stdev(valores) if len(valores) > 1 else 0.0
    )


def imprimir_tabela(resultados):
    nomes = {
        "ingenuo": VerdeFixoIngenuo.nome,
        "webster": TempoFixo.nome,
        "maxpressure": MaxPressure.nome,
        "maxpressure_teto": MaxPressureAjustado.nome,
    }
    for cenario in CENARIOS:
        print()
        print("=" * 78)
        print(f"CENARIO: {cenario}")
        print("=" * 78)
        cabecalho = f"{'Controlador':30s}"
        for _, rotulo in METRICAS:
            cabecalho += f"{rotulo:>22s}"
        print(cabecalho)
        print("-" * 78)
        for chave in ("ingenuo", "webster", "maxpressure", "maxpressure_teto"):
            amostras = resultados[(cenario, chave)]
            linha = f"{nomes[chave]:30s}"
            for metrica, _ in METRICAS:
                media, desvio = resumir(amostras, metrica)
                linha += f"{media:>15.1f} +-{desvio:5.1f}"
            print(linha)

        # quanto o Max-Pressure ganha de cada tempo fixo
        base_w, _ = resumir(resultados[(cenario, "webster")], "espera_media")
        base_i, _ = resumir(resultados[(cenario, "ingenuo")], "espera_media")
        mp, _ = resumir(resultados[(cenario, "maxpressure")], "espera_media")
        teto, _ = resumir(resultados[(cenario, "maxpressure_teto")], "espera_media")
        print("-" * 78)
        print(f"  ganho vs tempo fixo calibrado   -> "
              f"ajuste unico: {100 * (base_w - mp) / base_w:+5.1f}%   "
              f"teto: {100 * (base_w - teto) / base_w:+5.1f}%")
        print(f"  ganho vs tempo fixo sem calibrar -> "
              f"ajuste unico: {100 * (base_i - mp) / base_i:+5.1f}%   "
              f"teto: {100 * (base_i - teto) / base_i:+5.1f}%")
        print(f"  >> espaco que sobra para a IA ganhar: "
              f"{100 * (mp - teto) / mp:+.1f}% de espera")


def salvar(resultados):
    saida = {}
    for (cenario, chave), amostras in resultados.items():
        saida[f"{cenario}|{chave}"] = {
            metrica: resumir(amostras, metrica) for metrica, _ in METRICAS
        }
        saida[f"{cenario}|{chave}"]["rodadas"] = [
            {k: v for k, v in a.items() if k != "serie_filas"} for a in amostras
        ]
    caminho = os.path.join(simulacao.PASTA, "resultados", "baselines.json")
    with open(caminho, "w") as f:
        json.dump(saida, f, indent=2)
    return caminho


if __name__ == "__main__":
    print(f"Rodando {len(CENARIOS)} cenarios x 4 controladores x "
          f"{len(SEMENTES)} sementes = "
          f"{len(CENARIOS) * 4 * len(SEMENTES)} simulacoes de 1 hora\n")
    resultados = rodar_tudo()
    imprimir_tabela(resultados)
    print()
    print(f"Resultados brutos salvos em: {salvar(resultados)}")
