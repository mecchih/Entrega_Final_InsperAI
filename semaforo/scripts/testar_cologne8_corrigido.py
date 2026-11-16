"""Verifica novo contrato, atribuicao de contatos e retomada normalizada."""
from pathlib import Path
import tempfile
import unittest
import numpy as np
import xml.etree.ElementTree as ET

from ambiente_piloto_supervisor import atribuir_penalidades_colisao
from treinar_cologne8_corrigido import construir, classe_agente, criar_agentes, salvar, carregar, score_validacao
from treinar_piloto_supervisor import digest

REDE = Path('semaforo/resultados/cologne8_corrigido/20261116_rede_sem_espera_interna_v2/cologne8.net.xml').resolve()


class Corrigido(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.torch, cls.agente = classe_agente()
        cls.manifesto = construir(REDE)

    def test_arquitetura_e_tempos_preservados(self):
        m = self.manifesto
        self.assertEqual([s['entradas_com_supervisor'] for s in m['controladores']], [26,24,22,26,22,18,22,26])
        self.assertEqual([s['n_acoes'] for s in m['controladores']], [4,2,3,4,3,2,3,4])
        self.assertEqual(m['entradas_supervisor'], 176)
        self.assertEqual(m['tempos'], {'decisao_local':5,'supervisor':30,'verde_minimo':10,'amarelo':3,'vermelho_geral_local':2,'verde_max_condicional':60})
        self.assertTrue(m['episodio']['continuar_apos_colisao'])

    def test_selecao_nao_premia_travar_demanda_para_evitar_contatos(self):
        def resultado(pendencias, contatos, espera, insercao):
            return {'viagens_nao_concluidas':pendencias,'colisoes':contatos,
                    'viagens':{'demanda_janela':{'espera_todos_inclui_censura':{'media':espera},
                                               'atraso_insercao':{'media':insercao}}}}
        self.assertLess(score_validacao([resultado(0,1,20,2)]), score_validacao([resultado(559,0,1,200)]))
        self.assertLess(score_validacao([resultado(0,0,25,2)]), score_validacao([resultado(0,1,20,2)]))
        self.assertLess(score_validacao([resultado(0,0,15,1)]), score_validacao([resultado(0,0,10,20)]))

    def test_punicao_na_area_e_global_sem_culpar_outros_locais(self):
        m = self.manifesto
        local = m['controladores'][0]['conexoes'][0]['via']
        eventos = [{'faixa_evento':local}, {'faixa_evento':':sem_area_0_0'}]
        p, fora = atribuir_penalidades_colisao(eventos, m)
        self.assertEqual(fora, 1)
        np.testing.assert_array_equal(p, [-10000,0,0,0,0,0,0,0,-20000])
        self.assertEqual(eventos[1]['agentes_locais_penalizados'], [])

    def test_fases_protegidas_sem_conflitos_xml(self):
        root = ET.parse(REDE).getroot()
        junctions = {j.get('id'):j for j in root.findall('junction')}
        edges = {e.get('id'):e for e in root.findall('edge')}
        n = 0
        for s in self.manifesto['controladores']:
            for phase in s['fases']:
                cs = [c for c in s['conexoes'] if phase['state'][int(c['linkIndex'])]=='G']
                for i, a in enumerate(cs):
                    ja = junctions[edges[a['from']].get('to')]; lanes = ja.get('intLanes').split()
                    ai = lanes.index(a['via'])
                    req = {int(x.get('index')):x for x in ja.findall('request')}
                    for b in cs[i+1:]:
                        if edges[b['from']].get('to') != ja.get('id'):
                            continue
                        bi = lanes.index(b['via']); n += 1
                        self.assertEqual(req[ai].get('foes')[::-1][bi], '0')
        self.assertGreater(n, 100)

    def test_normalizacao_e_retomada_reproduzem_atualizacao(self):
        a = self.agente(3,2,4,aquecimento=8,lote=8)
        for i in range(12):
            a.lembrar(np.full(3,i/10),i%2,-10000 if i==0 else -i,np.full(3,(i+1)/10),5,False,True)
        self.assertEqual(float(a.memoria.r[0]), -10)
        with tempfile.TemporaryDirectory(dir=Path('tmp')) as d:
            self.assertTrue(Path(d).resolve().is_relative_to(Path('tmp').resolve()))
            p = Path(d)/'estado.pt'
            # Carregador de rodada exige nove atores e contrato completo.
            xs = criar_agentes(self.manifesto, 0, self.agente)
            xs[0] = a
            salvar(self.torch,p,xs,self.manifesto,1,0,{},True)
            ys = criar_agentes(self.manifesto,0,self.agente)
            ys[0] = self.agente(3,2,4,aquecimento=8,lote=8)
            carregar(self.torch,p,ys,self.manifesto,0,True)
            b = ys[0]
            self.assertEqual(a.escolher(np.ones(3),True), b.escolher(np.ones(3),True))
            for x in (a,b):
                x.lembrar(np.ones(3),1,-10000,np.zeros(3),5,True,True)
            self.assertEqual(digest([a]), digest([b]))
            self.assertEqual(a.gradientes, b.gradientes)
            with self.assertRaises(ValueError):
                carregar(self.torch,p,ys,self.manifesto,1,True)


if __name__=='__main__':
    unittest.main(verbosity=2)
