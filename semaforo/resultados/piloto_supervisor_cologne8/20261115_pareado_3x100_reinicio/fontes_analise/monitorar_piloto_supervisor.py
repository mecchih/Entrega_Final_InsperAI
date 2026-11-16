"""Le progresso do piloto sem alterar pesos, politicas ou simulacoes."""
import argparse,json,math,shutil,time
from datetime import datetime,timezone
from pathlib import Path


def estado(root):
    root=Path(root);cfg=json.loads((root/'protocolo.json').read_text())
    workers=[]
    for seed in cfg['sementes']:
        for variant in cfg['variantes']:
            folder=root/f'{variant}_seed{seed}';hist=folder/'historico.jsonl';last=None
            if hist.exists():
                for line in reversed(hist.read_text(encoding='utf-8').splitlines()):
                    try:last=json.loads(line);break
                    except json.JSONDecodeError:pass
            age=time.time()-hist.stat().st_mtime if hist.exists() else None
            warnings=[]
            if age is not None and age>600 and not (folder/'resumo.json').exists():warnings.append('sem episodio novo ha mais de 10min; verificar log/validacao')
            if last and last['episodio']>=25 and min(last['gradientes'])==0:warnings.append('ator sem gradientes apos episodio 25')
            if last and any(p is not None and not math.isfinite(p) for p in last['perda_media']):warnings.append('perda nao finita')
            workers.append({'variante':variant,'seed':seed,'episodio':last['episodio'] if last else 0,
                'concluido':(folder/'resumo.json').exists(),'metricas':last['metricas'] if last else None,
                'segundos_episodio':last['duracao_real_s'] if last else None,'alertas':warnings})
    return {'utc':datetime.now(timezone.utc).isoformat(),'episodios_concluidos':sum(w['episodio'] for w in workers),
            'episodios_previstos':cfg['episodios']*6,'concluido':(root/'CONCLUIDO.json').exists(),
            'falha':json.loads((root/'FALHA.json').read_text()) if (root/'FALHA.json').exists() else None,
            'disco_livre_GiB':round(shutil.disk_usage(root).free/2**30,2),'trabalhadores':workers}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pasta',type=Path)
    a=p.parse_args();print(json.dumps(estado(a.pasta),ensure_ascii=False,indent=2))
