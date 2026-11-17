"""EXPERIMENTO C5: copia de ../../otimizacao_final/ambiente_marl_insper_v2.py com a lista de semaforos
CONTROLADOS e a lista de semaforos MEDIDOS configuraveis (rodar_episodio(..., controlados=, medidos=)).
Com os padroes (controlados = os 3 do corredor, medidos = os mesmos) o comportamento e o da v2
(conferido em testar_c5.py). Mudancas:
  - controladores seguros, protecao de escrita, verificadores, conflitos e metricas por cruzamento
    seguem as listas, nao mais os 3 fixos; "outros" = os 14 menos os controlados;
  - a metrica do CORREDOR (espera nas areas de 100 m e dentro dos 3 cruzamentos da Ribeirao Claro, por
    veiculo que entrou por uma via de entrada direta deles) e o bloqueio da saida continuam restritos
    aos 3 originais, para comparar com os resultados anteriores;
  - nova metrica por cruzamento medido (mesma definicao, restrita a cada cruzamento), fila por
    aproximacao e colisoes por cruzamento;
  - observacao local: no modo independente as 13 entradas sao a base de 9 do cruzamento + o codigo
    "sem supervisor" [1, 0, 0, 0] (exatamente o que o Modelo C viu com 3 agentes), qualquer que
    seja o numero de controlados; o modo hierarquico so e aceito com os 3 originais.

Ambiente Multi-Agent do corredor Insper, VERSAO 2 (otimizacao final).

Copia de ../ambiente_marl_insper.py (v1, preservado) com tres opcoes experimentais,
todas em CONFIG; CONFIG_V1 reproduz exatamente a v1:
  verde_minimo  10 (v1) ou 5 s. Amarelo 3 s do programa e vermelho geral 2 s
                continuam iguais; o verificador independente cobra o minimo configurado.
  colisao       "global" (v1: -10000 por novo contato em QUALQUER lugar da rede, para
                todos os atores) ou "atribuida": so contatos dentro de um dos 3
                cruzamentos ou nas vias que entram/saem deles penalizam, e so o agente
                local desse(s) cruzamento(s) e o supervisor. Os demais contatos sao
                registrados (classe externa_area_observacao ou externa_distante), sem
                penalidade, porque nao ha como atribui-los as decisoes dos agentes.
  supervisor_s  30 (v1), 15 ou 10 s entre decisoes do supervisor.
Novo modo de comparacao: "atuado_equivalente" (controle classico atuado submetido as
MESMAS regras do RL; aproximacao do actuated do SUMO, nao reproducao exata).

--- documentacao da v1 ---
Ambiente Multi-Agent do corredor Insper (3 semaforos), derivado do Cologne8.

Reaproveita, sem alterar os originais:
  - ControladorFasesSeguro / SemaforosProtegidos (verde min 10 s, amarelo 3 s do
    programa, vermelho geral 2 s, verde maximo condicional 60 s);
  - SensoresInsper (observacao local 13, supervisor 48, formato do Cologne8);
  - DoubleDQN e Replay de scripts/agente_marl_cologne.py;
  - incremento_excesso e o contador de colisoes de scripts/ambiente_marl_cologne.py.

Mesmo protocolo de decisao do Cologne8 (ambiente_marl_cologne.rodar): relogio de
1 s, decisao local a cada 5 s depois do verde minimo, supervisor a cada 30 s,
transicoes semi-Markov (dt real), replay com a acao EXECUTADA.

Recompensa (forma do Cologne8):
  local_i   = -(fila_i + excesso_i + 0,5 * custo do priorizado) / 100 por segundo
  supervisor = -(fila + excesso do CORREDOR) / (100 * 3) por segundo
  colisao: -10000 por novo contato, para cada ator (penalidade de equipe)
  teletransporte: -10 por evento, para cada ator (no Cologne8 o episodio era abortado)
Diferencas necessarias: no Cologne8 a "rede" era toda controlada; aqui o
supervisor e cobrado pelo corredor (as 3 areas de chegada), nao pelos outros 11
semaforos que nao controla. Escalas da rede na observacao: 150 veiculos e 100
parados (maximos do cenario intenso), no lugar de 350/250.

Episodio: 0-300 s com os programas originais (aquecimento), controle de 300 s
ate a rede esvaziar depois de 3600 s (limite 5400 s).

Validade do episodio:
  travamento    fracao de parados na rede > 0,8 por 300 s seguidos, ou
                teletransportes > max(5, 1% dos veiculos); o episodio e encerrado
                e marcado invalido;
  nao_concluiu  menos de 95% das viagens concluidas no limite;
  ocasional     ate 1 teletransporte (o maximo do programa original nas 5 sementes):
                episodio valido, evento registrado;
  elevado       2..limite teletransportes: valido, mas marcado (pior que o baseline);
  seguranca     violacao das transicoes ou escrita em semaforo nao controlado:
                erro (interrompe o treino), nunca ignorado.
"""

from collections import Counter, defaultdict, deque
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

import numpy as np

AQUI = Path(__file__).resolve().parents[2]  # semaforo/integracao_insper
sys.path.insert(0, str(AQUI))
sys.path.insert(1, str(AQUI.parent / "scripts"))
import insper_comum as ic  # noqa: E402
from controle_seguro_insper import ControladorFasesSeguro, ErroSeguranca, SemaforosProtegidos  # noqa: E402
from observacao_insper import SensoresInsper, area_montante  # noqa: E402
from ambiente_marl_cologne import incremento_excesso, ContadorColisoes  # noqa: E402

FORMATO = "smartflow_marl_insper_c5_v1"
OBJETIVO_SEM_SUPERVISOR = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)  # orientacao 0 do Modelo C (3 agentes)
N_BASE = 9
FORMATO_V1 = "smartflow_marl_insper_corredor_v1"
CONFIG_V1 = {"verde_minimo": 10, "colisao": "global", "supervisor_s": 30}
GAP_ATUADO_S = 3.0  # max-gap padrao do actuated do SUMO
TLS = list(ic.CONTROLADOS)
AQUECIMENTO, FIM_DEMANDA, LIMITE = 300, 3600, 5400
SUPERVISOR_S = 30
ESCALAS_REDE = {"veiculos_rede": 150, "fila_rede": 100}
RECOMPENSA = {"escala": 100.0, "peso_priorizado": 0.5, "colisao": -10000.0, "teletransporte": -10.0}
TRAVAMENTO = {"fracao_parados": 0.8, "janela_s": 300, "teletransportes_min": 5, "teletransportes_frac": 0.01,
              "conclusao_min": 0.95}
PRESO_S = 180
TELEPORTES_BASELINE = 1  # maximo observado com o programa original nas 5 sementes de validacao do intenso
SAIDA = "234368026#1"
TRECHOS = ["760437731", "234368026#0", SAIDA]
N_LOCAL, N_SUPERVISOR, ACOES_LOCAL, ACOES_SUPERVISOR = 13, 48, 2, 4


def criar_agentes(modelo, semente, aquecimento=2000):
    """Mesmas sementes e hiperparametros locais nos dois modelos."""
    from agente_marl_cologne import DoubleDQN
    locais = [DoubleDQN(N_LOCAL, ACOES_LOCAL, 1000 * semente + k, aquecimento=aquecimento) for k in range(3)]
    if modelo == "hierarquico":
        return locais + [DoubleDQN(N_SUPERVISOR, ACOES_SUPERVISOR, 1000 * semente + 99, supervisor=True,
                                   aquecimento=aquecimento)]
    if modelo == "independente":
        return locais
    raise ValueError(modelo)


def pressao_maxima(conn, c):
    """Max-Pressure como no Cologne8 (modo max_pressure de ambiente_marl_cologne.rodar):
    soma, por faixa de entrada liberada, parados na entrada - media de parados nas saidas."""
    links = conn.trafficlight.getControlledLinks(c.id)
    pressoes = []
    for verde in c.verdes:
        por_faixa = defaultdict(set)
        for k, it in enumerate(links):
            if verde[k] in "Gg":
                por_faixa[it[0][0]].add(it[0][1])
        pressoes.append(sum(conn.lane.getLastStepHaltingNumber(f)
                            - statistics.fmean(conn.lane.getLastStepHaltingNumber(o) for o in saidas)
                            for f, saidas in por_faixa.items()))
    return max(range(len(pressoes)), key=lambda k: (pressoes[k], k == c.fase))


def atuado_equivalente(conn, c, ids, dados, tc):
    """Controle atuado classico sob as regras do RL (decisao a cada 5 s apos o verde minimo).

    Mantem o verde se algum veiculo que vai cruzar este semaforo por um link VERDE esta a
    no maximo GAP_ATUADO_S segundos da linha de retencao (ou parado a ate 30 m dela, fila
    em descarga). Senao, troca se ha veiculo esperando/chegando por link vermelho.
    Aproxima o actuated do SUMO (detectores e max-gap de 3 s), sem reproduzi-lo."""
    verde = c.verdes[c.fase]
    estender = demanda_vermelho = False
    for vid in ids:
        for proximo, link, dist, _ in conn.vehicle.getNextTLS(vid):
            if proximo == c.id:
                v = dados[vid][tc.VAR_SPEED] if vid in dados else 0.0
                if verde[int(link)] in "Gg":
                    if dist <= max(v, 0.1) * GAP_ATUADO_S or (v < 0.1 and dist <= 30):
                        estender = True
                else:
                    demanda_vermelho = True
            break
    if estender or not demanda_vermelho:
        return c.fase
    return (c.fase + 1) % len(c.verdes)


def classificar_colisao(faixa, entra, sai, area, juncoes_area, tls=TLS):
    """Classe espacial de um contato e os indices (0..2) dos semaforos a que ele e atribuivel.

    controlado: dentro de um dos 3 cruzamentos ou numa via que entra/sai dele (a luz desse
    semaforo governa diretamente quem esta ali). externa_area_observacao: em via ou juncao
    sem semaforo dentro das areas de 100 m (relacao possivel via fila, mas INCERTA).
    externa_distante: o resto da rede. So 'controlado' gera alvo."""
    j = ic.juncao_da_faixa(faixa)
    if j in tls:
        return "controlado", {tls.index(j)}
    edge = faixa.rsplit("_", 1)[0]
    alvo = {i for i in range(len(tls)) if edge in entra[i] or edge in sai[i]}
    if alvo:
        return "controlado", alvo
    if edge in area or (j is not None and j in juncoes_area):
        return "externa_area_observacao", set()
    return "externa_distante", set()


def penalidade_colisao(alvo, n_agentes, modo, n_locais=len(TLS)):
    """Penalidade por UM novo contato. global (v1): todos os atores, em qualquer lugar.
    atribuida: so os locais em `alvo` e o supervisor (indice 3), e so se houver alvo."""
    if modo == "global":
        return [RECOMPENSA["colisao"]] * n_agentes
    return [RECOMPENSA["colisao"] if alvo and (k in alvo or k == n_locais) else 0.0 for k in range(n_agentes)]


def _pct(v, q):
    if not v:
        return None
    v = sorted(v)
    k = (len(v) - 1) * q / 100
    a, b = math.floor(k), math.ceil(k)
    return round(v[a] + (v[b] - v[a]) * (k - a), 2)


def _resumo(v):
    v = list(v)
    return {"n": len(v), "media": round(statistics.fmean(v), 3), "p95": _pct(v, 95), "max": round(max(v), 2)} \
        if v else {"n": 0}


_NET = None


def _rede():
    global _NET
    if _NET is None:
        ic.sumo_home()
        import sumolib
        _NET = sumolib.net.readNet(str(ic.REDE))
    return _NET


def rodar_episodio(cfg, pasta, semente, agentes=None, modo="hierarquico", treinando=False,
                   monitor_completo=False, limite=LIMITE, rotulo=None, porta=None, config=None,
                   controlados=None, medidos=None):
    """Um episodio. modo: original | max_pressure | atuado_equivalente | independente | hierarquico."""
    cfgv = dict(CONFIG_V1, **(config or {}))
    if (cfgv["verde_minimo"] not in (5, 10) or cfgv["colisao"] not in ("global", "atribuida")
            or cfgv["supervisor_s"] not in (10, 15, 30)):
        raise ValueError(f"configuracao nao validada: {cfgv}")
    import traci
    import traci.constants as tc
    if modo not in ("original", "max_pressure", "atuado_equivalente", "independente", "hierarquico"):
        raise ValueError(modo)
    controlar = modo != "original"
    CTRL = [] if not controlar else list(controlados) if controlados is not None else list(TLS)
    MED = list(dict.fromkeys(list(TLS) + CTRL + list(medidos or [])))  # os 3 do corredor sempre primeiro
    if len(set(CTRL)) != len(CTRL) or (controlar and not CTRL):
        raise ValueError(f"lista de controlados invalida: {CTRL}")
    if modo == "hierarquico" and (CTRL != list(TLS) or MED != list(TLS)):
        raise ValueError("o modo hierarquico so foi validado com os 3 cruzamentos originais")
    n_agentes = {"original": 0, "max_pressure": 0, "atuado_equivalente": 0, "independente": len(CTRL),
                 "hierarquico": 4}[modo]
    if n_agentes and (agentes is None or len(agentes) != n_agentes):
        raise ValueError("numero de agentes incompativel com o modo")
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=False)
    tmp = Path(tempfile.mkdtemp(prefix="insper_ep_"))
    sumo = ic.sumo_home() / "bin" / "sumo.exe"
    cmd = [str(sumo), "-c", str(cfg), "--seed", str(semente), "--end", str(limite),
           "--tripinfo-output", str(tmp / "tripinfo.xml"), "--tripinfo-output.write-unfinished", "true",
           "--log", str(pasta / "sumo.log"), "--verbose", "false", "--no-step-log", "true",
           "--duration-log.disable", "true",
           # como no Cologne8: espera acumulada sem esquecimento (o padrao do SUMO esquece apos 100 s)
           "--waiting-time-memory", "10000",
           "--collision.action", "warn", "--collision.check-junctions", "true"]
    inicio_real = time.perf_counter()
    rotulo = rotulo or f"ep_{os.getpid()}_{semente}"
    traci.start(cmd, label=rotulo, port=porta)
    conn = traci.getConnection(rotulo)
    erro = None
    try:
        if ic.VERSAO_SUMO not in conn.getVersion()[1]:
            raise RuntimeError("versao do SUMO")
        tls_ids = sorted(conn.trafficlight.getIDList())
        outros = [t for t in tls_ids if t not in CTRL]
        if len(tls_ids) != 14 or not set(MED) <= set(tls_ids) or len(outros) != 14 - len(CTRL):
            raise RuntimeError(f"semaforos inesperados: {tls_ids}")
        net = _rede()
        foes, vias = {}, {}
        for t in MED:
            foes[t], vias[t], _ = ic.foes_traci(conn, t)
        protegido = SemaforosProtegidos(conn.trafficlight, CTRL)
        # areas de chegada (mesmas do observador) para filas, excesso e espera no corredor
        area, area_aprox, entradas_med = {}, {}, []
        for i, t in enumerate(MED):
            entradas_med.append(sorted({it[0][0].rsplit("_", 1)[0] for it in conn.trafficlight.getControlledLinks(t)}))
            for e in entradas_med[-1]:
                for edge in area_montante(net, e, 100.0):
                    if edge in area:
                        raise RuntimeError(f"via {edge} em duas areas de observacao")
                    area[edge] = i
                    area_aprox[edge] = (i, e)
        entrada_de = {e: i for i, es in enumerate(entradas_med) for e in es}
        internos_med = [f":{t}_" for t in MED]
        no_cruz = [set() for _ in MED]
        espera_cruz = [defaultdict(int) for _ in MED]
        fila_aprox = Counter()
        jusante = [(i, k, it[0][0], it[0][1]) for i, t in enumerate(TLS)
                   for k, it in enumerate(conn.trafficlight.getControlledLinks(t))
                   if it[0][1].rsplit("_", 1)[0] in TRECHOS]
        monitoradas = {f for _, _, a, b in jusante for f in (a, b)}
        comprimento = {f: conn.lane.getLength(f) for f in monitoradas}
        monitores = {t: ic.MonitorPrograma(conn, t, 0) for t in outros} if monitor_completo else {}
        vars_ = [tc.VAR_LANE_ID, tc.VAR_ROAD_ID, tc.VAR_SPEED, tc.VAR_ACCUMULATED_WAITING_TIME,
                 tc.VAR_WAITING_TIME, tc.VAR_LANEPOSITION]
        colisoes = ContadorColisoes()
        eventos_colisao, teleportes = [], []
        anteriores = {}
        # espera no corredor: segundos parado nas areas de chegada e dentro dos 3 cruzamentos,
        # media sobre TODOS os veiculos que chegaram a uma via de entrada dos 3 (inclusive espera zero)
        espera_corredor, espera_corredor_total = defaultdict(int), defaultdict(int)
        no_corredor, no_corredor_total = set(), set()
        entradas_diretas = {it[0][0].rsplit("_", 1)[0] for t in TLS for it in conn.trafficlight.getControlledLinks(t)}
        internos = tuple(f":{t}_" for t in TLS)
        espera_max = defaultdict(float)
        filas = [[] for _ in MED]
        bloqueio = [0] * 3
        parados_janela = deque(maxlen=TRAVAMENTO["janela_s"])
        n = len(MED)
        idx_ctrl = [MED.index(t) for t in CTRL]
        acumulados = [0.0] * n_agentes
        recompensas = [0.0] * n_agentes
        pendentes = [None] * n_agentes
        decisoes, intervencoes = Counter(), Counter()
        controladores, sensores = [], None
        # observa desde t=0 (para medir o verde em curso), cobra a partir de AQUECIMENTO
        verificadores = {t: ic.VerificadorSeguranca(
            t, foes[t], 3, ic.TEMPOS["vermelho_geral"] if t in CTRL else 0,
            cfgv["verde_minimo"] if t in CTRL else 5, AQUECIMENTO) for t in MED}
        # classificacao espacial das colisoes (registro sempre; penalidade so se 'atribuida')
        entra = {i: {it[0][0].rsplit("_", 1)[0] for it in conn.trafficlight.getControlledLinks(t)}
                 for i, t in enumerate(CTRL)}
        sai = {i: {it[0][1].rsplit("_", 1)[0] for it in conn.trafficlight.getControlledLinks(t)}
               for i, t in enumerate(CTRL)}
        juncoes_area = {net.getEdge(e).getToNode().getID() for e in area} - set(MED)
        ultima_faixa = {}

        orientacao, proximo_sup = 0, AQUECIMENTO
        gerados = sum(1 for v in ET.parse((Path(cfg).parent / ET.parse(cfg).getroot()
                                           .find("input/route-files").get("value")).resolve()).getroot()
                      if v.tag in ("vehicle", "trip"))
        limite_tele = max(TRAVAMENTO["teletransportes_min"], math.ceil(TRAVAMENTO["teletransportes_frac"] * gerados))
        dados = {}
        invalido, fim_natural = None, False
        agora = int(conn.simulation.getTime())

        def demanda_links(tls, ids):
            d = Counter()
            for vid in ids:
                for proximo, link, _, _ in conn.vehicle.getNextTLS(vid):
                    if proximo == tls:
                        d[int(link)] += 1
                    break
            return d

        while True:
            if agora == AQUECIMENTO:
                if controlar:
                    for t in CTRL:
                        controladores.append(ControladorFasesSeguro(
                            protegido, t, agora, foes[t], verde_minimo=cfgv["verde_minimo"],
                            vermelho_geral=ic.TEMPOS["vermelho_geral"],
                            intervalo_decisao=ic.TEMPOS["intervalo_decisao"], verde_maximo=ic.TEMPOS["verde_maximo"]))
                    sensores = SensoresInsper(conn, net, controladores, escalas=ESCALAS_REDE)
                    if [e["n_base"] for e in sensores.esquemas] != [N_BASE] * len(CTRL) or (
                            modo == "hierarquico" and sensores.n_supervisor != N_SUPERVISOR):
                        raise RuntimeError("dimensoes de observacao inesperadas")
            if controladores:
                for c in controladores:
                    c.atualizar(agora)
                foto = sensores.ler(dados, tc)
                locais, sup = sensores.vetores(foto, agora, orientacao)
                if modo != "hierarquico":
                    locais = [np.concatenate([l[:N_BASE], OBJETIVO_SEM_SUPERVISOR]) for l in locais]
                if modo == "hierarquico" and agora >= proximo_sup:
                    k = n
                    if pendentes[k] is not None:
                        st, ac, t0, total = pendentes[k]
                        agentes[k].lembrar(st, ac, acumulados[k] - total, sup, agora - t0, False, treinando)
                    orientacao, _, explorou = agentes[k].escolher(sup, treinando)
                    pendentes[k] = (sup.copy(), orientacao, agora, acumulados[k])
                    decisoes[f"supervisor_{orientacao}"] += 1
                    proximo_sup = agora + cfgv["supervisor_s"]
                    locais, sup = sensores.vetores(foto, agora, orientacao)
                    if modo != "hierarquico":
                        locais = [np.concatenate([l[:N_BASE], OBJETIVO_SEM_SUPERVISOR]) for l in locais]
                for i, c in enumerate(controladores):
                    if not c.pode_decidir(agora):
                        continue
                    estado = locais[i]
                    if n_agentes and pendentes[i] is not None:
                        st, ac, t0, total = pendentes[i]
                        agentes[i].lembrar(st, ac, acumulados[i] - total, estado, agora - t0, False, treinando)
                    if modo == "max_pressure":
                        pedida = pressao_maxima(conn, c)
                    elif modo == "atuado_equivalente":
                        pedida = atuado_equivalente(conn, c, foto["locais"][i]["ids"], dados, tc)
                    else:
                        pedida, _, explorou = agentes[i].escolher(estado, treinando)
                    executada, interveio = c.proteger(int(pedida), agora, demanda_links(c.id, foto["locais"][i]["ids"]))
                    motivo = c.pedir(int(executada), agora)
                    if motivo not in ("mantida", "troca_iniciada"):
                        raise ErroSeguranca(f"{c.id}: decisao elegivel recusada ({motivo})")
                    # o replay guarda a acao EXECUTADA (depois da protecao de verde maximo)
                    if n_agentes:
                        pendentes[i] = (estado.copy(), int(executada), agora, acumulados[i])
                    decisoes[f"{c.id}:{motivo}"] += 1
                    if interveio:
                        intervencoes[c.id] += 1
                        if treinando and n_agentes:
                            agentes[i].intervencoes += 1
            conn.simulationStep()
            agora = int(conn.simulation.getTime())
            for vid in conn.simulation.getDepartedIDList():
                conn.vehicle.subscribe(vid, vars_)
            for vid in conn.simulation.getStartingTeleportIDList():
                teleportes.append({"tempo": agora, "veiculo": vid, "faixa": ultima_faixa.get(vid)})
            dados = conn.vehicle.getAllSubscriptionResults()
            fila = [0] * n
            excesso = [0.0] * n
            parados = 0
            pos_min, pos_max = {}, {}
            novos = {}
            for vid, r in dados.items():
                acumulada = float(r[tc.VAR_ACCUMULATED_WAITING_TIME])
                inc = incremento_excesso(acumulada, anteriores.get(vid))
                novos[vid] = acumulada
                w = r[tc.VAR_WAITING_TIME]
                if w > espera_max[vid]:
                    espera_max[vid] = w
                via = r[tc.VAR_ROAD_ID]
                ultima_faixa[vid] = r[tc.VAR_LANE_ID]
                i = area.get(via)
                parado = r[tc.VAR_SPEED] < 0.1
                if via in entradas_diretas:
                    no_corredor_total.add(vid)
                    if agora > AQUECIMENTO:
                        no_corredor.add(vid)
                if agora > AQUECIMENTO:  # metrica por cruzamento medido (mesma definicao da do corredor)
                    q = entrada_de.get(via)
                    if q is not None:
                        no_cruz[q].add(vid)
                    if parado:
                        q = i if i is not None else next((k for k, p in enumerate(internos_med) if via.startswith(p)), None)
                        if q is not None:
                            espera_cruz[q][vid] += 1
                        if via in area_aprox:
                            fila_aprox[area_aprox[via]] += 1
                if parado and ((i is not None and i < len(TLS)) or via.startswith(internos)):
                    espera_corredor_total[vid] += 1
                    if agora > AQUECIMENTO:
                        espera_corredor[vid] += 1
                if i is not None:
                    excesso[i] += inc
                    if parado:
                        fila[i] += 1
                if parado:
                    parados += 1
                    f = r[tc.VAR_LANE_ID]
                    if f in monitoradas:
                        p = r[tc.VAR_LANEPOSITION]
                        pos_min[f] = min(p, pos_min.get(f, p))
                        pos_max[f] = max(p, pos_max.get(f, p))
            anteriores = novos
            estados = {t: conn.trafficlight.getRedYellowGreenState(t) for t in MED}
            for t, v in verificadores.items():
                v.observar(agora, estados[t])
            for c in controladores:
                c.conferir(agora)
            if monitores:
                for m in monitores.values():
                    m.conferir(agora)
            elif agora % 60 == 0:
                for t in outros:
                    if conn.trafficlight.getProgram(t) != "0":
                        raise ErroSeguranca(f"semaforo nao controlado {t} saiu do programa original")
            novas = colisoes.atualizar([{"veiculos": [c.collider, c.victim], "tempo": agora, "tipo": c.type,
                                         "faixa": c.lane} for c in conn.simulation.getCollisions()]
                                       if conn.simulation.getCollidingVehiclesNumber() else [])
            penal_col = [0.0] * n_agentes
            for e in novas:
                e["classe"], alvo = classificar_colisao(e["faixa"], entra, sai, area, juncoes_area, CTRL)
                e["semaforos_associados"] = [CTRL[i] for i in sorted(alvo)]
                penal_col = [a + b for a, b in zip(penal_col, penalidade_colisao(alvo, n_agentes, cfgv["colisao"],
                                                                                 len(CTRL)))]
            eventos_colisao.extend(novas)
            novos_tele = conn.simulation.getStartingTeleportNumber()
            if agora > AQUECIMENTO:
                for i in range(n):
                    filas[i].append(fila[i])
                ocup = {f: (comprimento[f] - pos_min[f]) / comprimento[f] if f in pos_min else 0.0 for f in monitoradas}
                bloqueados = set()
                for i, k, entrada, saida in jusante:
                    if (estados[TLS[i]][k] in "Gg" and pos_max.get(entrada, -1) >= comprimento[entrada] - 15
                            and ocup[saida] >= 0.8):
                        bloqueados.add(i)
                for i in bloqueados:
                    bloqueio[i] += 1
            if controladores:
                custos = [fila[i] + excesso[i] for i in range(n)]
                extra = RECOMPENSA["peso_priorizado"] * custos[orientacao - 1] if orientacao else 0.0
                inc = [-(custos[i] + extra) / RECOMPENSA["escala"] for i in idx_ctrl]
                if modo == "hierarquico":
                    inc.append(-sum(custos) / (RECOMPENSA["escala"] * n))
                penal = RECOMPENSA["teletransporte"] * novos_tele
                for k in range(n_agentes):
                    acumulados[k] += inc[k] + penal + penal_col[k]
                    recompensas[k] += inc[k] + penal + penal_col[k]
            parados_janela.append(parados / len(dados) if dados else 0.0)
            if (agora > AQUECIMENTO + TRAVAMENTO["janela_s"] and len(parados_janela) == parados_janela.maxlen
                    and statistics.fmean(parados_janela) > TRAVAMENTO["fracao_parados"]):
                invalido = "travamento_rede_parada"
            elif len(teleportes) > limite_tele:
                invalido = "travamento_teletransportes"
            if invalido:
                break
            if agora >= FIM_DEMANDA and conn.simulation.getMinExpectedNumber() == 0:
                fim_natural = True
                break
            if agora >= limite:
                break
        # fim do episodio: transicoes pendentes sem bootstrap (como no Cologne8)
        if controladores:
            foto = sensores.ler(dados, tc)
            locais, sup = sensores.vetores(foto, agora, orientacao)
            if modo != "hierarquico":
                locais = [np.concatenate([l[:N_BASE], OBJETIVO_SEM_SUPERVISOR]) for l in locais]
            for k, p in enumerate(pendentes):
                if p is not None:
                    st, ac, t0, total = p
                    agentes[k].lembrar(st, ac, acumulados[k] - total, sup if k == n else locais[k],
                                       max(1, agora - t0), True, treinando)
        em_rede = conn.vehicle.getIDCount()
        nao_inseridos = len(conn.simulation.getPendingVehicles())
        conn.close()
        conn = None
    except Exception as e:
        erro = e
        raise
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        if erro is not None:
            ic.json_novo(pasta / "erro.json", {"tipo": type(erro).__name__, "mensagem": str(erro)})
            shutil.rmtree(tmp, ignore_errors=True)
    # ------------------------------------------------------------ metricas resumidas
    viagens = ET.parse(tmp / "tripinfo.xml").getroot().findall("tripinfo")
    shutil.rmtree(tmp, ignore_errors=True)
    completas = [v for v in viagens if float(v.get("arrival")) >= 0]
    concluidas = len(completas) / gerados
    if invalido is None and limite >= LIMITE and concluidas < TRAVAMENTO["conclusao_min"]:
        invalido = "nao_concluiu"
    seg = {t: verificadores[t].resumo() for t in MED} if verificadores else {}
    violacoes = sum(s["violacoes"] for s in seg.values())
    if violacoes:
        ic.json_novo(pasta / "erro.json", {"tipo": "ErroSeguranca", "violacoes": {t: s["primeiras_violacoes"] for t, s in seg.items()}})
        raise ErroSeguranca(f"{violacoes} violacoes de seguranca: {[s['primeiras_violacoes'][:2] for s in seg.values()]}")
    if monitores and any(m.erros for m in monitores.values()):
        raise ErroSeguranca("um dos 11 semaforos nao controlados saiu do programa original")
    for e in eventos_colisao:
        e["juncao"] = ic.juncao_da_faixa(e["faixa"]) or e["faixa"]
    col_controlados = sum(1 for e in eventos_colisao if e["juncao"] in CTRL)
    col_por_cruzamento = {t: sum(1 for e in eventos_colisao if e["juncao"] == t) for t in MED}
    passos = max(1, len(filas[0]))
    cruzamentos = {t: {"controlado": t in CTRL, "veiculos": len(no_cruz[q]),
                       "espera_s": _resumo(espera_cruz[q].get(v, 0) for v in no_cruz[q]),
                       "fila": _resumo(filas[q]), "colisoes": col_por_cruzamento[t],
                       "aproximacoes": {e: {"fila_media": round(fila_aprox[(q, e)] / passos, 4)} for e in entradas_med[q]}}
                   for q, t in enumerate(MED)}
    m = {
        "formato": FORMATO, "config": cfgv, "modo": modo, "treinando": treinando, "semente_trafego": semente,
        "cfg": str(cfg),
        "valido": invalido is None, "motivo_invalido": invalido, "fim_natural": fim_natural, "fim_s": agora,
        "duracao_real_s": round(time.perf_counter() - inicio_real, 1),
        "veiculos_gerados": gerados, "veiculos_concluidos": len(completas), "fracao_concluida": round(concluidas, 4),
        "em_rede_no_fim": em_rede, "nao_inseridos_no_fim": nao_inseridos,
        "presos_gt180s": sum(1 for w in espera_max.values() if w > PRESO_S),
        "espera_rede_s": _resumo(float(v.get("waitingTime")) for v in viagens),
        "espera_corredor_s": _resumo(espera_corredor.get(v, 0) for v in no_corredor),
        "espera_corredor_desde_t0_s": _resumo(espera_corredor_total.get(v, 0) for v in no_corredor_total),
        "controlados": CTRL, "medidos": MED, "cruzamentos": cruzamentos,
        "filas": {t: _resumo(filas[i]) for i, t in enumerate(MED)},
        "verde_bloqueado_a_jusante_s": dict(zip(TLS, bloqueio)), "bloqueio_saida_corredor_s": bloqueio[2],
        "colisoes": {"eventos": len(eventos_colisao), "nos_controlados": col_controlados,
                     "nos_medidos": sum(col_por_cruzamento.values()),
                     "por_classe": dict(Counter(e["classe"] for e in eventos_colisao)),
                     "lista": eventos_colisao[:20]},
        "entreverdes_s": {t: round(sum(s[k].get("n", 0) * s[k].get("media", 0)
                                       for k in ("amarelos", "vermelhos_gerais")), 1) for t, s in seg.items()},
        "teleportes": {"total": len(teleportes), "limite_travamento": limite_tele,
                       "classe": ("nenhum" if not teleportes else "travamento" if invalido and "telet" in invalido
                                  else "ocasional" if len(teleportes) <= TELEPORTES_BASELINE else "elevado"),
                       "lista": teleportes[:20]},
        "seguranca": {"violacoes": 0, "verificacao": {t: {k: s[k] for k in ("verdes", "amarelos", "vermelhos_gerais")}
                                                      for t, s in seg.items()},
                      "escritas_em_nao_controlados": 0},
        "outros_semaforos": {t: {"trocas": mo.trocas, "erros": len(mo.erros)} for t, mo in monitores.items()},
        "decisoes": dict(decisoes), "intervencoes_verde_maximo": dict(intervencoes),
        "trocas": {c.id: c.trocas for c in controladores},
        "recompensas": [round(r, 4) for r in recompensas],
        "avisos_sumo": ic.avisos_log(pasta / "sumo.log")["por_tipo"],
    }
    if not all(math.isfinite(r) for r in recompensas):
        raise ValueError("recompensa nao finita")
    ic.json_novo(pasta / "metricas.json", m)
    return m
