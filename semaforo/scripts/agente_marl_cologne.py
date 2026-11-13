"""Double DQN para o experimento hierarquico; nao importa/altera modelos antigos."""

from collections import deque
import random

import numpy as np
import torch
from torch import nn


class Replay:
    def __init__(self, entradas, tamanho=50_000):
        self.capacidade = tamanho
        self.posicao = self.n = 0
        self.s = np.empty((tamanho, entradas), dtype=np.float32)
        self.s2 = np.empty_like(self.s)
        self.a = np.empty(tamanho, dtype=np.int64)
        self.r = np.empty(tamanho, dtype=np.float32)
        self.dt = np.empty(tamanho, dtype=np.float32)
        self.fim = np.empty(tamanho, dtype=np.float32)

    def adicionar(self, s, a, r, s2, dt, fim):
        if dt <= 0 or not np.isfinite(r):
            raise ValueError("Experiencia sem duracao ou recompensa finita")
        i = self.posicao
        self.s[i], self.s2[i] = s, s2
        self.a[i], self.r[i], self.dt[i], self.fim[i] = a, r, dt, fim
        self.posicao = (i + 1) % self.capacidade
        self.n = min(self.n + 1, self.capacidade)

    def estado(self):
        return {"capacidade": self.capacidade, "n": self.n, "posicao": self.posicao,
                **{k: torch.from_numpy(getattr(self, k)[:self.n].copy())
                   for k in ("s", "s2", "a", "r", "dt", "fim")}}

    def carregar(self, dados):
        if dados["capacidade"] != self.capacidade:
            raise ValueError("Capacidade de replay diferente")
        self.n, self.posicao = dados["n"], dados["posicao"]
        for k in ("s", "s2", "a", "r", "dt", "fim"):
            getattr(self, k)[:self.n] = dados[k].numpy()


class DoubleDQN:
    def __init__(self, entradas, acoes, semente, supervisor=False,
                 aquecimento=2000, lote=64):
        self.entradas, self.acoes = entradas, acoes
        self.semente = int(semente)
        self.rng = random.Random(self.semente)
        self.np_rng = np.random.default_rng(self.semente)
        self.gamma, self.lote = 0.95, lote
        self.aquecimento = max(aquecimento, lote)
        self.decaimento = 40_000 if not supervisor else 10_000
        self.decisoes = self.gradientes = self.intervencoes = 0
        self.perdas = deque(maxlen=200)
        with torch.random.fork_rng():
            torch.manual_seed(self.semente)
            self.rede = nn.Sequential(nn.Linear(entradas, 64), nn.ReLU(),
                                      nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, acoes))
            self.alvo = nn.Sequential(nn.Linear(entradas, 64), nn.ReLU(),
                                      nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, acoes))
        self.alvo.load_state_dict(self.rede.state_dict())
        self.alvo.eval().requires_grad_(False)
        self.otimizador = torch.optim.Adam(self.rede.parameters(), lr=5e-4)
        self.memoria = Replay(entradas)

    @property
    def epsilon(self):
        return max(0.05, 1.0 - self.decisoes / self.decaimento)

    def escolher(self, estado, treinando):
        estado = np.asarray(estado, dtype=np.float32)
        if estado.shape != (self.entradas,) or not np.isfinite(estado).all():
            raise ValueError("Estado invalido")
        self.rede.train(treinando)
        with torch.inference_mode():
            q = self.rede(torch.from_numpy(estado)).numpy()
        if not np.isfinite(q).all():
            raise ValueError("Q nao finito")
        explorou = treinando and self.rng.random() < self.epsilon
        acao = self.rng.randrange(self.acoes) if explorou else int(q.argmax())
        if treinando:
            self.decisoes += 1
        return acao, q.tolist(), bool(explorou)

    def lembrar(self, s, a, r, s2, dt, fim, treinando):
        if not treinando:
            return
        if not 0 <= a < self.acoes:
            raise ValueError("Acao fora da rede local")
        self.memoria.adicionar(s, a, r, s2, dt, fim)
        if self.memoria.n < self.aquecimento:
            return
        m = self.memoria
        ids = self.np_rng.choice(m.n, self.lote, replace=False)
        s, s2 = torch.from_numpy(m.s[ids]), torch.from_numpy(m.s2[ids])
        a = torch.from_numpy(m.a[ids]).unsqueeze(1)
        r, dt, fim = (torch.from_numpy(v[ids]).unsqueeze(1) for v in (m.r, m.dt, m.fim))
        atual = self.rede(s).gather(1, a)
        with torch.no_grad():
            escolhido = self.rede(s2).argmax(dim=1, keepdim=True)
            futuro = self.alvo(s2).gather(1, escolhido)
            alvo = r + self.gamma ** (dt / 5.0) * (1.0 - fim) * futuro
        perda = nn.functional.smooth_l1_loss(atual, alvo)
        if not torch.isfinite(perda):
            raise ValueError("Perda nao finita")
        self.otimizador.zero_grad(set_to_none=True)
        perda.backward()
        nn.utils.clip_grad_norm_(self.rede.parameters(), 10.0, error_if_nonfinite=True)
        self.otimizador.step()
        self.gradientes += 1
        self.perdas.append(float(perda.detach()))
        if self.gradientes % 500 == 0:
            self.alvo.load_state_dict(self.rede.state_dict())

    def estado(self, completo=False):
        dados = {"entradas": self.entradas, "acoes": self.acoes,
                 "rede": self.rede.state_dict(), "semente": self.semente,
                 "decisoes": self.decisoes, "gradientes": self.gradientes,
                 "intervencoes": self.intervencoes, "decaimento": self.decaimento,
                 "gamma": self.gamma, "lote": self.lote, "aquecimento": self.aquecimento}
        if completo:
            dados.update(alvo=self.alvo.state_dict(), otimizador=self.otimizador.state_dict(),
                         memoria=self.memoria.estado(), rng=self.rng.getstate(),
                         np_rng=self.np_rng.bit_generator.state, perdas=list(self.perdas))
        return dados

    def carregar(self, dados, completo=False):
        if (dados["entradas"], dados["acoes"]) != (self.entradas, self.acoes):
            raise ValueError("Checkpoint de outra arquitetura")
        self.rede.load_state_dict(dados["rede"], strict=True)
        self.semente = dados["semente"]
        if not all(torch.isfinite(v).all() for v in self.rede.state_dict().values()):
            raise ValueError("Peso invalido")
        self.alvo.load_state_dict(dados.get("alvo", dados["rede"]), strict=True)
        self.decisoes, self.gradientes = dados["decisoes"], dados["gradientes"]
        self.intervencoes, self.decaimento = dados["intervencoes"], dados["decaimento"]
        self.gamma, self.lote, self.aquecimento = dados["gamma"], dados["lote"], dados["aquecimento"]
        if completo:
            self.otimizador.load_state_dict(dados["otimizador"])
            self.memoria.carregar(dados["memoria"])
            self.rng.setstate(dados["rng"])
            self.np_rng.bit_generator.state = dados["np_rng"]
            self.perdas.extend(dados["perdas"])
