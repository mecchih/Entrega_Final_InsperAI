"""Um relogio SUMO, controladores locais assincronos e supervisor regional.

O protocolo e derivado do RESCO: preserva rede, demanda e fases G/g; troca
os tempos/transicoes. Nao representa o controlador original nem a cidade toda.
"""

from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import numpy as np

from esquema_dqn_cologne3 import carregar_esquemas

PROJETO = Path(os.environ.get("SMARTFLOW_PROJETO", Path(__file__).resolve().parents[1])).resolve()
FORMATO = "smartflow_marl_supervisor_cologne_v1"
FORMATO_CONTINUO = "smartflow_marl_supervisor_cologne_continuo_v2"
INICIO, FIM = 25200, 28800


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_novo(path, dados):
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2, allow_nan=False)


def construir_manifesto(cenario="cologne8", continuar_apos_colisao=False):
    """Confere o manifesto anterior contra os arquivos reais, sem muda-los."""
    referencia = PROJETO / f"referencias/{cenario}_sumo_rl_1.4.5"
    dados_cenario = referencia / f"sumo_rl/nets/RESCO/{cenario}"
    net = ET.parse(dados_cenario / f"{cenario}.net.xml").getroot()
    if cenario == "cologne3":
        esquemas = carregar_esquemas()
    else:
        esquemas = []
        edges = {e.get("id"): e for e in net.findall("edge")}
        for t in sorted(net.findall("tlLogic"), key=lambda t: t.get("id")):
            links = [dict(c.attrib) for c in net.findall("connection") if c.get("tl") == t.get("id")]
            entradas = []
            for edge in {c["from"] for c in links}:
                faixas = [dict(l.attrib) for l in edges[edge].findall("lane")]
                coords = [tuple(map(float, p.split(","))) for p in faixas[0]["shape"].split()]
                dx, dy = coords[-2][0] - coords[-1][0], coords[-2][1] - coords[-1][1]
                rumo = math.degrees(math.atan2(dx, dy)) % 360
                entradas.append({"edge": edge, "faixas": faixas, "rumo_montante_graus": rumo,
                                 "rotulo_geografico": ["N", "L", "S", "O"][int((rumo + 45) // 90) % 4]})
            entradas.sort(key=lambda e: (["N", "L", "S", "O"].index(e["rotulo_geografico"]),
                                          e["rumo_montante_graus"], e["edge"]))
            fases = []
            for indice, fase in enumerate(t.findall("phase")):
                state = fase.get("state")
                if "y" in state.lower() or not any(c in "Gg" for c in state):
                    continue
                movimentos = [{**c, "luz": state[int(c["linkIndex"])]} for c in links
                              if state[int(c["linkIndex"])] in "Gg"]
                fases.append({"acao_local": len(fases), "indice_xml": indice, "state": state,
                              "movimentos_liberados": movimentos,
                              "entradas_liberadas": sorted({c["from"] for c in movimentos})})
            esquemas.append({"id": t.get("id"), "entradas": entradas, "fases": fases,
                             "n_acoes": len(fases), "n_entradas_rede": 3 * len(entradas) + len(fases) + 1})
    tls = {t.get("id"): t for t in net.findall("tlLogic")}
    if set(tls) != {s["id"] for s in esquemas}:
        raise ValueError("Semaforos da rede diferem da auditoria")
    conexoes = defaultdict(list)
    for c in net.findall("connection"):
        if c.get("tl"):
            conexoes[c.get("tl")].append(dict(c.attrib))
    for s in esquemas:
        fases = tls[s["id"]].findall("phase")
        for p in s["fases"]:
            if fases[p["indice_xml"]].get("state") != p["state"]:
                raise ValueError("Fase mudou na fonte")
        reais = {c["from"] for c in conexoes[s["id"]]}
        if reais != {e["edge"] for e in s["entradas"]}:
            raise ValueError("Entradas divergentes")
        s["conexoes"] = conexoes[s["id"]]
        s["entradas_com_supervisor"] = s["n_entradas_rede"] + len(esquemas) + 1
    demanda = ET.parse(dados_cenario / f"{cenario}.rou.xml").getroot()
    viagens = [v for v in demanda if v.tag in ("trip", "vehicle")]
    primeira_partida = min(float(v.get("depart")) for v in viagens)
    manifesto = {"formato": FORMATO, "cenario": cenario, "cidade_inteira": False,
            "controladores": esquemas,
            "acoes_supervisor": ["equilibrado"] + ["priorizar_" + s["id"] for s in esquemas],
            "entradas_supervisor": sum(s["n_entradas_rede"] for s in esquemas)
                + sum(len(s["entradas"]) for s in esquemas) + 3 * len(esquemas)
                + len(esquemas) + 1 + 2,
            "ordem_supervisor": ["vetores_locais_base_por_ordem_controladores",
                "ocupacao_jusante_por_aproximacao/100", "estagio_onehot_verde_amarelo_vermelho_por_tls",
                "orientacao_anterior_onehot", "veiculos_rede/350", "fila_rede/250"],
            "sensores": "vias imediatamente controladas; sem ampliar ou imputar montante",
            "escalas": {"fila": 25, "carros": 35, "tempo": 60, "espera": 120,
                        "teto_tempo": 2, "teto_espera": 3},
            "tempos": {"decisao_local": 5, "supervisor": 30, "verde_minimo": 10,
                       "amarelo": 3, "vermelho_geral_local": 2, "verde_max_condicional": 60},
            "recompensa": {"W": 60, "beta": 1, "escala": 100,
                "local": "-(fila_local + excesso_local + 0.5*custo_no_priorizado)/100 por segundo; termo prioritario zero em equilibrado",
                "supervisor": "-(fila_rede + excesso_rede)/(100*n_controladores) por segundo",
                "excesso": "somente incremento no segundo atual; nao cobra espera anterior a entrada na area",
                "colisao": -10000.0, "atribuicao_colisao": "penalidade de equipe para cada ator, por evento novo; termina episodio",
                "avaliacao_colisao": "colisoes precedem censura e espera na selecao"},
            "demanda": {"total": len(viagens), "tipos": dict(Counter(v.tag for v in viagens)),
                        "antes_controle": sum(float(v.get("depart")) < INICIO for v in viagens),
                        "primeira_partida": primeira_partida,
                        "ultima_partida": max(float(v.get("depart")) for v in viagens)},
            "episodio": {"inicio_aquecimento": min(INICIO, primeira_partida), "inicio_controle": INICIO,
                "fim_demanda": FIM, "escoamento_maximo": 1200,
                "fim_replay": "termino natural OU limite finito do episodio: sem bootstrap; flags separados"},
            "selecao": "menor total de eventos de colisao; depois menor demanda prevista nao concluida (inclui partidas futuras apos termino precoce); depois espera media afetada",
            "fontes": {str(p.relative_to(PROJETO)): sha(p) for p in
                (dados_cenario / f"{cenario}.net.xml", dados_cenario / f"{cenario}.rou.xml",
                 referencia / "proveniencia.json")}}
    if continuar_apos_colisao:
        manifesto["formato"] = FORMATO_CONTINUO
        manifesto["episodio"]["continuar_apos_colisao"] = True
        manifesto["recompensa"]["atribuicao_colisao"] = (
            "-10000 por novo contato para cada ator; contato continuo do mesmo par e cobrado uma vez; episodio continua")
        manifesto["recompensa"]["definicao_evento_colisao"] = (
            "par nao reportado no passo anterior; desaparece da lista e volta: novo contato")
    return manifesto


def incremento_excesso(atual, anterior, limite=60.0):
    """No maximo um segundo: nao transfere historico de outro cruzamento."""
    anterior = atual if anterior is None else anterior
    return min(1.0, max(0.0, max(0.0, atual - limite) - max(0.0, anterior - limite)))


class ContadorColisoes:
    """Conta o inicio de cada contato, sem cobrar novamente a cada segundo."""
    def __init__(self):
        self.ativos = set()

    def atualizar(self, registros):
        unicos = {tuple(sorted(r["veiculos"])): r for r in registros}
        novos = [r for chave, r in unicos.items() if chave not in self.ativos]
        self.ativos = set(unicos)
        return novos


class RelogioLocal:
    def __init__(self, esquema, conn, agora, evento):
        self.esquema, self.conn, self.evento = esquema, conn, evento
        self.id = esquema["id"]
        self.verdes = [p["state"] for p in esquema["fases"]]
        estado = conn.trafficlight.getRedYellowGreenState(self.id)
        self.n_links = len(estado)
        self.ultimo_servico = np.full(self.n_links, agora, dtype=float)
        self.intervencoes = 0
        self.trocas = 0
        if estado in self.verdes:
            self.fase = self.verdes.index(estado)
            self.estagio = "verde"
            idade = conn.trafficlight.getSpentDuration(self.id)
            self.inicio_verde = agora - idade
            self.proxima = agora + max(0, 10 - idade)
            self.limite = math.inf
            self._aplicar(agora, estado, "assumir_verde_original")
        else:
            original = list(conn.trafficlight.getAllProgramLogics(self.id)[0].phases)
            indice = conn.trafficlight.getPhase(self.id)
            seguinte = next((original[(indice + j) % len(original)].state
                              for j in range(1, len(original) + 1)
                              if original[(indice + j) % len(original)].state in self.verdes), None)
            if seguinte is None:
                raise ValueError("Nao foi possivel assumir o programa original")
            self.fase = self.verdes.index(seguinte)
            self.inicio_verde = agora
            self.proxima = math.inf
            self.estagio = "amarelo" if "y" in estado.lower() else "vermelho"
            self.limite = agora + max(1, conn.trafficlight.getNextSwitch(self.id) - agora)
            self._aplicar(agora, estado, "assumir_transicao_original")

    def _aplicar(self, agora, estado, motivo):
        self.conn.trafficlight.setRedYellowGreenState(self.id, estado)
        if self.conn.trafficlight.getRedYellowGreenState(self.id) != estado:
            raise AssertionError("SUMO nao executou o estado solicitado")
        self.evento({"tempo": agora, "tls": self.id, "estagio": self.estagio,
                     "fase_alvo": self.fase, "estado": estado, "motivo": motivo})

    def atualizar(self, agora):
        if self.estagio == "amarelo" and agora >= self.limite:
            self.estagio = "vermelho"
            self.limite = agora + 2
            self._aplicar(agora, "r" * self.n_links, "fim_amarelo")
        elif self.estagio == "vermelho" and agora >= self.limite:
            self.estagio = "verde"
            self.inicio_verde = agora
            self.proxima = agora + 10
            self.limite = math.inf
            self._aplicar(agora, self.verdes[self.fase], "fim_vermelho")
        if self.estagio == "verde":
            for link, luz in enumerate(self.verdes[self.fase]):
                if luz in "Gg":
                    self.ultimo_servico[link] = agora

    def elegivel(self, agora):
        return self.estagio == "verde" and agora >= self.proxima and agora - self.inicio_verde >= 10

    def proteger(self, pedida, agora, ids):
        if not self.elegivel(agora) or not 0 <= pedida < len(self.verdes):
            raise ValueError("Decisao fora do momento/fases validas")
        if pedida != self.fase or agora - self.inicio_verde < 60:
            return pedida, False
        demanda = Counter()
        for vid in ids:
            for tls, link, distancia, _ in self.conn.vehicle.getNextTLS(vid):
                if tls == self.id:
                    demanda[int(link)] += 1
                    break
        nao_atendidos = {l: n for l, n in demanda.items() if self.verdes[self.fase][l] not in "Gg"}
        candidatos = []
        for i, verde in enumerate(self.verdes):
            links = [l for l in nao_atendidos if verde[l] in "Gg"]
            if i != self.fase and links:
                candidatos.append((max(agora - self.ultimo_servico[l] for l in links),
                                   sum(nao_atendidos[l] for l in links), -i, i))
        if not candidatos:
            return pedida, False
        self.intervencoes += 1
        return max(candidatos)[-1], True

    def aplicar_acao(self, acao, agora):
        if acao == self.fase:
            self.proxima = agora + 5
            return
        if agora - self.inicio_verde < 10:
            raise AssertionError("Violacao de verde minimo")
        antigo = self.verdes[self.fase]
        self.fase = acao
        self.estagio = "amarelo"
        self.limite = agora + 3
        self.proxima = math.inf
        self.trocas += 1
        self._aplicar(agora, "".join("y" if x in "Gg" else "r" for x in antigo), "troca_local")


class Sensores:
    def __init__(self, conn, manifesto):
        import traci.constants as tc
        self.conn, self.esquemas = conn, manifesto["controladores"]
        self.vars = [tc.VAR_ROAD_ID, tc.VAR_SPEED, tc.VAR_ACCUMULATED_WAITING_TIME]
        self.tc = tc
        self.edge_grupo = {a["edge"]: (i, j) for i, s in enumerate(self.esquemas)
                           for j, a in enumerate(s["entradas"])}
        if len(self.edge_grupo) != sum(len(s["entradas"]) for s in self.esquemas):
            raise ValueError("Uma via foi atribuida a dois sensores")
        self.jusante = []
        for s in self.esquemas:
            self.jusante.append([sorted({c["to"] + "_" + c["toLane"] for c in s["conexoes"]
                                        if c["from"] == a["edge"]}) for a in s["entradas"]])
        self.anteriores = {}
        for vid in conn.vehicle.getIDList():
            conn.vehicle.subscribe(vid, self.vars)

    def ler(self):
        conn, tc = self.conn, self.tc
        for vid in conn.simulation.getDepartedIDList():
            conn.vehicle.subscribe(vid, self.vars)
        dados = conn.vehicle.getAllSubscriptionResults()
        locais = [{"filas": [0] * len(s["entradas"]), "carros": [0] * len(s["entradas"]),
                   "esperas": [0.0] * len(s["entradas"]), "excesso": 0.0, "ids": []}
                  for s in self.esquemas]
        fila_rede, excesso_rede = 0, 0.0
        novos = {}
        for vid, r in dados.items():
            espera = float(r[tc.VAR_ACCUMULATED_WAITING_TIME])
            parado = r[tc.VAR_SPEED] < 0.1
            excesso = incremento_excesso(espera, self.anteriores.get(vid))
            novos[vid] = espera
            fila_rede += int(parado)
            excesso_rede += excesso
            grupo = self.edge_grupo.get(r[tc.VAR_ROAD_ID])
            if grupo is not None:
                i, j = grupo
                local = locais[i]
                local["carros"][j] += 1
                local["filas"][j] += int(parado)
                local["esperas"][j] = max(local["esperas"][j], espera)
                local["excesso"] += excesso
                local["ids"].append(vid)
        self.anteriores = novos
        self.ultimos_dados = dados
        ocupacao = [[float(np.mean([conn.lane.getLastStepOccupancy(l) for l in lanes])) / 100.0
                     if lanes else 0.0 for lanes in grupo] for grupo in self.jusante]
        return {"locais": locais, "fila_rede": fila_rede, "carros_rede": len(dados),
                "excesso_rede": excesso_rede, "ocupacao": ocupacao}


def vetor_base(esquema, local, relogio, agora):
    p = esquema["n_acoes"]
    verde = relogio.estagio == "verde"
    valores = [x / 25.0 for x in local["filas"]] + [x / 35.0 for x in local["carros"]]
    valores += [float(verde and i == relogio.fase) for i in range(p)]
    valores += [min(max(0, agora - relogio.inicio_verde) / 60, 2) if verde else 0.0]
    valores += [min(x / 120, 3) for x in local["esperas"]]
    if len(valores) != esquema["n_entradas_rede"] or not all(math.isfinite(v) and v >= 0 for v in valores):
        raise ValueError("Observacao local invalida")
    return valores


def estados(manifesto, foto, relogios, agora, orientacao):
    n = len(relogios)
    if not 0 <= orientacao <= n:
        raise ValueError("Orientacao desconhecida")
    objetivo = [float(i == orientacao) for i in range(n + 1)]
    base = [vetor_base(s, l, r, agora) for s, l, r in
            zip(manifesto["controladores"], foto["locais"], relogios)]
    supervisor = sum(base, []) + sum(foto["ocupacao"], [])
    supervisor += [float(r.estagio == e) for r in relogios for e in ("verde", "amarelo", "vermelho")]
    supervisor += objetivo + [foto["carros_rede"] / 350, foto["fila_rede"] / 250]
    if len(supervisor) != manifesto["entradas_supervisor"] or not np.isfinite(supervisor).all():
        raise ValueError("Dimensao/valores do supervisor invalidos")
    return [np.asarray(b + objetivo, dtype=np.float32) for b in base], np.asarray(supervisor, dtype=np.float32)


def resumir_esperas(valores):
    a = np.asarray(valores, dtype=float)
    return {"n": len(a), "media": float(a.mean()) if len(a) else None,
            "p95": float(np.percentile(a, 95)) if len(a) else None,
            "maximo": float(a.max()) if len(a) else None}


def metricas_viagens(path, fim_demanda):
    abrir = gzip.open if str(path).endswith(".gz") else open
    with abrir(path, "rb") as f:
        trips = list(ET.parse(f).getroot().findall("tripinfo"))
    grupos = {"demanda_janela": [], "aquecimento": [], "afetados_pelo_controle": []}
    for v in trips:
        depart, arrival = float(v.get("depart")), float(v.get("arrival"))
        grupos["demanda_janela" if depart >= INICIO else "aquecimento"].append(v)
        if depart >= INICIO or arrival < 0 or arrival >= INICIO:
            grupos["afetados_pelo_controle"].append(v)
    saida = {}
    for nome, vs in grupos.items():
        completos = [v for v in vs if float(v.get("arrival")) >= 0]
        saida[nome] = {"inseridos": len(vs), "concluidos": len(completos),
            "interrompidos": len(vs) - len(completos),
            "espera_concluidos": resumir_esperas([float(v.get("waitingTime")) for v in completos]),
            "espera_todos_inclui_censura": resumir_esperas([float(v.get("waitingTime")) for v in vs]),
            "atraso_insercao": resumir_esperas([float(v.get("departDelay")) for v in vs]),
            "duracao_concluidos": resumir_esperas([float(v.get("duration")) for v in completos])}
    return saida


def rodar(manifesto, agentes, pasta, semente, treinando=False, duracao=3600,
          escoamento=1200, backend="libsumo", sumo_home=None, gui=False,
          modo="hierarquico", detalhar=False):
    """Executa UM episodio completo. Todos os caminhos de saida sao novos."""
    import sys
    continuar_colisao = manifesto["episodio"].get("continuar_apos_colisao", False)
    if sumo_home:
        # Priorizar o wheel Python instalado: a distribuicao portatil pode
        # conter um _libsumo.pyd de outra ABI ou com DLLs nao carregaveis.
        sys.path.append(str(Path(sumo_home).resolve() / "tools"))
    if backend == "libsumo":
        import libsumo as conn
        if gui:
            raise ValueError("GUI no Windows exige --backend traci")
    else:
        import traci as conn
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=False)
    inicio_real = time.perf_counter()
    cenario = manifesto["cenario"]
    referencia = PROJETO / f"referencias/{cenario}_sumo_rl_1.4.5/sumo_rl/nets/RESCO/{cenario}"
    net, rotas = referencia / f"{cenario}.net.xml", referencia / f"{cenario}.rou.xml"
    fim_demanda = INICIO + duracao
    if not 0 < duracao <= 3600 or escoamento < 0:
        raise ValueError("Janela invalida")
    if duracao < 3600:
        tree = ET.parse(rotas)
        for v in list(tree.getroot()):
            if v.tag in ("trip", "vehicle") and float(v.get("depart")) >= fim_demanda:
                tree.getroot().remove(v)
        rotas = pasta / "rotas_recorte_curto.rou.xml"
        tree.write(rotas, encoding="utf-8", xml_declaration=True)
    demanda_prevista = sum(v.tag in ("trip", "vehicle") for v in ET.parse(rotas).getroot())
    binario = str(Path(sumo_home).resolve() / "bin" / ("sumo-gui.exe" if gui else "sumo.exe")) if sumo_home else "sumo"
    tripinfo = pasta / "tripinfo.xml.gz"
    cmd = [binario, "-n", str(net), "-r", str(rotas), "--begin", str(manifesto["episodio"]["inicio_aquecimento"]), "--seed", str(semente),
           "--step-length", "1", "--no-step-log", "true", "--duration-log.disable", "true",
           "--time-to-teleport", "-1", "--waiting-time-memory", "10000",
           "--tripinfo-output", str(tripinfo), "--tripinfo-output.write-unfinished", "true",
           "--log", str(pasta / "sumo.log"), "--collision.action", "warn", "--collision.check-junctions", "true"]
    if gui:
        cmd += ["--start", "true", "--quit-on-end", "true"]
    json_novo(pasta / "execucao.json", {"semente": semente, "treinando": treinando,
        "modo": modo, "backend": backend, "duracao": duracao, "escoamento": escoamento, "comando": cmd})
    decisoes = (pasta / "decisoes.jsonl").open("x", encoding="utf-8") if detalhar else None
    eventos = (pasta / "fases.jsonl").open("x", encoding="utf-8") if detalhar else None
    n_eventos = 0
    def evento(dado):
        nonlocal n_eventos
        n_eventos += 1
        if eventos:
            eventos.write(json.dumps(dado, allow_nan=False) + "\n")
    iniciado = False
    try:
        conn.start(cmd)
        iniciado = True
        versao = conn.getVersion()
        if "1.28.0" not in versao[1]:
            raise ValueError(f"Exigido SUMO 1.28.0, encontrado {versao}")
        if set(conn.trafficlight.getIDList()) != {s["id"] for s in manifesto["controladores"]}:
            raise ValueError("Controladores SUMO divergentes")
        sensores = Sensores(conn, manifesto)
        while conn.simulation.getTime() < INICIO:
            conn.simulationStep()
            if (conn.simulation.getCollidingVehiclesNumber() and not continuar_colisao) or conn.simulation.getStartingTeleportNumber():
                raise RuntimeError("Colisao/teleporte no aquecimento sem acao dos agentes: auditar cenario antes de aprender")
            for vid in conn.simulation.getDepartedIDList():
                conn.vehicle.subscribe(vid, sensores.vars)
        foto = sensores.ler()
        agora = int(conn.simulation.getTime())
        carry = int(conn.vehicle.getIDCount())
        relogios = [RelogioLocal(s, conn, agora, evento) for s in manifesto["controladores"]] if modo != "original_fixo" else []
        # Confere todos os links, inclusive os nao verdes na fase atual.
        for s in manifesto["controladores"]:
            links = conn.trafficlight.getControlledLinks(s["id"])
            for c in s["conexoes"]:
                item = (c["from"] + "_" + c["fromLane"], c["to"] + "_" + c["toLane"], c["via"])
                if item not in [tuple(x) for x in links[int(c["linkIndex"])]]:
                    raise AssertionError("Movimento real diferente do manifesto")
        n = len(relogios)
        orientacao, proximo_supervisor = 0, agora
        acumulados = np.zeros(n + 1)
        pendentes = [None] * (n + 1)
        recompensas = np.zeros(n + 1)
        contagem = Counter()
        fila_soma = fila_local_soma = 0.0
        fila_max = colisoes = teleportes = passos = simultaneos = 0
        veiculos_colidentes = 0
        eventos_colisao = []
        contador_colisoes = ContadorColisoes()
        esperas_por_entrada = [defaultdict(float) for _ in relogios]
        while True:
            if modo != "original_fixo":
                for r in relogios:
                    r.atualizar(agora)
                locais, sup = estados(manifesto, foto, relogios, agora, orientacao)
                # O supervisor age antes, mas todos os atores locais leem a mesma foto.
                if modo == "hierarquico" and agora >= proximo_supervisor:
                    k = n
                    if pendentes[k] is not None:
                        st, ac, t, total = pendentes[k]
                        agentes[k].lembrar(st, ac, acumulados[k] - total, sup, agora - t, False, treinando)
                    orientacao, qs, explorou = agentes[k].escolher(sup, treinando)
                    pendentes[k] = (sup.copy(), orientacao, agora, acumulados[k])
                    contagem[f"supervisor_{orientacao}"] += 1
                    proximo_supervisor = agora + 30
                    if decisoes:
                        decisoes.write(json.dumps({"tempo": agora, "agente": "supervisor", "estado": sup.tolist(),
                            "q": qs, "acao": orientacao, "explorou": explorou}) + "\n")
                    locais, _ = estados(manifesto, foto, relogios, agora, orientacao)
                escolhas = []
                for i, r in enumerate(relogios):
                    if not r.elegivel(agora):
                        continue
                    estado = locais[i]
                    if pendentes[i] is not None:
                        st, ac, t, total = pendentes[i]
                        agentes[i].lembrar(st, ac, acumulados[i] - total, estado, agora - t, False, treinando)
                    if modo == "max_pressure":
                        qs = []
                        for verde in r.verdes:
                            por_faixa = defaultdict(set)
                            for c in r.esquema["conexoes"]:
                                if verde[int(c["linkIndex"])] in "Gg":
                                    por_faixa[c["from"] + "_" + c["fromLane"]].add(c["to"] + "_" + c["toLane"])
                            qs.append(sum(conn.lane.getLastStepHaltingNumber(l)
                                - np.mean([conn.lane.getLastStepHaltingNumber(o) for o in outs])
                                for l, outs in por_faixa.items()))
                        pedida, explorou = int(np.argmax(qs)), False
                    else:
                        pedida, qs, explorou = agentes[i].escolher(estado, treinando)
                    executada, interveio = r.proteger(pedida, agora, foto["locais"][i]["ids"])
                    if interveio and treinando:
                        agentes[i].intervencoes += 1
                    if modo != "max_pressure":
                        pendentes[i] = (estado.copy(), executada, agora, acumulados[i])
                    contagem[f"decisoes_{i}"] += 1
                    escolhas.append((i, executada))
                    if decisoes:
                        decisoes.write(json.dumps({"tempo": agora, "agente": r.id, "estado": estado.tolist(),
                            "q": [float(v) for v in qs], "pedida": pedida, "executada": executada,
                            "intervencao": interveio, "orientacao": orientacao,
                            "fase_alvo": r.verdes[executada], "explorou": explorou}) + "\n")
                for i, acao in escolhas:
                    relogios[i].aplicar_acao(acao, agora)
            # Um unico passo para TODOS os sinais e veiculos.
            conn.simulationStep()
            agora = int(conn.simulation.getTime())
            foto = sensores.ler()
            custos = np.array([sum(l["filas"]) + l["excesso"] for l in foto["locais"]])
            if n:
                extra = 0.5 * custos[orientacao - 1] if orientacao else 0.0
                incrementos = np.r_[-(custos + extra) / 100.0,
                    -(foto["fila_rede"] + foto["excesso_rede"]) / (100.0 * n)]
                acumulados += incrementos
                recompensas += incrementos
            raw_colisao = conn.simulation.getCollidingVehiclesNumber()
            veiculos_colidentes += raw_colisao
            novas_colisoes = 0
            registros = []
            if raw_colisao:
                presentes = set(conn.vehicle.getIDList())
                for c in conn.simulation.getCollisions():
                    chave = tuple(sorted((c.collider, c.victim)))
                    registros.append({"tempo": agora, "veiculos": list(chave), "tipo": c.type,
                                     "faixa_evento": c.lane, "posicao_evento": c.pos,
                                     "faixa_colisor": conn.vehicle.getLaneID(c.collider) if c.collider in presentes else None,
                                     "faixa_vitima": conn.vehicle.getLaneID(c.victim) if c.victim in presentes else None})
                if not registros:
                    raise RuntimeError("SUMO sinalizou colisao sem fornecer seus eventos")
            novos = contador_colisoes.atualizar(registros)
            novas_colisoes = len(novos)
            if novas_colisoes:
                eventos_colisao.extend(novos)
                colisoes += novas_colisoes
                penalidade = manifesto["recompensa"]["colisao"] * novas_colisoes
                acumulados += penalidade
                recompensas += penalidade
            teleportes += conn.simulation.getStartingTeleportNumber()
            if teleportes:
                raise RuntimeError(f"Episodio abortado por {teleportes} teleportes inesperados")
            passos += 1
            fila_soma += foto["fila_rede"]
            fila_local_soma += sum(sum(l["filas"]) for l in foto["locais"])
            fila_max = max(fila_max, foto["fila_rede"])
            simultaneos += int(bool(relogios) and all(r.estagio == "verde" for r in relogios))
            for i, l in enumerate(foto["locais"][:n]):
                dados = sensores.ultimos_dados
                for vid in l["ids"]:
                    edge = dados[vid][sensores.tc.VAR_ROAD_ID]
                    # Espera efetivamente acumulada enquanto na area, por veiculo.
                    esperas_por_entrada[i][(edge, vid)] += float(dados[vid][sensores.tc.VAR_SPEED] < 0.1)
            vazio = conn.simulation.getMinExpectedNumber() == 0
            limite = agora >= fim_demanda + escoamento
            if (novas_colisoes and not continuar_colisao) or (agora >= fim_demanda and vazio) or limite:
                break
        if relogios:
            locais, sup = estados(manifesto, foto, relogios, agora, orientacao)
            for i, pendente in enumerate(pendentes):
                if pendente is not None:
                    st, ac, t, total = pendente
                    agentes[i].lembrar(st, ac, acumulados[i] - total, sup if i == n else locais[i],
                                       agora - t, True, treinando)
        pendentes_insercao = len(conn.simulation.getPendingVehicles())
        remanescentes = conn.vehicle.getIDCount()
        intervencoes = sum(r.intervencoes for r in relogios)
        conn.close()
        iniciado = False
        viagens = metricas_viagens(tripinfo, fim_demanda)
        total_inseridos = sum(viagens[k]["inseridos"] for k in ("demanda_janela", "aquecimento"))
        total_concluidos = sum(viagens[k]["concluidos"] for k in ("demanda_janela", "aquecimento"))
        por_entrada = {}
        for i, r in enumerate(relogios):
            por_entrada[r.id] = {e["edge"]: resumir_esperas([w for (edge, _), w in esperas_por_entrada[i].items()
                                                          if edge == e["edge"]]) for e in r.esquema["entradas"]}
        resultado = {"semente": semente, "modo": modo, "treinando": treinando,
            "versao_sumo": list(versao), "fim_sumo": agora, "passos_controlados": passos,
            "duracao_real_s": time.perf_counter() - inicio_real, "veiculos_presentes_ao_assumir": carry,
            "terminado_naturalmente": vazio, "truncado_no_limite": limite and not vazio,
            "terminado_por_colisao": bool(colisoes) and not continuar_colisao, "eventos_colisao": eventos_colisao,
            "continuou_apos_colisao": bool(colisoes) and continuar_colisao,
            "segundos_apos_primeira_colisao": agora - eventos_colisao[0]["tempo"] if eventos_colisao else 0,
            "pendentes_insercao": pendentes_insercao, "remanescentes": remanescentes,
            "demanda_prevista": demanda_prevista, "viagens_nao_inseridas": demanda_prevista - total_inseridos,
            "viagens_nao_concluidas": demanda_prevista - total_concluidos,
            "colisoes": colisoes, "veiculos_colidentes_reportados": veiculos_colidentes,
            "penalidade_colisao_por_agente": manifesto["recompensa"]["colisao"] * colisoes,
            "teleportes": teleportes, "intervencoes": intervencoes,
            "trocas": sum(r.trocas for r in relogios), "eventos": n_eventos,
            "segundos_todos_tls_verdes": simultaneos,
            "fila_media_rede": fila_soma / passos, "fila_media_sensores_locais": fila_local_soma / passos,
            "fila_max_rede": fila_max, "recompensas": recompensas.tolist(),
            "decisoes": dict(contagem), "viagens": viagens,
            "espera_por_entrada": por_entrada,
            "nota_espera_por_entrada": "tempo parado na area durante controle, entre veiculos observados inclusive espera zero; nao e espera total de viagem"}
        json_novo(pasta / "metricas.json", resultado)
        return resultado
    except Exception as e:
        json_novo(pasta / "erro.json", {"tipo": type(e).__name__, "mensagem": str(e)})
        raise
    finally:
        if iniciado:
            conn.close()
        for f in (decisoes, eventos):
            if f:
                f.close()
