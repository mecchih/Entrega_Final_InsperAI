"""Avalia uma demanda do cenario Insper com os programas semaforicos ORIGINAIS.

Nenhum semaforo e controlado: o TraCI so le o estado da simulacao. Mede o
corredor (476455095, 40278305, 40278183), o semaforo seguinte (cluster a 27,5 m
depois de 40278183) e a rede inteira. Todas as saidas vao para a pasta indicada.
"""

from collections import Counter, defaultdict
import csv
import math
from pathlib import Path
import re
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import insper_comum as ic  # noqa: E402
from observacao_insper import area_montante  # noqa: E402

SEGUINTE = "cluster_13529541823_13529541824_300058941_300063845_#2more"
SAIDA_CORREDOR = "234368026#1"
TRECHOS = ["760437731", "234368026#0", SAIDA_CORREDOR]  # o que liga 476->403->401->seguinte
LIMITE = 3600 + 1800
JANELA = (300, 3600)  # estatisticas de fila: depois do inicio, ate o fim da demanda
PRESO_S = 180  # espera continua acima disso = veiculo preso


def pct(v, q):
    if not v:
        return None
    v = sorted(v)
    k = (len(v) - 1) * q / 100
    a, b = math.floor(k), math.ceil(k)
    return round(v[a] + (v[b] - v[a]) * (k - a), 2)


def resumo(v):
    v = list(v)
    if not v:
        return {"n": 0}
    return {"n": len(v), "media": round(statistics.fmean(v), 3), "p95": pct(v, 95), "max": round(max(v), 2)}


def comando(cfg, pasta, semente):
    sumo = ic.sumo_home() / "bin" / "sumo.exe"
    return [str(sumo), "-c", str(cfg),
            "--additional-files", str(ic.CENARIO / "osm.poly.xml.gz"),
            "--tripinfo-output", str(pasta / "tripinfo.xml"), "--tripinfo-output.write-unfinished", "true",
            "--statistic-output", str(pasta / "estatisticas_sumo.xml"), "--log", str(pasta / "sumo.log"),
            "--verbose", "false", "--no-step-log", "true", "--duration-log.statistics", "true",
            "--collision.action", "warn", "--collision.check-junctions", "true",
            "--seed", str(semente), "--end", str(LIMITE)]


_NET = None


def rede():
    global _NET
    if _NET is None:
        ic.sumo_home()
        import sumolib
        _NET = sumolib.net.readNet(str(ic.REDE))
    return _NET


def teleportes_do_log(path):
    padrao = re.compile(r"Teleporting vehicle '([^']+)'; ([^,]+), lane='([^']*)', time=(\d+(?:\.\d+)?)")
    saida = []
    for linha in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        m = padrao.search(linha)
        if m:
            saida.append({"veiculo": m[1], "motivo": m[2], "faixa": m[3], "tempo": float(m[4])})
    return saida


def simular(cfg, pasta, semente, rotulo, porta=None):
    import traci
    import traci.constants as tc
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=False)
    cmd = comando(cfg, pasta, semente)
    ic.json_novo(pasta / "execucao.json", {"cfg": str(cfg), "semente_sumo": semente, "comando": cmd})
    net = rede()
    inicio_real = time.perf_counter()
    traci.start(cmd, label=rotulo, port=porta)
    conn = traci.getConnection(rotulo)
    try:
        if ic.VERSAO_SUMO not in conn.getVersion()[1]:
            raise RuntimeError("versao do SUMO")
        tls_ids = list(ic.CONTROLADOS)
        # areas de chegada (ate 100 m a montante, como no observador) e grupos verdes
        area, entradas, grupos = {}, {}, {}
        for i, t in enumerate(tls_ids):
            links = conn.trafficlight.getControlledLinks(t)
            entradas[t] = sorted({itens[0][0].rsplit("_", 1)[0] for itens in links})
            for j, e in enumerate(entradas[t]):
                for edge in area_montante(net, e, 100.0):
                    area[edge] = (t, j)
            logica = conn.trafficlight.getAllProgramLogics(t)[0]
            verdes = [p.state for p in logica.phases if "y" not in p.state and any(c in "Gg" for c in p.state)]
            grupos[t] = {link: g for g, s in enumerate(verdes) for link, c in enumerate(s) if c in "Gg"}
        entradas_seguinte = {itens[0][0].rsplit("_", 1)[0] for itens in conn.trafficlight.getControlledLinks(SEGUINTE)}
        comprimento = {}
        faixas_trecho = [f"{e}_{k}" for e in TRECHOS for k in range(net.getEdge(e).getLaneNumber())]
        faixas_chegada = {itens[0][0] for t in tls_ids for itens in conn.trafficlight.getControlledLinks(t)}
        monitoradas = set(faixas_trecho) | faixas_chegada
        for f in monitoradas:
            comprimento[f] = conn.lane.getLength(f)
        # links dos controlados cuja saida e um trecho do corredor (para "verde bloqueado a jusante")
        jusante = [(t, k, itens[0][0], itens[0][1]) for t in tls_ids
                   for k, itens in enumerate(conn.trafficlight.getControlledLinks(t))
                   if itens[0][1].rsplit("_", 1)[0] in TRECHOS]
        juncoes = set(tls_ids) | {SEGUINTE}
        travessias = ic.Travessias(conn, tls_ids + [SEGUINTE])
        colisoes = ic.ContadorColisoes()
        vars_ = [tc.VAR_LANE_ID, tc.VAR_ROAD_ID, tc.VAR_SPEED, tc.VAR_LANEPOSITION, tc.VAR_WAITING_TIME]
        espera_corredor = defaultdict(int)
        espera_max = defaultdict(float)
        ultima_faixa = {}
        teleportes = []
        series = []
        filas = {t: [] for t in tls_ids}
        filas_aprox = {t: [[] for _ in entradas[t]] for t in tls_ids}
        fila_seguinte, fila_saida, fracao_parados = [], [], []
        cheio = Counter()          # segundos com fila ocupando >= 90% de um trecho
        bloqueado = Counter()      # segundos com verde, fila na linha e trecho a jusante cheio
        episodios_bloqueio = Counter()
        anterior_bloqueado = set()
        parados_no_cruzamento = Counter()
        pendentes_max = 0
        agora = 0
        while conn.simulation.getMinExpectedNumber() > 0 and agora < LIMITE:
            conn.simulationStep()
            agora = int(conn.simulation.getTime())
            for vid in conn.simulation.getDepartedIDList():
                conn.vehicle.subscribe(vid, vars_)
            for vid in conn.simulation.getStartingTeleportIDList():
                teleportes.append({"tempo": agora, "veiculo": vid, "faixa": ultima_faixa.get(vid)})
                travessias.esquecer(vid, "teleporte")
            dados = conn.vehicle.getAllSubscriptionResults()
            fila = {t: [0] * len(entradas[t]) for t in tls_ids}
            seg = saida = parados = 0
            pos_min, pos_max = {}, {}
            faixas = {}
            for vid, r in dados.items():
                faixa, via, v = r[tc.VAR_LANE_ID], r[tc.VAR_ROAD_ID], r[tc.VAR_SPEED]
                faixas[vid] = faixa
                ultima_faixa[vid] = faixa
                w = r[tc.VAR_WAITING_TIME]
                if w > espera_max[vid]:
                    espera_max[vid] = w
                if v >= 0.1:
                    continue
                parados += 1
                g = area.get(via)
                if g is not None:
                    fila[g[0]][g[1]] += 1
                    espera_corredor[vid] += 1
                elif via.startswith(":"):
                    j = ic.juncao_da_faixa(via)
                    if j in juncoes:
                        parados_no_cruzamento[j] += 1
                        if j != SEGUINTE:
                            espera_corredor[vid] += 1
                if via in entradas_seguinte:
                    seg += 1
                    if via == SAIDA_CORREDOR:
                        saida += 1
                if faixa in monitoradas:
                    p = r[tc.VAR_LANEPOSITION]
                    pos_min[faixa] = min(p, pos_min.get(faixa, p))
                    pos_max[faixa] = max(p, pos_max.get(faixa, p))
            estados = {t: conn.trafficlight.getRedYellowGreenState(t) for t in tls_ids + [SEGUINTE]}
            travessias.atualizar(agora, faixas, estados)
            for vid in conn.simulation.getArrivedIDList():
                travessias.esquecer(vid, "chegou")
            colisoes.atualizar(conn, agora)
            pendentes = len(conn.simulation.getPendingVehicles())
            pendentes_max = max(pendentes_max, pendentes)

            def ocupacao(f):
                return (comprimento[f] - pos_min[f]) / comprimento[f] if f in pos_min else 0.0
            for e in TRECHOS:
                if any(ocupacao(f) >= 0.9 for f in faixas_trecho if f.rsplit("_", 1)[0] == e):
                    cheio[e] += 1
            agora_bloqueado = set()
            for t, k, entrada, saida_f in jusante:
                if (estados[t][k] in "Gg" and pos_max.get(entrada, -1) >= comprimento[entrada] - 15
                        and ocupacao(saida_f) >= 0.8):
                    agora_bloqueado.add(t)
            for t in agora_bloqueado:
                bloqueado[t] += 1
                if t not in anterior_bloqueado:
                    episodios_bloqueio[t] += 1
            anterior_bloqueado = agora_bloqueado
            if JANELA[0] <= agora <= JANELA[1]:
                for t in tls_ids:
                    filas[t].append(sum(fila[t]))
                    for j, n in enumerate(fila[t]):
                        filas_aprox[t][j].append(n)
                fila_seguinte.append(seg)
                fila_saida.append(saida)
                fracao_parados.append(parados / len(dados) if dados else 0.0)
            if agora % 10 == 0:
                series.append([agora, len(dados), parados, pendentes] + [sum(fila[t]) for t in tls_ids]
                              + [seg, saida] + [int(t in agora_bloqueado) for t in tls_ids])
        em_rede = conn.vehicle.getIDCount()
        pendentes_fim = len(conn.simulation.getPendingVehicles())
        fim = agora
        conn.close()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        raise
    with (pasta / "serie_10s.csv").open("x", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tempo", "veiculos_rede", "parados_rede", "pendentes_insercao"]
                   + [f"fila_{t}" for t in tls_ids] + ["fila_seguinte", "fila_saida_corredor"]
                   + [f"bloqueio_{t}" for t in tls_ids])
        w.writerows(series)
    # ------------------------------------------------------------ agregacao
    import xml.etree.ElementTree as ET
    viagens = ET.parse(pasta / "tripinfo.xml").getroot().findall("tripinfo")
    info = {v.get("id"): v for v in viagens}
    completas = [v for v in viagens if float(v.get("arrival")) >= 0]
    esperas_todas = [float(v.get("waitingTime")) for v in viagens]
    esperas_completas = [float(v.get("waitingTime")) for v in completas]
    cfg_raiz = ET.parse(cfg).getroot()
    rotas_path = (Path(cfg).parent / cfg_raiz.find("input/route-files").get("value")).resolve()
    raiz_rotas = ET.parse(rotas_path).getroot()
    gerados = sum(1 for v in raiz_rotas if v.tag in ("vehicle", "trip"))
    por_veiculo = defaultdict(list)
    for r in travessias.registros:
        por_veiculo[r["veiculo"]].append(r)
    corredor = {vid for vid, rs in por_veiculo.items() if any(r["tls"] in ic.CONTROLADOS for r in rs)}
    n_cruzados = Counter(len({r["tls"] for r in rs if r["tls"] in ic.CONTROLADOS}) for vid, rs in por_veiculo.items()
                         if vid in corredor)
    por_tls = {}
    for t in tls_ids:
        regs = [r for r in travessias.registros if r["tls"] == t]
        por_tls[t] = {"veiculos": len({r["veiculo"] for r in regs}),
                      "por_grupo_verde": {f"fase_{g}": n for g, n in
                                          sorted(Counter(grupos[t][r["link"]] for r in regs).items())},
                      "fila": {**resumo(filas[t]), "fracao_tempo_com_fila_ge1": round(sum(x >= 1 for x in filas[t]) / max(1, len(filas[t])), 3),
                               "fracao_tempo_com_fila_ge5": round(sum(x >= 5 for x in filas[t]) / max(1, len(filas[t])), 3),
                               "fracao_tempo_com_fila_ge10": round(sum(x >= 10 for x in filas[t]) / max(1, len(filas[t])), 3)},
                      "fila_por_aproximacao": {e: resumo(filas_aprox[t][j]) for j, e in enumerate(entradas[t])},
                      "segundos_verde_bloqueado_a_jusante": bloqueado[t],
                      "episodios_verde_bloqueado_a_jusante": episodios_bloqueio[t],
                      "veiculo_segundos_parados_dentro_do_cruzamento": parados_no_cruzamento[t]}
    seguinte_regs = [r for r in travessias.registros if r["tls"] == SEGUINTE]
    corredor_para_seguinte = {r["veiculo"] for r in seguinte_regs} & {r["veiculo"] for r in travessias.registros
                                                                      if r["tls"] == "40278183"}
    tele_log = teleportes_do_log(pasta / "sumo.log")
    for e in colisoes.eventos:
        e["juncao"] = ic.juncao_da_faixa(e["faixa"]) or e["faixa"]
    janela_parados = [statistics.fmean(fracao_parados[i:i + 300]) for i in range(0, max(1, len(fracao_parados) - 299), 60)] \
        if len(fracao_parados) >= 300 else [statistics.fmean(fracao_parados)] if fracao_parados else [0]
    resultado = {
        "cfg": str(cfg), "semente_sumo": semente, "fim_simulacao_s": fim,
        "duracao_real_s": round(time.perf_counter() - inicio_real, 1),
        "veiculos_gerados": gerados, "veiculos_inseridos": len(viagens) - sum(1 for v in viagens if float(v.get("depart")) < 0),
        "veiculos_concluidos": len(completas), "fracao_concluida": round(len(completas) / gerados, 4),
        "nao_inseridos_no_fim": pendentes_fim, "em_rede_no_fim": em_rede, "pendentes_insercao_max": pendentes_max,
        "veiculos_presos_espera_continua_gt_180s": sum(1 for w in espera_max.values() if w > PRESO_S),
        "por_semaforo": por_tls,
        "corredor": {"veiculos": len(corredor), "por_numero_de_cruzamentos": dict(sorted(n_cruzados.items())),
                     "veiculos_2_ou_3": n_cruzados[2] + n_cruzados[3],
                     "espera_no_corredor_s": resumo(espera_corredor.get(v, 0) for v in corredor),
                     "espera_viagem_veiculos_do_corredor_s": resumo(float(info[v].get("waitingTime"))
                                                                    for v in corredor if v in info),
                     "segundos_trecho_com_fila_ge90pct": dict(cheio),
                     "veiculos_40278183_para_seguinte": len(corredor_para_seguinte)},
        "seguinte": {"id": SEGUINTE, "fila_entradas": resumo(fila_seguinte),
                     "fila_saida_corredor_234368026#1": resumo(fila_saida),
                     "veiculo_segundos_parados_dentro_do_cruzamento": parados_no_cruzamento[SEGUINTE],
                     "veiculos_atendidos": len({r["veiculo"] for r in seguinte_regs})},
        "rede": {"espera_todos_s": resumo(esperas_todas), "espera_concluidos_s": resumo(esperas_completas),
                 "perda_de_tempo_concluidos_s": resumo(float(v.get("timeLoss")) for v in completas),
                 "atraso_insercao_s": resumo(float(v.get("departDelay")) for v in viagens if float(v.get("depart")) >= 0),
                 "fracao_parados_media": round(statistics.fmean(fracao_parados), 3) if fracao_parados else None,
                 "fracao_parados_max_janela_5min": round(max(janela_parados), 3)},
        "colisoes": {"eventos": len(colisoes.eventos), "por_juncao": dict(Counter(e["juncao"] for e in colisoes.eventos)),
                     "lista": colisoes.eventos[:30]},
        "teleportes": {"total": len(teleportes), "por_motivo": dict(Counter(x["motivo"] for x in tele_log)),
                       "por_via": dict(Counter(x["faixa"].rsplit("_", 1)[0] for x in tele_log)), "lista": tele_log[:30]},
        "avisos_sumo": ic.avisos_log(pasta / "sumo.log"),
        "estatisticas_sumo": ic.ler_estatisticas(pasta / "estatisticas_sumo.xml"),
        "problemas_rastreamento": dict(travessias.problemas),
    }
    ic.json_novo(pasta / "metricas.json", resultado)
    return resultado
