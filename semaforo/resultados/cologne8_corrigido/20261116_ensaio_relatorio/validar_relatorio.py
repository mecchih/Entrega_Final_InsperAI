"""Ensaio de software: dados de calibracao reutilizados; nao e experimento cientifico."""
from pathlib import Path
import sys,os,json,subprocess,shutil
sys.dont_write_bytecode=True
base=Path('semaforo').resolve();os.environ['SMARTFLOW_PROJETO']=str(base)
sys.path.insert(0,str(base/'scripts'))
from treinar_cologne8_corrigido import classe_agente,criar_agentes,carregar,avaliar,novo,sha
from treinar_piloto_supervisor import metrica,score
from ambiente_piloto_supervisor import rodar
from relatar_cologne8_corrigido import executar

root=base/'resultados/cologne8_corrigido/20261116_ensaio_relatorio';root.mkdir(exist_ok=False)
qa=base/'resultados/cologne8_corrigido/20261116_integracao_v4'
cp=qa/'estado_ensaio.pt';torch,cls=classe_agente();m=torch.load(cp,weights_only=True)['manifesto']
routes=json.loads((base/'resultados/cologne8_corrigido/20261116_calibracao_variada/indice.json').read_text())['demandas']
cfg={'episodios':2,'sementes':[0],'fontes':{},'sumo_home':str(Path('../tools/sumo-win64-1.28.0').resolve())}
novo(root/'ENSAIO.json',{'uso':'Somente teste de software do relatorio, demandas de calibracao reutilizadas; nao selecionar rede ou publicar estes numeros como resultado reservado.'})
novo(root/'protocolo.json',cfg);novo(root/'manifesto.json',m)
(root/'demandas').mkdir();novo(root/'demandas/indice.json',{'treino':routes,'validacao':routes[:1],'teste':routes[:1]})
folder=root/'seed0';folder.mkdir()
xs=criar_agentes(m,0,cls);carregar(torch,cp,xs,m,0)
tests=avaliar(rodar,m,xs,folder/'teste_reservado',routes[:1],20100,cfg)
vm=json.loads((qa/'avaliacao/cenario1/metricas.json').read_text())
hist=[]
for i,route in enumerate(routes,1):
 d=json.loads((qa/f'treino{i}/metricas.json').read_text());hist.append({'episodio':i,'demanda_sha256':route['sha256'],'metricas':metrica(d)})
with (folder/'historico.jsonl').open('x',encoding='utf-8') as f:
 for r in hist:f.write(json.dumps(r)+'\n')
novo(folder/'resumo.json',{'gradientes':[a.gradientes for a in xs],'checkpoint':str(cp),'sha256_checkpoint':sha(cp),'melhor_ep':2,
     'validacoes':[{'episodio':2,'score':score([vm]),'metricas':[metrica(vm)],'pasta':str(qa/'avaliacao')}],
     'origens_episodios':{str(i):str(qa/f'treino{i}') for i in (1,2)},'teste':[metrica(x) for x in tests]})
novo(root/'CONCLUIDO.json',{'episodios':2})
executar(root)
subprocess.run([str(Path('.venv-marl-relatorio/Scripts/python.exe').resolve()),'-B','-X','utf8',str(base/'scripts/relatar_cologne8_corrigido.py'),str(root),'--grafico'],check=True)
shutil.copyfile(__file__,root/'validar_relatorio.py')
novo(root/'VERIFICADO.json',{'status':'CONFERIDO','relatorio_json':True,'grafico':True,'tripinfo_recalculado':True,'comparadores_novos':2,'nao_usar_como_teste_reservado':True})
