"""Confere o contrato da comparacao antes do piloto com novos pesos."""
import hashlib,tempfile,unittest
from pathlib import Path
import numpy as np
import torch
from ambiente_piloto_supervisor import construir_manifesto,estados
from demandas_piloto_supervisor import gerar,preparar
from treinar_piloto_supervisor import agentes,digest,retomar_estado,salvar
from agente_marl_cologne import DoubleDQN
import xml.etree.ElementTree as ET
from types import SimpleNamespace

BASE=Path(__file__).resolve().parents[1]/'referencias/cologne8_sumo_rl_1.4.5/sumo_rl/nets/RESCO/cologne8/cologne8.rou.xml'


class Piloto(unittest.TestCase):
    def test_retomada_reproduz_proxima_acao_e_atualizacao(self):
        a=DoubleDQN(3,2,4,aquecimento=8,lote=8)
        for i in range(12):a.lembrar(np.full(3,i/10),i%2,-i,np.full(3,(i+1)/10),5,False,True)
        m={'formato':'piloto_supervisao_cologne8_v3'}
        with tempfile.TemporaryDirectory(dir=Path('tmp')) as d:
            self.assertTrue(Path(d).resolve().is_relative_to((Path.cwd()/'tmp').resolve()))
            p=Path(d)/'estado.pt';salvar(torch,p,[a],m,5,4,'sem_supervisor',True,{})
            b=DoubleDQN(3,2,4,aquecimento=8,lote=8)
            retomar_estado(torch,p,[b],m,4,'sem_supervisor')
            self.assertEqual(a.escolher(np.ones(3),True),b.escolher(np.ones(3),True))
            for x in (a,b):x.lembrar(np.ones(3),1,-10000,np.zeros(3),5,True,True)
            self.assertEqual(digest([a]),digest([b]))
            self.assertEqual(a.gradientes,b.gradientes)
            with self.assertRaises(ValueError):retomar_estado(torch,p,[b],m,4,'com_supervisor')

    def test_oito_locais_com_pesos_iniciais_identicos(self):
        m=construir_manifesto('cologne8',continuar_apos_colisao=True)
        a=agentes(m,0,'com_supervisor',DoubleDQN);b=agentes(m,0,'sem_supervisor',DoubleDQN)
        self.assertEqual(len(a),9);self.assertEqual(len(b),8)
        self.assertEqual(digest(a[:8]),digest(b))
        self.assertEqual([x.entradas for x in b],[26,24,22,26,22,18,22,26])
        self.assertEqual(a[-1].entradas,176)
        for x in a+b:
            self.assertEqual(x.aquecimento,2000);self.assertEqual(x.memoria.n,0)

    def test_neutro_e_onehot_valido_desde_o_treino(self):
        m=construir_manifesto('cologne8',continuar_apos_colisao=True)
        foto={'locais':[{'filas':[0]*len(s['entradas']),'carros':[1]*len(s['entradas']),
                         'esperas':[2.]*len(s['entradas'])} for s in m['controladores']],
              'ocupacao':[[0.]*len(s['entradas']) for s in m['controladores']],'carros_rede':27,'fila_rede':0}
        clocks=[SimpleNamespace(estagio='verde',fase=0,inicio_verde=0) for _ in range(8)]
        vs,_=estados(m,foto,clocks,10,0)
        for v in vs:np.testing.assert_array_equal(v[-9:],[1,0,0,0,0,0,0,0,0])

    def test_demanda_reprodutivel_sem_alterar_fontes(self):
        before=hashlib.sha256(BASE.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(dir=Path('tmp')) as d:
            d=Path(d)
            a=gerar(BASE,d/'a.xml',331,.8,'meio');b=gerar(BASE,d/'b.xml',331,.8,'meio')
            self.assertEqual(a['sha256'],b['sha256']);self.assertEqual(a['viagens'],1637)
            r=ET.parse(d/'a.xml').getroot();ts=r.findall('trip')
            self.assertEqual(len({t.get('id') for t in ts}),len(ts))
            times=[float(t.get('depart')) for t in ts]
            self.assertEqual(times,sorted(times));self.assertTrue(all(25200<=x<28800 for x in times))
            self.assertEqual(r.find('vType').attrib,ET.parse(BASE).getroot().find('vType').attrib)
            self.assertEqual(hashlib.sha256(BASE.read_bytes()).hexdigest(),before)

    def test_separacao_demandas_de_validacao_e_teste(self):
        with tempfile.TemporaryDirectory(dir=Path('tmp')) as d:
            dataset=preparar(BASE,Path(d)/'demandas',3)
            sets=[{r['sha256'] for r in dataset[k]} for k in ('treino','validacao','teste')]
            self.assertFalse(sets[0]&sets[1]);self.assertFalse(sets[0]&sets[2]);self.assertFalse(sets[1]&sets[2])
            self.assertEqual(len(dataset['teste']),4)


if __name__=='__main__':
    torch.set_num_threads(1)
    unittest.main(verbosity=2)
