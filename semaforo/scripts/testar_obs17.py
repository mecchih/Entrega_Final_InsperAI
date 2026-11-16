"""
Testes do Experimento 2: DQN de 17 entradas (13 de sempre + maior espera
acumulada por aproximacao, N, L, S, O).

  1. A observacao da rede de 17 entradas tem exatamente 17 numeros.
  2. As 13 primeiras sao identicas a observacao antiga (estado_para_vetor de 13).
  3. As 4 novas correspondem as direcoes certas (N, L, S, O).
  4. A maior espera de cada aproximacao bate com uma conta independente.
  5. Aproximacao sem carro recebe 0.
  6. Carro que para, anda e para de novo mantem a espera acumulada.
  7. A normalizacao min(espera / 120, 3) e aplicada exatamente.
  8. Todos os valores sao finitos.
  9. A recompensa e a mesma do Experimento 1 (fila_excesso, W = 60, beta = 1), e
     ler a espera nao muda a simulacao.
 10. A dinamica C nao mudou (parametros e rodadas antigas identicas).
 11. Todos os modelos de 13 entradas continuam funcionando (mesma saida, mesmo n).
 12. A rede de 17 entradas e salva e carregada corretamente (e o numero de
     entradas e reconhecido no checkpoint; checkpoint inconsistente e recusado).
 13. O simulador funciona com a observacao nova na hora e no escoamento.
 14. Treino curto (17 entradas, pasta temporaria) e inferencia com o modelo treinado.
 15. avaliar_17.py de ponta a ponta (com o modelo do treino curto no papel das
     3 redes novas) e o teste do carro sozinho nas 9 redes.
 16. Nada muda em modelos/ nem em resultados/.

Uso (de dentro de scripts/):  python testar_obs17.py
"""

import hashlib
import json
import os
import shutil
import tempfile

import numpy as np
import torch

import dqn
import gerar_demanda
import simulacao
import treinar_dqn
from simulacao import APROXIMACOES, DINAMICAS

DIN_C = DINAMICAS["C"]
# mapa via -> aproximacao vindo de gerar_demanda (independente de FAIXAS_ENTRADA)
VIA_PARA_APROX = {via: a for a, via in gerar_demanda.ENTRADA.items()}
CHAVES = ["n_carros", "espera_media", "espera_p95", "espera_max", "fila_media",
          "segundos_escoamento", "veiculos_sem_atendimento", "verde_max_executado_total",
          "intervencoes_seguranca_hora", "intervencoes_seguranca_escoamento"]
RES = os.path.join(simulacao.PASTA, "resultados")


def ok(msg):
    print("OK", msg, flush=True)


def hashes_projeto():
    out = {}
    for pasta in ("modelos", "resultados"):
        for raiz, _, arqs in os.walk(os.path.join(simulacao.PASTA, pasta)):
            for a in arqs:
                c = os.path.join(raiz, a)
                with open(c, "rb") as h:
                    out[c] = hashlib.sha256(h.read()).hexdigest()
    return out


def salvas(arq):
    with open(os.path.join(RES, arq, "avaliacao.json")) as f:
        return {(r["cenario"], r["controlador"], r["seed"]): r["metricas"]
                for r in json.load(f)["rodadas"]}


def espera_independente():
    """Maior espera acumulada por aproximacao, pela lista de TODOS os carros e a
    via em que cada um esta (sem usar as faixas nem simulacao._maior_espera)."""
    tr = simulacao.trafego
    maior = {a: 0.0 for a in APROXIMACOES}
    n = {a: 0 for a in APROXIMACOES}
    for v in tr.vehicle.getIDList():
        a = VIA_PARA_APROX.get(tr.vehicle.getRoadID(v))
        if a is not None:
            n[a] += 1
            maior[a] = max(maior[a], tr.vehicle.getAccumulatedWaitingTime(v))
    return maior, n


class ConferirObs:
    """Em cada decisao confere a observacao de 17 entradas contra a conta
    independente (testes 1-5, 7, 8, 13)."""

    def __init__(self, agente):
        self.agente = agente

    def inicio(self, estados_verdes, duracao):
        self.duracao = duracao
        self.n = {"hora": 0, "escoamento": 0}
        self.vazias = 0
        self.no_teto = 0
        self.maior_visto = 0.0
        self.obs = []

    def passo(self, *a):
        pass

    def decisao(self, obs, escolha):
        maior, n = espera_independente()
        assert obs.maior_espera is not None, "observacao sem maior_espera"
        assert list(obs.maior_espera) == APROXIMACOES, "ordem N, L, S, O"
        assert obs.maior_espera == maior, (obs.segundo, obs.maior_espera, maior)
        for a in APROXIMACOES:
            if n[a] == 0:
                assert obs.maior_espera[a] == 0.0
                self.vazias += 1
        v = self.agente.vetor(obs)
        assert v.shape == (17,) and v.dtype == np.float32
        assert np.array_equal(v[:13], dqn.estado_para_vetor(obs))  # 13 de sempre
        esperado = np.array([min(maior[a] / 120.0, 3.0) for a in APROXIMACOES], dtype=np.float32)
        assert np.array_equal(v[13:], esperado), (v[13:], esperado)
        assert np.all(np.isfinite(v))
        self.no_teto += int(np.sum(v[13:] == 3.0))
        self.maior_visto = max(self.maior_visto, max(maior.values()))
        self.n["hora" if obs.segundo < self.duracao else "escoamento"] += 1
        self.obs.append(obs)

    def fim(self, *a):
        pass


# -------------------------------------------------------------------------
def teste_sumo_direto(tmp):
    """3, 5, 6: carros so do Oeste e do Norte; vermelho 120 s, verde de 3 s so
    para o Oeste (a fila anda um pouco e para de novo), vermelho ate 300 s."""
    rotas = os.path.join(tmp, "carros.rou.xml")
    with open(rotas, "w") as f:
        f.write('<routes><vType id="carro" accel="2.6" decel="4.5" sigma="0" length="5.0" '
                'minGap="2.5" maxSpeed="13.89"/>'
                '<route id="ro" edges="left0A0 A0right0"/><route id="rn" edges="top0A0 A0bottom0"/>'
                + "".join(f'<vehicle id="o{i}" type="carro" route="ro" depart="{3 * i}" '
                          'departLane="0"/>' for i in range(10))
                + "".join(f'<vehicle id="n{i}" type="carro" route="rn" depart="{40 + 5 * i}" '
                          'departLane="1"/>' for i in range(3)) + "</routes>")
    tr = simulacao.trafego
    tr.start(["sumo", "-n", simulacao.REDE, "-r", rotas, "--no-step-log", "true",
              "--no-warnings", "true", "--time-to-teleport", "-1", "--duration-log.disable", "true",
              "--waiting-time-memory", str(simulacao.MEMORIA_ESPERA)])
    n = len(tr.trafficlight.getRedYellowGreenState(simulacao.SEMAFORO))
    verdes = [p.state for p in tr.trafficlight.getAllProgramLogics(simulacao.SEMAFORO)[0].phases
              if "G" in p.state or "g" in p.state]
    contado, serie = {}, {}
    try:
        for t in range(300):
            tr.trafficlight.setRedYellowGreenState(
                simulacao.SEMAFORO, verdes[3] if 120 <= t < 123 else "r" * n)
            tr.simulationStep()
            for v in tr.vehicle.getIDList():
                vel = tr.vehicle.getSpeed(v)
                if vel < 0.1:
                    contado[v] = contado.get(v, 0) + 1
                serie.setdefault(v, []).append((t, vel, tr.vehicle.getRoadID(v)))
            me = simulacao._maior_espera()
            maior, cont = espera_independente()
            assert me == maior, (t, me, maior)
            # a maior espera e a do carro (na via de entrada) que mais tempo ficou parado
            for a in APROXIMACOES:
                ids = [v for v in tr.vehicle.getIDList()
                       if VIA_PARA_APROX.get(tr.vehicle.getRoadID(v)) == a]
                assert me[a] == max((contado.get(v, 0) for v in ids), default=0), (t, a)
            assert me["L"] == 0.0 and me["S"] == 0.0  # sem carros: zero
            if t == 100:
                assert me["O"] > me["N"] > 0, me  # O chegou antes: espera maior
        fim = dict(me)
    finally:
        tr.close()
    para_anda_para = [v for v, s in serie.items() if v.startswith("o") and s[-1][2] == "left0A0"
                      and any(x[1] >= 0.1 for x in s if x[0] > 120) and s[-1][1] < 0.1]
    assert para_anda_para, "nenhum carro parou-andou-parou"
    ok(f"3/5: direcoes certas (O e N com espera, L e S = 0) e igual a conta independente "
       f"em todos os 300 segundos; ex. no fim O = {fim['O']:.0f} s, N = {fim['N']:.0f} s")
    ok(f"6: {len(para_anda_para)} carros do Oeste pararam, andaram no verde de 3 s e pararam "
       f"de novo; a maior espera do Oeste seguiu = segundos parados contados ({fim['O']:.0f} s)")


def main():
    antes = hashes_projeto()
    tmp = tempfile.mkdtemp(prefix="teste_obs17_")
    ref_c, ref_exc = salvas("comparacao_C"), salvas("comparacao_excesso_C")
    pasta_modelos = dqn.PASTA_MODELOS
    try:
        teste_sumo_direto(tmp)

        # 9 e 10: ler a espera nao muda nada; recompensa = Experimento 1; dinamica C
        assert (DIN_C.transicao_corrigida, DIN_C.verde_maximo, DIN_C.filas_no_escoamento,
                DIN_C.nome) == (True, 60, True, "C: transicao corrigida + verde maximo")
        assert (simulacao.AMARELO, simulacao.VERMELHO_GERAL, simulacao.VERDE_MINIMO,
                simulacao.INTERVALO_DECISAO) == (3, 2, 10, 5)
        rotas = {c: gerar_demanda.gerar(c) for c in ("equilibrado", "girado", "assimetrico", "pico")}
        resultados = []
        for forcar in (False, True):
            ag = dqn.AgenteDQN(tipo_recompensa="fila_excesso", treinando=False).carregar(
                "dqn_fila_excesso_C_seed0")
            ag.observa_espera = forcar  # so LE a espera; a rede continua de 13 entradas

            class Obs:
                def inicio(self, *a): self.o = []
                def passo(self, *a): pass
                def decisao(self, obs, e): self.o.append(obs)
                def fim(self, *a): pass
            col = Obs()
            m = simulacao.rodar(ag, "girado", rotas["girado"], seed=1, instrumentacao=col,
                                dinamica=DIN_C)
            rec = [dqn.recompensa_fila_excesso(a, b) for a, b in zip(col.o, col.o[1:])]
            resultados.append((m, rec, col.o))
        (m0, r0, o0), (m1, r1, o1) = resultados
        assert all(m0[k] == m1[k] for k in CHAVES) and r0 == r1
        assert all(x.maior_espera is None for x in o0) and all(x.maior_espera for x in o1)
        assert all(m0[k] == ref_exc[("girado", "DQN excesso C seed0", 1)][k] for k in CHAVES)
        ag17 = dqn.AgenteDQN(tipo_recompensa="fila_excesso", n_entradas=17)
        assert all(ag17.recompensa(a, b) == dqn.recompensa_fila_excesso(a, b, beta=1.0)
                   for a, b in zip(o1, o1[1:]))
        assert (ag17.espera_limite, ag17.beta) == (60.0, 1.0)
        ok(f"9: ler a maior espera nao muda a rodada (metricas e {len(r0)} recompensas iguais, e "
           f"iguais a comparacao_excesso_C); a rede de 17 usa a mesma recompensa fila_excesso "
           f"(W = 60, beta = 1)")

        import avaliar_C
        amostra = [(ref_c, "pico", "Webster", 3), (ref_c, "assimetrico", "Max-Pressure teto (recal. C)", 2),
                   (ref_c, "equilibrado", "DQN C seed1", 3), (ref_exc, "pico", "DQN excesso C seed2", 4)]
        for ref, cen, rot, s in amostra:
            mm = simulacao.rodar(avaliar_C.fabricar(rot), cen, rotas[cen], seed=s, dinamica=DIN_C)
            assert all(mm[k] == ref[(cen, rot, s)][k] for k in CHAVES), (cen, rot, s)
        ok(f"10: parametros da dinamica C (3 s + 2 s, verde minimo 10, verde maximo 60) "
           f"inalterados; {len(amostra) + 1} rodadas antigas identicas (Experimento 1 incluso)")

        # 11: todos os modelos de 13 entradas
        x = torch.rand(64, 13)
        n13 = 0
        for arq in sorted(os.listdir(pasta_modelos)):
            if not arq.endswith(".pt") or "_17_" in arq:
                continue
            n, pesos = dqn.ler_checkpoint(os.path.join(pasta_modelos, arq))
            assert n == 13, arq
            ag = dqn.AgenteDQN(treinando=False).carregar(arq[:-3])
            assert ag.n_entradas == 13 and not ag.observa_espera
            direto = dqn.Rede(13)
            direto.load_state_dict(torch.load(os.path.join(pasta_modelos, arq)))
            assert torch.equal(ag.rede(x), direto(x)), arq
            n13 += 1
        import diagnosticar_equilibrio as de
        with open(os.path.join(RES, "diagnostico_equilibrio", "automato.json")) as f:
            diag = json.load(f)
        for i in range(3):
            ag = dqn.AgenteDQN(treinando=False).carregar(f"dqn_fila_C_seed{i}")
            casos = [c for c in diag[f"DQN C seed{i}"]["casos"]]
            for c in casos:
                r = de._automato(ag, c["verde"], c["carro_em"], carros=c["carros"])
                assert r[0] == c["resultado"], (i, c, r)
        ok(f"11: {n13} modelos de 13 entradas reconhecidos (13) e com saida identica a carga "
           f"direta do state_dict; teste do carro sozinho das DQN C igual ao diagnostico")

        # 12: salvar / carregar 17
        dqn.PASTA_MODELOS = os.path.join(tmp, "modelos")
        a17 = dqn.AgenteDQN(n_entradas=17, semente=0)
        a17.salvar("rede17")
        bruto = torch.load(os.path.join(dqn.PASTA_MODELOS, "rede17.pt"))
        assert bruto["formato"] == "dqn_v2" and bruto["n_entradas"] == 17
        assert bruto["observacao"][13:] == [f"min(maior_espera_{a}/120, 3)" for a in APROXIMACOES]
        b17 = dqn.AgenteDQN(treinando=False).carregar("rede17")  # comeca com 13, vira 17
        assert b17.n_entradas == 17 and b17.observa_espera
        y = torch.rand(64, 17)
        assert torch.equal(a17.rede(y), b17.rede(y)) and torch.equal(b17.rede_alvo(y), b17.rede(y))
        a13 = dqn.AgenteDQN(semente=0)
        a13.salvar("rede13")
        assert not isinstance(torch.load(os.path.join(dqn.PASTA_MODELOS, "rede13.pt")).get(
            "formato"), str)  # 13 entradas: state_dict puro, como sempre
        torch.save({"formato": "dqn_v2", "n_entradas": 13, "state_dict": bruto["state_dict"]},
                   os.path.join(dqn.PASTA_MODELOS, "ruim.pt"))
        try:
            dqn.AgenteDQN().carregar("ruim")
            raise AssertionError("checkpoint inconsistente deveria ser recusado")
        except ValueError:
            pass
        ok("12: rede de 17 salva com o registro (formato dqn_v2, n_entradas 17, descricao da "
           "observacao) e recarregada com saidas identicas; 13 entradas continuam no formato "
           "antigo; checkpoint inconsistente e recusado")

        # 14: treino curto de 17 entradas + inferencia
        dqn.PASTA_MODELOS = pasta_modelos
        nome = os.path.join(tmp, "modelos", "dqn_fila_excesso_17_C_teste")
        espioes = []
        orig = treinar_dqn.AgenteDQN

        class Espiao(dqn.AgenteDQN):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                espioes.append(self)
        treinar_dqn.AgenteDQN = Espiao
        try:
            treinar_dqn.treinar("fila_excesso", episodios=4, semente=0, dinamica="C",
                                nome=nome, historico=os.path.join(tmp, "h17.json"), verboso=False,
                                intervalo_validacao=2, sementes_validacao=[201], n_entradas=17,
                                parametros_recompensa={"espera_limite": 60.0, "beta": 1.0})
        finally:
            treinar_dqn.AgenteDQN = orig
        ag = espioes[0]
        assert all(len(t[0]) == 17 and len(t[3]) == 17 for t in ag.memoria)
        assert all(np.all(np.isfinite(t[0])) for t in ag.memoria)
        with open(os.path.join(tmp, "h17.json")) as f:
            h = json.load(f)
        assert h["n_entradas"] == 17 and h["recompensa"] == "fila_excesso"
        assert h["parametros_recompensa"] == {"espera_limite": 60.0, "beta": 1.0}
        assert h["sementes_validacao"] == [201] and h["dinamica"] == DIN_C.nome
        assert "justica" in h["validacoes"][0]
        no_teto = sum(int(np.sum(t[0][13:] == 3.0)) for t in ag.memoria)
        ok(f"14a: treino curto de 17 entradas (4 episodios, dinamica C): {len(ag.memoria)} "
           f"experiencias de 17 numeros, todas finitas ({no_teto} entradas de espera no teto 3, "
           f"da exploracao aleatoria); historico registra n_entradas, recompensa e justica")

        inf = dqn.AgenteDQN(treinando=False).carregar(nome)
        assert inf.n_entradas == 17
        conf = ConferirObs(inf)
        m = simulacao.rodar(inf, "pico", rotas["pico"], seed=1, instrumentacao=conf, dinamica=DIN_C)
        assert conf.n["hora"] > 0 and conf.n["escoamento"] > 0
        ok(f"1-5, 7, 8, 13: inferencia com o modelo treinado (pico, semente 1): "
           f"{conf.n['hora']} decisoes na hora e {conf.n['escoamento']} no escoamento, todas com "
           f"17 numeros finitos, 13 primeiros = observacao antiga, maior espera N/L/S/O = conta "
           f"independente, normalizacao exata; {conf.vazias} aproximacoes vazias = 0; maior "
           f"espera vista {conf.maior_visto:.0f} s (espera media da rodada {m['espera_media']:.1f} s)")

        # 15: avaliar_17 de ponta a ponta, com o modelo do treino curto nas 3 vagas de C
        import avaliar_17
        pasta = os.path.join(tmp, "modelos_av")
        os.makedirs(pasta)
        for i in range(3):
            shutil.copy(nome + ".pt", os.path.join(pasta, f"dqn_fila_excesso_17_C_seed{i}.pt"))
            for base in ("dqn_fila_C_seed", "dqn_fila_excesso_C_seed"):
                shutil.copy(os.path.join(pasta_modelos, f"{base}{i}.pt"), pasta)
        dqn.PASTA_MODELOS = pasta
        saida = os.path.join(tmp, "saida17")
        avaliar_17.main(["--processos", "1", "--sementes", "1", "--saida", saida])
        dqn.PASTA_MODELOS = pasta_modelos
        with open(os.path.join(saida, "avaliacao.json")) as f:
            av = json.load(f)
        origem = {}
        for r in av["rodadas"]:
            origem.setdefault(r["origem"], set()).add(r["controlador"])
        assert origem["rodada agora"] == set(avaliar_17.NOVAS)
        assert origem["comparacao_excesso_C/avaliacao.json"] == set(avaliar_17.GERACOES[avaliar_17.GB])
        assert origem["comparacao_C/avaliacao.json"] == set(
            avaliar_17.REFERENCIAS + avaliar_17.GERACOES[avaliar_17.GA])
        assert len(av["rodadas"]) == 5 * (2 + 9)
        with open(os.path.join(saida, "resumo.json")) as f:
            rs = json.load(f)
        auto = rs["carro_sozinho"]
        assert len(auto) == 9 and {v["n_entradas"] for v in auto.values()} == {13, 17}
        assert [auto[f"DQN C seed{i}"]["presos"] for i in range(3)] == [0, 3, 3]
        assert all(auto[f"DQN excesso C seed{i}"]["presos"] == 0 for i in range(3))
        assert rs["criterios"] is not None and os.path.exists(os.path.join(saida, "resumo.md"))
        ok(f"15: avaliar_17 de ponta a ponta: 15 rodadas novas (so a geracao C), A/Webster/MP "
           f"de comparacao_C e B de comparacao_excesso_C reaproveitadas; carro sozinho nas 9 "
           f"redes (A: 0/3/3 presos, B: 0/0/0, como antes); criterios e relatorio gerados")
    finally:
        dqn.PASTA_MODELOS = pasta_modelos
        shutil.rmtree(tmp, ignore_errors=True)
        for raiz, _, arqs in os.walk(RES):
            for a in arqs:
                c = os.path.join(raiz, a)
                if a.startswith("_tmp_tripinfo") and c not in antes:
                    os.remove(c)

    depois = hashes_projeto()
    assert antes == depois, sorted(set(antes.items()) ^ set(depois.items()))
    ok(f"16: {len(antes)} arquivos de modelos/ e resultados/ intactos, nenhum criado")
    print("\nTUDO OK")


if __name__ == "__main__":
    main()
