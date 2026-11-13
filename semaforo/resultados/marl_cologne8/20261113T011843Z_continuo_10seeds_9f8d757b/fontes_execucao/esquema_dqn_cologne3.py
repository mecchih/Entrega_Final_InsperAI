"""Formato local proposto para DQNs de cologne3. Nao inicia treinamento."""

import json
import math
from pathlib import Path

FORMATO = "dqn_multi_local_v1"
REFERENCIA = Path(__file__).resolve().parents[1] / "referencias/cologne3_sumo_rl_1.4.5"


def carregar_esquemas(path=None):
    path = path or REFERENCIA / "esquema_proposto.json"
    return json.loads(Path(path).read_text(encoding="utf-8"))["controladores"]


def vetor_local(esquema, filas, carros, maior_espera, fase_verde, tempo_no_verde):
    """Fase e um indice LOCAL, nao a direcao geografica nem uma luz individual.

    A chamada e feita somente durante verde e antes de uma decisao valida.
    Amarelo/vermelho e bloqueio de decisao ficam no controlador de seguranca.
    """
    entradas = [a["edge"] for a in esquema["entradas"]]
    n_fases = len(esquema["fases"])
    if not isinstance(fase_verde, int) or not 0 <= fase_verde < n_fases:
        raise ValueError("Fase inexistente para este controlador")
    for label, values in [("filas", filas), ("carros", carros), ("maior_espera", maior_espera)]:
        if set(values) != set(entradas):
            raise ValueError(f"Entradas de {label} diferem do esquema local")
        if not all(math.isfinite(v) and v >= 0 for v in values.values()):
            raise ValueError(f"Valores invalidos em {label}")
    if not math.isfinite(tempo_no_verde) or tempo_no_verde < 0:
        raise ValueError("Tempo de verde invalido")
    vector = [filas[e] / 25.0 for e in entradas]
    vector += [carros[e] / 35.0 for e in entradas]
    vector += [float(i == fase_verde) for i in range(n_fases)]
    vector += [min(tempo_no_verde / 60.0, 2.0)]
    vector += [min(maior_espera[e] / 120.0, 3.0) for e in entradas]
    if len(vector) != esquema["n_entradas_rede"]:
        raise ValueError("Dimensao calculada diverge do manifesto")
    return vector


def estados_das_acoes(esquemas, acoes):
    """Um estado de luzes por controlador; nao existe exclusao global de verde."""
    by_id = {s["id"]: s for s in esquemas}
    if set(acoes) != set(by_id):
        raise ValueError("Deve haver uma acao para cada controlador")
    out = {}
    for tls, action in acoes.items():
        phases = by_id[tls]["fases"]
        if not isinstance(action, int) or not 0 <= action < len(phases):
            raise ValueError(f"Acao invalida em {tls}: {action}")
        out[tls] = phases[action]["state"]
    return out


def criar_rede_local(esquema):
    """Constroi arquitetura, mas nao otimiza nem salva pesos. Torch so sob demanda."""
    import torch.nn as nn
    return nn.Sequential(
        nn.Linear(esquema["n_entradas_rede"], 64), nn.ReLU(),
        nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, esquema["n_acoes"]),
    )
