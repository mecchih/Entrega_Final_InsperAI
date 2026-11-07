"""
Treina o agente.

Regras do treino, pensadas para o resultado ser honesto:

1. O agente treina nos 4 cenarios sorteados. Ele PODE ver todos os regimes
   de transito -- o que ele nao pode e ser avisado em qual esta. Essa
   informacao nao entra no estado.

2. As sementes de treino (1000+) sao diferentes das de teste (1 a 10).
   O transito do teste e literalmente trafego que ele nunca viu.

3. O cenario "girado" fica de fora do treino, guardado para o teste de
   generalizacao.

4. A cada 25 episodios o agente e testado de verdade (sem exploracao) e o
   melhor resultado e salvo. Isso existe porque desempenho de DQN oscila:
   pegar os pesos do ultimo episodio e apostar na sorte.
"""

import json
import os
import statistics
import sys
import time

import gerar_demanda
import simulacao
from dqn import AgenteDQN

CENARIOS_TREINO = ["equilibrado", "assimetrico", "pico", "saturado"]
SEMENTES_VALIDACAO = [201, 202]  # para escolher o melhor checkpoint
EPISODIOS = 300
PASSOS_DECAIMENTO = 40_000  # exploracao cai de 100% para 5% nesses passos
EPSILON_FINAL = 0.05


def treinar(tipo_recompensa="fila", episodios=EPISODIOS, semente=0, nome=None,
            verboso=True):
    nome = nome or f"dqn_{tipo_recompensa}"
    rotas = {c: gerar_demanda.gerar(c) for c in CENARIOS_TREINO + ["girado"]}

    import random
    random.seed(semente)

    agente = AgenteDQN(tipo_recompensa=tipo_recompensa, semente=semente)

    historico = []
    melhor_espera = float("inf")
    melhor_episodio = -1
    inicio = time.time()

    for ep in range(1, episodios + 1):
        cenario = CENARIOS_TREINO[ep % len(CENARIOS_TREINO)]
        # exploracao decai com os PASSOS de decisao, nao com os episodios
        agente.epsilon = max(
            EPSILON_FINAL, 1.0 - agente.passos / PASSOS_DECAIMENTO
        )
        m = simulacao.rodar(agente, cenario, rotas[cenario], seed=1000 + ep)

        historico.append({
            "episodio": ep,
            "cenario": cenario,
            "epsilon": round(agente.epsilon, 3),
            "recompensa": round(agente.recompensa_episodio, 2),
            "espera_media": round(m["espera_media"], 2),
            "fila_media": round(m["fila_media"], 2),
            "perda": round(statistics.mean(agente.perdas[-200:]), 5)
                     if agente.perdas else None,
        })

        if ep % 25 == 0:
            # teste de verdade: sem exploracao, nos 4 cenarios de treino
            esperas = _validar(agente, rotas)
            media = statistics.mean(esperas.values())
            marca = ""
            if media < melhor_espera:
                melhor_espera = media
                melhor_episodio = ep
                agente.salvar(nome)
                marca = "  <-- melhor ate agora, salvo"
            if verboso:
                print(
                    f"  ep {ep:4d} | exploracao {agente.epsilon:5.1%} | "
                    f"espera media nos 4 cenarios: {media:6.2f}s{marca}",
                    flush=True,
                )

    duracao = time.time() - inicio
    if verboso:
        print(f"\n  treino terminou em {duracao:.0f}s "
              f"({agente.passos} decisoes, {agente.passos_treino} passos de "
              f"gradiente)")
        print(f"  melhor checkpoint: episodio {melhor_episodio} "
              f"({melhor_espera:.2f}s de espera media)")

    caminho = os.path.join(simulacao.PASTA, "resultados",
                           f"treino_{tipo_recompensa}.json")
    with open(caminho, "w") as f:
        json.dump({
            "historico": historico,
            "melhor_episodio": melhor_episodio,
            "melhor_espera": melhor_espera,
            "duracao_s": duracao,
        }, f, indent=2)

    return nome, melhor_espera


def _validar(agente, rotas):
    """Roda o agente sem exploracao e devolve a espera de cada cenario."""
    estava_treinando = agente.treinando
    epsilon = agente.epsilon
    agente.treinando = False
    agente.epsilon = 0.0

    esperas = {}
    for cenario in CENARIOS_TREINO:
        valores = [
            simulacao.rodar(agente, cenario, rotas[cenario], seed=s)["espera_media"]
            for s in SEMENTES_VALIDACAO
        ]
        esperas[cenario] = statistics.mean(valores)

    agente.treinando = estava_treinando
    agente.epsilon = epsilon
    return esperas


if __name__ == "__main__":
    tipo = sys.argv[1] if len(sys.argv) > 1 else "fila"
    episodios = int(sys.argv[2]) if len(sys.argv) > 2 else EPISODIOS
    print(f"Treinando DQN com recompensa de '{tipo}' por {episodios} episodios")
    print(f"(cada episodio = 1 hora de transito; cenario sorteado entre "
          f"{', '.join(CENARIOS_TREINO)})\n")
    treinar(tipo_recompensa=tipo, episodios=episodios)
