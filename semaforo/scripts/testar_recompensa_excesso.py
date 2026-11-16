"""
Testes da recompensa fila_excesso (Experimento 1 de equilibrio).

  0. Configuracao: rodar() passa --waiting-time-memory 10000 ao SUMO.
  1. beta = 0 reproduz a recompensa original: transicao a transicao numa rodada
     inteira, e num treino curto (historico e pesos identicos ao treino 'fila').
  2. O excesso medido bate com uma contagem independente segundo a segundo
     (velocidade de cada carro), em todas as decisoes de uma rodada inteira.
  3. Carro que para, anda um pouco e para de novo: a espera acumulada nao zera
     (getWaitingTime zera; getAccumulatedWaitingTime nao) -- SUMO direto.
  4. Carro parado mais de 100 s: com memoria 10000 a espera passa de 100; com o
     padrao do SUMO (100 s) ela ficaria travada em 100 -- SUMO direto.
  5. Escoamento: o excesso continua sendo medido e a recompensa fica mais
     negativa que a 'fila' quando ha carro esperando ha muito.
  6. A dinamica C nao mudou: mesmos parametros, e rodadas de avaliacao (inclusive
     com o medidor de excesso ligado) identicas a comparacao_C/avaliacao.json.
  7. Modelos e avaliacoes antigos continuam reproduziveis (amostra aqui; a bateria
     completa e testar_dinamica.py + testar_treino_C.py).
  8. Treino curto fila_excesso em pasta temporaria: memoria com a recompensa certa,
     historico com metricas de justica, nada gravado em modelos/ ou resultados/.

Uso (de dentro de scripts/):  python testar_recompensa_excesso.py
"""

import hashlib
import json
import os
import shutil
import tempfile

import torch

import dqn
import gerar_demanda
import simulacao
import treinar_dqn
from simulacao import DINAMICAS, VIAS_ENTRADA

DIN_C = DINAMICAS["C"]
W = dqn.ESPERA_LIMITE
AVALIACAO_C = os.path.join(simulacao.PASTA, "resultados", "comparacao_C", "avaliacao.json")
CHAVES = ["n_carros", "espera_media", "espera_p95", "espera_max", "fila_media",
          "segundos_escoamento", "veiculos_sem_atendimento", "verde_max_executado_total",
          "intervencoes_seguranca_hora", "intervencoes_seguranca_escoamento"]


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


def salvas():
    with open(AVALIACAO_C) as f:
        return {(r["cenario"], r["controlador"], r["seed"]): r["metricas"]
                for r in json.load(f)["rodadas"]}


# -------------------------------------------------------------------------
# Contagem independente: segundos parados de cada carro, pela velocidade
# -------------------------------------------------------------------------
class ConferirExcesso:
    """Instrumentacao que conta, por conta propria, quantos segundos cada carro
    passou com velocidade < 0,1 m/s (o criterio de espera do SUMO) e soma 1 a
    cada segundo parado de carro na via de entrada que ja passou de W. Guarda
    obs de cada decisao para conferir a recompensa."""

    def __init__(self, limite):
        self.limite = limite

    def inicio(self, estados_verdes, duracao):
        self.duracao = duracao
        self.parado = {}
        self.excesso = 0
        self._lido = 0  # resultado de quantos passos ja foi lido
        self.decisoes = []  # (segundo, excesso_do_simulador, excesso_contado, obs)
        self.maior_espera_contada = 0

    def _atualizar(self, t):
        tr = simulacao.trafego
        while self._lido < t:  # le o estado depois do passo t-1
            for v in tr.vehicle.getIDList():
                if tr.vehicle.getSpeed(v) < 0.1:
                    self.parado[v] = self.parado.get(v, 0) + 1
                    if tr.vehicle.getRoadID(v) in VIAS_ENTRADA and self.parado[v] > self.limite:
                        self.excesso += 1
                    self.maior_espera_contada = max(self.maior_espera_contada, self.parado[v])
            self._lido = t

    def passo(self, t, estado):
        self._atualizar(t)

    def decisao(self, obs, escolha):
        self._atualizar(obs.segundo)
        self.decisoes.append((obs.segundo, obs.excesso_acumulado, self.excesso, obs))

    def fim(self, caminho):
        pass


# -------------------------------------------------------------------------
# 3 e 4: SUMO direto, sem controlador
# -------------------------------------------------------------------------
def sumo_direto(memoria, tmp):
    """12 carros vindos do Oeste na mesma faixa; vermelho 120 s, verde de so 3 s
    (a fila anda um pouco e para de novo), vermelho ate 400 s.
    Devolve, por carro e por segundo: (via, velocidade, espera, espera acumulada,
    segundos parados contados aqui) e o excesso do MedidorExcesso."""
    rotas = os.path.join(tmp, "quatro_carros.rou.xml")
    with open(rotas, "w") as f:
        f.write('<routes><vType id="carro" accel="2.6" decel="4.5" sigma="0" length="5.0" '
                'minGap="2.5" maxSpeed="13.89"/>'
                '<route id="r" edges="left0A0 A0right0"/>'
                + "".join(f'<vehicle id="c{i}" type="carro" route="r" depart="{3 * i}" '
                          'departLane="0"/>' for i in range(12)) + "</routes>")
    cmd = ["sumo", "-n", simulacao.REDE, "-r", rotas, "--no-step-log", "true",
           "--no-warnings", "true", "--time-to-teleport", "-1", "--duration-log.disable", "true"]
    if memoria is not None:
        cmd += ["--waiting-time-memory", str(memoria)]
    tr = simulacao.trafego
    tr.start(cmd)
    n = len(tr.trafficlight.getRedYellowGreenState(simulacao.SEMAFORO))
    verde_o = simulacao.trafego.trafficlight.getAllProgramLogics(simulacao.SEMAFORO)[0].phases
    verde_o = [p.state for p in verde_o if "G" in p.state or "g" in p.state][3]  # 4a fase = O
    med = simulacao.MedidorExcesso(W)
    serie, contado, excesso_contado = {}, {}, 0
    for t in range(400):
        estado = verde_o if 120 <= t < 123 else "r" * n
        tr.trafficlight.setRedYellowGreenState(simulacao.SEMAFORO, estado)
        tr.simulationStep()
        med.passo()
        for v in tr.vehicle.getIDList():
            vel = tr.vehicle.getSpeed(v)
            if vel < 0.1:
                contado[v] = contado.get(v, 0) + 1
                if tr.vehicle.getRoadID(v) in VIAS_ENTRADA and contado[v] > W:
                    excesso_contado += 1
            serie.setdefault(v, []).append({
                "t": t, "via": tr.vehicle.getRoadID(v), "vel": vel,
                "espera": tr.vehicle.getWaitingTime(v),
                "acumulada": tr.vehicle.getAccumulatedWaitingTime(v),
                "contado": contado.get(v, 0)})
        if t >= 1 and memoria == simulacao.MEMORIA_ESPERA:  # com 100 s nao bate (4b)
            assert med.total == excesso_contado, (t, med.total, excesso_contado)
    tr.close()
    return serie, med.total


def teste_sumo_direto(tmp):
    serie, excesso = sumo_direto(simulacao.MEMORIA_ESPERA, tmp)
    # carro que parou, andou um pouco no verde curto e parou de novo sem cruzar
    candidatos = []
    for v, s in serie.items():
        parou = [i for i, x in enumerate(s) if x["vel"] < 0.1 and x["contado"] > 10]
        if not parou:
            continue
        andou = [i for i in range(parou[0], len(s)) if s[i]["vel"] >= 0.1]
        if andou and all(x["via"] == "left0A0" for x in s) and s[-1]["vel"] < 0.1:
            candidatos.append(v)
    assert candidatos, "nenhum carro parou-andou-parou no cenario de teste"
    for v in candidatos:
        s = serie[v]
        zerou = any(s[i]["espera"] < s[i - 1]["espera"] for i in range(1, len(s)))
        assert zerou, "getWaitingTime deveria zerar quando o carro anda"
        assert all(x["acumulada"] == x["contado"] for x in s), \
            f"{v}: espera acumulada difere da contagem independente"
        assert all(s[i]["acumulada"] >= s[i - 1]["acumulada"] for i in range(1, len(s)))
    v = candidatos[0]
    ok(f"3: {v} parou, andou no verde curto e parou de novo; getWaitingTime zerou "
       f"(foi a {serie[v][-1]['espera']:.0f} s) mas a acumulada seguiu = contagem "
       f"independente ({serie[v][-1]['acumulada']:.0f} s)")

    maior = max(x["acumulada"] for s in serie.values() for x in s)
    assert maior > 200, maior
    assert excesso > 0
    ok(f"4: com --waiting-time-memory {simulacao.MEMORIA_ESPERA}, carro parado ate "
       f"{maior:.0f} s sem truncar; MedidorExcesso = contagem independente em todos os "
       f"segundos (excesso total {excesso:.0f} s)")

    serie_padrao, excesso_padrao = sumo_direto(None, tmp)  # padrao do SUMO
    maior_padrao = max(x["acumulada"] for s in serie_padrao.values() for x in s)
    assert maior_padrao <= 100.0 + 1e-9, maior_padrao
    assert excesso_padrao < excesso
    ok(f"4b: com a memoria padrao do SUMO (100 s) a mesma espera ficaria travada em "
       f"{maior_padrao:.0f} s e o excesso cairia de {excesso:.0f} para {excesso_padrao:.0f} s "
       f"-- por isso rodar() usa {simulacao.MEMORIA_ESPERA}")


# -------------------------------------------------------------------------
def main():
    antes = hashes_projeto()
    tmp = tempfile.mkdtemp(prefix="teste_excesso_")
    ref = salvas()
    try:
        # 0
        import inspect
        assert '"--waiting-time-memory", str(MEMORIA_ESPERA)' in inspect.getsource(simulacao.rodar)
        assert simulacao.MEMORIA_ESPERA >= 3600 + 1200
        ok(f"0: rodar() usa --waiting-time-memory {simulacao.MEMORIA_ESPERA} "
           f"(> 3600 s + 1200 s de escoamento)")

        teste_sumo_direto(tmp)

        # 2, 5 e 1a: rodada inteira com um carro preso no fim (DQN C seed1,
        # equilibrado, semente 3: um carro do Oeste espera ~1180 s no escoamento)
        rotas = gerar_demanda.gerar("equilibrado")
        ag = dqn.AgenteDQN(tipo_recompensa="fila_excesso", treinando=False).carregar("dqn_fila_C_seed1")
        conf = ConferirExcesso(W)
        m = simulacao.rodar(ag, "equilibrado", rotas, seed=3, instrumentacao=conf, dinamica=DIN_C)
        dif = [(t, a, b) for t, a, b, _ in conf.decisoes if a != b]
        assert not dif, f"excesso difere da contagem independente: {dif[:5]}"
        n_hora = sum(1 for t, *_ in conf.decisoes if t < conf.duracao)
        ok(f"2: excesso do simulador = contagem independente nas {len(conf.decisoes)} decisoes "
           f"({n_hora} na hora, {len(conf.decisoes) - n_hora} no escoamento); "
           f"total {conf.decisoes[-1][1]:.0f} carro-segundos acima de {W:.0f} s")

        obs = [d[3] for d in conf.decisoes]
        for a, b in zip(obs, obs[1:]):
            assert dqn.recompensa_fila_excesso(a, b, beta=0.0) == dqn.recompensa_fila(a, b)
        ok(f"1a: com beta = 0, recompensa_fila_excesso == recompensa_fila em todas as "
           f"{len(obs) - 1} transicoes da rodada")

        esc = [(a, b) for a, b in zip(obs, obs[1:]) if a.segundo >= conf.duracao]
        com_excesso = [(a, b) for a, b in esc if b.excesso_acumulado > a.excesso_acumulado]
        assert esc and com_excesso
        assert all(dqn.recompensa_fila_excesso(a, b) < dqn.recompensa_fila(a, b) < 0
                   for a, b in com_excesso)
        fim = esc[-1]
        ok(f"5: no escoamento o excesso cresce em {len(com_excesso)}/{len(esc)} transicoes; "
           f"ultima: fila {dqn.recompensa_fila(*fim):+.3f} x fila_excesso "
           f"{dqn.recompensa_fila_excesso(*fim):+.3f} (carro preso ha "
           f"{conf.maior_espera_contada} s)")

        # 6 / 7
        assert (DIN_C.transicao_corrigida, DIN_C.verde_maximo, DIN_C.filas_no_escoamento,
                DIN_C.nome) == (True, 60, True, "C: transicao corrigida + verde maximo")
        r = ref[("equilibrado", "DQN C seed1", 3)]
        assert all(m[k] == r[k] for k in CHAVES), {k: (m[k], r[k]) for k in CHAVES if m[k] != r[k]}
        import avaliar_C
        amostra = [("pico", "Webster", 1), ("girado", "DQN C seed0", 2),
                   ("assimetrico", "Max-Pressure teto (recal. C)", 4), ("saturado", "DQN original", 5)]
        for cen, rot, s in amostra:
            mm = simulacao.rodar(avaliar_C.fabricar(rot), cen, gerar_demanda.gerar(cen), seed=s,
                                 dinamica=DIN_C)
            rr = ref[(cen, rot, s)]
            assert all(mm[k] == rr[k] for k in CHAVES), (cen, rot, s)
        ok("6/7: parametros da dinamica C inalterados; rodada com o medidor de excesso ligado "
           f"e {len(amostra)} rodadas antigas (tradicionais e DQNs) identicas a avaliacao.json")

        # 1b: treino curto: beta = 0 x 'fila', mesmo resultado
        # 7 episodios: passa do aquecimento (2000 transicoes) e chega a treinar a rede
        kw = dict(episodios=7, semente=0, dinamica="C", verboso=False,
                  intervalo_validacao=5, sementes_validacao=[201])
        treinar_dqn.treinar("fila", nome=os.path.join(tmp, "a"),
                            historico=os.path.join(tmp, "a.json"), **kw)
        treinar_dqn.treinar("fila_excesso", nome=os.path.join(tmp, "b"),
                            historico=os.path.join(tmp, "b.json"),
                            parametros_recompensa={"beta": 0.0, "espera_limite": W}, **kw)
        ha, hb = (json.load(open(os.path.join(tmp, x))) for x in ("a.json", "b.json"))
        assert ha["historico"] == hb["historico"]
        assert [v["esperas"] for v in ha["validacoes"]] == [v["esperas"] for v in hb["validacoes"]]
        pa, pb = torch.load(os.path.join(tmp, "a.pt")), torch.load(os.path.join(tmp, "b.pt"))
        assert all(torch.equal(pa[k], pb[k]) for k in pa)
        assert ha["passos_gradiente"] > 0 and ha["passos_gradiente"] == hb["passos_gradiente"]
        ok(f"1b: treino curto com beta = 0 identico ao treino 'fila' (historico de "
           f"{len(ha['historico'])} episodios, validacao e pesos); {ha['passos_gradiente']} "
           f"passos de gradiente")

        # 8: treino curto de verdade (beta = 1), memoria conferida
        class Espiao(dqn.AgenteDQN):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                self.obs_log = []

            def reiniciar(self):
                super().reiniciar()
                self.obs_log.append(None)

            def decidir(self, obs):
                if self.treinando:
                    self.obs_log.append(obs)
                return super().decidir(obs)

        original = treinar_dqn.AgenteDQN
        treinar_dqn.AgenteDQN = Espiao
        try:
            espioes = []
            orig_init = Espiao.__init__

            def init(self, *a, **k):
                orig_init(self, *a, **k)
                espioes.append(self)
            Espiao.__init__ = init
            treinar_dqn.treinar("fila_excesso", nome=os.path.join(tmp, "c"),
                                historico=os.path.join(tmp, "c.json"),
                                parametros_recompensa={"beta": 1.0, "espera_limite": W},
                                episodios=4, semente=0, dinamica="C", verboso=False,
                                intervalo_validacao=2, sementes_validacao=[201])
        finally:
            treinar_dqn.AgenteDQN = original
        ag = espioes[0]
        # reconstroi as transicoes de treino a partir das obs anotadas
        esperadas, anterior = [], None
        for o in ag.obs_log:
            if o is None:
                anterior = None
                continue
            if anterior is not None:
                esperadas.append(dqn.recompensa_fila_excesso(anterior, o, beta=1.0))
            anterior = o
        guardadas = [t[2] for t in ag.memoria]
        assert guardadas == esperadas, "recompensas na memoria nao batem"
        diferentes = sum(
            1 for o1, o2 in zip(ag.obs_log, ag.obs_log[1:])
            if o1 is not None and o2 is not None and o2.excesso_acumulado > o1.excesso_acumulado)
        h = json.load(open(os.path.join(tmp, "c.json")))
        assert h["recompensa"] == "fila_excesso"
        assert h["parametros_recompensa"] == {"espera_limite": W, "beta": 1.0}
        assert h["dinamica"] == DIN_C.nome
        j = h["validacoes"][0]["justica"]
        assert set(j) == set(treinar_dqn.CENARIOS_TREINO)
        assert {"espera_p95", "espera_max", "veiculos_sem_atendimento", "p95_por_aprox",
                "pior_p95_aprox"} <= set(j["equilibrado"])
        assert os.path.exists(os.path.join(tmp, "c.pt"))
        ok(f"8: treino curto fila_excesso (4 episodios, dinamica C): {len(guardadas)} "
           f"recompensas na memoria = -(dfila + dexcesso)/100 recalculado; {diferentes} "
           f"transicoes com excesso > 0; validacao registra justica "
           f"(ex. equilibrado: P95 {j['equilibrado']['espera_p95']:.0f} s, pior P95 aprox "
           f"{j['equilibrado']['pior_p95_aprox']:.0f} s)")

        # nomes dos modelos novos e recusa a sobrescrever
        for i in range(3):
            mod, hist = treinar_dqn.caminhos(f"dqn_fila_excesso_C_seed{i}", None, "fila_excesso")
            assert mod.endswith(os.path.join("modelos", f"dqn_fila_excesso_C_seed{i}.pt"))
        try:
            treinar_dqn.treinar("fila_excesso", episodios=1, nome="dqn_fila_C_seed0",
                                historico=os.path.join(tmp, "x.json"), verboso=False)
            raise AssertionError("deveria recusar sobrescrever dqn_fila_C_seed0.pt")
        except FileExistsError:
            pass
        ok("8b: nomes dqn_fila_excesso_C_seed{0,1,2}.pt preparados; treino recusa "
           "sobrescrever um modelo existente")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for raiz, _, arqs in os.walk(os.path.join(simulacao.PASTA, "resultados")):
            for a in arqs:
                # so os que este teste criou (ha um _tmp_tripinfo antigo versionado no git)
                if a.startswith("_tmp_tripinfo") and os.path.join(raiz, a) not in antes:
                    os.remove(os.path.join(raiz, a))

    depois = hashes_projeto()
    assert antes == depois, sorted(set(antes.items()) ^ set(depois.items()))
    ok(f"9: {len(antes)} arquivos de modelos/ e resultados/ intactos, nenhum criado")
    print("\nTUDO OK")


if __name__ == "__main__":
    main()
