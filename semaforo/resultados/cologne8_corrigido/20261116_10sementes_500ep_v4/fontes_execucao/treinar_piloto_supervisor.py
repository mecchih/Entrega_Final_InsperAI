"""Piloto pareado: 3 inicializacoes x 100 episodios, com/sem supervisor."""
import argparse
from datetime import datetime,timezone
import hashlib,json,os
from pathlib import Path
import shutil,statistics,subprocess,sys,time,uuid,zipfile

for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):os.environ[key]='1'
sys.dont_write_bytecode=True
PROJETO=Path(os.environ.get('SMARTFLOW_PROJETO',Path(__file__).resolve().parents[1])).resolve()


def novo(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,allow_nan=False,indent=2)


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def bibliotecas():
    import torch
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    from agente_marl_cologne import DoubleDQN
    from ambiente_piloto_supervisor import construir_manifesto,rodar
    return torch,DoubleDQN,construir_manifesto,rodar


def agentes(m,seed,variante,classe):
    local=[classe(s['entradas_com_supervisor'],s['n_acoes'],seed*100+i) for i,s in enumerate(m['controladores'])]
    if variante=='com_supervisor':local.append(classe(m['entradas_supervisor'],9,seed*100+99,supervisor=True))
    elif variante!='sem_supervisor':raise ValueError(variante)
    return local


def manifesto_v3(construir):
    m=construir('cologne8',continuar_apos_colisao=True)
    m['formato']='piloto_supervisao_cologne8_v3'
    m['recompensa']['local']='-(fila_local+excesso_local)/100 por segundo; mesma base nos dois bracos'
    m['demanda_base']=m.pop('demanda')
    m['demanda_episodio']='arquivo explicito do indice pareado, com quantidade verificada em cada episodio'
    m['controle_sem_supervisor']='8 atores; orientacao neutra constante desde inicializacao; sem rede supervisora'
    return m


def digest(xs):
    h=hashlib.sha256()
    for a in xs:
        for v in a.rede.state_dict().values():h.update(v.detach().numpy().tobytes())
    return h.hexdigest()


def score(rows):
    # Mesmo criterio nos dois bracos; teste final nunca seleciona checkpoint.
    return [sum(m['colisoes'] for m in rows),sum(m['viagens_nao_concluidas'] for m in rows),
        statistics.mean(m['viagens']['afetados_pelo_controle']['espera_todos_inclui_censura']['media'] for m in rows)]


def metrica(m):
    v=m['viagens']['demanda_janela']
    return {'espera':v['espera_todos_inclui_censura']['media'],'p95':v['espera_todos_inclui_censura']['p95'],
            'colisoes':m['colisoes'],'nao_concluidas':m['viagens_nao_concluidas'],'concluidas':v['concluidos']}


def executar_episodio(rodar,m,xs,pasta,route,seed,cfg,variante,treinando=False,detalhar=False):
    f=Path(route['arquivo'])
    if sha(f)!=route['sha256']:raise ValueError('Demanda pareada mudou')
    resultado=rodar(m,xs,pasta,seed,treinando=treinando,modo='hierarquico' if variante=='com_supervisor' else 'sem_supervisor',
        backend='libsumo',sumo_home=Path(cfg['sumo_home']),detalhar=detalhar,rotas_cenario=f,recompensa_base_comum=True)
    if resultado['terminado_por_colisao'] or resultado['fim_sumo']<28800:raise AssertionError('Termino indevido')
    if resultado['demanda_prevista']!=route['viagens']:raise AssertionError('Demanda real diverge')
    return resultado


def avaliar(rodar,m,xs,pasta,routes,seed_base,cfg,variante,detalhar=False):
    before=digest(xs)
    counters=[(a.decisoes,a.gradientes,a.memoria.n,a.rng.getstate(),json.dumps(a.np_rng.bit_generator.state,sort_keys=True)) for a in xs]
    out=[executar_episodio(rodar,m,xs,pasta/f'cenario{i}',r,seed_base+i,cfg,variante,detalhar=detalhar) for i,r in enumerate(routes,1)]
    assert digest(xs)==before
    assert counters==[(a.decisoes,a.gradientes,a.memoria.n,a.rng.getstate(),json.dumps(a.np_rng.bit_generator.state,sort_keys=True)) for a in xs]
    return out


def salvar(torch,p,xs,m,ep,seed,variante,completo=False,retomada=None):
    with Path(p).open('xb') as f:torch.save({'formato':'piloto_supervisao_cologne8_v3','manifesto':m,'episodio':ep,
        'semente':seed,'variante':variante,'completo':completo,'retomada':retomada,'agentes':[a.estado(completo) for a in xs]},f)


def retomar_estado(torch,path,xs,m,seed,variante):
    d=torch.load(path,map_location='cpu',weights_only=True)
    if (d.get('formato')!='piloto_supervisao_cologne8_v3' or not d.get('completo')
            or d['manifesto']!=m or d['semente']!=seed or d['variante']!=variante
            or len(d['agentes'])!=len(xs)):
        raise ValueError('Checkpoint de outro contrato ou sem estado completo')
    for a,payload in zip(xs,d['agentes'],strict=True):
        if (a.entradas,a.acoes)!=(payload['entradas'],payload['acoes']):raise ValueError('Arquitetura difere')
    for a,payload in zip(xs,d['agentes'],strict=True):a.carregar(payload,completo=True)
    return d


def worker(root,variante,seed,retomar=None):
    torch,cls,construir,rodar=bibliotecas()
    cfg=json.loads((root/'protocolo.json').read_text());datasets=json.loads((root/'demandas/indice.json').read_text())
    m=manifesto_v3(construir)
    assert m==json.loads((root/'manifesto.json').read_text())
    folder=root/f'{variante}_seed{seed}';folder.mkdir(exist_ok=False)
    xs=agentes(m,seed,variante,cls)
    novo(folder/'inicializacao.json',{'digest_locais':digest(xs[:8]),'n_atores':len(xs),
        'arquiteturas':[(a.entradas,64,64,a.acoes) for a in xs]})
    best=None;best_path=None;best_ep=None;validacoes=[];primeiro=1;anteriores=[];origens={}
    if retomar:
        d=retomar_estado(torch,retomar,xs,m,seed,variante);primeiro=d['episodio']+1;state=d['retomada']
        best=state['melhor'];best_ep=state['melhor_ep'];best_path=Path(state['melhor_path']) if state['melhor_path'] else None
        validacoes=state['validacoes']
        for v in validacoes:v.setdefault('pasta',str(Path(retomar).parent/'validacao'/f'ep{v["episodio"]:04d}'))
        anteriores=[json.loads(l) for l in (Path(retomar).parent/'historico.jsonl').read_text().splitlines()]
        anteriores=[r for r in anteriores if r['episodio']<primeiro]
        assert len(anteriores)==primeiro-1
        origens=state.get('origens_episodios',{str(i):str(Path(retomar).parent/'episodios'/f'ep{i:04d}') for i in range(1,primeiro)})
        for row in anteriores:assert row['demanda_sha256']==datasets['treino'][row['episodio']-1]['sha256']
        novo(folder/'retomada.json',{'checkpoint':str(retomar),'sha256':sha(retomar),'proximo_episodio':primeiro})
    with (folder/'historico.jsonl').open('x',encoding='utf-8') as hist:
        for row in anteriores:hist.write(json.dumps(row,allow_nan=False)+'\n')
        hist.flush()
        for ep,route in enumerate(datasets['treino'],1):
            if ep<primeiro:continue
            if shutil.disk_usage(root).free<8*1024**3:raise RuntimeError('Reserva de disco insuficiente; checkpoints anteriores preservados')
            r=executar_episodio(rodar,m,xs,folder/'episodios'/f'ep{ep:04d}',route,10000+ep,cfg,variante,True,ep in (1,cfg['episodios']))
            record={'episodio':ep,'semente':seed,'variante':variante,'metricas':metrica(r),
                'gradientes':[a.gradientes for a in xs],'epsilon':[a.epsilon for a in xs],
                'perda_media':[statistics.mean(a.perdas) if a.perdas else None for a in xs],
                'duracao_real_s':r['duracao_real_s'],'demanda_sha256':route['sha256']}
            hist.write(json.dumps(record,allow_nan=False)+'\n');hist.flush()
            origens[str(ep)]=str(folder/'episodios'/f'ep{ep:04d}')
            print(f'{variante} seed={seed} ep={ep}/{cfg["episodios"]} '+json.dumps(metrica(r)),flush=True)
            if ep%25==0 or ep==cfg['episodios']:
                vals=avaliar(rodar,m,xs,folder/'validacao'/f'ep{ep:04d}',datasets['validacao'],9200,cfg,variante)
                s=score(vals);improved=best is None or s<best
                if improved:
                    best=s;best_ep=ep;best_path=folder/f'politica_ep{ep:04d}.pt'
                    salvar(torch,best_path,xs,m,ep,seed,variante)
                validacoes.append({'episodio':ep,'score':s,'melhorou':improved,'metricas':[metrica(v) for v in vals],
                                   'pasta':str(folder/'validacao'/f'ep{ep:04d}')})
                novo(folder/'validacao'/f'ep{ep:04d}'/'resumo.json',validacoes[-1])
            if ep==1 or ep%5==0 or ep==cfg['episodios']:
                salvar(torch,folder/f'estado_ep{ep:04d}.pt',xs,m,ep,seed,variante,True,
                       {'melhor':best,'melhor_ep':best_ep,'melhor_path':str(best_path) if best_path else None,
                        'validacoes':validacoes,'origens_episodios':dict(origens)})
    assert all(a.gradientes>0 for a in xs),'Algum ator nao aprendeu'
    data=torch.load(best_path,map_location='cpu',weights_only=True)
    chosen=agentes(m,seed,variante,cls)
    for a,d in zip(chosen,data['agentes'],strict=True):a.carregar(d)
    tests=avaliar(rodar,m,chosen,folder/'teste_reservado',datasets['teste'],9300,cfg,variante,True)
    novo(folder/'resumo.json',{'variante':variante,'semente':seed,'episodios':cfg['episodios'],'n_atores':len(xs),
        'melhor_ep':best_ep,'melhor_score':best,'checkpoint':str(best_path),'sha256_checkpoint':sha(best_path),
        'validacoes':validacoes,'teste':[metrica(v) for v in tests],'gradientes':[a.gradientes for a in xs],
        'origens_episodios':origens})


def principal(args):
    from demandas_piloto_supervisor import preparar
    root=Path(args.saida).resolve();root.mkdir(parents=True,exist_ok=False)
    scripts=Path(__file__).resolve().parent
    frozen=root/'fontes_execucao';frozen.mkdir()
    sources=['treinar_piloto_supervisor.py','demandas_piloto_supervisor.py','ambiente_piloto_supervisor.py',
             'agente_marl_cologne.py','esquema_dqn_cologne3.py']
    for f in sources:shutil.copyfile(scripts/f,frozen/f)
    cfg={'episodios':args.episodios,'sementes':[0,1,2],'variantes':['com_supervisor','sem_supervisor'],
         'sumo_home':str(Path(args.sumo_home).resolve()),'max_processos':3,'inicio_utc':datetime.now(timezone.utc).isoformat(),
         'checkpoints_completos':'primeiro episodio, depois a cada 5; validacao permanece a cada 25',
         'fontes':{f:sha(frozen/f) for f in sources},'recompensa_local_comum':'-(fila_local+excesso_local)/100 por segundo; sem adicional prioritario',
         'colisao':-10000,'termina_por_colisao':False,'sem_supervisor':'oito redes; canais de orientacao constantes no one-hot neutro desde o treino',
         'comparacao':'mesma capacidade e inicializacao das oito redes locais; mesma sequencia de demandas/seed SUMO',
         'avaliacao':'validacao a cada 25; selecao colisao, censura, espera; teste reservado sem escolha de pesos',
         'ambiente':'SUMO/rede/vType originais. Contatos persistem tambem no programa original; comparacao de eficiencia condicional, nao de seguranca fisica.'}
    novo(root/'protocolo.json',cfg)
    from ambiente_piloto_supervisor import construir_manifesto
    novo(root/'manifesto.json',manifesto_v3(construir_manifesto))
    fonte=PROJETO/'referencias/cologne8_sumo_rl_1.4.5/sumo_rl/nets/RESCO/cologne8/cologne8.rou.xml'
    preparar(fonte,root/'demandas',args.episodios)
    if args.retomar_raiz:
        old=json.loads((args.retomar_raiz/'protocolo.json').read_text())
        for key in ('episodios','sementes','variantes','recompensa_local_comum','colisao','termina_por_colisao'):
            assert old[key]==cfg[key],key
        for key in ('agente_marl_cologne.py','ambiente_piloto_supervisor.py','esquema_dqn_cologne3.py','demandas_piloto_supervisor.py'):
            assert old['fontes'][key]==cfg['fontes'][key],key
    env=os.environ.copy();env.update(SMARTFLOW_PROJETO=str(PROJETO),PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1')
    # Os pares de inicializacao entram juntos, evitando confundir ordem e tratamento.
    queue=[(v,s) for s in (0,1,2) for v in cfg['variantes']];running=[];failed=[]
    while queue or running:
        while queue and len(running)<3 and not failed:
            v,s=queue.pop(0);log=(root/f'{v}_seed{s}.log').open('x',encoding='utf-8')
            cmd=[sys.executable,'-B','-X','utf8',str(frozen/Path(__file__).name),'--worker',v,'--seed',str(s),'--saida',str(root)]
            if args.retomar_raiz:
                candidates=sorted((args.retomar_raiz/f'{v}_seed{s}').glob('estado_ep*.pt'),reverse=True)
                latest=next((p for p in candidates if zipfile.is_zipfile(p)),None)
                if latest:cmd+=['--retomar-checkpoint',str(latest.resolve())]
            proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            running.append((proc,log,v,s));print('INICIADO',v,s,proc.pid,flush=True)
        for proc,log,v,s in list(running):
            code=proc.poll()
            if code is not None:
                log.close();running.remove((proc,log,v,s));print('FIM',v,s,code,flush=True)
                if code:failed.append({'variante':v,'seed':s,'exit_code':code})
        if failed and not running:break
        time.sleep(2)
    if failed:
        novo(root/'FALHA.json',{'falhas':failed,'fila_nao_iniciada':queue});raise RuntimeError(failed)
    rows=[json.loads((root/f'{v}_seed{s}/resumo.json').read_text()) for s in (0,1,2) for v in cfg['variantes']]
    for s in (0,1,2):
        inits=[json.loads((root/f'{v}_seed{s}/inicializacao.json').read_text()) for v in cfg['variantes']]
        assert inits[0]['digest_locais']==inits[1]['digest_locais']
    novo(root/'RESUMO.json',{'modelos':rows,'piloto':True,'nao_e_confirmacao_10_sementes':True})
    novo(root/'CONCLUIDO.json',{'utc':datetime.now(timezone.utc).isoformat(),'modelos':6,'episodios':args.episodios*6})
    print('CONCLUIDO',root,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--saida',type=Path,required=True);p.add_argument('--sumo-home',type=Path)
    p.add_argument('--episodios',type=int,default=100);p.add_argument('--worker',choices=('com_supervisor','sem_supervisor'))
    p.add_argument('--seed',type=int)
    p.add_argument('--retomar-checkpoint',type=Path);p.add_argument('--retomar-raiz',type=Path)
    a=p.parse_args()
    if a.worker:worker(a.saida,a.worker,a.seed,a.retomar_checkpoint)
    else:
        if not a.sumo_home or a.episodios<1:p.error('Forneca SUMO_HOME e episodios positivos')
        principal(a)
