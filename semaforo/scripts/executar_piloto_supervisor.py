"""Coordena treino, acompanhamento e verificacao em processo independente."""
import argparse,hashlib,json,os,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[2]


def novo(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2,ensure_ascii=False)


def main(args):
    os.chdir(BASE)
    root=args.saida.resolve()
    if root.exists():raise FileExistsError('A saida ja existe; preservar a rodada anterior')
    from monitorar_piloto_supervisor import estado
    cmd=[sys.executable,'-B','-X','utf8',str(Path(__file__).with_name('treinar_piloto_supervisor.py')),
         '--saida',str(root),'--episodios','100','--sumo-home',str(args.sumo_home.resolve())]
    if args.retomar_raiz:cmd+=['--retomar-raiz',str(args.retomar_raiz.resolve())]
    print('LANCADOR',os.getpid(),datetime.now(timezone.utc).isoformat(),flush=True)
    proc=subprocess.Popen(cmd,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    while proc.poll() is None:
        if (root/'protocolo.json').exists():
            s=estado(root)
            print(json.dumps({'utc':s['utc'],'progresso':s['episodios_concluidos'],'total':600,
                 'alertas':[w for w in s['trabalhadores'] if w['alertas']],
                 'disco_GiB':s['disco_livre_GiB']}),flush=True)
        time.sleep(45)
    if proc.returncode:raise RuntimeError(f'Coordenador falhou: {proc.returncode}')
    print('TREINO_CONCLUIDO; conferindo resultados',flush=True)
    with (root/'analise_execucao.log').open('x',encoding='utf-8') as f:
        subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__).with_name('relatar_piloto_supervisor.py')),str(root)],
                       stdout=f,stderr=subprocess.STDOUT,check=True)
    before=json.loads((BASE/'tmp/piloto_supervisor_cologne8/antes.json').read_text())
    for record in before['arquivos']:
        p=BASE/record['arquivo'];h=hashlib.sha256()
        with p.open('rb') as f:
            for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
        if h.hexdigest()!=record['sha256']:raise AssertionError(f'Arquivo protegido diverge: {p}')
    novo(root/'PRESERVACAO.json',{'status':'PRESERVADO','arquivos':before['arquivos']})
    novo(root/'TUDO_CONCLUIDO.json',{'utc':datetime.now(timezone.utc).isoformat(),
        'treino':True,'analise':True,'preservacao':True})
    print('TUDO_CONCLUIDO',json.dumps(json.loads((root/'ANALISE.json').read_text())['medias']),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--saida',required=True,type=Path);ap.add_argument('--sumo-home',required=True,type=Path)
    ap.add_argument('--retomar-raiz',type=Path)
    main(ap.parse_args())
