"""Falhas que o monitor precisa distinguir de aquecimento/arquivo em gravacao."""

import copy
import json
from pathlib import Path
import unittest
import uuid

from monitorar_marl_continuo import ArquivoIncremental, validar_registro, processo_vivo
import os


class Monitoramento(unittest.TestCase):
    def arquivo(self):
        pasta = Path(__file__).resolve().parents[2] / "tmp/testes_monitor_marl" / uuid.uuid4().hex
        pasta.mkdir(parents=True, exist_ok=False)
        return pasta / "dados.jsonl"

    def test_linha_parcial_nao_vira_erro_nem_e_contada_duas_vezes(self):
        p = self.arquivo()
        p.write_bytes(b'{"ep":1}\n{"ep":')
        a = ArquivoIncremental(p)
        self.assertEqual(a.novos(), [{"ep": 1}])
        self.assertEqual(a.novos(), [])
        with p.open("ab") as f:
            f.write(b'2}\n')
        self.assertEqual(a.novos(), [{"ep": 2}])
        self.assertEqual(a.novos(), [])

    def test_detecta_historico_truncado(self):
        p = self.arquivo()
        p.write_text('{"ep":1}\n', encoding="utf-8")
        a = ArquivoIncremental(p)
        a.novos()
        p.write_bytes(b'')
        with self.assertRaisesRegex(RuntimeError, "truncado"):
            a.novos()

    def test_distingue_aquecimento_de_falta_de_aprendizado(self):
        cfg = {"duracao": 3600, "aquecimento_supervisor": 2000, "aquecimento_local": 2000}
        x = {"epsilon": [.9]*9, "gradientes": [0]*9, "decisoes_treino": [100]*9,
             "perda_media_200": [None]*9, "metricas": {"terminado_por_colisao": False,
                 "fim_sumo": 29000, "colisoes": 3, "penalidade_colisao_por_agente": -30000,
                 "recompensas": [-30010]*9, "teleportes": 0}}
        self.assertEqual(validar_registro(x, cfg), [])
        x["decisoes_treino"][0] = 2100
        self.assertIn("ator_0_sem_gradientes_apos_aquecimento", validar_registro(x, cfg))
        x["gradientes"][0] = 101
        self.assertEqual(validar_registro(x, cfg), [])
        x["perda_media_200"][0] = float("nan")
        self.assertIn("valor_nao_finito", validar_registro(x, cfg))
        x["perda_media_200"][0] = .1
        x["metricas"]["terminado_por_colisao"] = True
        self.assertIn("episodio_fora_do_protocolo", validar_registro(x, cfg))

    def test_consulta_processo_vivo_sem_controla_lo(self):
        self.assertTrue(processo_vivo(os.getpid()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
