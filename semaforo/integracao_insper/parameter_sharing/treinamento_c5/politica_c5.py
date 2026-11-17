"""Modelo C5: Parameter Sharing com CINCO agentes treinados juntos, desde o primeiro episodio.

Reaproveita sem alterar:
  - a rede compartilhada do Modelo C (politica_compartilhada.criar_rede): a mesma DoubleDQN 13 -> 64 -> 64 -> 2,
    agora com n_aprendizes = 5 (replay 5 x 50 mil, aquecimento 5 x 2000, epsilon em 5 x 40 mil decisoes e
    UM gradiente a cada 5 transicoes = o mesmo numero de atualizacoes por rede que o C3 e o Modelo A);
  - o mapeamento canonico derivado da rede (experimento_c5/adaptador_c5.mapeamento), ja testado no SUMO;
  - o ambiente generalizado (experimento_c5/ambiente_c5.py) com controlados = os 5.
O adaptador zero-shot (VisaoC5) recusa treino de proposito; aqui ha uma visao PROPRIA para treino.
Inicializacao aleatoria (semente do modelo); nenhum peso do C3 e carregado.
"""

from pathlib import Path
import sys

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))                       # politica_compartilhada
sys.path.insert(0, str(AQUI.parent / "experimento_c5"))    # adaptador_c5, ambiente_c5
sys.path.insert(0, str(AQUI.parents[1]))                   # insper_comum
sys.path.insert(0, str(AQUI.parents[1] / "otimizacao_final"))
import adaptador_c5 as ad  # noqa: E402
import politica_compartilhada as pc  # noqa: E402

FORMATO = "smartflow_marl_insper_parameter_sharing_c5_v1"
TLS5 = ad.TLS5


def criar_rede(semente):
    rede = pc.criar_rede(semente, n_aprendizes=len(TLS5))
    rede.transicoes_por_agente = [0] * len(TLS5)  # o contador do C3 tinha 3 posicoes
    return rede


class VisaoTreinoC5:
    """Agente k: observacao propria -> referencial canonico -> rede compartilhada; guarda no replay
    compartilhado a transicao com a acao EXECUTADA traduzida para o referencial canonico."""

    acoes = 2

    def __init__(self, rede, k, mapa):
        self.rede, self.k, self.mapa = rede, k, mapa
        self.perm = mapa["perm_obs"]
        self.real = {int(c): int(f) for c, f in mapa["acao_real"].items()}
        self.canonica = {f: c for c, f in self.real.items()}
        self.intervencoes = 0
        self.decisoes = self.decisoes_vazias = 0  # vazias: nenhum veiculo nas duas aproximacoes

    def canon(self, estado):
        import numpy as np
        e = np.asarray(estado, dtype=np.float32)
        if e.shape != (13,):
            raise ValueError("observacao local deve ter 13 entradas")
        return np.concatenate([e[self.perm], e[9:]]).astype(np.float32)

    def escolher(self, estado, treinando):
        c = self.canon(estado)
        self.decisoes += 1
        self.decisoes_vazias += int(c[2] == 0 and c[3] == 0)
        a, q, explorou = self.rede.escolher(c, treinando)
        return self.real[int(a)], [q[self.canonica[0]], q[self.canonica[1]]], explorou

    def lembrar(self, s, a, r, s2, dt, fim, treinando):
        self.rede.lembrar_de(self.k, self.canon(s), self.canonica[int(a)], r, self.canon(s2), dt, fim, treinando)

    @property
    def memoria(self):
        return self.rede.memoria

    @property
    def gradientes(self):
        return self.rede.gradientes

    @property
    def perdas(self):
        return self.rede.perdas

    @property
    def epsilon(self):
        return self.rede.epsilon


def criar_agentes(semente, mapa=None):
    mapa = mapa or ad.mapeamento(TLS5)
    rede = criar_rede(semente)
    return rede, [VisaoTreinoC5(rede, k, mapa[t]) for k, t in enumerate(TLS5)]


def visoes_avaliacao(rede, mapa=None):
    mapa = mapa or ad.mapeamento(TLS5)
    return [VisaoTreinoC5(rede, k, mapa[t]) for k, t in enumerate(TLS5)]


def salvar(path, rede, semente, episodio, completo, config):
    import torch
    with Path(path).open("xb") as f:
        torch.save({"formato": FORMATO, "config": config, "semente_modelo": semente, "episodio": episodio,
                    "tls": TLS5, "mapeamento": {t: {k: v for k, v in m.items()} for t, m in ad.mapeamento(TLS5).items()},
                    "completo_para_retomada": completo, "rede": rede.estado(completo)}, f)


def carregar(path):
    import torch
    d = torch.load(path, map_location="cpu", weights_only=False)
    if d["formato"] != FORMATO or d["tls"] != TLS5:
        raise ValueError("checkpoint de outro formato")
    rede = criar_rede(d["semente_modelo"])
    rede.carregar(d["rede"], completo=d["completo_para_retomada"])
    return d, rede
