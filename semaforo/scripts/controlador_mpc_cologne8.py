"""Adaptador Cologne8 para o MPC CENTRAL store-and-forward externo (MIT).

Nao e o IR-MPC distribuido. Modelo/solver externos ficam intactos em referencias.
Sem torch, replay, recompensas ou acesso a partidas/rotas futuras. O perfil de
giros e destinos e estimado numa simulacao separada com o programa original.
"""

from collections import Counter, defaultdict, deque
from contextlib import contextmanager
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
from types import ModuleType
import xml.etree.ElementTree as ET

import numpy as np

PROJETO = Path(__file__).resolve().parents[1]
EXTERNO = PROJETO / "referencias/mpc_externo_fdbdf4a"
CONFIG = dict(STEP=120, STEPS=4, HORIZON=480, G_MIN=10, G_MAX=60,
              MU=1e-2, GREEN_WEIGHT=1e-4, CHI_BAR=0.9)


def json_novo(path, dados):
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, allow_nan=False, indent=2)


def _modulo(nome, path):
    spec = importlib.util.spec_from_file_location(nome, path)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@contextmanager
def _imports_temporarios(mapa):
    antes = {nome: sys.modules.get(nome) for nome in mapa}
    sys.modules.update(mapa)
    try:
        yield
    finally:
        for nome, valor in antes.items():
            if valor is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = valor


def carregar_modelo_externo():
    """Injeta apenas constantes e a classe QP; nao executa o launcher original."""
    base = _modulo("_smartflow_mpc_aligned", EXTERNO / "aligned_model.py")
    frozen = ModuleType("frozen")
    frozen.v3_model = base
    desenho = ModuleType("cc_design")
    desenho.__dict__.update(CONFIG)
    with _imports_temporarios({"cc_design": desenho, "frozen": frozen}):
        modelo = _modulo("_smartflow_mpc_central", EXTERNO / "cc_model.py")
    solver = _modulo("_smartflow_mpc_solver", EXTERNO / "strict_qp.py")
    return modelo, solver


def quantizar_verdes(valores, orcamento):
    """Maior resto em blocos de 5 s, preservando soma e limites 10--60 s."""
    a = np.asarray(valores, dtype=float)
    if (a.ndim != 1 or not np.isfinite(a).all() or orcamento % 5
            or abs(a.sum() - orcamento) > 0.01
            or np.any(a < 10 - 0.01) or np.any(a > 60 + 0.01)):
        raise ValueError("Verdes do QP nao atendem ao orcamento/limites")
    a = np.clip(a, 10, 60)
    blocos = np.floor(a / 5 + 1e-8).astype(int)
    faltam = int(orcamento // 5 - blocos.sum())
    ordem = sorted(range(len(a)), key=lambda i: (-(a[i] / 5 - blocos[i]), i))
    if not 0 <= faltam <= len(a):
        raise ValueError("Arredondamento impossivel")
    for i in ordem[:faltam]:
        blocos[i] += 1
    verdes = (blocos * 5).tolist()
    if sum(verdes) != orcamento or not all(10 <= v <= 60 for v in verdes):
        raise ValueError("Verdes quantizados invalidos")
    return verdes


class Observador:
    """Contagens causais; nao le .rou.xml, getRoute nem getNextTLS."""
    def __init__(self, net_path, janela=120):
        raiz = ET.parse(net_path).getroot()
        self.roads = {e.get("id"): {"lanes": [dict(l.attrib) for l in e.findall("lane")]}
                      for e in raiz.findall("edge") if e.get("function") != "internal"}
        self.connections = [dict(c.attrib) for c in raiz.findall("connection")
                            if c.get("from") in self.roads and c.get("to") in self.roads]
        self.janela = janela
        self.anteriores = {}
        self.giros = defaultdict(Counter)
        self.destinos, self.partidas = Counter(), Counter()
        self.entradas, self.insercoes = deque(), deque()
        self.tempo_inicial = None
        self.ultimo_tempo = None
        self.arrivals_sem_posicao = 0

    def observar(self, conn, foto, agora):
        if self.ultimo_tempo == agora:
            return
        if self.tempo_inicial is None:
            self.tempo_inicial = agora
        self.ultimo_tempo = agora
        presentes = set(conn.vehicle.getIDList())
        atuais = {vid: conn.vehicle.getRoadID(vid) for vid in presentes}
        partidas = conn.simulation.getDepartedIDList()
        inseridos = Counter()
        entradas = Counter()
        for vid in partidas:
            edge = atuais.get(vid)
            if edge in self.roads:
                self.partidas[edge] += 1
                inseridos[edge] += 1
        for vid, edge in atuais.items():
            if edge not in self.roads:
                continue
            anterior = self.anteriores.get(vid)
            if anterior != edge:
                entradas[edge] += 1
                if anterior is not None:
                    self.giros[anterior][edge] += 1
            self.anteriores[vid] = edge  # guarda a ultima via fisica nos links internos
        for vid in conn.simulation.getArrivedIDList():
            edge = self.anteriores.get(vid)
            if edge is None:
                self.arrivals_sem_posicao += 1
            else:
                self.destinos[edge] += 1
        self.anteriores = {v: e for v, e in self.anteriores.items() if v in presentes}
        self.insercoes.append((agora, inseridos))
        self.entradas.append((agora, entradas))
        for fila in (self.insercoes, self.entradas):
            while fila and fila[0][0] <= agora - self.janela:
                fila.popleft()

    def taxas(self, agora):
        divisor = max(1, min(self.janela, agora - self.tempo_inicial))
        def somar(fila):
            total = Counter()
            for _, counts in fila:
                total.update(counts)
            return {e: total[e] / divisor for e in self.roads}
        return somar(self.insercoes), somar(self.entradas)

    def perfil(self):
        return {"giros": {e: dict(v) for e, v in self.giros.items()},
                "destinos": dict(self.destinos), "partidas": dict(self.partidas),
                "chegadas_sem_ultima_via": self.arrivals_sem_posicao,
                "fontes": "somente estados observados no SUMO; programa original, seed 1001",
                "nao_e_treino_de_rede": True}


def construir_rede(observador, manifesto, perfil):
    """149 vias reais + sumidouros MATEMATICOS para destinos internos observados.

    Nao altera rede/demanda SUMO. Todos os caminhos externos sao declarados por
    geometria, com pseudocontagem 0.1, sem selecionar giros pelo teste final.
    """
    roads = dict(observador.roads)
    by_tls = {s["id"]: s for s in manifesto["controladores"]}
    conns = [dict(c) for c in observador.connections]
    por_origem = defaultdict(list)
    for c in conns:
        por_origem[c["from"]].append(c)
    # Um destino dentro de uma via retira veiculos da rede, mesmo havendo conexoes.
    for edge, numero in sorted(perfil["destinos"].items()):
        if edge not in roads or not numero or not por_origem[edge]:
            continue
        sink = "__mpc_destino__" + edge
        roads[sink] = {"lanes": [{"length": "100000", "id": sink + "_0"}]}
        reais = por_origem[edge]
        tls = reais[0].get("tl")
        for lane in range(len(roads[edge]["lanes"])):
            c = {"from": edge, "to": sink, "fromLane": str(lane), "toLane": "0",
                 "destino_virtual": True}
            if tls:
                c["tl"] = tls
            conns.append(c)
    for c in conns:
        tls = c.get("tl")
        c["service_veh_per_second"] = 0.5
        if tls:
            c["served_native_phases"] = [p["indice_xml"] for p in by_tls[tls]["fases"]
                if c.get("destino_virtual") or p["state"][int(c["linkIndex"])] in "Gg"]
        else:
            c["served_native_phases"] = []
    targets = defaultdict(set)
    for c in conns:
        targets[c["from"]].add(c["to"])
    priors = {}
    for edge, outs in targets.items():
        weights = {o: 0.1 + (perfil["destinos"].get(edge, 0) if o.startswith("__mpc_destino__")
                    else perfil["giros"].get(edge, {}).get(o, 0)) for o in sorted(outs)}
        total = sum(weights.values())
        priors[edge] = {"shares": {o: w / total for o, w in weights.items()}}
    signals = {tls: {"green_native_indices": [p["indice_xml"] for p in s["fases"]]}
               for tls, s in by_tls.items()}
    network = {"roads": roads, "connections": conns, "signals": signals,
               "entry_edges": sorted(observador.roads),  # insercoes podem ocorrer em vias internas
               "exit_edges": sorted(set(roads) - set(targets)),
               "turn_priors": priors, "nonsignal_service_veh_per_lane_second": 0.5}
    plans = {tls: {"cycle_seconds": 120, "stage_count": s["n_acoes"],
                 "green_budget_seconds": 120 - 5 * s["n_acoes"],
                 "stages": [{"green_native_index": p["indice_xml"]} for p in s["fases"]]}
             for tls, s in by_tls.items()}
    # Ownership apenas particiona parametros do QP; nao cria sinais no SUMO.
    owner = {edge: next((c["tl"] for c in conns if c["from"] == edge and c.get("tl")),
                       sorted(signals)[0]) for edge in roads}
    service = {"signals": {tls: {"movement_capacity_groups": []} for tls in signals}}
    for tls, s in by_tls.items():
        pairs = {(c["from"], c["to"]) for c in conns if c.get("tl") == tls}
        for edge, target in sorted(pairs):
            links = [c for c in conns if c["from"] == edge and c["to"] == target]
            lanes = {c["fromLane"] for c in links}
            gamma = [len({c["fromLane"] for c in links if p["indice_xml"] in c["served_native_phases"]})
                     / len(lanes) for p in s["fases"]]
            service["signals"][tls]["movement_capacity_groups"].append({
                "incoming_edge": edge, "destination_edge": target,
                "declared_turn_share": priors[edge]["shares"][target],
                "saturation_rate_veh_per_second": 0.5 * len(lanes), "gamma": gamma})
    return network, plans, service, owner


class MPC(Observador):
    def __init__(self, net_path, manifesto, perfil, pasta):
        super().__init__(net_path)
        self.modelo, self.solver = carregar_modelo_externo()
        self.network, self.signals, self.service, self.owner = construir_rede(self, manifesto, perfil)
        self.pasta = Path(pasta)
        self.pasta.mkdir(parents=True, exist_ok=False)
        json_novo(self.pasta / "modelo_rede.json", {"network": self.network, "signals": self.signals,
                                                   "service": self.service, "owner": self.owner})
        self.verdes = {tls: quantizar_verdes([v["green_budget_seconds"] / v["stage_count"]] * v["stage_count"],
                                            v["green_budget_seconds"]) for tls, v in self.signals.items()}
        self.planos, self.tempos_solver = [], []
        self.proximo = 25200
        self.log = (self.pasta / "otimizacoes.jsonl").open("x", encoding="utf-8")

    def preparar(self, conn, foto, relogios, agora):
        if agora < self.proximo:
            return
        release, entradas = self.taxas(agora)
        snapshot = {"time_seconds": agora - 25200,
            "edge_vehicle_count": {e: conn.edge.getLastStepVehicleNumber(e) if e in self.roads else 0
                                   for e in self.network["roads"]},
            "boundary_backlog_vehicles": {e: 0 for e in self.roads},
            "boundary_release_rate_veh_per_second": release,
            "signals": {tls: {"previous_executed_green_seconds": values} for tls, values in self.verdes.items()}}
        tick = time.perf_counter()
        instance = self.modelo.build(self.network, self.signals, snapshot, entradas,
                                    self.service, self.owner)
        answer = self.solver.solve_matrices(instance["matrices"])
        wall = time.perf_counter() - tick
        record = {"tempo": agora, "indice_plano": len(self.planos), "snapshot": snapshot,
                  "taxa_entrada_observada": entradas, "metadata": instance["metadata"],
                  "solver": {k: v for k, v in answer.items() if k not in ("x", "y")},
                  "construcao_e_solver_s": wall, "verdes_anteriores": self.verdes}
        if not answer["valid"]:
            self.log.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
            self.log.flush()
            raise RuntimeError(f"QP MPC invalido em t={agora}; nenhum fallback silencioso: {answer['status']}")
        if set(instance["output_indices"]) != set(self.signals):
            raise AssertionError("QP nao produziu tempos para os oito sinais")
        continuous = {tls: answer["x"][ids].tolist() for tls, ids in instance["output_indices"].items()}
        self.verdes = {tls: quantizar_verdes(values, self.signals[tls]["green_budget_seconds"])
                       for tls, values in continuous.items()}
        record.update(verdes_continuos=continuous, verdes_quantizados=self.verdes,
                      custo_direto=self.modelo.direct_cost(instance, answer["x"]),
                      pendentes_insercao_sem_localizacao=len(conn.simulation.getPendingVehicles()))
        self.log.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
        self.log.flush()
        self.planos.append({"tempo": agora, "verdes": self.verdes})
        self.tempos_solver.append(wall)
        self.proximo += CONFIG["STEP"]

    def escolher(self, relogio, agora):
        alvo = self.verdes[relogio.id][relogio.fase]
        acao = (relogio.fase + 1) % len(relogio.verdes) if agora - relogio.inicio_verde >= alvo else relogio.fase
        return acao, [], False

    def detalhes(self, relogio):
        return {"indice_plano": len(self.planos) - 1, "verdes_alvo_s": self.verdes[relogio.id],
                "nota_q": "MPC nao calcula valores Q; q fica vazio"}

    def resumo(self):
        a = np.asarray(self.tempos_solver)
        return {"tipo": "MPC_central_store_and_forward_externo_adaptado",
                "otimizacoes": len(a), "falhas_solver": 0, "fallbacks": 0,
                "construcao_e_solver_s": {"media": float(a.mean()) if len(a) else None,
                    "p95": float(np.percentile(a, 95)) if len(a) else None,
                    "maximo": float(a.max()) if len(a) else None},
                "torch_importado": "torch" in sys.modules, "rede_treinada": False}

    def fechar(self):
        self.log.close()
