"""Testes do comparador cientifico: causalidade, conservacao, QP e execucao."""

import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import numpy as np

from ambiente_comparacao_mpc import construir_manifesto
from comparar_mpc_cologne8 import checar_fontes
from controlador_mpc_cologne8 import (MPC, Observador, carregar_modelo_externo,
                                     construir_rede, quantizar_verdes)

NET = Path(__file__).resolve().parents[1] / "referencias/cologne8_sumo_rl_1.4.5/sumo_rl/nets/RESCO/cologne8/cologne8.net.xml"


class Comparador(unittest.TestCase):
    def test_integridade_fontes_licenca_e_motor_original(self):
        checar_fontes()
        self.assertNotIn("torch", sys.modules)

    def test_imports_externos_nao_contaminam_modulos(self):
        sentinel = object()
        previo = sys.modules.get("frozen", sentinel)
        carregar_modelo_externo()
        self.assertIs(sys.modules.get("frozen", sentinel), previo)

    def test_quantizacao_soma_limites_e_cadencia(self):
        for values, total in (([55, 55], 110), ([34, 35, 36], 105), ([10.2, 20.7, 28.9, 40.2], 100),
                              ([9.99999999, 60, 30.00000001], 100)):
            result = quantizar_verdes(values, total)
            self.assertEqual(sum(result), total)
            self.assertTrue(all(10 <= v <= 60 and v % 5 == 0 for v in result))
            self.assertLessEqual(max(abs(a - b) for a, b in zip(values, result)), 5)

    def test_quantizacao_rejeita_qp_invalido(self):
        for values, total in (([float("nan"), 55], 110), ([55, 54], 110), ([9, 61], 70), ([15, 15], 31)):
            with self.assertRaises(ValueError):
                quantizar_verdes(values, total)

    def test_observador_causal_preserva_ultimo_edge_nos_links_internos(self):
        obs = Observador(NET)
        # Escolhe uma conexao existente; nao supoe rumo, numero de fase ou nome de via.
        a, b = obs.connections[0]["from"], obs.connections[0]["to"]
        state = {"cars": {}, "departed": [], "arrived": []}
        conn = SimpleNamespace(vehicle=SimpleNamespace(getIDList=lambda: list(state["cars"]),
                        getRoadID=lambda v: state["cars"][v]),
            simulation=SimpleNamespace(getDepartedIDList=lambda: state["departed"],
                        getArrivedIDList=lambda: state["arrived"]))
        obs.observar(conn, {}, 0)
        state.update(cars={"v": a}, departed=["v"], arrived=[])
        obs.observar(conn, {}, 1)
        state.update(cars={"v": ":internal"}, departed=[], arrived=[])
        obs.observar(conn, {}, 2)
        state.update(cars={"v": b}, departed=[], arrived=[])
        obs.observar(conn, {}, 3)
        state.update(cars={}, departed=[], arrived=["v"])
        obs.observar(conn, {}, 4)
        self.assertEqual(obs.giros[a][b], 1)
        self.assertEqual(obs.destinos[b], 1)
        self.assertEqual(obs.partidas[a], 1)
        self.assertEqual(obs.arrivals_sem_posicao, 0)
        releases, arrivals = obs.taxas(4)
        self.assertEqual(releases[a], 0.25)
        self.assertEqual(arrivals[b], 0.25)
        self.assertNotIn("torch", sys.modules)

    def test_taxas_usam_somente_janela_passada(self):
        obs = Observador(NET, janela=120)
        edge = next(iter(obs.roads))
        obs.tempo_inicial = 0
        obs.insercoes.append((1, {edge: 10}))
        obs.insercoes.append((125, {edge: 2}))
        state = SimpleNamespace(vehicle=SimpleNamespace(getIDList=lambda: []),
            simulation=SimpleNamespace(getDepartedIDList=lambda: [], getArrivedIDList=lambda: []))
        obs.observar(state, {}, 126)
        self.assertAlmostEqual(obs.taxas(126)[0][edge], 2 / 120)

    def test_destinos_internos_sao_sumidouros_do_modelo_nao_novas_ruas_sumo(self):
        obs = Observador(NET)
        m = construir_manifesto("cologne8", continuar_apos_colisao=True)
        source = obs.connections[0]["from"]
        perfil = {"destinos": {source: 20}, "giros": {}, "partidas": {}}
        network, plans, service, owner = construir_rede(obs, m, perfil)
        sink = "__mpc_destino__" + source
        self.assertIn(sink, network["roads"])
        self.assertNotIn(sink, obs.roads)
        self.assertIn(sink, network["exit_edges"])
        for row in network["turn_priors"].values():
            self.assertAlmostEqual(sum(row["shares"].values()), 1)
        self.assertEqual(len(plans), 8)
        self.assertEqual([p["stage_count"] for p in plans.values()], [4, 2, 3, 4, 3, 2, 3, 4])
        self.assertEqual(set(owner), set(network["roads"]))

    def test_qp_rede_real_vazia_e_conservacao(self):
        obs = Observador(NET)
        m = construir_manifesto("cologne8", continuar_apos_colisao=True)
        net, plans, service, owner = construir_rede(obs, m, {"destinos": {}, "giros": {}})
        zeros = {e: 0 for e in net["roads"]}
        snap = {"time_seconds": 0, "edge_vehicle_count": zeros,
                "boundary_backlog_vehicles": zeros, "boundary_release_rate_veh_per_second": zeros,
                "signals": {t: {"previous_executed_green_seconds": [s["green_budget_seconds"] / s["stage_count"]] * s["stage_count"]}
                            for t, s in plans.items()}}
        model, solver = carregar_modelo_externo()
        instance = model.build(net, plans, snap, zeros, service, owner)
        self.assertEqual(instance["metadata"]["turns_without_green_service"], [])
        result = solver.solve_matrices(instance["matrices"])
        self.assertTrue(result["valid"], result["attempts"])
        self.assertLessEqual(result["eq_violation"], 1e-7)
        self.assertLessEqual(result["ineq_violation"], 1e-7)
        self.assertEqual(len(instance["output_indices"]), 8)
        for tls, ids in instance["output_indices"].items():
            self.assertEqual(sum(quantizar_verdes(result["x"][ids], plans[tls]["green_budget_seconds"])),
                             plans[tls]["green_budget_seconds"])

    def test_solver_externo_rejeita_problema_inviavel(self):
        from scipy import sparse
        _, solver = carregar_modelo_externo()
        result = solver.solve_matrices({"P": sparse.eye(1, format="csc"), "q": np.zeros(1),
            "A": sparse.csc_matrix([[1.], [1.]]), "l": np.array([2., -np.inf]), "u": np.array([np.inf, 1.])})
        self.assertFalse(result["valid"])

    def test_executor_ciclico_respeita_fases_reais_e_idade(self):
        fake = SimpleNamespace(verdes={"x": [10, 20, 30]})
        clock = SimpleNamespace(id="x", fase=1, verdes=["a", "b", "c"], inicio_verde=100)
        self.assertEqual(MPC.escolher(fake, clock, 115)[0], 1)
        self.assertEqual(MPC.escolher(fake, clock, 120)[0], 2)
        clock.fase = 2
        self.assertEqual(MPC.escolher(fake, clock, 130)[0], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
