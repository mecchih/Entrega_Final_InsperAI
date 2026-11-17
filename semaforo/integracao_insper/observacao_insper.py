"""Observacoes no MESMO formato do Cologne8 (ambiente_marl_cologne.vetor_base/estados).

Local, por semaforo com E aproximacoes e P fases verdes:
    filas/25 (E) + carros/35 (E) + fase verde atual one-hot (P)
    + idade do verde/60 limitada a 2 (1) + maior espera/120 limitada a 3 (E)
    + orientacao do supervisor one-hot (n_controladores + 1)
Supervisor:
    vetores locais sem orientacao + ocupacao a jusante por aproximacao/100
    + estagio verde/amarelo/vermelho por semaforo + orientacao one-hot
    + veiculos na rede/escala + parados na rede/escala

Diferenca intencional: no Insper a aproximacao inclui as vias a montante ate
100 m (parando em outro semaforo), porque algumas vias de chegada sao muito
curtas (Rua Quata: 7,1 m). O Cologne8 olhava so a via imediatamente controlada.
As escalas da rede (350/250) vieram do Cologne8 e precisam ser recalibradas.
"""

import math

import numpy as np

ESCALAS = {"fila": 25, "carros": 35, "tempo": 60, "espera": 120, "teto_tempo": 2, "teto_espera": 3,
           "veiculos_rede": 350, "fila_rede": 250}


def area_montante(net, edge_id, alcance=100.0):
    """Vias que levam a `edge_id` ate `alcance` metros antes da linha de retencao."""
    area, fila, vistos = [], [(net.getEdge(edge_id), 0.0)], set()
    while fila:
        e, antes = fila.pop(0)
        if e.getID() in vistos:
            continue
        vistos.add(e.getID())
        area.append(e.getID())
        fim = antes + e.getLength()
        if fim >= alcance or e.getFromNode().getType() == "traffic_light":
            continue
        fila.extend((anterior, fim) for anterior in e.getIncoming())
    return area


class SensoresInsper:
    def __init__(self, conn, net, controladores, alcance=100.0, escalas=None):
        """controladores: lista ordenada de ControladorFasesSeguro."""
        self.conn, self.controladores = conn, controladores
        self.escalas = dict(ESCALAS, **(escalas or {}))
        self.esquemas = []
        dono = {}
        for i, c in enumerate(controladores):
            links = conn.trafficlight.getControlledLinks(c.id)
            entradas = sorted({itens[0][0].rsplit("_", 1)[0] for itens in links})
            areas = [area_montante(net, e, alcance) for e in entradas]
            jusante = [sorted({itens[0][1] for itens in links if itens[0][0].rsplit("_", 1)[0] == e})
                       for e in entradas]
            for j, area in enumerate(areas):
                for edge in area:
                    if edge in dono:
                        raise ValueError(f"via {edge} atribuida a duas aproximacoes")
                    dono[edge] = (i, j)
            self.esquemas.append({"id": c.id, "entradas": entradas, "areas": areas, "jusante": jusante,
                                  "n_acoes": len(c.verdes), "n_base": 3 * len(entradas) + len(c.verdes) + 1})
        self.dono = dono
        n = len(controladores)
        self.n_local = [s["n_base"] + n + 1 for s in self.esquemas]
        self.n_supervisor = (sum(s["n_base"] for s in self.esquemas) + sum(len(s["entradas"]) for s in self.esquemas)
                             + 3 * n + n + 1 + 2)

    def ler(self, dados, tc):
        """dados: conn.vehicle.getAllSubscriptionResults() com ROAD_ID, SPEED e ACCUMULATED_WAITING_TIME."""
        locais = [{"filas": [0] * len(s["entradas"]), "carros": [0] * len(s["entradas"]),
                   "esperas": [0.0] * len(s["entradas"]), "ids": []} for s in self.esquemas]
        fila_rede = 0
        for vid, r in dados.items():
            parado = r[tc.VAR_SPEED] < 0.1
            fila_rede += int(parado)
            alvo = self.dono.get(r[tc.VAR_ROAD_ID])
            if alvo is not None:
                i, j = alvo
                locais[i]["carros"][j] += 1
                locais[i]["ids"].append(vid)
                locais[i]["filas"][j] += int(parado)
                locais[i]["esperas"][j] = max(locais[i]["esperas"][j], float(r[tc.VAR_ACCUMULATED_WAITING_TIME]))
        ocupacao = [[float(np.mean([self.conn.lane.getLastStepOccupancy(l) for l in faixas])) / 100.0
                     for faixas in s["jusante"]] for s in self.esquemas]
        return {"locais": locais, "ocupacao": ocupacao, "carros_rede": len(dados), "fila_rede": fila_rede}

    def vetores(self, foto, agora, orientacao=0):
        n = len(self.controladores)
        if not 0 <= orientacao <= n:
            raise ValueError("orientacao desconhecida")
        objetivo = [float(i == orientacao) for i in range(n + 1)]
        e = self.escalas
        bases = []
        for s, local, c in zip(self.esquemas, foto["locais"], self.controladores):
            verde = c.estagio == "verde"
            v = [x / e["fila"] for x in local["filas"]] + [x / e["carros"] for x in local["carros"]]
            v += [float(verde and k == c.fase) for k in range(s["n_acoes"])]
            v += [min(max(0, agora - c.inicio_verde) / e["tempo"], e["teto_tempo"]) if verde else 0.0]
            v += [min(x / e["espera"], e["teto_espera"]) for x in local["esperas"]]
            if len(v) != s["n_base"] or not all(math.isfinite(x) and x >= 0 for x in v):
                raise ValueError(f"observacao local invalida em {s['id']}")
            bases.append(v)
        sup = sum(bases, []) + sum(foto["ocupacao"], [])
        sup += [float(c.estagio == g) for c in self.controladores for g in ("verde", "amarelo", "vermelho_geral")]
        sup += objetivo + [foto["carros_rede"] / e["veiculos_rede"], foto["fila_rede"] / e["fila_rede"]]
        if len(sup) != self.n_supervisor or not np.isfinite(sup).all():
            raise ValueError("observacao do supervisor invalida")
        return ([np.asarray(b + objetivo, dtype=np.float32) for b in bases],
                np.asarray(sup, dtype=np.float32))
