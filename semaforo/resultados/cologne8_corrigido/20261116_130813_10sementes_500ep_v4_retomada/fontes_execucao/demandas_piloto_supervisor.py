"""Demandas derivadas e pareadas; nao modifica fontes ou pesos existentes."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np

PERFIS={'uniforme':[1,1,1],'inicio':[1.6,.8,.6],'meio':[.7,1.6,.7],
        'fim':[.6,.8,1.6],'duplo':[1.3,.4,1.3]}


def gerar(fonte,saida,semente,fator,perfil):
    if perfil not in PERFIS or not .5 <= fator <= 1.5:
        raise ValueError('Perfil/fator invalido')
    tree=ET.parse(fonte);r=tree.getroot();trips=[v for v in r if v.tag=='trip']
    rng=np.random.default_rng(semente)
    origens=sorted({v.get('from') for v in trips})
    pesos=dict(zip(origens,rng.uniform(.7,1.3,len(origens))))
    prob=np.array([pesos[v.get('from')] for v in trips]);prob/=prob.sum()
    indices=rng.choice(len(trips),round(len(trips)*fator),replace=True,p=prob)
    cdf=np.r_[0,np.cumsum(np.array(PERFIS[perfil])/sum(PERFIS[perfil]))]
    root=ET.Element('routes')
    for v in r:
        if v.tag!='trip':root.append(ET.fromstring(ET.tostring(v)))
    rows=[]
    for i,k in enumerate(indices):
        original=trips[k]
        u=np.clip((float(original.get('depart'))-25200)/3600,0,1-1e-9)
        seg=min(int(np.searchsorted(cdf,u,side='right')-1),2)
        warped=(seg+(u-cdf[seg])/(cdf[seg+1]-cdf[seg]))/3
        t=float(np.clip(25200+3600*warped+rng.uniform(-30,30),25200,28799))
        attrs=dict(original.attrib);attrs.update(id=f'v{semente}_{i:05d}',depart=f'{t:.2f}')
        rows.append((t,attrs))
    for _,attrs in sorted(rows,key=lambda x:(x[0],x[1]['id'])):ET.SubElement(root,'trip',attrs)
    target=Path(saida)
    with target.open('xb') as f:ET.ElementTree(root).write(f,encoding='utf-8',xml_declaration=True)
    return {'arquivo':str(target.resolve()),'semente_geracao':semente,'fator':fator,'perfil':perfil,
            'viagens':len(rows),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'partidas_por_terco':dict(Counter(min(2,int((t-25200)//1200)) for t,_ in rows)),
            'modelo_veicular':'vType original intacto; so OD/horarios/amostragem variam'}


def preparar(fonte,pasta,episodios=100):
    pasta=Path(pasta);pasta.mkdir(parents=True,exist_ok=False)
    train=[]
    for ep in range(1,episodios+1):
        rng=np.random.default_rng(30000+ep)
        fator=float(rng.choice([.8,1.,1.2]));perfil=str(rng.choice(['uniforme','inicio','meio','fim']))
        train.append(gerar(fonte,pasta/f'treino_ep{ep:04d}.rou.xml',30000+ep,fator,perfil))
    val=[gerar(fonte,pasta/f'validacao_{i}.rou.xml',41000+i,fator,perfil)
         for i,(fator,perfil) in enumerate([(.9,'uniforme'),(1.1,'meio'),(1.,'inicio')],1)]
    test=[gerar(fonte,pasta/f'teste_{i}.rou.xml',61000+i,fator,perfil)
          for i,(fator,perfil) in enumerate([(.75,'uniforme'),(1.25,'meio'),(1.,'fim'),(1.1,'duplo')],1)]
    d={'treino':train,'validacao':val,'teste':test,'gerador':'reamostragem de pares OD existentes + variacao de origens e horarios',
       'teste_reservado_antes_treino':True,'base_sha256':hashlib.sha256(Path(fonte).read_bytes()).hexdigest()}
    with (pasta/'indice.json').open('x',encoding='utf-8') as f:json.dump(d,f,indent=2)
    return d
