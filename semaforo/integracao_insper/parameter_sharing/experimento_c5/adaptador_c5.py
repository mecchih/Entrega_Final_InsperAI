"""Adaptador zero-shot C3 -> C5: a MESMA DoubleDQN do Modelo C (pesos congelados) em 5 cruzamentos.

Referencial canonico (o que a rede viu no treino com 3 cruzamentos):
  slot 0 = aproximacao da via PRINCIPAL, slot 1 = transversal (filas, carros, maior espera);
  fase one-hot canonica: posicao 0 = verde da transversal, posicao 1 = verde da via principal;
  acao canonica 1 = verde da via principal, acao canonica 0 = verde da transversal;
  as 4 ultimas entradas = codigo "sem supervisor" [1, 0, 0, 0].
Via principal: Ribeirao Claro nos 3 do corredor (como no Modelo C) e Rua Fiandeiras nos 2 novos
(a via de maior volume, com o mesmo numero de faixas da transversal).

A transformacao de cada cruzamento e DERIVADA da rede (programa + ligacoes), nao escrita a mao:
  slot_principal = posicao da aproximacao principal na ordem do sensor (ids das vias em ordem alfabetica)
  fase_principal = indice da fase verde que serve a aproximacao principal (a outra serve a transversal)
Resultado (conferido em testar_c5.py):
  476455095  principal no slot 0, servida pela fase 1 -> identidade
  40278305   principal no slot 1, servida pela fase 0 -> troca slots e fases; acao real = 1 - canonica
  40278183   principal no slot 0, servida pela fase 1 -> identidade
  300058973  principal no slot 0, servida pela fase 1 -> identidade
  302806060  principal no slot 0, servida pela fase 0 -> troca SO a fase one-hot; acao real = 1 - canonica
Para os 3 originais a transformacao e identica a de politica_compartilhada.py (testado).
"""

from pathlib import Path
import sys

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI.parents[1]))
import insper_comum as ic  # noqa: E402

TLS3 = list(ic.CONTROLADOS)
NOVOS = ["300058973", "302806060"]
TLS5 = TLS3 + NOVOS
PRINCIPAL = {"476455095": "Rua Ribeirão Claro", "40278305": "Rua Ribeirão Claro", "40278183": "Rua Ribeirão Claro",
             "300058973": "Rua Fiandeiras", "302806060": "Rua Fiandeiras"}


def _rede():
    ic.sumo_home()
    import sumolib
    return sumolib.net.readNet(str(ic.REDE), withPrograms=True)


def mapeamento(tls_ids, net=None):
    """{tls: dict(slot_principal, fase_principal, entradas, nomes, perm_obs, acao_real={canonica: real})}."""
    net = net or _rede()
    saida = {}
    for t in tls_ids:
        tl = net.getTLS(t)
        con = sorted(tl.getConnections(), key=lambda c: c[2])
        prog = list(tl.getPrograms().values())[0]
        verdes = [p.state for p in prog.getPhases() if "y" not in p.state]
        entradas = sorted({i.getEdge().getID() for i, o, li in con})
        if len(entradas) != 2 or len(verdes) != 2:
            raise RuntimeError(f"{t}: o adaptador exige 2 aproximacoes e 2 fases verdes")
        servida = []
        for e in entradas:
            links = [li for i, o, li in con if i.getEdge().getID() == e]
            fases = [k for k, v in enumerate(verdes) if all(v[li] in "Gg" for li in links)]
            vermelho = [k for k, v in enumerate(verdes) if all(v[li] == "r" for li in links)]
            if len(fases) != 1 or len(vermelho) != 1 or fases[0] == vermelho[0]:
                raise RuntimeError(f"{t}: a aproximacao {e} nao e servida por exatamente uma fase verde")
            servida.append(fases[0])
        if sorted(servida) != [0, 1]:
            raise RuntimeError(f"{t}: as duas aproximacoes sao servidas pela mesma fase")
        nomes = [net.getEdge(e).getName() for e in entradas]
        principais = [j for j, n in enumerate(nomes) if n == PRINCIPAL[t]]
        if len(principais) != 1:
            raise RuntimeError(f"{t}: via principal {PRINCIPAL[t]} ambigua em {nomes}")
        sp = principais[0]
        fp = servida[sp]
        fc = 1 - fp
        perm = [sp, 1 - sp, 2 + sp, 2 + (1 - sp), 4 + fc, 4 + fp, 6, 7 + sp, 7 + (1 - sp)]
        saida[t] = {"entradas": entradas, "nomes": nomes, "slot_principal": sp, "fase_principal": fp,
                    "fase_transversal": fc, "perm_obs": perm, "acao_real": {1: fp, 0: fc}}
    return saida


class VisaoC5:
    """Agente k: observacao propria -> referencial canonico -> rede compartilhada (congelada) -> acao real."""

    acoes = 2

    def __init__(self, rede, k, mapa):
        self.rede, self.k, self.mapa = rede, k, mapa
        self.perm = mapa["perm_obs"]
        self.real = mapa["acao_real"]
        self.canonica = {v: c for c, v in self.real.items()}
        self.intervencoes = 0
        self.registro = None  # lista opcional de (estado_canonico, acao_canonica, acao_real)

    def canon(self, estado):
        import numpy as np
        e = np.asarray(estado, dtype=np.float32)
        if e.shape != (13,):
            raise ValueError("observacao local deve ter 13 entradas")
        return np.concatenate([e[self.perm], e[9:]]).astype(np.float32)

    def escolher(self, estado, treinando):
        if treinando:
            raise RuntimeError("experimento zero-shot: avaliacao sem aprendizado")
        c = self.canon(estado)
        a, q, _ = self.rede.escolher(c, False)
        real = self.real[int(a)]
        if self.registro is not None:
            self.registro.append((self.k, c, int(a), real))
        return real, [q[self.canonica[0]], q[self.canonica[1]]], False

    def lembrar(self, *args, **kwargs):
        if args and args[-1] or kwargs.get("treinando"):
            raise RuntimeError("experimento zero-shot: o replay nao recebe experiencias")


def visoes(rede, tls_ids, mapa=None):
    mapa = mapa or mapeamento(tls_ids)
    return [VisaoC5(rede, k, mapa[t]) for k, t in enumerate(tls_ids)]
