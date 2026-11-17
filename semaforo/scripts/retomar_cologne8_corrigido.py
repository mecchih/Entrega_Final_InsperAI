"""Retoma somente a semente pendente da v4, reutilizando resultados concluidos.

Nao modifica os sete fontes congelados nem os parametros do aprendizado.
Preparar com --origem RAIZ --saida NOVA_RAIZ --preparar-apenas; depois executar
a copia congelada com --saida NOVA_RAIZ --executar-preparado.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

sys.dont_write_bytecode = True


def ler(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def novo(p, data):
    with Path(p).open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def margem(root):
    if shutil.disk_usage(root).free < 11 * 2**30:
        raise RuntimeError('Exigidos 11 GiB livres para retomar; reserva durante o treino continua 8 GiB')


def copiar(src, dst, evidencias):
    src, dst = Path(src).resolve(), Path(dst)
    if not src.is_file() or src.is_symlink():
        raise ValueError(f'Origem irregular: {src}')
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open('rb') as inp, dst.open('xb') as out:
        shutil.copyfileobj(inp, out)
    digest = sha(src)
    if sha(dst) != digest:
        raise ValueError(f'Copia diferente: {src}')
    evidencias.append({'origem': str(src), 'copia': str(dst.resolve()), 'sha256': digest})


def preparar(origem, root):
    cfg = ler(origem/'protocolo.json')
    if cfg['formato'] != 'smartflow_cologne8_corrigido_v4' or cfg['sementes'] != list(range(10)) or cfg['episodios'] != 500:
        raise ValueError('Este orquestrador atende somente a rodada v4 10 x 500')
    completas = [s for s in cfg['sementes'] if (origem/f'seed{s}/resumo.json').exists()]
    if completas != list(range(9)):
        raise ValueError(f'Esperadas sementes 0-8 concluidas, encontradas: {completas}')
    diagnostico = ler(origem/'DIAGNOSTICO_PARADA_20261116_1509.json')
    cp = Path(diagnostico['checkpoint'])
    if (diagnostico['episodio_salvo'] != 201 or not diagnostico['checkpoint_completo']
            or not diagnostico['tensores_finitos'] or not zipfile.is_zipfile(cp)
            or sha(cp) != diagnostico['checkpoint_sha256']):
        raise ValueError('Checkpoint de emergencia nao corresponde ao diagnostico conferido')
    margem(root.parent)
    root.mkdir(exist_ok=False)
    copies = []
    projeto = Path(__file__).resolve().parents[1]
    for name, expected in cfg['fontes'].items():
        src = origem/'fontes_execucao'/name
        if sha(src) != expected:
            raise ValueError(f'Fonte congelado diferente: {name}')
        copiar(src, root/'fontes_execucao'/name, copies)
    for name in ('manifesto.json', 'PROTEGIDOS_ANTES.json', 'demandas/indice.json'):
        copiar(origem/name, root/name, copies)
    if sha(cfg['rede']) != cfg['rede_sha256'] or sha(cfg['auditoria']) != cfg['auditoria_sha256']:
        raise ValueError('Rede ou auditoria alterada')
    for seed in completas:
        folder = origem/f'seed{seed}'
        summary = ler(folder/'resumo.json')
        history = [json.loads(l) for l in (folder/'historico.jsonl').read_text(encoding='utf-8').splitlines()]
        if ([h['episodio'] for h in history] != list(range(1, 501)) or min(summary['gradientes']) <= 0
                or summary['episodios'] != 500 or sha(summary['checkpoint']) != summary['sha256_checkpoint']):
            raise ValueError(f'Resultado incompleto/inconsistente: seed{seed}')
        for name in ('historico.jsonl', 'resumo.json', 'inicializacao.json'):
            copiar(folder/name, root/f'seed{seed}'/name, copies)
        for i in range(1, 11):
            for name in ('metricas.json', 'tripinfo.xml.gz'):
                copiar(folder/f'teste_reservado/cenario{i}'/name,
                       root/f'seed{seed}/teste_reservado/cenario{i}'/name, copies)
    copiar(Path(__file__), root/'fontes_execucao'/Path(__file__).name, copies)
    cfg['inicio_utc'] = datetime.now(timezone.utc).isoformat()
    cfg['retomada_seletiva'] = {'origem': str(origem), 'sementes_reutilizadas': completas,
                               'semente_pendente': 9, 'proximo_episodio': 202,
                               'max_processos_retomada': 1, 'parametros_aprendizado_inalterados': True}
    novo(root/'protocolo.json', cfg)
    novo(root/'RETOMADA_SELETIVA.json', {
        'projeto': str(projeto), 'origem': str(origem), 'checkpoint': str(cp),
        'checkpoint_sha256': diagnostico['checkpoint_sha256'], 'episodio_salvo': 201,
        'sementes_reutilizadas': completas, 'copias_conferidas': copies,
        'orquestrador_sha256': sha(Path(__file__)),
        'limite': 'Resultados concluidos copiados sem reavaliar; origens de treino/validacao e politicas apontam para raizes preservadas.'})
    print(json.dumps({'status': 'PREPARADO', 'saida': str(root), 'reutilizadas': completas,
                      'episodios_concluidos': 4701, 'retomar_em': 202,
                      'copias_conferidas': len(copies), 'disco_GiB': shutil.disk_usage(root).free/2**30}), flush=True)


def executar(root):
    meta = ler(root/'RETOMADA_SELETIVA.json')
    cfg = ler(root/'protocolo.json')
    if sha(Path(__file__)) != meta['orquestrador_sha256']:
        raise ValueError('Execute a copia congelada e conferida do orquestrador')
    if (root/'seed9').exists() or (root/'EXECUCAO_INICIADA.json').exists():
        raise FileExistsError('Saida ja executada; preparar outra raiz para nova retomada')
    margem(root)
    for item in meta['copias_conferidas']:
        if sha(item['origem']) != item['sha256'] or sha(item['copia']) != item['sha256']:
            raise ValueError(f'Arquivo reutilizado mudou: {item["origem"]}')
    if sha(meta['checkpoint']) != meta['checkpoint_sha256']:
        raise ValueError('Checkpoint mudou')
    projeto = Path(meta['projeto'])
    frozen = root/'fontes_execucao'
    env = os.environ.copy()
    env.update(SMARTFLOW_PROJETO=str(projeto), PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
    os.environ.update(SMARTFLOW_PROJETO=str(projeto))
    sys.path.insert(0, str(frozen))
    from treinar_cologne8_corrigido import progresso
    novo(root/'EXECUCAO_INICIADA.json', {'utc': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid()})
    cmd = [sys.executable, '-B', '-X', 'utf8', str(frozen/'treinar_cologne8_corrigido.py'),
           '--worker', '9', '--saida', str(root), '--retomar-checkpoint', meta['checkpoint']]
    with (root/'seed9.log').open('x', encoding='utf-8') as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        print('INICIADO', 9, proc.pid, flush=True)
        heartbeat = 0
        while proc.poll() is None:
            if time.monotonic() - heartbeat >= 60:
                status = progresso(root, cfg)
                with (root/'monitoramento.jsonl').open('a', encoding='utf-8') as f:
                    f.write(json.dumps(status, allow_nan=False) + '\n')
                print(json.dumps({k: status[k] for k in ('utc', 'concluidos', 'total', 'disco_GiB')}), flush=True)
                heartbeat = time.monotonic()
            time.sleep(2)
    print('FIM', 9, proc.returncode, flush=True)
    if proc.returncode:
        novo(root/'FALHA.json', {'falhas': [{'semente': 9, 'exit_code': proc.returncode}], 'fila_nao_iniciada': []})
        return
    if (root/'seed9/PAUSADO.json').exists():
        novo(root/'PAUSADO.json', {'semente': 9})
        return
    if not all((root/f'seed{s}/resumo.json').exists() for s in cfg['sementes']):
        raise ValueError('Resumo final ausente')
    novo(root/'CONCLUIDO.json', {'utc': datetime.now(timezone.utc).isoformat(), 'episodios': 5000})
    with (root/'analise_execucao.log').open('x', encoding='utf-8') as log:
        subprocess.run([sys.executable, '-B', '-X', 'utf8', str(frozen/'relatar_cologne8_corrigido.py'), str(root)],
                       stdout=log, stderr=subprocess.STDOUT, env=env, check=True)
    plot_python = projeto.parent/'.venv-marl-relatorio/Scripts/python.exe'
    if plot_python.exists():
        with (root/'grafico_execucao.log').open('x', encoding='utf-8') as log:
            subprocess.run([str(plot_python), '-B', '-X', 'utf8', str(frozen/'relatar_cologne8_corrigido.py'),
                            str(root), '--grafico'], stdout=log, stderr=subprocess.STDOUT, env=env, check=True)
    protected = ler(root/'PROTEGIDOS_ANTES.json')['arquivos']
    for item in protected:
        if sha(item['arquivo']) != item['sha256']:
            raise ValueError(f'Arquivo protegido mudou: {item["arquivo"]}')
    for item in meta['copias_conferidas']:
        if sha(item['origem']) != item['sha256'] or sha(item['copia']) != item['sha256']:
            raise ValueError('Origem/copia reutilizada mudou durante a execucao')
    if sha(meta['checkpoint']) != meta['checkpoint_sha256']:
        raise ValueError('Checkpoint anterior mudou')
    novo(root/'PRESERVACAO.json', {'status': 'PRESERVADO', 'arquivos': len(protected),
                                  'copias_reutilizadas': len(meta['copias_conferidas']), 'checkpoint_anterior': True})
    novo(root/'TUDO_CONCLUIDO.json', {'utc': datetime.now(timezone.utc).isoformat(),
                                    'treino': True, 'analise': True, 'preservacao': True})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origem', type=Path)
    parser.add_argument('--saida', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--preparar-apenas', action='store_true')
    mode.add_argument('--executar-preparado', action='store_true')
    args = parser.parse_args()
    root = args.saida.resolve()
    if not args.executar_preparado:
        if args.origem is None:
            parser.error('Informe --origem para preparar uma saida nova')
        preparar(args.origem.resolve(), root)
    if not args.preparar_apenas:
        try:
            executar(root)
        except BaseException:
            import traceback
            if root.exists() and not (root/'FALHA_COORDENADOR.json').exists():
                novo(root/'FALHA_COORDENADOR.json', {'traceback': traceback.format_exc()})
            raise
