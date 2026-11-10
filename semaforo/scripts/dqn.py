"""
O agente que aprende -- um DQN (Deep Q-Network).

A ideia do DQN em uma frase: em vez de alguem programar a regra, a rede
neural aprende a responder "se eu der verde para esta aproximacao agora,
quanto de fila eu vou ter acumulado daqui para frente?". Depois e so
escolher a opcao de melhor resposta.

Quem ensina isso a rede e a propria experiencia: ela chuta, ve a fila que
deu, e corrige. O truque do Q-learning e que ela nao precisa esperar o fim
da hora para saber se acertou -- ela se corrige usando a propria estimativa
do momento seguinte (o tal "bootstrapping").

Encaixa no mesmo molde dos semaforos tradicionais: tem um metodo decidir(obs)
e e medido exatamente do mesmo jeito.
"""

import os
import random
from collections import deque

import numpy as np
import torch
import torch.nn as nn

from simulacao import APROXIMACOES, Controlador, INTERVALO_DECISAO

PASTA_MODELOS = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "modelos")
)

# --- Como a situacao do cruzamento vira numeros para a rede ---------------
# Tudo aqui e informacao que um semaforo real teria com sensores no asfalto.
# Nada de espiar o futuro, nada de "em qual cenario estou".
ESCALA_FILA = 25.0
ESCALA_CARROS = 35.0
ESCALA_TEMPO = 60.0
TAMANHO_ESTADO = 4 + 4 + 4 + 1  # filas + carros + fase atual + tempo no verde
N_ACOES = 4


def estado_para_vetor(obs):
    v = []
    v += [obs.filas[a] / ESCALA_FILA for a in APROXIMACOES]
    v += [obs.carros[a] / ESCALA_CARROS for a in APROXIMACOES]
    v += [1.0 if a == obs.aprox_verde else 0.0 for a in APROXIMACOES]
    v += [min(obs.tempo_no_verde / ESCALA_TEMPO, 2.0)]
    return np.array(v, dtype=np.float32)


# --- As duas recompensas que vamos comparar -------------------------------
ESCALA_RECOMPENSA = 100.0


def recompensa_fila(obs_antes, obs_depois):
    """Carros x segundos de fila no intervalo, com sinal negativo.

    Esta e a recompensa certa. Por que: ela mede a fila INTEGRADA no tempo,
    entao o agente paga pelos 5 segundos de amarelo/vermelho geral em que
    ninguem anda. Trocar de fase sem motivo machuca -- como deve ser.
    """
    delta = obs_depois.fila_acumulada - obs_antes.fila_acumulada
    return -delta / ESCALA_RECOMPENSA


def recompensa_espera(obs_antes, obs_depois):
    """Tempo de espera acumulado, com sinal negativo.

    Esta e a recompensa INTUITIVA e provavelmente ruim -- e exatamente por
    isso ela esta aqui: para ser comparada. A suspeita e que ela ensina o
    agente a deixar a rua secundaria parada, porque a espera de poucos
    carros pesa pouco na media.
    """
    delta = obs_depois.espera_acumulada - obs_antes.espera_acumulada
    return -delta / (ESCALA_RECOMPENSA * 10)


RECOMPENSAS = {"fila": recompensa_fila, "espera": recompensa_espera}


class Rede(nn.Module):
    """A rede neural. Pequena de proposito: o problema tem 13 numeros de
    entrada e 4 opcoes de saida -- rede grande so acrescentaria instabilidade."""

    def __init__(self, n_entrada=TAMANHO_ESTADO, n_saida=N_ACOES, oculta=64):
        super().__init__()
        self.camadas = nn.Sequential(
            nn.Linear(n_entrada, oculta),
            nn.ReLU(),
            nn.Linear(oculta, oculta),
            nn.ReLU(),
            nn.Linear(oculta, n_saida),
        )

    def forward(self, x):
        return self.camadas(x)


class AgenteDQN(Controlador):
    """O semaforo que aprende."""

    nome = "DQN"

    def __init__(self, tipo_recompensa="fila", gamma=0.95, lr=5e-4,
                 tamanho_lote=64, memoria=50_000, aquecimento=2_000,
                 atualizar_alvo=500, treinando=True, semente=0):
        self.recompensa = RECOMPENSAS[tipo_recompensa]
        self.tipo_recompensa = tipo_recompensa
        self.gamma = gamma
        self.tamanho_lote = tamanho_lote
        self.aquecimento = aquecimento
        self.atualizar_alvo = atualizar_alvo
        self.treinando = treinando

        torch.manual_seed(semente)
        self.rede = Rede()
        # A "rede alvo" e uma copia congelada, atualizada de vez em quando.
        # Serve para o agente nao ficar perseguindo a propria sombra: se o
        # alvo mudasse a cada passo, o treino nao estabilizaria.
        self.rede_alvo = Rede()
        self.rede_alvo.load_state_dict(self.rede.state_dict())
        self.otimizador = torch.optim.Adam(self.rede.parameters(), lr=lr)

        self.memoria = deque(maxlen=memoria)
        # Em paralelo a memoria (mesma ordem, mesmo tamanho): o que a rede
        # PEDIU e se a regra de seguranca do simulador trocou o pedido. Fica
        # separado para nao mudar o formato que _aprender amostra.
        self.memoria_info = deque(maxlen=memoria)
        self.intervencoes_total = 0
        self.intervencoes_episodio = 0
        self._acao_pedida_anterior = None
        self.epsilon = 1.0
        self.passos = 0
        self.passos_treino = 0
        self.perdas = []
        self.recompensa_episodio = 0.0

        self._obs_anterior = None
        self._acao_anterior = None
        self._segundo_anterior = None

    # --- interface de Controlador ----------------------------------------
    def reiniciar(self):
        self._obs_anterior = None
        self._acao_anterior = None
        self._acao_pedida_anterior = None
        self._segundo_anterior = None
        self.recompensa_episodio = 0.0
        self.intervencoes_episodio = 0

    def acao_substituida(self, pedida, executada):
        """Chamado pelo simulador quando a regra de seguranca troca a acao.

        A experiencia guardada passa a usar a acao EXECUTADA: a recompensa e
        o proximo estado que vierem a seguir sao consequencia dela, nao do
        pedido. Como o DQN aprende fora da politica (off-policy), uma
        transicao (estado, acao executada, recompensa, proximo estado) e uma
        amostra valida do ambiente, nao importa quem escolheu a acao.
        """
        if pedida != self._acao_anterior:
            raise RuntimeError("acao_substituida fora de ordem")
        self._acao_pedida_anterior = pedida
        self._acao_anterior = int(executada)
        self.intervencoes_episodio += 1
        if self.treinando:  # total = so episodios de treino (nao a validacao)
            self.intervencoes_total += 1

    def decidir(self, obs):
        # 1) fecha a conta da decisao anterior
        if self._obs_anterior is not None:
            r = self.recompensa(self._obs_anterior, obs)
            dt = max(obs.segundo - self._segundo_anterior, 1)
            self.recompensa_episodio += r
            if self.treinando:
                self.memoria.append((
                    estado_para_vetor(self._obs_anterior),
                    self._acao_anterior,
                    r,
                    estado_para_vetor(obs),
                    dt,
                ))
                pedida = self._acao_pedida_anterior
                self.memoria_info.append({
                    "acao_pedida": self._acao_anterior if pedida is None else pedida,
                    "acao_executada": self._acao_anterior,
                    "intervencao": pedida is not None,
                })
                self._aprender()

        # 2) escolhe a proxima acao
        acao = self._escolher(obs)

        self._obs_anterior = obs
        self._acao_anterior = acao
        self._acao_pedida_anterior = None
        self._segundo_anterior = obs.segundo
        self.passos += 1
        return acao

    def encerrar(self):
        pass

    # --- miolo do DQN -----------------------------------------------------
    def _escolher(self, obs):
        if self.treinando and random.random() < self.epsilon:
            return random.randrange(N_ACOES)
        with torch.no_grad():
            q = self.rede(torch.from_numpy(estado_para_vetor(obs)).unsqueeze(0))
        return int(torch.argmax(q, dim=1).item())

    def _aprender(self):
        if len(self.memoria) < self.aquecimento:
            return
        lote = random.sample(self.memoria, self.tamanho_lote)
        estados, acoes, recompensas, proximos, dts = zip(*lote)

        estados = torch.from_numpy(np.stack(estados))
        proximos = torch.from_numpy(np.stack(proximos))
        acoes = torch.tensor(acoes, dtype=torch.int64).unsqueeze(1)
        recompensas = torch.tensor(recompensas, dtype=torch.float32).unsqueeze(1)
        # Desconto ajustado pela duracao real do intervalo: trocar de fase
        # gasta mais segundos que manter, e o desconto precisa saber disso.
        descontos = torch.tensor(
            [self.gamma ** (dt / INTERVALO_DECISAO) for dt in dts],
            dtype=torch.float32,
        ).unsqueeze(1)

        q_atual = self.rede(estados).gather(1, acoes)

        with torch.no_grad():
            # Double DQN: a rede principal ESCOLHE a melhor acao futura e a
            # rede alvo AVALIA ela. Separar as duas coisas evita o vicio
            # classico do DQN de superestimar o valor das acoes.
            melhor = torch.argmax(self.rede(proximos), dim=1, keepdim=True)
            q_futuro = self.rede_alvo(proximos).gather(1, melhor)
            alvo = recompensas + descontos * q_futuro

        perda = nn.functional.smooth_l1_loss(q_atual, alvo)
        self.otimizador.zero_grad()
        perda.backward()
        nn.utils.clip_grad_norm_(self.rede.parameters(), 10.0)
        self.otimizador.step()

        self.perdas.append(float(perda.item()))
        self.passos_treino += 1
        if self.passos_treino % self.atualizar_alvo == 0:
            self.rede_alvo.load_state_dict(self.rede.state_dict())

    # --- salvar / carregar ------------------------------------------------
    def salvar(self, nome):
        os.makedirs(PASTA_MODELOS, exist_ok=True)
        caminho = os.path.join(PASTA_MODELOS, f"{nome}.pt")
        torch.save(self.rede.state_dict(), caminho)
        return caminho

    def carregar(self, nome):
        caminho = os.path.join(PASTA_MODELOS, f"{nome}.pt")
        self.rede.load_state_dict(torch.load(caminho))
        self.rede_alvo.load_state_dict(self.rede.state_dict())
        self.treinando = False
        self.epsilon = 0.0
        return self
