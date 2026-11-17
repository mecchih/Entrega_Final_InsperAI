"""Teste de integracao TraCI no cenario Insper, SEM modelos treinados e sem treino.

Controla somente 476455095, 40278305 e 40278183; os outros 11 semaforos ficam
no programa original (o acesso de escrita a eles e bloqueado). Cada rodada:

  1. aquece com os programas originais ate --assumir segundos;
  2. assume os tres semaforos no estado em que estiverem (verde ou amarelo);
  3. aplica uma politica de teste, sempre atraves do ControladorFasesSeguro:
       original     nenhum controle (referencia);
       ciclo_fixo   troca quando o verde chega a 30 s;
       aleatoria    escolhe uma fase ao acaso a cada decisao (5 s);
       adversaria   pede troca A CADA SEGUNDO, inclusive durante amarelo/vermelho;
       dqn_inicial  Double DQN do Cologne8 com pesos iniciais aleatorios (nao treinada,
                    sem replay): so demonstra a interface de observacao/acao;
  4. registra fases executadas, travessias, colisoes, teletransportes, paradas
     de emergencia, avisos do SUMO e erros, e confere os criterios de seguranca.

uso (na raiz do repositorio):
    python -B -X utf8 semaforo/integracao_insper/testar_integracao_traci_insper.py
    python -B -X utf8 semaforo/integracao_insper/testar_integracao_traci_insper.py --politicas ciclo_fixo --sementes 1 --gui
"""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import random
import sys
import time
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))
import insper_comum as ic  # noqa: E402
from controle_seguro_insper import ControladorFasesSeguro, SemaforosProtegidos  # noqa: E402
from observacao_insper import SensoresInsper  # noqa: E402

POLITICAS = ["original", "ciclo_fixo", "aleatoria", "adversaria", "dqn_inicial"]
LIMITE = 3600 + 1800


def criar_politica(nome, semente, sensores):
    rng = random.Random(semente)
    if nome == "ciclo_fixo":
        return lambda i, c, agora, obs: (1 - c.fase) if c.idade_verde(agora) >= 30 else c.fase
    if nome == "aleatoria":
        return lambda i, c, agora, obs: rng.randrange(len(c.verdes))
    if nome == "adversaria":
        return lambda i, c, agora, obs: (c.fase + 1) % len(c.verdes)
    if nome == "dqn_inicial":
        sys.path.insert(0, str(ic.SEMAFORO / "scripts"))
        from agente_marl_cologne import DoubleDQN  # so importa; nao altera nada do Cologne8
        agentes = [DoubleDQN(n, len(c.verdes), semente + 10 * k)
                   for k, (n, c) in enumerate(zip(sensores.n_local, sensores.controladores))]

        def dqn(i, c, agora, obs):
            acao, _, explorou = agentes[i].escolher(obs[i], treinando=False)
            assert not explorou
            return int(acao)
        dqn.agentes = agentes
        return dqn
    raise ValueError(nome)


def rodar(pasta, politica_nome, semente, assumir, gui=False, proteger_verde_maximo=True):
    import sumolib
    import traci.constants as tc
    pasta.mkdir(parents=True, exist_ok=False)
    cmd = ic.comando_sumo(pasta, semente, gui=gui)
    ic.json_novo(pasta / "execucao.json", {"politica": politica_nome, "semente": semente, "assumir_em_s": assumir,
                                           "tempos_seguranca": ic.TEMPOS,
                                           "protecao_verde_maximo": proteger_verde_maximo, "comando": cmd})
    conn = ic.iniciar(cmd, f"{politica_nome}_{semente}")
    inicio_real = time.perf_counter()
    controlar = politica_nome != "original"
    eventos_fases = []
    falhas, erro = [], None
    decisoes = Counter()
    try:
        tls_ids = sorted(conn.trafficlight.getIDList())
        if len(tls_ids) != 14 or not set(ic.CONTROLADOS) <= set(tls_ids):
            raise RuntimeError(f"semaforos inesperados: {tls_ids}")
        outros = [t for t in tls_ids if t not in ic.CONTROLADOS]
        raiz = ic.ler_rede_xml()
        foes, vias = {}, {}
        for t in ic.CONTROLADOS:
            foes[t], vias[t], _ = ic.foes_traci(conn, t)
            req = ic.foes_requisicao(raiz, t)
            req_link = {ic.indice_juncao(vias[t][i]): i for i in range(len(vias[t]))}
            if {req_link[k]: {req_link[x] for x in v} for k, v in req.items()} != foes[t]:
                raise RuntimeError(f"{t}: conflitos do <request> diferem da geometria do TraCI")
        monitores = {t: ic.MonitorPrograma(conn, t, 0) for t in tls_ids}
        verificadores = {t: ic.VerificadorSeguranca(
            t, foes[t], 3, ic.TEMPOS["vermelho_geral"] if controlar else 0,
            ic.TEMPOS["verde_minimo"] if controlar else 5, assumir) for t in ic.CONTROLADOS}
        travessias = ic.Travessias(conn, tls_ids)
        colisoes = ic.ContadorColisoes()
        protegido = SemaforosProtegidos(conn.trafficlight, ic.CONTROLADOS)
        vars_ = [tc.VAR_LANE_ID, tc.VAR_ROAD_ID, tc.VAR_SPEED, tc.VAR_ACCUMULATED_WAITING_TIME]
        net = sumolib.net.readNet(str(ic.REDE))

        def ocupados(tls, estado):
            return sum(conn.lane.getLastStepVehicleNumber(vias[tls][f])
                       for link, c in enumerate(estado) if c in "Gg" for f in foes[tls][link])

        def demanda_links(tls, ids):
            """Veiculos na area de observacao que vao cruzar `tls`, por link (getNextTLS)."""
            demanda = Counter()
            for vid in ids:
                for proximo, link, _, _ in conn.vehicle.getNextTLS(vid):
                    if proximo == tls:
                        demanda[int(link)] += 1
                    break
            return demanda

        controladores, sensores, politica = [], None, None
        teleportes, emergencias = [], 0
        linha_tempo = []
        estatisticas_obs = {"amostras": 0, "max_local": 0.0}
        agora = int(conn.simulation.getTime())
        while conn.simulation.getMinExpectedNumber() > 0 and agora < LIMITE:
            if controlar and agora == assumir:
                for t in ic.CONTROLADOS:
                    controladores.append(ControladorFasesSeguro(
                        protegido, t, agora, foes[t], eventos_fases.append,
                        verde_minimo=ic.TEMPOS["verde_minimo"], vermelho_geral=ic.TEMPOS["vermelho_geral"],
                        intervalo_decisao=ic.TEMPOS["intervalo_decisao"], verde_maximo=ic.TEMPOS["verde_maximo"],
                        conflitantes_ocupados=ocupados))
                sensores = SensoresInsper(conn, net, controladores)
                politica = criar_politica(politica_nome, semente, sensores)
            obs = None
            if controladores:
                for c in controladores:
                    c.atualizar(agora)
                foto = sensores.ler(conn.vehicle.getAllSubscriptionResults(), tc)
                obs, sup = sensores.vetores(foto, agora)
                estatisticas_obs["amostras"] += 1
                estatisticas_obs["max_local"] = max(estatisticas_obs["max_local"], float(max(o.max() for o in obs)))
                for i, c in enumerate(controladores):
                    if politica_nome == "adversaria" or c.pode_decidir(agora):
                        pedida = politica(i, c, agora, obs)
                        acao, interveio = (c.proteger(pedida, agora, demanda_links(c.id, foto["locais"][i]["ids"]))
                                           if proteger_verde_maximo else (pedida, False))
                        motivo = c.pedir(acao, agora)
                        decisoes[f"{c.id}:{motivo}" + (":intervencao_verde_maximo" if interveio else "")] += 1
            conn.simulationStep()
            agora = int(conn.simulation.getTime())
            for vid in conn.simulation.getDepartedIDList():
                conn.vehicle.subscribe(vid, vars_)
            for vid in conn.simulation.getStartingTeleportIDList():
                teleportes.append({"tempo": agora, "veiculo": vid})
                travessias.esquecer(vid, "teleporte_durante_travessia")
            estados = {t: conn.trafficlight.getRedYellowGreenState(t) for t in tls_ids}
            for t in outros:
                monitores[t].conferir(agora)
            for t in ic.CONTROLADOS:
                if not controladores:
                    monitores[t].conferir(agora)
            for c in controladores:
                c.conferir(agora)
            for t, v in verificadores.items():
                v.observar(agora, estados[t])
            linha_tempo.append([agora] + [estados[t] for t in ic.CONTROLADOS])
            dados = conn.vehicle.getAllSubscriptionResults()
            travessias.atualizar(agora, {vid: r[tc.VAR_LANE_ID] for vid, r in dados.items()}, estados)
            for vid in conn.simulation.getArrivedIDList():
                travessias.esquecer(vid, "chegou_antes_de_sair_do_cruzamento")
            colisoes.atualizar(conn, agora)
            emergencias += conn.simulation.getEmergencyStoppingVehiclesNumber()
        programas_finais = {t: conn.trafficlight.getProgram(t) for t in tls_ids}
        pendentes = len(conn.simulation.getPendingVehicles())
        em_rede = conn.vehicle.getIDCount()
        conn.close()
        conn = None
    except Exception as e:
        erro = {"tipo": type(e).__name__, "mensagem": str(e), "rastreamento": traceback.format_exc()}
        ic.json_novo(pasta / "erro.json", erro)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        return {"politica": politica_nome, "semente": semente, "aprovado": False, "erro": erro,
                "falhas": [f"erro: {erro['tipo']}: {erro['mensagem']}"]}
    # ------------------------------------------------------------ registros
    with (pasta / "fases.jsonl").open("x", encoding="utf-8") as f:
        for ev in eventos_fases:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    with (pasta / "linha_do_tempo_semaforos.csv").open("x", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tempo"] + list(ic.CONTROLADOS))
        w.writerows(linha_tempo)
    with (pasta / "travessias.csv").open("x", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tempo", "veiculo", "tls", "link", "luz", "aproximado"])
        w.writerows([r["tempo"], r["veiculo"], r["tls"], r["link"], r["luz"], r["aproximado"]]
                    for r in travessias.registros)
    regs = travessias.registros
    depois = [r for r in regs if r["tempo"] > assumir]
    por_tls = {}
    for t in ic.CONTROLADOS:
        meus = [r for r in regs if r["tls"] == t]
        meus_depois = [r for r in depois if r["tls"] == t]
        c = next((c for c in controladores if c.id == t), None)
        por_tls[t] = {"veiculos_atendidos_total": len({r["veiculo"] for r in meus}),
                      "veiculos_atendidos_apos_assumir": len({r["veiculo"] for r in meus_depois}),
                      "luz_ao_cruzar_apos_assumir": dict(Counter(r["luz"] for r in meus_depois)),
                      "verificacao": verificadores[t].resumo(),
                      "programa_original_ate_assumir": monitores[t].resumo(),
                      "trocas_controlador": c.trocas if c else None,
                      "recusas_controlador": c.recusas if c else None,
                      "intervencoes_verde_maximo": c.intervencoes if c else None,
                      "como_assumiu": next((e["motivo"] for e in eventos_fases if e["tls"] == t), None),
                      "escritas_traci": protegido.escritas[t],
                      "aberturas_com_veiculo_em_conflitante": sum(
                          1 for e in eventos_fases if e["tls"] == t and e.get("veiculos_em_conflitantes_ao_abrir")),
                      "programa_final": programas_finais[t]}
    outros_resumo = {t: monitores[t].resumo() for t in outros}
    viagens = ic.ler_tripinfo(pasta / "tripinfo.xml")
    stats = ic.ler_estatisticas(pasta / "estatisticas_sumo.xml")
    avisos = ic.avisos_log(pasta / "sumo.log")
    vermelho = [r for r in regs if r["luz"] in "rR"]
    # ------------------------------------------------------------ criterios
    if any(m["erros"] for m in outros_resumo.values()):
        falhas.append("algum dos outros 11 semaforos saiu do programa original")
    if any(programas_finais[t] != "0" for t in outros):
        falhas.append("programa final de um semaforo nao controlado nao e o original")
    if any(protegido.escritas.get(t) for t in outros):
        falhas.append("escrita TraCI em semaforo nao controlado")
    for t, d in por_tls.items():
        if d["verificacao"]["violacoes"]:
            falhas.append(f"{t}: {d['verificacao']['violacoes']} violacoes de seguranca")
        if controlar and d["programa_final"] != "online":
            falhas.append(f"{t}: semaforo nao ficou sob controle TraCI")
        if d["programa_original_ate_assumir"]["erros"]:
            falhas.append(f"{t}: programa original inconsistente antes de assumir")
        if d["aberturas_com_veiculo_em_conflitante"]:
            falhas.append(f"{t}: verde aberto com veiculo em movimento conflitante")
    if vermelho:
        falhas.append(f"{len(vermelho)} travessias com luz vermelha")
    faixas_controladas = {f for t in ic.CONTROLADOS for f in travessias.entradas if t in travessias.entradas[f]}
    for e in colisoes.eventos:
        e["juncao"] = ic.juncao_da_faixa(e["faixa"])
        e["em_controlado"] = e["juncao"] in ic.CONTROLADOS or e["faixa"] in faixas_controladas
    nos_controlados = [e for e in colisoes.eventos if e["em_controlado"]]
    if nos_controlados:
        falhas.append(f"{len(nos_controlados)} colisoes nos cruzamentos controlados ou em suas faixas de chegada")
    if teleportes:
        falhas.append(f"{len(teleportes)} teletransportes")
    if viagens["nao_concluidas"] or pendentes or em_rede:
        falhas.append("viagens nao concluidas")
    resultado = {
        "politica": politica_nome, "semente": semente, "assumir_em_s": assumir, "aprovado": not falhas,
        "protecao_verde_maximo": proteger_verde_maximo,
        "falhas": falhas, "fim_simulacao_s": agora, "duracao_real_s": round(time.perf_counter() - inicio_real, 1),
        "viagens": viagens, "estatisticas_sumo": stats,
        "colisoes": {"eventos": len(colisoes.eventos), "nos_controlados": len(nos_controlados),
                     "fora_dos_controlados": len(colisoes.eventos) - len(nos_controlados),
                     "lista": colisoes.eventos[:50]},
        "teleportes": {"total": len(teleportes), "lista": teleportes[:50]},
        "veiculo_passos_em_parada_de_emergencia": emergencias,
        "travessias_no_vermelho": vermelho[:20], "avisos_sumo": avisos,
        "decisoes": dict(sorted(decisoes.items())),
        "observacoes": {"amostras": estatisticas_obs["amostras"], "max_valor_local": estatisticas_obs["max_local"],
                        "dimensao_local": sensores.n_local if sensores else None,
                        "dimensao_supervisor": sensores.n_supervisor if sensores else None,
                        "acoes_locais": [len(c.verdes) for c in controladores] or None,
                        "areas": [{"tls": s["id"], "entradas": s["entradas"], "areas": s["areas"]}
                                  for s in sensores.esquemas] if sensores else None},
        "por_semaforo": por_tls, "outros_semaforos": outros_resumo,
        "problemas_rastreamento": dict(travessias.problemas),
    }
    ic.json_novo(pasta / "metricas.json", resultado)
    return resultado


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--politicas", nargs="+", default=POLITICAS, choices=POLITICAS)
    ap.add_argument("--sementes", nargs="+", type=int, default=[1, 2, 3])
    ap.add_argument("--assumir", type=int, default=300, help="segundo em que o controle assume (aquecimento)")
    ap.add_argument("--gui", action="store_true")
    ap.add_argument("--sem-verde-maximo", action="store_true",
                    help="desliga a protecao de verde maximo condicional (so para demonstrar o risco de bloqueio)")
    args = ap.parse_args()
    antes = ic.hashes_cenario()
    pasta = ic.nova_pasta("teste_integracao" + ("_sem_verde_maximo" if args.sem_verde_maximo else ""))
    resumo = []
    for politica in args.politicas:
        for semente in args.sementes:
            print(f"{politica:12s} semente {semente} ...", end=" ", flush=True)
            r = rodar(pasta / f"{politica}_semente{semente}", politica, semente, args.assumir, args.gui,
                      not args.sem_verde_maximo)
            resumo.append(r)
            if r.get("erro"):
                print("ERRO:", r["erro"]["mensagem"], flush=True)
                continue
            p = r["por_semaforo"]
            print(("APROVADO" if r["aprovado"] else "REPROVADO") +
                  f" | concluidas {r['viagens']['concluidas']}/{r['viagens']['registradas']}"
                  f" | espera media {r['viagens']['espera_media_s']} s"
                  f" | atendidos {[p[t]['veiculos_atendidos_total'] for t in ic.CONTROLADOS]}"
                  f" | colisoes {r['colisoes']['nos_controlados']} nos 3 + {r['colisoes']['fora_dos_controlados']} fora"
                  f" | teleportes {r['teleportes']['total']}"
                  f" | violacoes {sum(p[t]['verificacao']['violacoes'] for t in ic.CONTROLADOS)}"
                  f" | {r['duracao_real_s']} s", flush=True)
            for f in r["falhas"]:
                print("    -", f, flush=True)
    ic.conferir_cenario(antes)
    tabela = [{k: r.get(k) for k in ("politica", "semente", "aprovado", "protecao_verde_maximo", "falhas")} |
              ({"espera_media_s": r["viagens"]["espera_media_s"], "concluidas": r["viagens"]["concluidas"],
                "colisoes": r["colisoes"]["eventos"], "colisoes_nos_controlados": r["colisoes"]["nos_controlados"],
                "locais_colisoes": [e["juncao"] or e["faixa"] for e in r["colisoes"]["lista"]],
                "teleportes": r["teleportes"]["total"],
                "intervencoes_verde_maximo": {t: r["por_semaforo"][t]["intervencoes_verde_maximo"]
                                              for t in ic.CONTROLADOS},
                "atendidos": {t: r["por_semaforo"][t]["veiculos_atendidos_total"] for t in ic.CONTROLADOS},
                "como_assumiu": {t: r["por_semaforo"][t]["como_assumiu"] for t in ic.CONTROLADOS},
                "verdes": {t: r["por_semaforo"][t]["verificacao"]["verdes"] for t in ic.CONTROLADOS},
                "amarelos": {t: r["por_semaforo"][t]["verificacao"]["amarelos"] for t in ic.CONTROLADOS},
                "vermelhos_gerais": {t: r["por_semaforo"][t]["verificacao"]["vermelhos_gerais"]
                                     for t in ic.CONTROLADOS}}
               if not r.get("erro") else {"erro": r["erro"]["mensagem"]}) for r in resumo]
    ic.json_novo(pasta / "resumo.json", {"hashes_cenario_inalterados": antes, "rodadas": tabela})
    aprovados = sum(r["aprovado"] for r in resumo)
    print(f"\n{aprovados}/{len(resumo)} rodadas aprovadas. Resultados em {pasta}")
    return 0 if aprovados == len(resumo) else 1


if __name__ == "__main__":
    sys.exit(main())
