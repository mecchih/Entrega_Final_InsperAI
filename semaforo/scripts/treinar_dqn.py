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

5. A dinamica do simulador (simulacao.DINAMICAS) e a mesma no treino e na
   validacao que escolhe o checkpoint. O padrao "A" e a dinamica original,
   com a qual os modelos dqn_fila*.pt foram treinados.

Uso:
  python treinar_dqn.py fila 250                       # como sempre (dinamica A)
  python treinar_dqn.py fila 250 --dinamica C --semente 0 --nome dqn_fila_C_seed0

Nada e sobrescrito: se o modelo ou o historico ja existirem, o treino nem
comeca (a nao ser com --sobrescrever).
"""

import argparse
import json
import os
import statistics
import time

import gerar_demanda
import simulacao
from dqn import AgenteDQN, PASTA_MODELOS

CENARIOS_TREINO = ["equilibrado", "assimetrico", "pico", "saturado"]
SEMENTES_VALIDACAO = [201, 202]  # para escolher o melhor checkpoint
EPISODIOS = 300
PASSOS_DECAIMENTO = 40_000  # exploracao cai de 100% para 5% nesses passos
EPSILON_FINAL = 0.05
INTERVALO_VALIDACAO = 25


def caminhos(nome, historico=None, tipo_recompensa="fila"):
    """Onde o modelo e o historico de um treino vao parar. Sem nome explicito,
    os mesmos caminhos de sempre (dqn_<tipo>.pt e treino_<tipo>.json)."""
    modelo = os.path.join(PASTA_MODELOS, f"{nome or 'dqn_' + tipo_recompensa}.pt")
    if historico is None:
        sufixo = nome if nome else tipo_recompensa
        historico = os.path.join(simulacao.PASTA, "resultados", f"treino_{sufixo}.json")
    return modelo, historico


def treinar(tipo_recompensa="fila", episodios=EPISODIOS, semente=0, nome=None,
            verboso=True, dinamica="A", historico=None, sobrescrever=False,
            intervalo_validacao=INTERVALO_VALIDACAO,
            sementes_validacao=SEMENTES_VALIDACAO):
    arq_modelo, arq_historico = caminhos(nome, historico, tipo_recompensa)
    nome = nome or f"dqn_{tipo_recompensa}"
    din = simulacao.DINAMICAS[dinamica]
    if not sobrescrever:
        existentes = [c for c in (arq_modelo, arq_historico) if os.path.exists(c)]
        if existentes:
            raise FileExistsError(
                f"ja existe(m): {existentes}. Use outro --nome ou --sobrescrever.")

    rotas = {c: gerar_demanda.gerar(c) for c in CENARIOS_TREINO}

    import random
    random.seed(semente)

    agente = AgenteDQN(tipo_recompensa=tipo_recompensa, semente=semente)

    historico = []
    validacoes = []
    melhor_espera = float("inf")
    melhor_episodio = -1
    inicio = time.time()

    for ep in range(1, episodios + 1):
        cenario = CENARIOS_TREINO[ep % len(CENARIOS_TREINO)]
        # exploracao decai com os PASSOS de decisao, nao com os episodios
        agente.epsilon = max(
            EPSILON_FINAL, 1.0 - agente.passos / PASSOS_DECAIMENTO
        )
        m = simulacao.rodar(agente, cenario, rotas[cenario], seed=1000 + ep,
                            dinamica=None if din.original() else din)

        historico.append({
            "episodio": ep,
            "cenario": cenario,
            "epsilon": round(agente.epsilon, 3),
            "recompensa": round(agente.recompensa_episodio, 2),
            "espera_media": round(m["espera_media"], 2),
            "fila_media": round(m["fila_media"], 2),
            "perda": round(statistics.mean(agente.perdas[-200:]), 5)
                     if agente.perdas else None,
            "intervencoes_seguranca": agente.intervencoes_episodio,
            "veiculos_sem_atendimento": m.get("veiculos_sem_atendimento"),
        })

        if ep % intervalo_validacao == 0:
            # teste de verdade: sem exploracao, nos 4 cenarios de treino,
            # na MESMA dinamica do treino
            esperas, intervencoes_val = _validar(agente, rotas, din, sementes_validacao)
            media = statistics.mean(esperas.values())
            marca = ""
            melhorou = media < melhor_espera
            if melhorou:
                melhor_espera = media
                melhor_episodio = ep
                agente.salvar(nome)
                marca = "  <-- melhor ate agora, salvo"
            validacoes.append({"episodio": ep, "esperas": esperas, "media": media,
                               "intervencoes_seguranca": intervencoes_val,
                               "salvo": melhorou})
            if verboso:
                print(
                    f"  ep {ep:4d} | exploracao {agente.epsilon:5.1%} | "
                    f"espera media nos 4 cenarios: {media:6.2f}s | "
                    f"intervencoes no treino: {agente.intervencoes_total}{marca}",
                    flush=True,
                )

    duracao = time.time() - inicio
    if verboso:
        print(f"\n  treino terminou em {duracao:.0f}s "
              f"({agente.passos} decisoes, {agente.passos_treino} passos de "
              f"gradiente, {agente.intervencoes_total} intervencoes de seguranca)")
        print(f"  melhor checkpoint: episodio {melhor_episodio} "
              f"({melhor_espera:.2f}s de espera media)")

    os.makedirs(os.path.dirname(arq_historico), exist_ok=True)
    with open(arq_historico, "w") as f:
        json.dump({
            "historico": historico,
            "melhor_episodio": melhor_episodio,
            "melhor_espera": melhor_espera,
            "duracao_s": duracao,
            "modelo": nome,
            "semente": semente,
            "dinamica": din.nome,
            "episodios": episodios,
            "sementes_transito_treino": "1000 + episodio",
            "sementes_validacao": list(sementes_validacao),
            "validacoes": validacoes,
            "decisoes": agente.passos,
            "passos_gradiente": agente.passos_treino,
            "intervencoes_seguranca_treino": agente.intervencoes_total,
            "experiencias_com_intervencao": sum(
                1 for i in agente.memoria_info if i["intervencao"]),
        }, f, indent=2)

    return nome, melhor_espera


def _validar(agente, rotas, din, sementes):
    """Roda o agente sem exploracao e devolve a espera de cada cenario."""
    estava_treinando = agente.treinando
    epsilon = agente.epsilon
    agente.treinando = False
    agente.epsilon = 0.0

    esperas, intervencoes = {}, 0
    for cenario in CENARIOS_TREINO:
        valores = []
        for s in sementes:
            m = simulacao.rodar(agente, cenario, rotas[cenario], seed=s,
                                dinamica=None if din.original() else din)
            valores.append(m["espera_media"])
            intervencoes += agente.intervencoes_episodio
        esperas[cenario] = statistics.mean(valores)

    agente.treinando = estava_treinando
    agente.epsilon = epsilon
    return esperas, intervencoes


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Treina uma DQN.")
    ap.add_argument("tipo", nargs="?", default="fila", help="recompensa: fila | espera")
    ap.add_argument("episodios", nargs="?", type=int, default=EPISODIOS)
    ap.add_argument("--dinamica", default="A", choices=sorted(simulacao.DINAMICAS))
    ap.add_argument("--semente", type=int, default=0)
    ap.add_argument("--nome", default=None, help="nome do modelo (padrao: dqn_<tipo>)")
    ap.add_argument("--historico", default=None,
                    help="arquivo do historico (padrao: resultados/treino_<nome>.json)")
    ap.add_argument("--sobrescrever", action="store_true")
    args = ap.parse_args()

    din = simulacao.DINAMICAS[args.dinamica]
    print(f"Treinando {args.nome or 'dqn_' + args.tipo}: recompensa '{args.tipo}', {args.episodios} episodios, "
          f"semente {args.semente}, dinamica {din.nome}")
    print(f"(cada episodio = 1 hora de transito; cenario sorteado entre "
          f"{', '.join(CENARIOS_TREINO)})\n")
    treinar(tipo_recompensa=args.tipo, episodios=args.episodios, semente=args.semente,
            nome=args.nome, dinamica=args.dinamica, historico=args.historico,
            sobrescrever=args.sobrescrever)
