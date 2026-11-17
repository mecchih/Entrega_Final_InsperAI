"""Testes da versao 2 antes dos treinos (episodios curtos de 1500 s, sem treino real).

uso: python -B -X utf8 semaforo/integracao_insper/otimizacao_final/testar_otimizacao.py
"""

from pathlib import Path
import sys
import tempfile

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI))
import insper_comum as ic  # noqa: E402
import ambiente_marl_insper as v1  # noqa: E402
import ambiente_marl_insper_v2 as v2  # noqa: E402
import treinar_marl_insper_v2 as tr  # noqa: E402

LIM = 1500
ANT = AQUI.parent / "resultados" / "bateria_principal_20261116" / "treinos"
OK = []


def checar(cond, msg):
    print(("OK   " if cond else "FALHA") + " " + msg, flush=True)
    OK.append(cond)


def cfg(s, nivel="intenso_validacao"):
    return ic.SEMAFORO / "cenarios" / "insper_demanda" / nivel / f"semente_{s}" / "cenario.sumocfg"


def principais(m):
    return (m["espera_corredor_s"], m["filas"], m["recompensas"], m["decisoes"], m["teleportes"]["total"],
            m["colisoes"]["eventos"], m["trocas"])


def main():
    import torch
    torch.set_num_threads(1)
    from agente_marl_cologne import DoubleDQN
    antes = ic.hashes_cenario()
    pasta = ic.nova_pasta("teste_otimizacao")

    # 1. classificacao e atribuicao das colisoes (sem SUMO)
    entra = {0: {"234368025#0", "27579109#4"}, 1: {"760437731", "1160862341#1"}, 2: {"234368026#0", "8547878#5"}}
    sai = {0: {"760437731", "234368022#0"}, 1: {"234368026#0", "760437730#0"}, 2: {"234368026#1", "8547878#6"}}
    area = {"8547878#4": 2, "-522284928": 2}
    jar = {"5087305044"}
    casos = {":40278183_3_0": ("controlado", {2}), "760437731_1": ("controlado", {0, 1}),
             ":5087305044_3_0": ("externa_area_observacao", set()), ":1550389898_0_2": ("externa_distante", set()),
             "8547878#4_0": ("externa_area_observacao", set())}
    checar(all(v2.classificar_colisao(f, entra, sai, area, jar) == esp for f, esp in casos.items()),
           "classificacao espacial das colisoes")
    checar(v2.penalidade_colisao(set(), 4, "global") == [-10000.0] * 4
           and v2.penalidade_colisao(set(), 4, "atribuida") == [0.0] * 4
           and v2.penalidade_colisao({2}, 4, "atribuida") == [0, 0, -10000.0, -10000.0]
           and v2.penalidade_colisao({0, 1}, 3, "atribuida") == [-10000.0, -10000.0, 0],
           "penalidade global (v1) x atribuida (so local do cruzamento + supervisor)")

    # 2. v2 com CONFIG_V1 reproduz a v1 (mesmo checkpoint antigo, mesma demanda)
    for modelo in ("independente", "hierarquico"):
        ck = ANT / f"{modelo}_s1" / "politica_ep0150.pt"
        _, ag1 = tr.carregar(ck)
        _, ag2 = tr.carregar(ck)
        m1 = v1.rodar_episodio(cfg(224), pasta / f"equiv_v1_{modelo}", 224, ag1, modelo, limite=LIM)
        m2 = v2.rodar_episodio(cfg(224), pasta / f"equiv_v2_{modelo}", 224, ag2, modelo, limite=LIM)
        checar(principais(m1) == principais(m2), f"v2 com CONFIG_V1 identica a v1 ({modelo}, checkpoint antigo)")
    d, _ = tr.carregar(ANT / "hierarquico_s1" / "politica_ep0150.pt")
    checar(d["config"] == v2.CONFIG_V1, "checkpoint v1 carregado com CONFIG_V1")

    # 3. episodios curtos de treino nas configuracoes novas
    casos = [("independente", {"verde_minimo": 5, "colisao": "atribuida", "supervisor_s": 30}),
             ("hierarquico", {"verde_minimo": 10, "colisao": "atribuida", "supervisor_s": 15}),
             ("hierarquico", {"verde_minimo": 5, "colisao": "atribuida", "supervisor_s": 15}),
             ("hierarquico", {"verde_minimo": 5, "colisao": "atribuida", "supervisor_s": 10})]
    for modelo, conf in casos:
        nome = f"{modelo}_v{conf['verde_minimo']}_s{conf['supervisor_s']}"
        ag = v2.criar_agentes(modelo, 7, aquecimento=64)
        m = v2.rodar_episodio(cfg(1001, "intenso_treino"), pasta / nome, 1001, ag, modelo, treinando=True,
                              monitor_completo=True, limite=LIM, config=conf)
        ver = m["seguranca"]["verificacao"]
        checar(m["seguranca"]["violacoes"] == 0 and all(
            x["verdes"]["min"] >= conf["verde_minimo"] and x["amarelos"]["min"] == x["amarelos"]["max"] == 3
            and x["vermelhos_gerais"]["min"] == x["vermelhos_gerais"]["max"] == 2 for x in ver.values()),
            f"{nome}: verde >= {conf['verde_minimo']} s, amarelo 3 s, vermelho geral 2 s, sem conflitos")
        if conf["verde_minimo"] == 5:
            checar(any(x["verdes"]["min"] == 5 for x in ver.values()), f"{nome}: ha verdes de 5 s (nova regra ativa)")
        checar(len(m["outros_semaforos"]) == 11 and all(o["erros"] == 0 for o in m["outros_semaforos"].values()),
               f"{nome}: os outros 11 semaforos no programa original")
        checar(all(a.memoria.s.shape[1] == (13 if a.acoes == 2 else 48) for a in ag)
               and all(set(a.memoria.a[:a.memoria.n].tolist()) <= set(range(a.acoes)) for a in ag)
               and all(isinstance(r, float) for r in m["recompensas"]), f"{nome}: dimensoes 13/48, acoes validas, recompensas finitas")
        checar(all(a.gradientes > 0 for a in ag[:3]), f"{nome}: locais com gradientes {[a.gradientes for a in ag]}")
        if modelo == "hierarquico":
            n_sup = sum(v for k, v in m["decisoes"].items() if k.startswith("supervisor_"))
            esperado = (LIM - v2.AQUECIMENTO) / conf["supervisor_s"]
            checar(abs(n_sup - esperado) <= 1 and ag[3].memoria.n == n_sup - 1 + 1,
                   f"{nome}: supervisor decidiu {n_sup} vezes (esperado ~{esperado:.0f}), replay {ag[3].memoria.n}")
        with tempfile.TemporaryDirectory() as tmp:
            tr.salvar(Path(tmp) / "c.pt", ag, modelo, 7, 1, completo=True, config=dict(v2.CONFIG_V1, **conf))
            d, novos = tr.carregar(Path(tmp) / "c.pt", modelo)
            x = torch.from_numpy(ag[0].memoria.s[0])
            checar(d["config"] == dict(v2.CONFIG_V1, **conf) and torch.equal(ag[0].rede(x), novos[0].rede(x))
                   and novos[-1].memoria.n == ag[-1].memoria.n, f"{nome}: checkpoint salvo/carregado com a config")
        checar("por_classe" in m["colisoes"] and all("faixa" in t for t in m["teleportes"]["lista"]),
               f"{nome}: registro de colisoes por classe e de teletransportes com local "
               f"(colisoes {m['colisoes']['eventos']}, teleportes {m['teleportes']['total']})")

    # 4. o replay guarda a acao EXECUTADA: agente que sempre pede a fase 0
    class SempreZero(DoubleDQN):
        def escolher(self, estado, treinando):
            if treinando:
                self.decisoes += 1
            return 0, [0.0, 0.0], False
    ag = [SempreZero(13, 2, 70 + k, aquecimento=64) for k in range(3)]
    m = v2.rodar_episodio(cfg(1001, "intenso_treino"), pasta / "sempre_zero", 1001, ag, "independente", treinando=True,
                          limite=LIM, config={"verde_minimo": 5, "colisao": "atribuida"})
    uns = [int((a.memoria.a[:a.memoria.n] == 1).sum()) for a in ag]
    checar(all(u == a.intervencoes and u > 0 for u, a in zip(uns, ag)),
           f"replay guarda a acao executada: acoes 1 no replay {uns} = intervencoes {[a.intervencoes for a in ag]}")

    # 5. baselines com as mesmas regras
    for nome, (modo, conf) in {"atuado_eq_v10": ("atuado_equivalente", {"verde_minimo": 10}),
                               "atuado_eq_v5": ("atuado_equivalente", {"verde_minimo": 5}),
                               "max_pressure_v5": ("max_pressure", {"verde_minimo": 5})}.items():
        m = v2.rodar_episodio(cfg(224), pasta / nome, 224, None, modo, monitor_completo=True, limite=LIM, config=conf)
        checar(m["seguranca"]["violacoes"] == 0 and all(o["erros"] == 0 for o in m["outros_semaforos"].values()),
               f"{nome}: seguro; espera no corredor {m['espera_corredor_s']['media']} s (900-1500 s simulados)")
    ic.conferir_cenario(antes)
    print(f"{sum(OK)}/{len(OK)} verificacoes OK; saida em {pasta}")
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
