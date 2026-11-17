"""Diagnostico do cenario Insper para o MARL: rede, rotas, demanda e fases.

Nao controla semaforo nenhum: roda o cenario com os programas originais e so
observa. Nao altera os arquivos do cenario (os hashes sao conferidos no fim).

uso (na raiz do repositorio):
    python -B -X utf8 semaforo/integracao_insper/diagnosticar_cenario_insper.py [--sementes padrao 1 2]
"""

import argparse
from collections import Counter, defaultdict
import math
from pathlib import Path
import statistics
import sys
import time
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import insper_comum as ic  # noqa: E402

ALCANCE_SENSOR = 100.0  # metros a montante, para propor a area de observacao


def est(v):
    v = list(v)
    if not v:
        return {"n": 0}
    return {"n": len(v), "min": round(min(v), 2), "media": round(statistics.fmean(v), 2),
            "mediana": round(statistics.median(v), 2), "max": round(max(v), 2)}


# ---------------------------------------------------------------- parte estatica

def tls_da_conexao(e1, e2):
    for c in e1.getConnections(e2):
        if c.getTLSID():
            return c.getTLSID()
    return None


def area_montante(edge, alcance):
    """Arvore de vias que levam a `edge` ate `alcance` m antes da linha de retencao."""
    area, fila = [], [(edge, 0.0)]
    vistos = set()
    while fila:
        e, antes = fila.pop(0)
        if e.getID() in vistos:
            continue
        vistos.add(e.getID())
        area.append({"edge": e.getID(), "nome": e.getName(), "comprimento_m": round(e.getLength(), 1),
                     "faixas": e.getLaneNumber(), "inicio_m": round(antes, 1)})
        fim = antes + e.getLength()
        if fim >= alcance:
            continue
        no = e.getFromNode()
        if no.getType() == "traffic_light":
            area[-1]["para_em_semaforo"] = no.getID()
            continue
        for anterior in e.getIncoming():
            if anterior.getFunction() != "internal" and not anterior.getID().startswith(":"):
                fila.append((anterior, fim))
    return area


def analisar_rede(net, raiz):
    tl_ids = sorted(t.getID() for t in net.getTrafficLights())
    xml_tls = {t.get("id"): t for t in raiz.findall("tlLogic")}
    controlados = {}
    for tls in ic.CONTROLADOS:
        no = net.getNode(tls)
        conexoes = sorted(net.getTLS(tls).getConnections(), key=lambda c: c[2])
        links = []
        for entrada, saida, indice in conexoes:
            con = next(c for c in entrada.getEdge().getConnections(saida.getEdge())
                       if c.getFromLane() == entrada and c.getToLane() == saida)
            links.append({"link": indice, "de": entrada.getID(), "para": saida.getID(),
                          "via": con.getViaLaneID(), "direcao": con.getDirection(),
                          "rua_de": entrada.getEdge().getName(), "rua_para": saida.getEdge().getName()})
        fases = [{"state": p.get("state"), "duration": float(p.get("duration")),
                  "minDur": float(p.get("minDur")) if p.get("minDur") else None,
                  "maxDur": float(p.get("maxDur")) if p.get("maxDur") else None}
                 for p in xml_tls[tls].findall("phase")]
        foes_req = ic.foes_requisicao(raiz, tls)
        # o <request> usa o indice da juncao; converte para o linkIndex do semaforo
        juncao_para_link = {ic.indice_juncao(l["via"]): l["link"] for l in links}
        foes_link = {juncao_para_link[i]: sorted(juncao_para_link[j] for j in f) for i, f in foes_req.items()}
        entradas = []
        for e in no.getIncoming():
            entradas.append({"edge": e.getID(), "nome": e.getName(), "comprimento_m": round(e.getLength(), 1),
                             "faixas": e.getLaneNumber(), "velocidade_ms": e.getSpeed(),
                             "prioridade": e.getPriority(), "tipo": e.getType(),
                             "no_anterior": e.getFromNode().getID(), "tipo_no_anterior": e.getFromNode().getType(),
                             "area_montante_100m": area_montante(e, ALCANCE_SENSOR)})
        saidas = [{"edge": e.getID(), "nome": e.getName(), "comprimento_m": round(e.getLength(), 1),
                   "faixas": e.getLaneNumber(), "proximo_no": e.getToNode().getID(),
                   "tipo_proximo_no": e.getToNode().getType()} for e in no.getOutgoing()]
        controlados[tls] = {"nome": ic.CONTROLADOS[tls], "xy": no.getCoord(),
                            "tipo_programa": xml_tls[tls].get("type"), "programa": xml_tls[tls].get("programID"),
                            "offset": xml_tls[tls].get("offset"), "fases": fases, "links": links,
                            "foes_request": foes_link, "entradas": entradas, "saidas": saidas}
    # relacao espacial e rotas entre os tres
    ids = list(ic.CONTROLADOS)
    pares = {}
    for a in ids:
        for b in ids:
            if a == b:
                continue
            melhor = None
            for s in net.getNode(a).getOutgoing():
                for e in net.getNode(b).getIncoming():
                    caminho, custo = net.getShortestPath(s, e, vClass="passenger")
                    if caminho and (melhor is None or custo < melhor[1]):
                        melhor = (caminho, custo)
            if melhor is None:
                pares[f"{a}->{b}"] = {"existe_rota": False}
                continue
            caminho, custo = melhor
            semaforos = [t for t in (tls_da_conexao(x, y) for x, y in zip(caminho, caminho[1:])) if t]
            pares[f"{a}->{b}"] = {"existe_rota": True, "comprimento_m": round(custo, 1),
                                  "n_vias": len(caminho), "vias": [x.getID() for x in caminho],
                                  "ruas": list(dict.fromkeys(x.getName() for x in caminho)),
                                  "semaforos_atravessados_entre": [t for t in semaforos if t not in (a, b)],
                                  "ligacao_direta": len(caminho) == 1}
    distancias = {f"{a}-{b}": round(ic.distancia(net.getNode(a).getCoord(), net.getNode(b).getCoord()), 1)
                  for i, a in enumerate(ids) for b in ids[i + 1:]}
    # os outros 11 semaforos
    outros = {}
    for tls in tl_ids:
        if tls in ic.CONTROLADOS:
            continue
        t = net.getTLS(tls)
        nos = sorted({c[0].getEdge().getToNode().getID() for c in t.getConnections()})
        xy = net.getNode(nos[0]).getCoord()
        vizinho_direto = []
        for c in ids:
            for e in net.getNode(c).getOutgoing():
                if e.getToNode().getID() in nos:
                    vizinho_direto.append({"de": c, "via": e.getID(), "comprimento_m": round(e.getLength(), 1)})
            for e in net.getNode(c).getIncoming():
                if e.getFromNode().getID() in nos:
                    vizinho_direto.append({"para": c, "via": e.getID(), "comprimento_m": round(e.getLength(), 1)})
        outros[tls] = {"tipo": xml_tls[tls].get("type"), "n_links": len(xml_tls[tls].find("phase").get("state")),
                       "n_fases": len(xml_tls[tls].findall("phase")), "nos": nos,
                       "distancia_ao_mais_proximo_m": round(min(ic.distancia(xy, net.getNode(c).getCoord())
                                                                for c in ids), 1),
                       "ligado_diretamente_a": vizinho_direto}
    return {"total_semaforos": len(tl_ids), "ids": tl_ids, "controlados": controlados,
            "distancias_retas_m": distancias, "rotas_entre_controlados": pares, "outros_semaforos": outros}


# ---------------------------------------------------------------- parte dinamica

def rodar(pasta, semente, rotulo, links_controlados):
    import traci.constants as tc
    pasta.mkdir(exist_ok=False)
    conn = ic.iniciar(ic.comando_sumo(pasta, semente), rotulo)
    inicio_real = time.perf_counter()
    try:
        tls_ids = sorted(conn.trafficlight.getIDList())
        if len(tls_ids) != 14 or not set(ic.CONTROLADOS) <= set(tls_ids):
            raise RuntimeError(f"Semaforos inesperados: {tls_ids}")
        monitores = {t: ic.MonitorPrograma(conn, t, 0) for t in tls_ids}
        foes, verificadores, vias = {}, {}, {}
        for t in ic.CONTROLADOS:
            foes[t], vias[t], _ = ic.foes_traci(conn, t)
            # programa original: sem vermelho geral, verde minimo do programa (5 s)
            verificadores[t] = ic.VerificadorSeguranca(t, foes[t], 3, 0, 5, 0)
        geo = {t: conn.simulation.convertGeo(*conn.junction.getPosition(t)) for t in ic.CONTROLADOS}
        pares_tls = {}
        for t in tls_ids:
            for itens in conn.trafficlight.getControlledLinks(t):
                for entrada, saida, _ in itens:
                    pares_tls[(entrada.rsplit("_", 1)[0], saida.rsplit("_", 1)[0])] = t
        faixas_entrada = {t: sorted({i[0][0] for i in conn.trafficlight.getControlledLinks(t)})
                          for t in ic.CONTROLADOS}
        travessias = ic.Travessias(conn, tls_ids)
        colisoes = ic.ContadorColisoes()
        planejado, partida = {}, {}
        teleportes, emergencias = [], 0
        parados = {t: defaultdict(list) for t in ic.CONTROLADOS}
        while conn.simulation.getMinExpectedNumber() > 0 and conn.simulation.getTime() < 7200:
            conn.simulationStep()
            agora = int(conn.simulation.getTime())
            for vid in conn.simulation.getDepartedIDList():
                conn.vehicle.subscribe(vid, [tc.VAR_LANE_ID])
                rota = conn.vehicle.getRoute(vid)
                partida[vid] = agora
                planejado[vid] = list(dict.fromkeys(pares_tls[p] for p in zip(rota, rota[1:]) if p in pares_tls))
            for vid in conn.simulation.getStartingTeleportIDList():
                teleportes.append({"tempo": agora, "veiculo": vid})
                travessias.esquecer(vid, "teleporte_durante_travessia")
            estados = {t: conn.trafficlight.getRedYellowGreenState(t) for t in tls_ids}
            for t in tls_ids:
                monitores[t].conferir(agora)
            for t, v in verificadores.items():
                v.observar(agora, estados[t])
            faixas = {vid: r[tc.VAR_LANE_ID] for vid, r in conn.vehicle.getAllSubscriptionResults().items()}
            travessias.atualizar(agora, faixas, estados)
            for vid in conn.simulation.getArrivedIDList():
                travessias.esquecer(vid, "chegou_antes_de_sair_do_cruzamento")
            colisoes.atualizar(conn, agora)
            emergencias += conn.simulation.getEmergencyStoppingVehiclesNumber()
            for t, faixas_t in faixas_entrada.items():
                for f in faixas_t:
                    parados[t][f.rsplit("_", 1)[0]].append(conn.lane.getLastStepHaltingNumber(f))
        fim = int(conn.simulation.getTime())
        pendentes = len(conn.simulation.getPendingVehicles())
        conn.close()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        raise
    # ------------------------------------------------------------ agregacao
    por_tls = {}
    for t in ic.CONTROLADOS:
        regs = [r for r in travessias.registros if r["tls"] == t]
        por_link = Counter(r["link"] for r in regs)
        links = links_controlados[t]
        por_aproximacao = Counter(links[r["link"]]["de"].rsplit("_", 1)[0] for r in regs)
        planejados = sum(t in p for p in planejado.values())
        por_tls[t] = {"veiculos_planejados_na_insercao": planejados,
                      "veiculos_observados_cruzando": len({r["veiculo"] for r in regs}),
                      "travessias": len(regs), "por_link": dict(sorted(por_link.items())),
                      "por_aproximacao": dict(por_aproximacao),
                      "luz_ao_cruzar": dict(Counter(r["luz"] for r in regs)),
                      "travessias_aproximadas": sum(r["aproximado"] for r in regs),
                      "por_15min": dict(sorted(Counter(int(r["tempo"] // 900) * 15 for r in regs).items())),
                      "parados_por_aproximacao": {e: {"media": round(statistics.fmean(v), 3), "max": max(v)}
                                                  for e, v in parados[t].items()},
                      "programa_original": monitores[t].resumo(),
                      "verificacao_original": verificadores[t].resumo(),
                      "lon_lat": geo[t]}
    sequencias = Counter()
    tempos_corredor = defaultdict(list)
    ids = list(ic.CONTROLADOS)
    for vid, lista in travessias.por_veiculo.items():
        nossos = [(tempo, t) for tempo, t in lista if t in ic.CONTROLADOS]
        if not nossos:
            continue
        seq = tuple(t for _, t in nossos)
        sequencias[" > ".join(seq)] += 1
        for (t1, a), (t2, b) in zip(nossos, nossos[1:]):
            tempos_corredor[f"{a}->{b}"].append(t2 - t1)
    compartilhado = Counter(len(set(k.split(" > "))) for k in sequencias.elements())
    planej_seq = Counter(" > ".join(t for t in p if t in ic.CONTROLADOS) for p in planejado.values())
    planej_seq.pop("", None)
    divergentes = sum(1 for vid, p in planejado.items()
                      if [t for t in p if t in ic.CONTROLADOS] !=
                      [t for _, t in travessias.por_veiculo.get(vid, []) if t in ic.CONTROLADOS])
    luz_outros = Counter(r["luz"] for r in travessias.registros if r["tls"] not in ic.CONTROLADOS)
    resultado = {
        "semente": semente if semente is not None else "padrao_do_sumo",
        "fim_simulacao_s": fim, "duracao_real_s": round(time.perf_counter() - inicio_real, 1),
        "viagens_no_arquivo": len(ET.parse(ic.VIAGENS).getroot().findall("trip")),
        "veiculos_inseridos": len(partida), "pendentes_no_fim": pendentes,
        "viagens": ic.ler_tripinfo(pasta / "tripinfo.xml"),
        "estatisticas_sumo": ic.ler_estatisticas(pasta / "estatisticas_sumo.xml"),
        "colisoes": {"eventos": len(colisoes.eventos), "lista": colisoes.eventos[:50],
                     "por_juncao": dict(Counter(ic.juncao_da_faixa(e["faixa"]) or e["faixa"]
                                                for e in colisoes.eventos))},
        "teleportes": {"total": len(teleportes), "lista": teleportes[:50]},
        "veiculo_passos_em_parada_de_emergencia": emergencias,
        "avisos_sumo": ic.avisos_log(pasta / "sumo.log"),
        "por_semaforo": por_tls,
        "sequencias_entre_os_tres": dict(sequencias.most_common()),
        "veiculos_por_numero_de_controlados_cruzados": dict(sorted(compartilhado.items())),
        "sequencias_planejadas_na_insercao": dict(planej_seq.most_common()),
        "veiculos_com_rota_observada_diferente_da_planejada": divergentes,
        "tempo_entre_cruzamentos_s": {k: est(v) for k, v in tempos_corredor.items()},
        "luz_ao_cruzar_nos_outros_11": dict(luz_outros),
        "problemas_rastreamento": dict(travessias.problemas),
        "exemplos_nao_mapeados": travessias.nao_mapeadas,
        "outros_semaforos_programa_original": {t: monitores[t].resumo() for t in tls_ids
                                               if t not in ic.CONTROLADOS},
    }
    return resultado


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sementes", nargs="+", default=["padrao", "1", "2"])
    args = ap.parse_args()
    ic.sumo_home()
    import sumolib
    antes = ic.hashes_cenario()
    pasta = ic.nova_pasta("diagnostico")
    raiz = ic.ler_rede_xml()
    net = sumolib.net.readNet(str(ic.REDE), withPrograms=True)
    rede = analisar_rede(net, raiz)
    links = {t: {l["link"]: l for l in d["links"]} for t, d in rede["controlados"].items()}
    rodadas = {}
    for s in args.sementes:
        semente = None if s == "padrao" else int(s)
        print(f"rodando programa original, semente {s} ...", flush=True)
        rodadas[s] = rodar(pasta / f"original_semente_{s}", semente, f"diag_{s}", links)
        r = rodadas[s]
        print(f"  {r['veiculos_inseridos']} inseridos, {r['viagens']['concluidas']} concluidas, "
              f"{r['colisoes']['eventos']} colisoes, {r['teleportes']['total']} teleportes, "
              f"{r['duracao_real_s']} s", flush=True)
    # o mesmo que o usuario viu no SUMO-GUI (tripinfos.xml/stats.xml do cenario, so leitura)
    referencia = {"tripinfos_do_cenario": ic.ler_tripinfo(ic.CENARIO / "tripinfos.xml"),
                  "stats_do_cenario": ic.ler_estatisticas(ic.CENARIO / "stats.xml")}
    # conferencia: foes do <request> == foes geometricos do TraCI
    pasta_foes = pasta / "conferencia_foes"
    pasta_foes.mkdir()
    conn = ic.iniciar(ic.comando_sumo(pasta_foes, None, limite=1), "diag_foes")
    try:
        for t in ic.CONTROLADOS:
            f_traci, _, _ = ic.foes_traci(conn, t)
            req = {int(k): set(v) for k, v in rede["controlados"][t]["foes_request"].items()}
            rede["controlados"][t]["foes_traci"] = {k: sorted(v) for k, v in f_traci.items()}
            rede["controlados"][t]["foes_request_igual_traci"] = req == f_traci
    finally:
        conn.close()
    ic.conferir_cenario(antes)
    dados = {"cenario": str(ic.CENARIO.relative_to(ic.SEMAFORO.parent)), "hashes_cenario": antes,
             "rede": rede, "rodadas_programa_original": rodadas, "referencia_gui_do_usuario": referencia,
             "nota": "planejado = rota calculada pelo SUMO na insercao (trips sem rota fixa); observado = "
                     "veiculo que efetivamente cruzou a linha de retencao de um link do semaforo"}
    ic.json_novo(pasta / "diagnostico.json", dados)
    print("diagnostico salvo em", pasta)


if __name__ == "__main__":
    main()
