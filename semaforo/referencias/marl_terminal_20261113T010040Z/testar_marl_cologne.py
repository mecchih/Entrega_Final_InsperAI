"""Verificacoes do protocolo que antecedem os treinos longos."""

import copy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

from agente_marl_cologne import DoubleDQN
from ambiente_marl_cologne import (RelogioLocal, construir_manifesto, estados,
                                   incremento_excesso)
from treinar_marl_cologne import assinatura_treino, digest_pesos, pontuacao


class Protocolo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.manifesto = construir_manifesto("cologne3")

    def test_cologne8_real_sem_completar_fases_artificiais(self):
        m = construir_manifesto("cologne8")
        self.assertEqual(len(m["controladores"]), 8)
        self.assertEqual([s["n_acoes"] for s in m["controladores"]], [4, 2, 3, 4, 3, 2, 3, 4])
        self.assertEqual([s["entradas_com_supervisor"] for s in m["controladores"]],
                         [26, 24, 22, 26, 22, 18, 22, 26])
        self.assertEqual(m["entradas_supervisor"], 176)
        self.assertEqual(len(m["acoes_supervisor"]), 9)
        self.assertEqual(m["demanda"]["total"], 2046)
        self.assertEqual(m["demanda"]["antes_controle"], 0)
        self.assertEqual(m["episodio"]["inicio_aquecimento"], 25200)
        self.assertEqual(m["recompensa"]["colisao"], -10000)

    def test_entradas_fases_e_orientacao(self):
        m = self.manifesto
        self.assertEqual([s["entradas_com_supervisor"] for s in m["controladores"]], [17, 21, 21])
        self.assertEqual([s["n_acoes"] for s in m["controladores"]], [3, 4, 4])
        foto = {"locais": [{"filas": [25] * len(s["entradas"]),
                "carros": [35] * len(s["entradas"]), "esperas": [500] * len(s["entradas"])}
                for s in m["controladores"]], "ocupacao": [[0.3] * len(s["entradas"])
                for s in m["controladores"]], "carros_rede": 350, "fila_rede": 250}
        relogios = [SimpleNamespace(estagio="verde", fase=0, inicio_verde=0) for _ in range(3)]
        locais, sup = estados(m, foto, relogios, 180, 2)
        self.assertEqual(len(sup), 73)
        for v, s in zip(locais, m["controladores"]):
            a, p = len(s["entradas"]), s["n_acoes"]
            np.testing.assert_equal(v[:2*a], 1)
            np.testing.assert_equal(v[-4:], [0, 0, 1, 0])
            self.assertEqual(sum(v[2*a:2*a+p]), 1)
            self.assertEqual(v[2*a+p], 2)
            np.testing.assert_equal(v[2*a+p+1:-4], 3)
        # Cada no tem seu proprio one-hot; uma transicao local nao apaga outros.
        relogios[0].estagio = "amarelo"
        locais2, _ = estados(m, foto, relogios, 180, 2)
        np.testing.assert_equal(locais2[0][6:9], 0)
        np.testing.assert_equal(locais2[1], locais[1])

    def test_excesso_nao_transfere_historico(self):
        self.assertEqual(incremento_excesso(200, None), 0)
        self.assertEqual(incremento_excesso(200, 199), 1)
        self.assertEqual(incremento_excesso(60, 59), 0)
        self.assertEqual(incremento_excesso(61, 60), 1)
        self.assertEqual(incremento_excesso(200, 50), 1)
        self.assertEqual(incremento_excesso(0, 200), 0)

    def test_selecao_nao_premia_colisao_precoce_com_media_baixa(self):
        def metrica(colisoes, nao_concluidas, espera):
            return {"colisoes": colisoes, "viagens_nao_concluidas": nao_concluidas,
                    "viagens": {"afetados_pelo_controle": {"espera_todos_inclui_censura": {"media": espera}}}}
        cedo = pontuacao([metrica(1, 2000, 1)])
        tarde = pontuacao([metrica(1, 500, 70)])
        sem_colisao = pontuacao([metrica(0, 1900, 500)])
        self.assertLess(tarde, cedo)
        self.assertLess(sem_colisao, tarde)

    def relogio(self, esquema):
        fases = [p["state"] for p in esquema["fases"]]
        atual = {esquema["id"]: fases[0]}
        tl = SimpleNamespace(getRedYellowGreenState=lambda tls: atual[tls],
            getSpentDuration=lambda tls: 10,
            setRedYellowGreenState=lambda tls, valor: atual.update({tls: valor}))
        conn = SimpleNamespace(trafficlight=tl, vehicle=SimpleNamespace(getNextTLS=lambda vid: []))
        eventos = []
        r = RelogioLocal(esquema, conn, 100, eventos.append)
        return r, conn, eventos

    def test_transicao_exata_3_amarelo_2_vermelho_e_minimo(self):
        r, conn, eventos = self.relogio(self.manifesto["controladores"][0])
        self.assertTrue(r.elegivel(100))
        r.aplicar_acao(1, 100)
        self.assertEqual(r.estagio, "amarelo")
        r.atualizar(102)
        self.assertEqual(r.estagio, "amarelo")
        r.atualizar(103)
        self.assertEqual(r.estagio, "vermelho")
        r.atualizar(104)
        self.assertEqual(r.estagio, "vermelho")
        r.atualizar(105)
        self.assertEqual(r.estagio, "verde")
        self.assertFalse(r.elegivel(114))
        self.assertTrue(r.elegivel(115))
        self.assertEqual([e["tempo"] for e in eventos], [100, 100, 103, 105])
        self.assertEqual(eventos[-1]["estado"], r.verdes[1])

    def test_protecao_usa_movimento_real_nao_indice_direcao(self):
        r, conn, eventos = self.relogio(self.manifesto["controladores"][0])
        link = next(i for i in range(r.n_links) if r.verdes[0][i] == "r"
                    and any(v[i] in "Gg" for v in r.verdes[1:]))
        conn.vehicle.getNextTLS = lambda vid: [(r.id, link, 20, "r")]
        acao, trocou = r.proteger(0, 160, ["veiculo"])
        self.assertTrue(trocou)
        self.assertIn(r.verdes[acao][link], "Gg")
        self.assertNotEqual(acao, 0)
        # Demanda apenas no verde corrente nao dispara a regra.
        link_verde = next(i for i, v in enumerate(r.verdes[0]) if v in "Gg")
        conn.vehicle.getNextTLS = lambda vid: [(r.id, link_verde, 20, "G")]
        self.assertEqual(r.proteger(0, 160, ["veiculo"]), (0, False))

    def test_gradiente_terminal_e_desconto_dt_real(self):
        for fim in (False, True):
            a = DoubleDQN(3, 2, 9, aquecimento=8, lote=8)
            with torch.no_grad():
                for net in (a.rede, a.alvo):
                    for p in net.parameters():
                        p.zero_()
                a.alvo[-1].bias.fill_(4)
            capturados = []
            original = torch.nn.functional.smooth_l1_loss
            def perda(atual, alvo):
                capturados.append(alvo.detach().numpy().copy())
                return original(atual, alvo)
            with patch("torch.nn.functional.smooth_l1_loss", side_effect=perda):
                for _ in range(8):
                    a.lembrar(np.zeros(3), 1, -2, np.zeros(3), 10, fim, True)
            self.assertEqual(a.gradientes, 1)
            esperado = -2 if fim else -2 + 0.95 ** 2 * 4
            np.testing.assert_allclose(capturados[0], esperado, rtol=1e-6)

    def test_avaliacao_nao_avanca_replay_exploracao_ou_pesos(self):
        a = DoubleDQN(3, 2, 7, aquecimento=8, lote=8)
        antes, pesos = assinatura_treino([a]), digest_pesos([a])
        for _ in range(20):
            acao, qs, explorou = a.escolher(np.zeros(3), False)
            self.assertFalse(explorou)
            self.assertEqual(acao, int(np.argmax(qs)))
            a.lembrar(np.zeros(3), acao, -2, np.zeros(3), 5, False, False)
        self.assertEqual(antes, assinatura_treino([a]))
        self.assertEqual(pesos, digest_pesos([a]))

    def test_retomada_reproduz_proxima_atualizacao_e_semente(self):
        a = DoubleDQN(3, 2, 7, aquecimento=8, lote=8)
        for i in range(8):
            a.lembrar(np.full(3, i/10), i % 2, -i, np.full(3, (i+1)/10), 5, i == 7, True)
        dados = copy.deepcopy(a.estado(completo=True))
        b = DoubleDQN(3, 2, 999)
        b.carregar(dados, completo=True)
        self.assertEqual(b.semente, 7)
        self.assertEqual(b.aquecimento, 8)
        self.assertEqual(b.lote, 8)
        self.assertEqual(a.escolher(np.ones(3), True), b.escolher(np.ones(3), True))
        for x in (a, b):
            x.lembrar(np.ones(3), 1, -10000, np.zeros(3), 10, True, True)
        self.assertEqual(assinatura_treino([a]), assinatura_treino([b]))
        self.assertEqual(digest_pesos([a]), digest_pesos([b]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
