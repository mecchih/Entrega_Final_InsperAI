"""Testes do treino C5 (5 agentes, uma DoubleDQN) antes do treino principal. Episodios curtos (1500 s).

uso: python -B -X utf8 semaforo/integracao_insper/parameter_sharing/treinamento_c5/testar_treino_c5.py
"""

import datetime
import json
from pathlib import Path
import sys
import tempfile

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import politica_c5 as p5  # noqa: E402
import insper_comum as ic  # noqa: E402

LIM = 1500
OK = []
CONFIG = {"verde_minimo": 10, "colisao": "atribuida", "supervisor_s": 30}


def checar(cond, msg):
    print(("OK   " if cond else "FALHA") + " " + msg, flush=True)
    OK.append(bool(cond))


def cfg(s, nivel):
    return ic.SEMAFORO / "cenarios" / "insper_demanda" / nivel / f"semente_{s}" / "cenario.sumocfg"


def main():
    import numpy as np
    import torch
    torch.set_num_threads(1)
    import ambiente_c5 as env5
    antes = ic.hashes_cenario()
    pasta = AQUI / "resultados" / f"{datetime.datetime.now():%Y%m%dT%H%M%S}_testes"
    pasta.mkdir(parents=True)
    config = dict(env5.CONFIG_V1, **CONFIG)
    mapa = p5.ad.mapeamento(p5.TLS5)

    # 1. estrutura e orcamento
    rede, ag = p5.criar_agentes(11, mapa)
    checar(len(ag) == 5 and all(a.rede is rede for a in ag) and rede.n_aprendizes == 5
           and rede.memoria.capacidade == 250_000 and rede.aquecimento == 10_000 and rede.decaimento == 200_000
           and len(rede.transicoes_por_agente) == 5,
           "5 agentes numa so rede; replay 5x50 mil, aquecimento 5x2000, epsilon em 5x40 mil decisoes, 1 gradiente a cada 5")
    man = json.loads((AQUI.parent / "modelos_finais" / "manifesto.json").read_text(encoding="utf-8"))
    import politica_compartilhada as pc
    _, c3 = pc.carregar(AQUI.parents[3] / man["bracos"]["C"]["sementes_modelo"]["1"]["arquivo"])
    nova = p5.criar_rede(11)
    checar(all(torch.equal(a, b) for a, b in zip(rede.rede.parameters(), nova.rede.parameters()))
           and not all(torch.equal(a, b) for a, b in zip(rede.rede.parameters(), c3.rede.parameters())),
           "inicializacao aleatoria pela semente do modelo; nenhum peso do C3 carregado")
    checar(ag[4].real == {1: 0, 0: 1} and ag[1].real == {1: 0, 0: 1} and ag[0].real == ag[2].real == ag[3].real == {1: 1, 0: 0}
           and ag[4].perm == [0, 1, 2, 3, 5, 4, 6, 7, 8] and ag[1].perm == [1, 0, 3, 2, 5, 4, 6, 8, 7],
           "transformacoes iguais as do adaptador testado no SUMO (Casa do Ator: slots+fase; 302806060: so fase)")

    # 2. episodio curto de treino com os 5
    rede.aquecimento = 64  # so no teste
    reg = []
    orig = p5.VisaoTreinoC5.escolher

    def espiao(self, estado, treinando):
        r = orig(self, estado, treinando)
        reg.append((self.k, self.canon(estado), r[0]))
        return r
    p5.VisaoTreinoC5.escolher = espiao
    pesos0 = [p.detach().clone() for p in rede.rede.parameters()]
    m = env5.rodar_episodio(cfg(1001, "intenso_treino"), pasta / "treino_curto", 1001, ag, "independente", treinando=True,
                            limite=LIM, config=config, controlados=p5.TLS5, monitor_completo=True)
    p5.VisaoTreinoC5.escolher = orig
    por_k = {k: [r for r in reg if r[0] == k] for k in range(5)}
    checar(all(len(por_k[k]) > 50 for k in range(5)) and all(r[1].shape == (13,) and np.isfinite(r[1]).all() for r in reg),
           f"cada agente decide com 13 entradas: {[len(por_k[k]) for k in range(5)]} decisoes")
    n = min(len(por_k[k]) for k in range(5))
    checar(any(len({por_k[k][i][2] for k in range(5)}) > 1 for i in range(n)), "agentes escolhem acoes diferentes entre si")
    checar(all(t > 0 for t in rede.transicoes_por_agente) and sum(rede.transicoes_por_agente) == rede.transicoes == rede.memoria.n,
           f"replay compartilhado recebe experiencias dos 5: {rede.transicoes_por_agente} = {rede.memoria.n}")
    esperado = (rede.transicoes - rede.aquecimento) // 5
    checar(rede.gradientes > 0 and abs(rede.gradientes - esperado) <= 5
           and any(not torch.equal(a, b) for a, b in zip(pesos0, rede.rede.parameters())),
           f"pesos compartilhados atualizados: {rede.gradientes} gradientes (~1 a cada 5 transicoes; esperado ~{esperado})")
    checar(len(m["recompensas"]) == 5 and all(np.isfinite(r) for r in m["recompensas"]),
           f"5 recompensas locais finitas {m['recompensas']}")
    ver = m["seguranca"]["verificacao"]
    checar(m["seguranca"]["violacoes"] == 0 and set(ver) == set(p5.TLS5) and all(
        x["verdes"]["min"] >= 10 and x["amarelos"]["min"] == x["amarelos"]["max"] == 3
        and x["vermelhos_gerais"]["min"] == x["vermelhos_gerais"]["max"] == 2 for x in ver.values()),
        "seguranca nos 5: verde >= 10 s, amarelo 3 s, vermelho geral 2 s, sem conflitos")
    checar(len(m["outros_semaforos"]) == 9 and all(o["erros"] == 0 for o in m["outros_semaforos"].values()),
           "os outros 9 semaforos no programa original")
    checar(set(m["trocas"]) == set(p5.TLS5) and all(c["veiculos"] > 0 for c in m["cruzamentos"].values()),
           f"trocas e metricas por cruzamento registradas: trocas {m['trocas']}")

    # 3. replay guarda a acao EXECUTADA (rede pede sempre a transversal = canonica 0)
    r2, ag2 = p5.criar_agentes(12, mapa)
    r2.escolher = lambda estado, treinando: (0, [0.0, 0.0], False)
    env5.rodar_episodio(cfg(1001, "intenso_treino"), pasta / "sempre_transversal", 1001, ag2, "independente", treinando=True,
                        limite=LIM, config=config, controlados=p5.TLS5)
    uns = int((r2.memoria.a[:r2.memoria.n] == 1).sum())
    interv = sum(a.intervencoes for a in ag2)
    checar(uns == interv and interv > 0,
           f"replay guarda a acao executada (canonica): acoes 1 no replay {uns} = intervencoes {interv} "
           f"(por agente {[a.intervencoes for a in ag2]})")

    # 4. checkpoint
    with tempfile.TemporaryDirectory() as tmp:
        p5.salvar(Path(tmp) / "c.pt", rede, 11, 1, True, config)
        d, nova = p5.carregar(Path(tmp) / "c.pt")
        xs = torch.from_numpy(rede.memoria.s[:32])
        checar(torch.equal(rede.rede(xs), nova.rede(xs)) and nova.memoria.n == rede.memoria.n
               and nova.transicoes_por_agente == rede.transicoes_por_agente and d["config"] == config,
               "checkpoint completo salvo/carregado (pesos, replay de 5 agentes, contadores, config)")

    # 5. avaliacao congelada
    pesos = [p.detach().clone() for p in rede.rede.parameters()]
    n0, g0 = rede.memoria.n, rede.gradientes
    m3 = env5.rodar_episodio(cfg(224, "intenso_validacao"), pasta / "avaliacao", 224, p5.visoes_avaliacao(rede, mapa),
                             "independente", treinando=False, limite=LIM, config=config, controlados=p5.TLS5)
    checar(all(torch.equal(a, b) for a, b in zip(pesos, rede.rede.parameters())) and rede.memoria.n == n0
           and rede.gradientes == g0 and m3["seguranca"]["violacoes"] == 0, "avaliacao com pesos congelados: sem aprendizado")
    ic.conferir_cenario(antes)
    checar(True, "arquivos do cenario inalterados (SHA-256)")
    print(f"{sum(OK)}/{len(OK)} verificacoes OK; saida em {pasta}")
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
