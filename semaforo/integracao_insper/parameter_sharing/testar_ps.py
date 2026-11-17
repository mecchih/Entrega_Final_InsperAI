"""Testes do Modelo C (Parameter Sharing) antes do treino. Episodios curtos (300-1500 s), sem treino real.

uso: python -B -X utf8 semaforo/integracao_insper/parameter_sharing/testar_ps.py
"""

import datetime
from pathlib import Path
import sys
import tempfile

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import politica_compartilhada as pc  # noqa: E402
import insper_comum as ic  # noqa: E402
import ambiente_marl_insper_v2 as amb  # noqa: E402
import treinar_ps as tps  # noqa: E402

LIM = 1500
OK = []


def checar(cond, msg):
    print(("OK   " if cond else "FALHA") + " " + msg, flush=True)
    OK.append(bool(cond))


def cfg(s, nivel):
    return ic.SEMAFORO / "cenarios" / "insper_demanda" / nivel / f"semente_{s}" / "cenario.sumocfg"


def main():
    import numpy as np
    import torch
    torch.set_num_threads(1)
    antes = ic.hashes_cenario()
    pasta = AQUI / "resultados" / f"{datetime.datetime.now():%Y%m%dT%H%M%S}_testes"
    pasta.mkdir(parents=True)
    config = dict(amb.CONFIG_V1, **tps.CONFIG)

    # 0. compatibilidade da representacao (rede SUMO, sem simular)
    ori = pc.orientacao_canonica()
    checar(ori == {"476455095": False, "40278305": True, "40278183": False},
           f"slot j servido pela fase 1-j nos 3 cruzamentos; so Casa do Ator precisa permutar: {ori}")
    v = pc.VisaoAgente(None, 1, True)
    x = np.arange(13, dtype=np.float32)
    checar(v.canon(x).tolist() == [1, 0, 3, 2, 5, 4, 6, 8, 7, 9, 10, 11, 12] and v.acao_real(v.acao_canonica(0)) == 0
           and v.acao_real(0) == 1, "permutacao da observacao e traducao da acao (involucao) corretas")
    checar(amb.N_LOCAL == pc.N_LOCAL == 13 and amb.ACOES_LOCAL == pc.ACOES == 2, "13 entradas e 2 acoes, como o Modelo A")

    # 1-7, 9-10. episodio curto de treino com registro das decisoes de cada agente
    rede, agentes = pc.criar_agentes(7, (0, 1, 2), ori)
    rede.aquecimento = 64  # so no teste, para haver gradientes num episodio curto
    checar(all(a.rede is rede for a in agentes) and len({id(a.rede.rede) for a in agentes}) == 1,
           "os 3 agentes usam o MESMO objeto de rede (online, alvo e replay)")
    registro = []
    original = pc.VisaoAgente.escolher

    def espiao(self, estado, treinando):
        r = original(self, estado, treinando)
        registro.append((self.k, np.asarray(estado).copy(), r[0]))
        return r
    pc.VisaoAgente.escolher = espiao
    pesos0 = [p.detach().clone() for p in rede.rede.parameters()]
    m = amb.rodar_episodio(cfg(1001, "intenso_treino"), pasta / "treino_curto", 1001, agentes, "independente",
                           treinando=True, monitor_completo=True, limite=LIM, config=config)
    pc.VisaoAgente.escolher = original
    por_k = {k: [e for kk, e, _ in registro if kk == k] for k in range(3)}
    checar(all(len(por_k[k]) > 50 for k in range(3)) and all(e.shape == (13,) and np.isfinite(e).all()
                                                               for _, e, _ in registro),
           f"cada agente decide sozinho com observacao de 13 entradas finitas: {[len(por_k[k]) for k in range(3)]} decisoes")
    medias = [np.mean(por_k[k], axis=0)[:4] for k in range(3)]
    checar(not np.allclose(medias[0], medias[1]) and not np.allclose(medias[1], medias[2]),
           f"observacoes diferentes por cruzamento (filas/carros medios {[np.round(mm, 2).tolist() for mm in medias]})")
    acoes_por_k = {k: [a for kk, _, a in registro if kk == k] for k in range(3)}
    checar(all(set(acoes_por_k[k]) == {0, 1} for k in range(3)), "cada agente escolhe as duas acoes ao longo do episodio")
    n = min(len(acoes_por_k[k]) for k in range(3))
    checar(any(len({acoes_por_k[k][i] for k in range(3)}) > 1 for i in range(n)), "agentes escolhem acoes diferentes entre si")
    checar(all(t > 0 for t in rede.transicoes_por_agente) and sum(rede.transicoes_por_agente) == rede.transicoes
           == rede.memoria.n, f"replay compartilhado recebe experiencias dos 3: {rede.transicoes_por_agente} = {rede.memoria.n}")
    esperado = (rede.transicoes - rede.aquecimento) // 3
    checar(rede.gradientes > 0 and abs(rede.gradientes - esperado) <= 3
           and any(not torch.equal(a, b) for a, b in zip(pesos0, rede.rede.parameters())),
           f"pesos compartilhados atualizados: {rede.gradientes} gradientes (~1 a cada 3 transicoes, esperado ~{esperado})")
    checar(all(isinstance(r, float) and np.isfinite(r) for r in m["recompensas"]), f"recompensas finitas {m['recompensas']}")
    ver = m["seguranca"]["verificacao"]
    checar(m["seguranca"]["violacoes"] == 0 and all(x["verdes"]["min"] >= 10 and x["amarelos"]["min"] == x["amarelos"]["max"] == 3
                                                    and x["vermelhos_gerais"]["min"] == x["vermelhos_gerais"]["max"] == 2
                                                    for x in ver.values()),
           "seguranca: verde >= 10 s, amarelo 3 s, vermelho geral 2 s, sem conflitos")
    checar(len(m["outros_semaforos"]) == 11 and all(o["erros"] == 0 for o in m["outros_semaforos"].values()),
           "os outros 11 semaforos ficaram no programa original")

    # 8. checkpoint salvo e carregado
    with tempfile.TemporaryDirectory() as tmp:
        pc.salvar(Path(tmp) / "c.pt", rede, 7, 1, True, config, (0, 1, 2))
        d, nova = pc.carregar(Path(tmp) / "c.pt")
        xs = torch.from_numpy(rede.memoria.s[:32])
        checar(torch.equal(rede.rede(xs), nova.rede(xs)) and nova.memoria.n == rede.memoria.n
               and nova.transicoes_por_agente == rede.transicoes_por_agente and d["config"] == config,
               "checkpoint completo salvo/carregado (pesos, replay, contadores e config)")

    # replay guarda a acao EXECUTADA: a rede sempre pede a acao canonica 0 (verde da transversal)
    rede2, ag2 = pc.criar_agentes(8, (0, 1, 2), ori)
    rede2.escolher = lambda estado, treinando: (0, [0.0, 0.0], False)
    m2 = amb.rodar_episodio(cfg(1001, "intenso_treino"), pasta / "sempre_transversal", 1001, ag2, "independente",
                            treinando=True, limite=LIM, config=config)
    uns = int((rede2.memoria.a[:rede2.memoria.n] == 1).sum())
    interv = sum(a.intervencoes for a in ag2)
    checar(uns == interv and interv > 0,
           f"replay guarda a acao executada (canonica): acoes 1 no replay {uns} = intervencoes do verde maximo {interv}")

    # transferencia: Casa do Ator fora do treino
    rede3, ag3 = pc.criar_agentes(9, (0, 2), ori)
    rede3.aquecimento = 64
    m3 = amb.rodar_episodio(cfg(1002, "intenso_treino"), pasta / "transferencia", 1002, ag3, "independente",
                            treinando=True, limite=LIM, config=config)
    checar(rede3.transicoes_por_agente[1] == 0 and rede3.transicoes_por_agente[0] > 0 and rede3.transicoes_por_agente[2] > 0
           and rede3.n_aprendizes == 2 and ag3[1].decisoes_proprias > 0 and m3["seguranca"]["violacoes"] == 0,
           f"transferencia: cruzamento 40278305 decide pela regra classica e nao alimenta o replay {rede3.transicoes_por_agente}")

    # avaliacao congelada: pesos e replay nao mudam
    pesos = [p.detach().clone() for p in rede.rede.parameters()]
    n_antes, g_antes = rede.memoria.n, rede.gradientes
    m4 = amb.rodar_episodio(cfg(224, "intenso_validacao"), pasta / "avaliacao", 224, pc.visoes_avaliacao(rede, ori),
                            "independente", treinando=False, limite=LIM, config=config)
    checar(all(torch.equal(a, b) for a, b in zip(pesos, rede.rede.parameters())) and rede.memoria.n == n_antes
           and rede.gradientes == g_antes and m4["seguranca"]["violacoes"] == 0,
           "avaliacao com pesos congelados: nenhum aprendizado")
    ic.conferir_cenario(antes)
    checar(True, "arquivos do cenario original inalterados (SHA-256)")
    print(f"{sum(OK)}/{len(OK)} verificacoes OK; saida em {pasta}")
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
