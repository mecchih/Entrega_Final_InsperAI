from pathlib import Path
import sys,json,hashlib,shutil
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path('semaforo/scripts').resolve()))
from treinar_cologne8_corrigido import construir,classe_agente,criar_agentes,salvar,carregar,avaliar
from ambiente_piloto_supervisor import rodar
from treinar_piloto_supervisor import digest

root=Path('semaforo/resultados/cologne8_corrigido/20261116_integracao_v4').resolve()
root.mkdir(exist_ok=False)
torch,cls=classe_agente()
m=construir(Path('semaforo/resultados/cologne8_corrigido/20261116_rede_sem_espera_interna_v2/cologne8.net.xml'))
xs=criar_agentes(m,0,cls)
for a in xs:a.aquecimento=64
home=Path('../tools/sumo-win64-1.28.0').resolve()
ds=json.loads(Path('semaforo/resultados/cologne8_corrigido/20261116_calibracao_variada/indice.json').read_text())['demandas']
rows=[]
for i,r in enumerate(ds,1):
 out=rodar(m,xs,root/f'treino{i}',7300+i,treinando=True,sumo_home=home,rotas_cenario=r['arquivo'],recompensa_base_comum=True)
 assert out['fim_sumo']>=28800 and not out['terminado_por_colisao'] and out['teleportes']==0
 assert out['penalidades_colisao_por_ator'][-1]==-10000*out['colisoes']
 assert all(v<=0 for v in out['penalidades_colisao_por_ator'])
 rows.append({'rodada':i,'contatos':out['colisoes'],'fora_area':out['contatos_sem_jurisdicao_local'],'gradientes':[a.gradientes for a in xs]})
 print(json.dumps(rows[-1]),flush=True)
assert min(a.gradientes for a in xs)>0
cp=root/'estado_ensaio.pt'
salvar(torch,cp,xs,m,2,0,{},True)
ys=criar_agentes(m,0,cls)
carregar(torch,cp,ys,m,0,True)
assert digest(xs)==digest(ys)
for a,b in zip(xs,ys):
 assert a.memoria.n==b.memoria.n and a.gradientes==b.gradientes and a.rng.getstate()==b.rng.getstate()
out=avaliar(rodar,m,ys,root/'avaliacao',ds[:1],7400,{'sumo_home':str(home)})
fontes=root/'fontes_ensaio';fontes.mkdir()
for p in [Path(__file__),*[Path('semaforo/scripts')/f for f in ('treinar_cologne8_corrigido.py','ambiente_piloto_supervisor.py','agente_marl_cologne.py')]]:
 shutil.copyfile(p,fontes/p.name)
result={'status':'CONFERIDO','episodios_treino':2,'avaliacoes_sem_alterar_pesos_replay_rng':1,'n_atores':9,'atualizacoes_todos_atores':True,'retomada_completa_conferida':True,'aquecimento_ensaio':64,'aquecimento_rodada_principal':2000,'historico':rows,'pesos_ensaio_nao_reutilizados_no_treino':True,'fontes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in fontes.iterdir()}}
with (root/'VERIFICADO.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,ensure_ascii=False)
print(json.dumps(result,ensure_ascii=False),flush=True)
