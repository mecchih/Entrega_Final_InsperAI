"""Testes da maquina de estados e do verificador, sem SUMO (TraCI falso).

uso: python -B semaforo/integracao_insper/testar_controle_seguro_insper.py
"""

from types import SimpleNamespace
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from controle_seguro_insper import (ControladorFasesSeguro, ErroSeguranca, SemaforosProtegidos,  # noqa: E402
                                    analisar_programa)
from insper_comum import VerificadorSeguranca  # noqa: E402

# Programas reais (osm.net.xml.gz) e conflitos do <request> das tres juncoes.
PROGRAMAS = {
    "40278183": [("GGGrrr", 42, 5, 50), ("yyyrrr", 3, 3, 3), ("rrrGGG", 42, 5, 50), ("rrryyy", 3, 3, 3)],
    "40278305": [("GGGrr", 42, 5, 50), ("yyyrr", 3, 3, 3), ("rrrGG", 42, 5, 50), ("rrryy", 3, 3, 3)],
    "476455095": [("GGGGrrrr", 42, 5, 50), ("yyyyrrrr", 3, 3, 3), ("rrrrGGGG", 42, 5, 50),
                  ("rrrryyyy", 3, 3, 3)],
}
FOES = {
    "40278183": {0: {3, 4}, 1: {3, 4, 5}, 2: {3, 4, 5}, 3: {0, 1, 2}, 4: {0, 1, 2}, 5: {1, 2}},
    "40278305": {0: {3}, 1: {3, 4}, 2: {3, 4}, 3: {0, 1, 2}, 4: {1, 2}},
    "476455095": {0: {4, 5}, 1: {4, 5, 6, 7}, 2: {4, 5, 6, 7}, 3: {4, 5, 6, 7},
                  4: {0, 1, 2, 3}, 5: {0, 1, 2, 3}, 6: {1, 2, 3}, 7: {1, 2, 3}},
}


class TLFalso:
    """Imita o necessario de traci.trafficlight para um semaforo."""

    def __init__(self, tls, fases, indice=0, gasto=0, proxima=None, agora=0):
        self.tls, self.fases = tls, fases
        self.programa, self.indice = "0", indice
        self.estado = fases[indice][0]
        self.gasto, self.proxima_troca = gasto, proxima if proxima is not None else agora + fases[indice][1]
        self.escritos = []

    def getProgram(self, tls):
        return self.programa

    def getAllProgramLogics(self, tls):
        fases = [SimpleNamespace(state=s, duration=d, minDur=a, maxDur=b) for s, d, a, b in self.fases]
        return [SimpleNamespace(programID="0", type=3, phases=fases)]

    def getRedYellowGreenState(self, tls):
        return self.estado

    def setRedYellowGreenState(self, tls, estado):
        self.programa, self.estado = "online", estado
        self.escritos.append(estado)

    def getSpentDuration(self, tls):
        return float(self.gasto)

    def getPhase(self, tls):
        return self.indice

    def getNextSwitch(self, tls):
        return float(self.proxima_troca)


def simular(ctl, tl, inicio, fim, politica):
    """Executa a ordem real do teste: atualizar, decidir, passo, conferir. Devolve os estados por segundo."""
    linha = []
    for agora in range(inicio, fim):
        ctl.atualizar(agora)
        politica(ctl, agora)
        linha.append(tl.estado)  # estado em vigor durante o passo agora -> agora+1
        ctl.conferir(agora + 1)
    return linha


class TestarPrograma(unittest.TestCase):
    def test_programas_reais_aceitos(self):
        for tls, fases in PROGRAMAS.items():
            plano = analisar_programa(fases, FOES[tls])
            self.assertEqual(plano["amarelo"], 3)
            self.assertEqual(plano["vermelho_geral_programa"], 0)
            self.assertEqual(len(plano["verdes"]), 2)

    def test_recusa_verde_seguido_de_verde(self):
        with self.assertRaises(ErroSeguranca):
            analisar_programa([("GGrr", 30, 5, 50), ("rrGG", 30, 5, 50)], {0: {2}, 2: {0}})

    def test_recusa_verdes_G_conflitantes(self):
        with self.assertRaises(ErroSeguranca):
            analisar_programa([("GGrr", 30, 5, 50), ("yyrr", 3, 3, 3), ("rrGG", 30, 5, 50),
                               ("rryy", 3, 3, 3)], {0: {1}, 1: {0}})

    def test_aceita_g_permissivo_conflitante(self):
        analisar_programa([("Ggrr", 30, 5, 50), ("yyrr", 3, 3, 3), ("rrGG", 30, 5, 50),
                           ("rryy", 3, 3, 3)], {0: {1}, 1: {0}})

    def test_recusa_amarelo_errado_e_cor_desconhecida(self):
        with self.assertRaises(ErroSeguranca):
            analisar_programa([("GGrr", 30, 5, 50), ("yrrr", 3, 3, 3), ("rrGG", 30, 5, 50),
                               ("rryy", 3, 3, 3)], {})
        with self.assertRaises(ErroSeguranca):
            analisar_programa([("GGrr", 30, 5, 50), ("uurr", 3, 3, 3), ("rrGG", 30, 5, 50),
                               ("rryy", 3, 3, 3)], {})

    def test_recusa_link_sempre_vermelho_e_amarelo_curto(self):
        with self.assertRaises(ErroSeguranca):
            analisar_programa([("GGrr", 30, 5, 50), ("yyrr", 3, 3, 3), ("rrGr", 30, 5, 50),
                               ("rryr", 3, 3, 3)], {})
        with self.assertRaises(ErroSeguranca):
            analisar_programa([("GGrr", 30, 5, 50), ("yyrr", 2, 2, 2), ("rrGG", 30, 5, 50),
                               ("rryy", 2, 2, 2)], {})


class TestarControlador(unittest.TestCase):
    def novo(self, tls="40278305", **kw):
        tl = TLFalso(tls, PROGRAMAS[tls], **{k: v for k, v in kw.items() if k in ("indice", "gasto", "proxima", "agora")})
        eventos = []
        ctl = ControladorFasesSeguro(tl, tls, kw.get("agora", 100), FOES[tls], eventos.append)
        return tl, ctl, eventos

    def test_verde_minimo_conta_tempo_ja_gasto(self):
        tl, ctl, _ = self.novo(gasto=4, agora=100)
        self.assertEqual(ctl.inicio_verde, 96)
        self.assertEqual(ctl.pedir(1, 105), "recusada_verde_minimo")
        self.assertEqual(ctl.pedir(1, 106), "troca_iniciada")

    def test_sequencia_exata_de_troca(self):
        tl, ctl, _ = self.novo(gasto=0, agora=100)

        def pede_sempre(c, agora):
            if c.pode_decidir(agora):
                c.pedir(1 - c.fase, agora)
        linha = simular(ctl, tl, 100, 140, pede_sempre)
        # 10 s verde, 3 s amarelo, 2 s vermelho geral, 10 s do outro verde ...
        esperado = (["GGGrr"] * 10 + ["yyyrr"] * 3 + ["rrrrr"] * 2 + ["rrrGG"] * 10 + ["rrryy"] * 3
                    + ["rrrrr"] * 2 + ["GGGrr"] * 10)
        self.assertEqual(linha, esperado[:40])

    def test_recusas_durante_transicao(self):
        tl, ctl, _ = self.novo(gasto=20, agora=100)
        self.assertEqual(ctl.pedir(1, 100), "troca_iniciada")
        for t in range(100, 105):
            ctl.atualizar(t)
            self.assertTrue(ctl.pedir(0, t).startswith("recusada"))
        ctl.atualizar(105)
        self.assertEqual(tl.estado, "rrrGG")
        self.assertEqual(ctl.pedir(0, 106), "recusada_verde_minimo")
        self.assertEqual(ctl.pedir(5, 115), "recusada_acao_invalida")

    def test_manter_respeita_intervalo(self):
        tl, ctl, _ = self.novo(gasto=30, agora=100)
        self.assertEqual(ctl.pedir(0, 100), "mantida")
        self.assertEqual(ctl.pedir(1, 103), "recusada_fora_do_intervalo")
        self.assertEqual(ctl.pedir(1, 105), "troca_iniciada")

    def test_verde_maximo_condicional(self):
        tl, ctl, _ = self.novo(gasto=0, agora=100)
        for t in range(100, 160):
            ctl.atualizar(t)
        self.assertEqual(ctl.proteger(0, 155, {3: 2}), (0, False))   # antes de 60 s
        self.assertEqual(ctl.proteger(0, 160, {}), (0, False))       # sem demanda no vermelho
        self.assertEqual(ctl.proteger(0, 160, {1: 4}), (0, False))   # demanda so no proprio verde
        self.assertEqual(ctl.proteger(0, 160, {4: 1}), (1, True))
        self.assertEqual(ctl.proteger(1, 160, {4: 1}), (1, False))   # troca ja pedida
        self.assertEqual(ctl.pedir(1, 160), "troca_iniciada")
        self.assertEqual(ctl.intervencoes, 1)

    def test_assumir_no_meio_do_amarelo(self):
        tl, ctl, eventos = self.novo(indice=1, gasto=1, proxima=102, agora=100)
        self.assertEqual(ctl.estagio, "amarelo")
        self.assertEqual(ctl.fase, 1)  # o programa abriria rrrGG depois de yyyrr
        linha = simular(ctl, tl, 100, 106, lambda c, t: None)
        self.assertEqual(linha, ["yyyrr"] * 2 + ["rrrrr"] * 2 + ["rrrGG"] * 2)

    def test_assumir_amarelo_ja_completo(self):
        # amarelo ja exibido por 3 s (getSpentDuration=3, troca prevista agora): nenhum segundo extra
        tl, ctl, _ = self.novo(indice=1, gasto=3, proxima=100, agora=100)
        linha = simular(ctl, tl, 100, 104, lambda c, t: None)
        self.assertEqual(linha, ["rrrrr"] * 2 + ["rrrGG"] * 2)

    def test_assumir_amarelo_do_fim_do_ciclo(self):
        tl, ctl, _ = self.novo(tls="476455095", indice=3, gasto=0, proxima=103, agora=100)
        self.assertEqual(ctl.fase, 0)
        self.assertEqual(ctl.limite, 103)

    def test_sumo_divergente_interrompe(self):
        tl, ctl, _ = self.novo(gasto=0, agora=100)
        tl.estado = "GGGGG"
        with self.assertRaises(ErroSeguranca):
            ctl.conferir(101)

    def test_protecao_de_escrita(self):
        tl = TLFalso("40278305", PROGRAMAS["40278305"])
        protegido = SemaforosProtegidos(tl, {"40278305"})
        protegido.setRedYellowGreenState("40278305", "GGGrr")
        with self.assertRaises(PermissionError):
            protegido.setRedYellowGreenState("outro", "GGGrr")
        with self.assertRaises(PermissionError):
            protegido.setPhase("outro", 0)
        self.assertEqual(protegido.escritas["40278305"], 1)


class TestarVerificador(unittest.TestCase):
    def rodar(self, linha, vermelho_geral=2, inicio=0):
        v = VerificadorSeguranca("x", FOES["40278305"], 3, vermelho_geral, 10, inicio)
        for t, s in enumerate(linha):
            v.observar(t, s)
        return v

    def test_sequencia_correta_sem_violacoes(self):
        linha = ["GGGrr"] * 12 + ["yyyrr"] * 3 + ["rrrrr"] * 2 + ["rrrGG"] * 10 + ["rrryy"] * 3 + ["rrrrr"] * 2 + ["GGGrr"] * 3
        v = self.rodar(linha)
        self.assertEqual(v.violacoes, [])
        self.assertEqual(v.amarelos, [3, 3])
        self.assertEqual(v.vermelhos_gerais, [2, 2])

    def test_programa_original_sem_vermelho_geral(self):
        linha = ["GGGrr"] * 12 + ["yyyrr"] * 3 + ["rrrGG"] * 10 + ["rrryy"] * 3 + ["GGGrr"] * 3
        self.assertEqual(self.rodar(linha, vermelho_geral=0).violacoes, [])
        tipos = {x["tipo"] for x in self.rodar(linha, vermelho_geral=2).violacoes}
        self.assertEqual(tipos, {"verde_sem_vermelho_geral_dos_conflitantes"})

    def test_detecta_saltos_inseguros(self):
        casos = {
            "verde_direto_para_vermelho": ["GGGrr"] * 12 + ["rrrGG"] * 3,
            "amarelo_com_duracao_errada": ["GGGrr"] * 12 + ["yyyrr"] * 2 + ["rrrrr"] * 2 + ["rrrGG"],
            "verde_menor_que_minimo": ["GGGrr"] * 12 + ["yyyrr"] * 3 + ["rrrrr"] * 2 + ["rrrGG"] * 4
                                      + ["rrryy"] * 3,
            "conflitantes_ativos_juntos": ["GGGrr"] * 12 + ["GGGGG"],
            "amarelo_direto_para_verde": ["GGGrr"] * 12 + ["yyyrr"] * 3 + ["GGGrr"],
        }
        for tipo, linha in casos.items():
            with self.subTest(tipo=tipo):
                self.assertIn(tipo, {x["tipo"] for x in self.rodar(linha).violacoes})


if __name__ == "__main__":
    unittest.main(verbosity=2)
