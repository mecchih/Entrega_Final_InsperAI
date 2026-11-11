"""
Testes do treinamento na dinamica C (antes de rodar os treinos completos).

Confere que:
  1. o treino com --dinamica C chama o simulador com a dinamica C em TODOS
     os episodios;
  2. a transicao executada no treino tem 3 s de amarelo + 2 s de vermelho
     geral e o verde dura exatamente o que o agente contou;
  3. a regra de verde maximo funciona durante o treino e as intervencoes
     sao contadas;
  4. cada experiencia guardada na memoria e exatamente
     (estado, acao EXECUTADA, recompensa, proximo estado, duracao) e a
     memoria paralela registra a acao pedida e a intervencao;
  5. a validacao que escolhe o checkpoint usa a mesma dinamica do treino e
     nunca o cenario girado;
  6. o treino antigo (dinamica A) reproduz treino_fila_original.json;
  7. a avaliacao das DQNs antigas na dinamica C nao mudou com a alteracao;
  8. nenhum modelo/resultado existente e alterado ou apagado, e o treino se
     recusa a sobrescrever um modelo que ja existe;
  9. a fila acumulada da observacao (base da recompensa) e a soma exata dos
     carros parados segundo a segundo -- na dinamica C tambem durante o
     escoamento; na A ela continua congelando no fim da hora, como antes.

Tudo que o teste treina vai para uma pasta temporaria.
Uso (de dentro de scripts/):  python testar_treino_C.py
"""

import hashlib
import json
import os
import random
import shutil
import tempfile

import numpy as np

import analisar_comportamento as ac
import dqn
import gerar_demanda
import simulacao
import treinar_dqn
from simulacao import AMARELO, APROXIMACOES, DINAMICAS, INTERVALO_DECISAO, VERMELHO_GERAL

EPISODIOS_REPRODUCAO = 6


def hashes_projeto():
    out = {}
    for pasta in ["modelos", "resultados"]:
        raiz = os.path.join(simulacao.PASTA, pasta)
        for dirpath, _, arquivos in os.walk(raiz):
            for a in arquivos:
                if a.startswith("_tmp_"):
                    continue
                p = os.path.join(dirpath, a)
                with open(p, "rb") as f:
                    out[os.path.relpath(p, simulacao.PASTA)] = hashlib.sha256(f.read()).hexdigest()
    return out


# -------------------------------------------------------------------------
# Espioes: registram o que o treino realmente faz, sem mudar nada
# -------------------------------------------------------------------------
CHAMADAS = []
_rodar_original = simulacao.rodar


def rodar_espiao(controlador, cenario, arquivo_rotas, seed, **kw):
    """Envolve simulacao.rodar: guarda os argumentos e confere, com a
    instrumentacao, os estados executados segundo a segundo."""
    reg = ac.Registro()
    outra = kw.pop("instrumentacao", None)  # a da validacao (EsperasPorAprox)
    m = _rodar_original(controlador, cenario, arquivo_rotas, seed,
                        instrumentacao=reg if outra is None else Ambas(reg, outra), **kw)
    segs = reg.segmentos()
    ac.checar_consistencia(reg, segs, m, kw.get("dinamica"))  # erro se inconsistente
    CHAMADAS.append({
        "cenario": cenario, "seed": seed, "dinamica": kw.get("dinamica"),
        "treinando": getattr(controlador, "treinando", None),
        "amarelos": {s["dur"] for s in segs[:-1] if s["tipo"] == "amarelo"},
        "vermelhos": {s["dur"] for s in segs[:-1] if s["tipo"] == "vermelho"},
        "decisoes_executadas": [d["escolha"] for d in reg.decisoes],
        "intervencoes": len(reg.intervencoes),
        # verde mantido alem do limite COM carro esperando em outra aproximacao
        "violacoes_verde_maximo": sum(
            1 for d in reg.decisoes
            if kw.get("dinamica") is not None and kw["dinamica"].verde_maximo is not None
            and d["escolha"] == d["verde"]
            and d["tempo_no_verde"] >= kw["dinamica"].verde_maximo
            and any(c > 0 for j, c in enumerate(d["carros"]) if j != d["verde"])),
        "maior_verde_completo": max([s["dur"] for s in segs if s["tipo"] == "verde"
                                     and s["completo"]] or [0]),
        "metricas": m,
    })
    return m


class Ambas:
    """Repassa os ganchos da rodada para duas instrumentacoes."""

    def __init__(self, *insts):
        self.insts = insts

    def __getattr__(self, nome):
        alvos = [getattr(i, nome) for i in self.insts if hasattr(i, nome)]
        if not alvos:
            raise AttributeError(nome)
        return lambda *a: [f(*a) for f in alvos][-1]


class ConferirFila:
    """Instrumentacao que soma, por conta propria, os carros parados nas
    faixas de entrada apos cada segundo simulado, para conferir a
    fila_acumulada que o controlador recebe em cada decisao."""

    @staticmethod
    def _parados():
        return sum(simulacao.trafego.lane.getLastStepHaltingNumber(f)
                   for faixas in simulacao.FAIXAS_ENTRADA.values() for f in faixas)

    def inicio(self, estados_verdes, duracao):
        self.duracao = duracao
        self.acum = 0  # parados apos os passos ja somados
        self.acum_hora = None
        self.decisoes = []

    def passo(self, t, estado):
        if t >= 1:  # le o resultado do passo t-1
            self.acum += self._parados()
        if t == self.duracao:
            self.acum_hora = self.acum  # soma dos passos 0..duracao-1

    def decisao(self, obs, escolha):
        esperado = self.acum + self._parados()  # inclui o passo t-1
        self.decisoes.append((obs.segundo, obs.fila_acumulada, esperado))

    def fim(self, caminho):
        pass


class AgenteEspiao(dqn.AgenteDQN):
    """AgenteDQN normal que anota cada decisao (para conferir a memoria)."""
    prob_manter = None  # se definido, no treino pede MANTER com essa chance

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.log = []  # por decisao: obs, pedida, executada, treinando

    def reiniciar(self):
        super().reiniciar()
        self.log.append(None)  # separador de episodio

    def _escolher(self, obs):
        if self.treinando and self.prob_manter is not None and random.random() < self.prob_manter:
            return APROXIMACOES.index(obs.aprox_verde)
        return super()._escolher(obs)

    def decidir(self, obs):
        acao = super().decidir(obs)
        self.log.append({"obs": obs, "pedida": acao, "executada": acao,
                         "treinando": self.treinando})
        return acao

    def acao_substituida(self, pedida, executada):
        super().acao_substituida(pedida, executada)
        self.log[-1]["executada"] = int(executada)


class AgenteTeimoso(AgenteEspiao):
    prob_manter = 0.95


def conferir_memoria(agente, din):
    """Reconstroi as experiencias a partir do log e compara com a memoria."""
    esperado, info = [], []
    episodio = []
    for item in agente.log + [None]:
        if item is None:
            if episodio and episodio[0]["treinando"]:
                for a, b in zip(episodio, episodio[1:]):
                    esperado.append((
                        dqn.estado_para_vetor(a["obs"]), a["executada"],
                        agente.recompensa(a["obs"], b["obs"]),
                        dqn.estado_para_vetor(b["obs"]),
                        max(b["obs"].segundo - a["obs"].segundo, 1)))
                    info.append((a["pedida"], a["executada"], a["pedida"] != a["executada"]))
            episodio = []
        else:
            episodio.append(item)
    mem = list(agente.memoria)
    erros = []
    if len(mem) != len(esperado) or len(agente.memoria_info) != len(esperado):
        erros.append(f"memoria {len(mem)} / info {len(agente.memoria_info)} / esperado {len(esperado)}")
    for k, (m, e, i) in enumerate(zip(mem, esperado, agente.memoria_info)):
        if not (np.array_equal(m[0], e[0]) and m[1] == e[1] and m[2] == e[2]
                and np.array_equal(m[3], e[3]) and m[4] == e[4]):
            erros.append(f"experiencia {k} difere")
        if (i["acao_pedida"], i["acao_executada"], i["intervencao"]) != info[k]:
            erros.append(f"info {k} difere")
    # consequencia da acao executada: o proximo verde e o da acao executada,
    # e a duracao bate com manter (5 s) ou trocar (5 s de transicao + 10 s minimo)
    duracoes = set()
    for m in mem:
        atual = int(np.argmax(m[0][8:12]))
        prox = int(np.argmax(m[3][8:12]))
        if prox != m[1]:
            erros.append(f"proximo verde {prox} != acao executada {m[1]}")
        duracoes.add(("manter" if m[1] == atual else "trocar", m[4]))
    troca = AMARELO + VERMELHO_GERAL + 10 if din.transicao_corrigida else 15
    if not duracoes <= {("manter", INTERVALO_DECISAO), ("trocar", troca)}:
        erros.append(f"duracoes inesperadas: {duracoes}")
    return erros, duracoes


# -------------------------------------------------------------------------
def main():
    antes = hashes_projeto()
    tmp = tempfile.mkdtemp(prefix="teste_treino_C_")
    falhas = 0
    simulacao.rodar = rodar_espiao  # treinar_dqn chama simulacao.rodar
    try:
        # 8a. recusa sobrescrever
        try:
            treinar_dqn.treinar(episodios=1, nome="dqn_fila", verboso=False)
            ok = False
        except FileExistsError:
            ok = True
        falhas += not ok
        print(f"8. treino recusa sobrescrever modelos/dqn_fila.pt: {'ok' if ok else 'FALHOU'}")

        # 1/2/4/5. treino curto normal na dinamica C, validando a cada 2 episodios
        CHAMADAS.clear()
        treinar_dqn.AgenteDQN = AgenteEspiao
        agentes = []
        orig_init = AgenteEspiao.__init__

        def init_guardando(self, *a, **kw):
            orig_init(self, *a, **kw)
            agentes.append(self)
        AgenteEspiao.__init__ = init_guardando
        treinar_dqn.treinar(episodios=4, semente=0, nome=os.path.join(tmp, "dqn_C_teste"),
                            historico=os.path.join(tmp, "treino_C_teste.json"),
                            dinamica="C", intervalo_validacao=2, sementes_validacao=[201],
                            verboso=False)
        AgenteEspiao.__init__ = orig_init
        agente = agentes[-1]
        C = DINAMICAS["C"]
        treino = [c for c in CHAMADAS if c["treinando"]]
        valid = [c for c in CHAMADAS if not c["treinando"]]
        ok1 = len(treino) == 4 and all(c["dinamica"] is C for c in CHAMADAS)
        ok2 = all(c["amarelos"] == {AMARELO} and c["vermelhos"] == {VERMELHO_GERAL}
                  for c in CHAMADAS)
        ok5 = (len(valid) == 2 * 4 and all(c["dinamica"] is C for c in valid)
               and {c["cenario"] for c in CHAMADAS} == set(treinar_dqn.CENARIOS_TREINO)
               and all(c["seed"] == 201 for c in valid))
        erros, duracoes = conferir_memoria(agente, C)
        ok4 = not erros
        # transicoes de treino inteiramente no escoamento com recompensa negativa
        esc = [(a["obs"], b["obs"]) for a, b in zip(agente.log, agente.log[1:])
               if a and b and a["treinando"] and a["obs"].segundo >= 3600]
        esc_neg = sum(1 for a, b in esc if agente.recompensa(a, b) < 0)
        hist = json.load(open(os.path.join(tmp, "treino_C_teste.json")))
        ok_hist = ("C:" in hist["dinamica"] and os.path.exists(os.path.join(tmp, "dqn_C_teste.pt"))
                   and len(hist["validacoes"]) == 2)
        for n, ok, txt in [(1, ok1, "todas as chamadas do treino usam a dinamica C"),
                           (2, ok2, "amarelo 3 s e vermelho geral 2 s em todas as rodadas"),
                           (4, ok4, f"memoria = experiencias reconstruidas ({len(agente.memoria)} "
                                    f"transicoes; duracoes {sorted(duracoes)})" + (f" {erros[:3]}" if erros else "")),
                           (5, ok5 and ok_hist, "validacao na dinamica C, sem girado, checkpoint "
                                                "e historico salvos na pasta temporaria")]:
            falhas += not ok
            print(f"{n}. {txt}: {'ok' if ok else 'FALHOU'}")
        ok9b = len(esc) > 0 and esc_neg > 0
        falhas += not ok9b
        print(f"9b. treino C: {len(esc)} transicoes no escoamento, {esc_neg} com recompensa "
              f"negativa (antes eram todas zero): {'ok' if ok9b else 'FALHOU'}")

        # 3. regra de seguranca no treino: agente que quase sempre pede manter
        CHAMADAS.clear()
        treinar_dqn.AgenteDQN = AgenteTeimoso
        agentes.clear()
        orig_init_t = AgenteTeimoso.__init__

        def init_t(self, *a, **kw):
            orig_init_t(self, *a, **kw)
            agentes.append(self)
        AgenteTeimoso.__init__ = init_t
        treinar_dqn.treinar(episodios=2, semente=1, nome=os.path.join(tmp, "dqn_teimoso"),
                            historico=os.path.join(tmp, "treino_teimoso.json"),
                            dinamica="C", intervalo_validacao=10, verboso=False)
        AgenteTeimoso.__init__ = orig_init_t
        teimoso = agentes[-1]
        hist = json.load(open(os.path.join(tmp, "treino_teimoso.json")))
        n_sim = sum(c["intervencoes"] for c in CHAMADAS)
        n_hist = sum(h["intervencoes_seguranca"] for h in hist["historico"])
        n_mem = sum(1 for i in teimoso.memoria_info if i["intervencao"])
        erros, duracoes = conferir_memoria(teimoso, C)
        # um verde so passa de 60 s se ninguem espera do outro lado (ex.: fim
        # do escoamento); por isso conferimos os verdes ENCERRADOS e as decisoes
        maior = max(c["maior_verde_completo"] for c in CHAMADAS)
        violacoes = sum(c["violacoes_verde_maximo"] for c in CHAMADAS)
        ok3 = (n_sim > 0 and n_sim == n_hist == hist["intervencoes_seguranca_treino"]
               == teimoso.intervencoes_total and n_mem > 0 and n_mem <= n_sim
               and not erros and maior <= C.verde_maximo and violacoes == 0)
        falhas += not ok3
        print(f"3. regra de seguranca no treino: {n_sim} intervencoes no simulador = {n_hist} no "
              f"historico; {n_mem} experiencias marcadas como intervencao; maior verde encerrado {maior} s; verdes mantidos alem de 60 s com carro "
              f"esperando: {violacoes}; "
              f"memoria consistente={not erros}: {'ok' if ok3 else 'FALHOU'}")
        if erros:
            print("   ", erros[:3])

        # 6. treino antigo reproduzivel
        CHAMADAS.clear()
        treinar_dqn.AgenteDQN = dqn.AgenteDQN
        treinar_dqn.treinar(episodios=EPISODIOS_REPRODUCAO, semente=0,
                            nome=os.path.join(tmp, "dqn_A"),
                            historico=os.path.join(tmp, "treino_A.json"), verboso=False)
        novo = json.load(open(os.path.join(tmp, "treino_A.json")))["historico"]
        velho = json.load(open(os.path.join(simulacao.PASTA, "resultados",
                                            "treino_fila_original.json")))["historico"]
        iguais = all(all(n[k] == v[k] for k in v) for n, v in zip(novo, velho))
        ok6 = (iguais and len(novo) == EPISODIOS_REPRODUCAO
               and all(c["dinamica"] is None for c in CHAMADAS)
               and novo[-1]["perda"] is not None)
        falhas += not ok6
        print(f"6. dinamica A reproduz os {EPISODIOS_REPRODUCAO} primeiros episodios de "
              f"treino_fila_original.json (incl. aprendizado): {'ok' if ok6 else 'FALHOU'}")
    finally:
        simulacao.rodar = _rodar_original
        treinar_dqn.AgenteDQN = dqn.AgenteDQN

    # 7. avaliacao na dinamica C: mesmas metricas da avaliacao anterior (a
    # fila acumulada no escoamento so muda a recompensa, nao o controle)
    salvo = json.load(open(os.path.join(simulacao.PASTA, "resultados",
                                        "seguranca_transicao", "rodadas.json")))
    com_int = [r for r in salvo["rodadas"] if r["modo"] == "C"
               and r["controlador"].startswith("DQN") and r["intervencoes"]][:3]
    outros = [r for r in salvo["rodadas"] if r["modo"] == "C" and r["seed"] == 1
              and r["cenario"] == "saturado" and not r["controlador"].startswith("DQN")]
    ok7 = bool(com_int) and bool(outros)
    for r in com_int + outros:
        m = simulacao.rodar(ac.fabricar(r["controlador"]), r["cenario"],
                            gerar_demanda.gerar(r["cenario"]), seed=r["seed"],
                            dinamica=DINAMICAS["C"])
        ok7 = ok7 and m == r["metricas"]
    falhas += not ok7
    print(f"7. {len(com_int)} rodadas de DQN antigas (com intervencao) e {len(outros)} de "
          f"tradicionais na dinamica C identicas as de resultados/seguranca_transicao: "
          f"{'ok' if ok7 else 'FALHOU'}")

    # 9. fila acumulada da observacao = soma exata, segundo a segundo, dos
    # carros parados (C: tambem no escoamento; A: congela no fim da hora)
    for chave in ["C", "A"]:
        conf = ConferirFila()
        m = simulacao.rodar(ac.fabricar("DQN seed2"), "equilibrado",
                            gerar_demanda.gerar("equilibrado"), seed=1,
                            instrumentacao=conf,
                            dinamica=DINAMICAS[chave] if chave == "C" else None)
        hora = [(o, e) for t, o, e in conf.decisoes if t < 3600]
        esc = [(t, o, e) for t, o, e in conf.decisoes if t >= 3600]
        ok_hora = all(o == e for o, e in hora)
        if chave == "C":
            ok_esc = all(o == e for _, o, e in esc)
        else:
            congelado = conf.acum_hora
            ok_esc = all(o == congelado for _, o, _ in esc)
        ok9 = ok_hora and ok_esc and len(esc) > 0
        falhas += not ok9
        print(f"9. dinamica {chave}: fila acumulada exata em {len(hora)} decisoes da hora; "
              f"{len(esc)} decisoes no escoamento "
              f"{'somando os carros parados' if chave == 'C' else 'com o valor congelado (original)'}"
              f" (escoamento {m['segundos_escoamento']} s): {'ok' if ok9 else 'FALHOU'}")

    depois = hashes_projeto()
    alterados = [k for k in antes if depois.get(k) != antes[k]]
    novos = [k for k in depois if k not in antes]
    ok8 = not alterados and not novos
    falhas += not ok8
    print(f"8. {len(antes)} arquivos de modelos/ e resultados/ intactos; alterados/apagados: "
          f"{alterados or 'nenhum'}; criados: {novos or 'nenhum'}: {'ok' if ok8 else 'FALHOU'}")
    shutil.rmtree(tmp, ignore_errors=True)

    print("\nTUDO OK" if falhas == 0 else f"\n{falhas} FALHAS")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
