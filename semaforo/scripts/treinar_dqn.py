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
  python treinar_dqn.py fila_excesso 250 --dinamica C --semente 0 --nome dqn_fila_excesso_C_seed0
      (fila + excesso de espera; W = 60 s e beta = 1 por padrao)
  python treinar_dqn.py fila_excesso 250 --dinamica C --entradas 17 --semente 0 --nome dqn_fila_excesso_17_C_seed0
      (Experimento 2: mesma recompensa, + maior espera por aproximacao na entrada da rede)

Nada e sobrescrito: se o modelo ou o historico ja existirem, o treino nem
comeca (a nao ser com --sobrescrever).
"""

import argparse
import json
import os
import statistics
import time
import xml.etree.ElementTree as ET

import gerar_demanda
import simulacao
from dqn import (AgenteDQN, BETA_EXCESSO, ENTRADAS_VALIDAS, ESPERA_LIMITE, PASTA_MODELOS,
                 RECOMPENSAS, TAMANHO_ESTADO, descricao_observacao)
from simulacao import APROXIMACOES

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
            sementes_validacao=SEMENTES_VALIDACAO, parametros_recompensa=None,
            n_entradas=TAMANHO_ESTADO):
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

    extras = {} if parametros_recompensa is None else dict(parametros_recompensa)
    agente = AgenteDQN(tipo_recompensa=tipo_recompensa, semente=semente,
                       n_entradas=n_entradas, **extras)

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
            esperas, intervencoes_val, justica = _validar(agente, rotas, din, sementes_validacao)
            # o checkpoint continua escolhido SO pela espera media (mesmo
            # criterio da primeira comparacao); justica so e registrada
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
                               "justica": justica,
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
            "recompensa": tipo_recompensa,
            "parametros_recompensa": (
                {"espera_limite": agente.espera_limite, "beta": agente.beta}
                if tipo_recompensa == "fila_excesso" else None),
            "n_entradas": agente.n_entradas,
            "observacao": descricao_observacao(agente.n_entradas),
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

    esperas, intervencoes, justica = {}, 0, {}
    for cenario in CENARIOS_TREINO:
        valores, rodadas = [], []
        for s in sementes:
            medidor = EsperasPorAprox()  # so observa: nao muda a rodada
            m = simulacao.rodar(agente, cenario, rotas[cenario], seed=s,
                                dinamica=None if din.original() else din,
                                instrumentacao=medidor)
            valores.append(m["espera_media"])
            intervencoes += agente.intervencoes_episodio
            rodadas.append((m, medidor.esperas))
        esperas[cenario] = statistics.mean(valores)
        justica[cenario] = {
            "espera_p95": statistics.mean(m["espera_p95"] for m, _ in rodadas),
            # inclui quem nao terminou a viagem (limite inferior da espera)
            "espera_max": max(m["espera_max"] for m, _ in rodadas),
            "veiculos_sem_atendimento": sum(
                m.get("veiculos_sem_atendimento", 0) for m, _ in rodadas),
            "p95_por_aprox": {a: _percentil([w for _, e in rodadas for w in e[a]], 95)
                              for a in APROXIMACOES},
        }
        justica[cenario]["pior_p95_aprox"] = max(justica[cenario]["p95_por_aprox"].values())

    agente.treinando = estava_treinando
    agente.epsilon = epsilon
    return esperas, intervencoes, justica


class EsperasPorAprox:
    """Instrumentacao de simulacao.rodar que so le o tripinfo no fim e separa
    a espera de cada carro pela aproximacao de entrada (id f<bloco>_<aprox>_...)."""

    def inicio(self, estados_verdes, duracao):
        self.esperas = {a: [] for a in APROXIMACOES}

    def passo(self, segundo, estado):
        pass

    def decisao(self, obs, escolha):
        pass

    def fim(self, caminho_tripinfo):
        if not os.path.exists(caminho_tripinfo):
            return
        for v in ET.parse(caminho_tripinfo).getroot():
            self.esperas[v.get("id").split("_")[1]].append(float(v.get("waitingTime", 0)))


def _percentil(valores, p):
    if not valores:
        return 0.0
    s = sorted(valores)
    return s[int(round((p / 100.0) * (len(s) - 1)))]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Treina uma DQN.")
    ap.add_argument("tipo", nargs="?", default="fila", choices=sorted(RECOMPENSAS),
                    help="recompensa: fila | espera | fila_excesso")
    ap.add_argument("episodios", nargs="?", type=int, default=EPISODIOS)
    ap.add_argument("--dinamica", default="A", choices=sorted(simulacao.DINAMICAS))
    ap.add_argument("--semente", type=int, default=0)
    ap.add_argument("--nome", default=None, help="nome do modelo (padrao: dqn_<tipo>)")
    ap.add_argument("--historico", default=None,
                    help="arquivo do historico (padrao: resultados/treino_<nome>.json)")
    ap.add_argument("--sobrescrever", action="store_true")
    ap.add_argument("--espera-limite", type=float, default=ESPERA_LIMITE,
                    help="W (s), so para fila_excesso")
    ap.add_argument("--beta", type=float, default=BETA_EXCESSO, help="so para fila_excesso")
    ap.add_argument("--entradas", type=int, default=TAMANHO_ESTADO, choices=ENTRADAS_VALIDAS,
                    help="13 (padrao) ou 17 (+ maior espera por aproximacao)")
    args = ap.parse_args()

    din = simulacao.DINAMICAS[args.dinamica]
    params = ({"espera_limite": args.espera_limite, "beta": args.beta}
              if args.tipo == "fila_excesso" else None)
    print(f"Treinando {args.nome or 'dqn_' + args.tipo}: recompensa '{args.tipo}'"
          f"{f' {params}' if params else ''}, {args.entradas} entradas, {args.episodios} episodios, "
          f"semente {args.semente}, dinamica {din.nome}")
    print(f"(cada episodio = 1 hora de transito; cenario sorteado entre "
          f"{', '.join(CENARIOS_TREINO)})\n")
    treinar(tipo_recompensa=args.tipo, episodios=args.episodios, semente=args.semente,
            nome=args.nome, dinamica=args.dinamica, historico=args.historico,
            sobrescrever=args.sobrescrever, parametros_recompensa=params,
            n_entradas=args.entradas)
