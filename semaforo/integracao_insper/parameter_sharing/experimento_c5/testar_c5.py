"""Testes do experimento zero-shot C3 -> C5 (sem treino). Episodios curtos (ate 1500 s).

uso: python -B -X utf8 semaforo/integracao_insper/parameter_sharing/experimento_c5/testar_c5.py
"""

import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI.parents[1] / "otimizacao_final"))
import adaptador_c5 as ad  # noqa: E402
import insper_comum as ic  # noqa: E402

LIM = 1500
OK = []
CONFIG = {"verde_minimo": 10, "colisao": "atribuida", "supervisor_s": 30}


def checar(cond, msg):
    print(("OK   " if cond else "FALHA") + " " + msg, flush=True)
    OK.append(bool(cond))


def cfg(s, nivel):
    return ic.SEMAFORO / "cenarios" / "insper_demanda" / nivel / f"semente_{s}" / "cenario.sumocfg"


def hash_pesos(rede):
    h = hashlib.sha256()
    for v in rede.rede.state_dict().values():
        h.update(v.numpy().tobytes())
    for v in rede.alvo.state_dict().values():
        h.update(v.numpy().tobytes())
    return h.hexdigest()


def teste_semantica_acoes(mapa, pasta):
    """Com TraCI direto: pede a acao canonica 1 e depois 0 em cada cruzamento e confere, no estado que o
    SUMO executou, que a via principal (1) ou a transversal (0) recebeu verde e a outra ficou em vermelho."""
    import traci
    from controle_seguro_insper import ControladorFasesSeguro, SemaforosProtegidos
    tmp = tempfile.mkdtemp()
    traci.start([str(ic.sumo_home() / "bin" / "sumo.exe"), "-c", str(cfg(1001, "intenso_treino")), "--seed", "1001",
                 "--no-step-log", "true", "--tripinfo-output", os.path.join(tmp, "t.xml"), "--log", os.path.join(tmp, "l.log")],
                label="sem_c5")
    conn = traci.getConnection("sem_c5")
    try:
        # verificadores desde t = 0 (cobrando a partir de 300 s), como no ambiente: assim a duracao do verde
        # e do amarelo em curso no momento em que o controle assume e conhecida
        foes = {t: ic.foes_traci(conn, t)[0] for t in ad.TLS5}
        verif = {t: ic.VerificadorSeguranca(t, foes[t], 3, 2, 10, 300) for t in ad.TLS5}
        while conn.simulation.getTime() < 300:
            conn.simulationStep()
            for t in ad.TLS5:
                verif[t].observar(int(conn.simulation.getTime()), conn.trafficlight.getRedYellowGreenState(t))
        prot = SemaforosProtegidos(conn.trafficlight, ad.TLS5)
        agora = int(conn.simulation.getTime())
        ctrl, links = {}, {}
        for t in ad.TLS5:
            ctrl[t] = ControladorFasesSeguro(prot, t, agora, foes[t], verde_minimo=10, vermelho_geral=2,
                                             intervalo_decisao=5, verde_maximo=60)
            links[t] = [it[0][0].rsplit("_", 1)[0] for it in conn.trafficlight.getControlledLinks(t)]
        resultado = {}
        for canonica in (1, 0, 1):
            feito = {t: False for t in ad.TLS5}
            limite = agora + 200
            while not all(feito.values()) and agora < limite:
                for t, c in ctrl.items():
                    c.atualizar(agora)
                    alvo = mapa[t]["acao_real"][canonica]
                    if c.pode_decidir(agora) and not feito[t]:
                        if c.fase != alvo:
                            c.pedir(alvo, agora)
                        else:
                            estado = conn.trafficlight.getRedYellowGreenState(t)
                            principal = mapa[t]["entradas"][mapa[t]["slot_principal"]]
                            g_p = all(estado[k] in "Gg" for k, e in enumerate(links[t]) if e == principal)
                            r_t = all(estado[k] == "r" for k, e in enumerate(links[t]) if e != principal)
                            g_t = all(estado[k] in "Gg" for k, e in enumerate(links[t]) if e != principal)
                            r_p = all(estado[k] == "r" for k, e in enumerate(links[t]) if e == principal)
                            resultado[(t, canonica)] = (g_p and r_t) if canonica == 1 else (g_t and r_p)
                            feito[t] = True
                conn.simulationStep()
                agora = int(conn.simulation.getTime())
                for t in ad.TLS5:
                    verif[t].observar(agora, conn.trafficlight.getRedYellowGreenState(t))
                    ctrl[t].conferir(agora)
        violacoes = sum(v.resumo()["violacoes"] for v in verif.values())
        outros_ok = all(conn.trafficlight.getProgram(t) == "0" for t in conn.trafficlight.getIDList() if t not in ad.TLS5)
    finally:
        conn.close()
    return resultado, violacoes, outros_ok


def main():
    import numpy as np
    import torch
    torch.set_num_threads(1)
    import ambiente_c5 as env5
    import ambiente_marl_insper_v2 as v2
    import politica_compartilhada as pc
    antes = ic.hashes_cenario()
    pasta = AQUI / "resultados" / f"{datetime.datetime.now():%Y%m%dT%H%M%S}_testes"
    pasta.mkdir(parents=True)
    man = json.loads((AQUI.parent / "modelos_finais" / "manifesto.json").read_text(encoding="utf-8"))
    ck = AQUI.parents[3] / man["bracos"]["C"]["sementes_modelo"]["1"]["arquivo"]

    # 1. mapeamento derivado da rede
    mapa = ad.mapeamento(ad.TLS5)
    esperado = {"476455095": (0, 1), "40278305": (1, 0), "40278183": (0, 1), "300058973": (0, 1), "302806060": (0, 0)}
    checar({t: (m["slot_principal"], m["fase_principal"]) for t, m in mapa.items()} == esperado,
           "via principal e fase que a serve: " + ", ".join(f"{t}: slot {m['slot_principal']}, fase {m['fase_principal']} "
                                                            f"({m['nomes'][m['slot_principal']]})" for t, m in mapa.items()))
    ori = pc.orientacao_canonica()
    ident = list(range(9))
    checar(all(mapa[t]["perm_obs"] == (pc.PERMUTACAO_OBS[:9] if ori[t] else ident) and
               mapa[t]["acao_real"] == ({1: 0, 0: 1} if ori[t] else {1: 1, 0: 0}) for t in ad.TLS3),
           "para os 3 originais a transformacao e identica a do Modelo C (politica_compartilhada)")
    checar(mapa["302806060"]["perm_obs"] == [0, 1, 2, 3, 5, 4, 6, 7, 8] and mapa["302806060"]["acao_real"] == {1: 0, 0: 1}
           and mapa["300058973"]["perm_obs"] == ident and mapa["300058973"]["acao_real"] == {1: 1, 0: 0},
           "302806060: so a fase one-hot e a acao sao invertidas; 300058973: identidade")
    v = ad.VisaoC5(None, 4, mapa["302806060"])
    x = np.array([.1, .2, .3, .4, 1, 0, .5, .6, .7, 1, 0, 0, 0], dtype=np.float32)
    checar(v.canon(x).tolist() == pytest_list([.1, .2, .3, .4, 0, 1, .5, .6, .7, 1, 0, 0, 0]),
           "302806060: verde real na fase 0 (Fiandeiras) aparece como verde da via principal no referencial canonico")

    # 2. semantica das acoes no SUMO (controlador seguro + verificador)
    res, viol, outros_ok = teste_semantica_acoes(mapa, pasta)
    checar(len(res) == 10 and all(res.values()) and viol == 0 and outros_ok,
           f"acao canonica 1 = verde SO na via principal e 0 = verde SO na transversal, nos 5 cruzamentos "
           f"(estado executado pelo SUMO); {viol} violacoes; outros 9 no programa original: {outros_ok}")

    # 3. equivalencia: ambiente C5 com os 3 controlados reproduz a v2 (mesmo checkpoint)
    _, r1 = pc.carregar(ck)
    _, r2 = pc.carregar(ck)
    _, r3 = pc.carregar(ck)
    m_v2 = v2.rodar_episodio(cfg(224, "intenso_validacao"), pasta / "eq_v2", 224, pc.visoes_avaliacao(r1), "independente",
                             limite=LIM, config=CONFIG)
    m_c5 = env5.rodar_episodio(cfg(224, "intenso_validacao"), pasta / "eq_c5", 224, ad.visoes(r2, ad.TLS3, mapa),
                               "independente", limite=LIM, config=CONFIG, controlados=ad.TLS3)
    m_c5m = env5.rodar_episodio(cfg(224, "intenso_validacao"), pasta / "eq_c5_medidos", 224, ad.visoes(r3, ad.TLS3, mapa),
                                "independente", limite=LIM, config=CONFIG, controlados=ad.TLS3, medidos=ad.NOVOS)

    def chave(m):
        return (m["espera_corredor_s"], {t: m["filas"][t] for t in ad.TLS3}, m["recompensas"], m["decisoes"],
                m["teleportes"]["total"], m["colisoes"]["eventos"], m["trocas"], m["bloqueio_saida_corredor_s"],
                m["espera_rede_s"])
    checar(chave(m_v2) == chave(m_c5) == chave(m_c5m),
           "ambiente C5 com os 3 originais reproduz exatamente a v2 (com e sem medir os 2 novos)")

    # 4. zero-shot C5: 5 agentes, mesma rede congelada
    _, rede = pc.carregar(ck)
    h0, g0, n0, d0 = hash_pesos(rede), rede.gradientes, rede.memoria.n, rede.decisoes
    ag = ad.visoes(rede, ad.TLS5, mapa)
    reg = []
    for a in ag:
        a.registro = reg
    m = env5.rodar_episodio(cfg(224, "intenso_validacao"), pasta / "c5_curto", 224, ag, "independente", limite=LIM,
                            config=CONFIG, controlados=ad.TLS5, monitor_completo=True)
    checar(all(a.rede is rede for a in ag) and len(ag) == 5, "os 5 agentes usam o mesmo objeto de rede")
    por_k = {k: [r for r in reg if r[0] == k] for k in range(5)}
    checar(all(len(por_k[k]) > 20 for k in range(5)) and all(r[1].shape == (13,) and np.isfinite(r[1]).all() for r in reg),
           f"cada agente decide com 13 entradas finitas: {[len(por_k[k]) for k in range(5)]} decisoes")
    medias = [np.mean([r[1][:4] for r in por_k[k]], axis=0) for k in range(5)]
    checar(len({tuple(np.round(mm, 4)) for mm in medias}) == 5,
           "observacoes diferentes entre os 5 cruzamentos (cada um ve so a propria area)")
    n = min(len(por_k[k]) for k in range(5))
    checar(any(len({por_k[k][i][2] for k in range(5)}) > 1 for i in range(n)),
           "os agentes escolhem acoes canonicas diferentes entre si")
    checar(hash_pesos(rede) == h0 and rede.gradientes == g0 and rede.memoria.n == n0 and rede.decisoes == d0,
           f"pesos identicos antes/depois (sha256 {h0[:12]}), 0 gradientes, replay {rede.memoria.n}, sem decisoes de treino")
    ver = m["seguranca"]["verificacao"]
    checar(m["seguranca"]["violacoes"] == 0 and set(ver) == set(ad.TLS5) and all(
        x["verdes"]["min"] >= 10 and x["amarelos"]["min"] == x["amarelos"]["max"] == 3
        and x["vermelhos_gerais"]["min"] == x["vermelhos_gerais"]["max"] == 2 for x in ver.values()),
        "seguranca nos 5: verde >= 10 s, amarelo 3 s, vermelho geral 2 s, sem conflitos")
    checar(len(m["outros_semaforos"]) == 9 and all(o["erros"] == 0 for o in m["outros_semaforos"].values()),
           "os outros 9 semaforos ficaram no programa original")
    checar(set(m["cruzamentos"]) == set(ad.TLS5) and all(m["cruzamentos"][t]["veiculos"] > 0 for t in ad.TLS5)
           and set(m["trocas"]) == set(ad.TLS5),
           "metricas por cruzamento registradas: " + str({t: m["cruzamentos"][t]["veiculos"] for t in ad.TLS5}))
    erros = [l for l in (pasta / "c5_curto" / "sumo.log").read_text(encoding="utf-8", errors="replace").splitlines()
             if l.startswith("Error")]
    checar(not erros, f"sumo.log sem erros ({len(erros)})")
    # 5. original medindo os 5
    mo = env5.rodar_episodio(cfg(224, "intenso_validacao"), pasta / "original", 224, None, "original", limite=LIM,
                             config=CONFIG, medidos=ad.NOVOS, monitor_completo=True)
    checar(mo["seguranca"]["violacoes"] == 0 and len(mo["outros_semaforos"]) == 14 and set(mo["cruzamentos"]) == set(ad.TLS5)
           and mo["espera_corredor_s"] == env5.rodar_episodio(cfg(224, "intenso_validacao"), pasta / "original_3", 224, None,
                                                               "original", limite=LIM, config=CONFIG)["espera_corredor_s"],
           "original: 14 semaforos intactos, 5 cruzamentos medidos e corredor igual ao da medicao sem os novos")
    ic.conferir_cenario(antes)
    checar(True, "arquivos do cenario inalterados (SHA-256)")
    print(f"{sum(OK)}/{len(OK)} verificacoes OK; saida em {pasta}")
    return 0 if all(OK) else 1


def pytest_list(v):
    import numpy as np
    return np.asarray(v, dtype=np.float32).tolist()


if __name__ == "__main__":
    sys.exit(main())
