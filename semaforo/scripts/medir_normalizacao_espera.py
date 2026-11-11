"""
Experimento 2: de onde vem a escala das 4 entradas novas (maior espera por
aproximacao)?

Mede a distribuicao da maior espera acumulada por aproximacao, no momento de
cada decisao, SO com dados de treino:
  - os 4 cenarios de treino (equilibrado, assimetrico, pico, saturado);
  - sementes de transito de TREINO (1000 + episodio; aqui 1001-1008);
  - as 3 DQNs fila_excesso de 13 entradas (Experimento 1), a politica mais
    proxima da que a rede de 17 entradas vai encontrar. Elas nao usam a
    entrada nova: so a leem (observa_espera = True nao muda as decisoes).
Nada do cenario girado nem das sementes de teste (1-10) entra aqui.

Saida: resultados/treino_fila_excesso_17_C/normalizacao_espera.json
Uso (de dentro de scripts/):  python medir_normalizacao_espera.py
"""

import json
import os
from multiprocessing import Pool

import numpy as np

import gerar_demanda
import simulacao
from simulacao import APROXIMACOES, DINAMICAS

CENARIOS = ["equilibrado", "assimetrico", "pico", "saturado"]
SEMENTES = {c: [1001 + 4 * k + i for k in range(2)] for i, c in enumerate(CENARIOS)}
MODELOS = [f"dqn_fila_excesso_C_seed{i}" for i in range(3)]
ARQUIVO = os.path.join(simulacao.PASTA, "resultados", "treino_fila_excesso_17_C",
                       "normalizacao_espera.json")


class Coletar:
    def inicio(self, *a):
        self.valores = []

    def passo(self, *a):
        pass

    def decisao(self, obs, escolha):
        self.valores.append([obs.maior_espera[a] for a in APROXIMACOES])

    def fim(self, *a):
        pass


def _rodar(args):
    from dqn import AgenteDQN
    modelo, cenario, seed, rotas = args
    ag = AgenteDQN(treinando=False).carregar(modelo)
    ag.observa_espera = True  # so le a espera; as decisoes continuam de 13 entradas
    col = Coletar()
    simulacao.rodar(ag, cenario, rotas, seed=seed, instrumentacao=col, dinamica=DINAMICAS["C"])
    return cenario, col.valores


def main():
    import dqn
    rotas = {c: gerar_demanda.gerar(c) for c in CENARIOS}
    tarefas = [(m, c, s, rotas[c]) for m in MODELOS for c in CENARIOS for s in SEMENTES[c]]
    with Pool(6) as pool:
        res = pool.map(_rodar, tarefas)
    por_cen = {c: np.array([v for cc, vals in res if cc == c for v in vals]).ravel() for c in CENARIOS}
    todos = np.concatenate(list(por_cen.values()))

    def resumo(x):
        return {"n": int(x.size), **{f"p{q}": float(np.percentile(x, q)) for q in (50, 90, 95, 99)},
                "max": float(x.max()),
                "pct_acima_do_teto": float(100 * np.mean(x > dqn.ESCALA_ESPERA * dqn.TETO_ESPERA)),
                "media_normalizada": float(np.mean(np.minimum(x / dqn.ESCALA_ESPERA, dqn.TETO_ESPERA)))}

    saida = {
        "escolha": {"escala_s": dqn.ESCALA_ESPERA, "teto": dqn.TETO_ESPERA,
                    "formula": f"min(maior_espera / {dqn.ESCALA_ESPERA:g}, {dqn.TETO_ESPERA:g})"},
        "dados": {"cenarios": CENARIOS, "sementes_de_treino": SEMENTES, "modelos": MODELOS,
                  "unidade": "maior espera acumulada (s) por aproximacao, em cada decisao"},
        "todos": resumo(todos),
        "por_cenario": {c: resumo(x) for c, x in por_cen.items()},
    }
    os.makedirs(os.path.dirname(ARQUIVO), exist_ok=True)
    with open(ARQUIVO, "w") as f:
        json.dump(saida, f, indent=1)
    print(json.dumps({k: saida[k] for k in ("todos", "por_cenario")}, indent=1))
    print(f"Salvo em {ARQUIVO}")


if __name__ == "__main__":
    main()
