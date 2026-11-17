"""Confere e compara o piloto pareado; baselines novos usam as demandas reservadas."""
import argparse,hashlib,json,os,statistics,sys
from pathlib import Path

sys.dont_write_bytecode=True


def ler(p):return json.loads(Path(p).read_text(encoding='utf-8'))


def novo(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,allow_nan=False,indent=2)


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def detalhes(m):
    v=m['viagens']['demanda_janela']
    return {'fila_media':m['fila_media_rede'],'fila_maxima':m['fila_max_rede'],
            'atraso_insercao':v['atraso_insercao']['media'],'duracao_viagem':v['duracao_concluidos']['media'],
            'intervencoes':m['intervencoes'],'teleportes':m['teleportes'],
            'colisoes_por_1000_viagens':1000*m['colisoes']/m['demanda_prevista']}


def executar(root,baselines=True):
    root=Path(root).resolve();cfg=ler(root/'protocolo.json');ds=ler(root/'demandas/indice.json')
    assert ler(root/'CONCLUIDO.json')['episodios']==600
    for name,expected in cfg['fontes'].items():assert sha(root/'fontes_execucao'/name)==expected,name
    for split in ('treino','validacao','teste'):
        for r in ds[split]:assert sha(r['arquivo'])==r['sha256']
    sys.path.insert(0,str(root/'fontes_execucao'))
    os.environ['SMARTFLOW_PROJETO']=str(Path(__file__).resolve().parents[1])
    from ambiente_piloto_supervisor import rodar,metricas_viagens
    from treinar_piloto_supervisor import metrica
    m=ler(root/'manifesto.json');allrows=[];n_sim=0;n_dec=0;n_actor=0
    byarm={v:[] for v in cfg['variantes']};locais=[];episodios_truncados={}
    initial={}
    for seed in cfg['sementes']:
        for variant in cfg['variantes']:
            folder=root/f'{variant}_seed{seed}';res=ler(folder/'resumo.json');n=9 if variant=='com_supervisor' else 8
            assert res['n_atores']==n and len(res['gradientes'])==n and min(res['gradientes'])>0
            initial[variant,seed]=ler(folder/'inicializacao.json')['digest_locais']
            history=[json.loads(l) for l in (folder/'historico.jsonl').read_text().splitlines()]
            assert len(history)==100 and [r['episodio'] for r in history]==list(range(1,101))
            episodios_truncados[f'{variant}_seed{seed}']=sum(r['metricas']['nao_concluidas']>0 for r in history)
            for ep,row in enumerate(history,1):
                assert row['demanda_sha256']==ds['treino'][ep-1]['sha256']
            assert sha(res['checkpoint'])==res['sha256_checkpoint']
            score=[r['score'] for r in res['validacoes']]
            assert res['melhor_score']==min(score)
            origins=res.get('origens_episodios',{str(i):str(folder/'episodios'/f'ep{i:04d}') for i in range(1,101)})
            paths=[Path(origins[str(i)])/'metricas.json' for i in range(1,101)]
            for val in res['validacoes']:
                val_folder=Path(val.get('pasta',str(folder/'validacao'/f'ep{val["episodio"]:04d}')))
                paths.extend(sorted(val_folder.glob('cenario*/metricas.json')))
            paths.extend(sorted((folder/'teste_reservado').glob('cenario*/metricas.json')))
            for p in paths:
                mm=ler(p);n_sim+=1
                assert not mm['terminado_por_colisao'] and mm['teleportes']==0 and mm['fim_sumo']>=28800
                assert len(mm['recompensas'])==n
                assert mm['viagens']==metricas_viagens(p.parent/'tripinfo.xml.gz',28800)
                assert mm['colisoes']==len(mm['eventos_colisao'])
                n_dec+=sum(v for k,v in mm['decisoes'].items() if k.startswith('decisoes_'))
                n_actor+=sum(v for k,v in mm['decisoes'].items() if k.startswith('supervisor_'))
            for i,row in enumerate(res['teste'],1):
                mm=ler(folder/f'teste_reservado/cenario{i}/metricas.json')
                assert mm['demanda_prevista']==ds['teste'][i-1]['viagens']
                assert metrica(mm)==row
                record={'variante':variant,'seed':seed,'cenario':i,**row,**detalhes(mm)}
                allrows.append(record);byarm[variant].append(record)
                for tls,entries in mm['espera_por_entrada'].items():
                    for edge,stats in entries.items():locais.append({'variante':variant,'seed':seed,'cenario':i,'tls':tls,'edge':edge,**stats})
    for seed in cfg['sementes']:assert initial['com_supervisor',seed]==initial['sem_supervisor',seed]
    expected=6*(100+4*3+4)
    assert n_sim==expected,(n_sim,expected)
    if baselines:
        for mode in ('original_fixo','max_pressure'):
            for i,r in enumerate(ds['teste'],1):
                folder=root/'comparadores'/mode/f'cenario{i}'
                if (folder/'metricas.json').exists():
                    mm=ler(folder/'metricas.json')
                else:
                    mm=rodar(m,[],folder,9300+i,backend='libsumo',sumo_home=Path(cfg['sumo_home']),
                        modo=mode,rotas_cenario=r['arquivo'],recompensa_base_comum=True)
                assert mm['demanda_prevista']==r['viagens']
                allrows.append({'variante':mode,'seed':None,'cenario':i,**metrica(mm),**detalhes(mm)})
                for tls,entries in mm['espera_por_entrada'].items():
                    for edge,stats in entries.items():locais.append({'variante':mode,'seed':None,'cenario':i,'tls':tls,'edge':edge,**stats})
    keys=['espera','p95','colisoes','concluidas','nao_concluidas','fila_media','fila_maxima',
          'atraso_insercao','duracao_viagem','intervencoes','teleportes','colisoes_por_1000_viagens']
    means={v:{k:statistics.mean(r[k] for r in rows) for k in keys} for v,rows in byarm.items()}
    for mode in ('original_fixo','max_pressure'):
        rows=[r for r in allrows if r['variante']==mode]
        if rows:means[mode]={k:statistics.mean(r[k] for r in rows) for k in keys}
    pairs=[]
    for s in cfg['sementes']:
        grouped={v:[r for r in byarm[v] if r['seed']==s] for v in cfg['variantes']}
        means_s={v:{k:statistics.mean(r[k] for r in rows) for k in keys} for v,rows in grouped.items()}
        pairs.append({'seed':s,'medias':means_s,'delta_com_menos_sem':{k:means_s['com_supervisor'][k]-means_s['sem_supervisor'][k] for k in keys}})
    # Decisao de ampliar considera apenas validacao e exige sinal consistente nos 3 pares.
    val=[]
    for s in cfg['sementes']:
        items={v:ler(root/f'{v}_seed{s}/resumo.json') for v in cfg['variantes']}
        selected={v:next(r for r in data['validacoes'] if r['episodio']==data['melhor_ep']) for v,data in items.items()}
        scores={v:{k:statistics.mean(r[k] for r in row['metricas']) for k in ('espera','colisoes','nao_concluidas')} for v,row in selected.items()}
        good=(scores['com_supervisor']['espera']<=.95*scores['sem_supervisor']['espera']
              and scores['com_supervisor']['colisoes']<=scores['sem_supervisor']['colisoes']
              and scores['com_supervisor']['nao_concluidas']==0)
        val.append({'seed':s,'medias_validacao':scores,'sinal_consistente_para_ampliar':good})
    evidence={'status':'CONFERIDO','simulacoes_treino_validacao_teste':n_sim,'decisoes_locais':n_dec,
              'decisoes_supervisor':n_actor,'inicializacoes_pareadas_identicas':True,'tripinfo_recalculado':True}
    novo(root/'VERIFICADO.json',evidence)
    novo(root/'ANALISE.json',{'medias':means,'pares_por_inicializacao':pairs,'rodadas':allrows,'validacao':val,
        'esperas_locais_por_entrada':locais,'episodios_de_treino_com_viagens_pendentes':episodios_truncados,
        'ampliar_indicado_pelo_piloto':all(v['sinal_consistente_para_ampliar'] for v in val),
        'limites':'3 inicializacoes e 4 demandas reservadas; diagnostico, sem afirmacao de significancia ou generalizacao para outra cidade. Ambiente original continua com contatos.',
        'nao_comparar_diretamente_v2':'Demandas novas e recompensa local comum sem termo adicional do objetivo; nao e continuacao dos pesos antigos.'})
    print(json.dumps({'verificacao':evidence,'medias':means,'validacao':val},ensure_ascii=False),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pasta',type=Path)
    p.add_argument('--sem-baselines',action='store_true');a=p.parse_args();executar(a.pasta,not a.sem_baselines)
