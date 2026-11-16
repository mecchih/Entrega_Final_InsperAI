"""Treino novo Cologne8 derivado: 10 sementes, checkpoints e analise automatica."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET
import zipfile

for key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'):
    os.environ[key] = '1'
sys.dont_write_bytecode = True
PROJETO = Path(os.environ.get('SMARTFLOW_PROJETO', Path(__file__).resolve().parents[1])).resolve()
FORMATO = 'smartflow_cologne8_corrigido_v4'
ESCALA = 1000.0


def ler(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def novo(p, data):
    with Path(p).open('x', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, allow_nan=False)


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def classe_agente():
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    from agente_marl_cologne import DoubleDQN

    class Normalizada(DoubleDQN):
        def lembrar(self, s, a, r, s2, dt, fim, treinando):
            return super().lembrar(s, a, r / ESCALA, s2, dt, fim, treinando)

        def estado(self, completo=False):
            return {**super().estado(completo), 'escala_recompensa_aprendizado': ESCALA}

        def carregar(self, data, completo=False):
            if data.get('escala_recompensa_aprendizado') != ESCALA:
                raise ValueError('Checkpoint de outra escala de recompensa')
            super().carregar(data, completo)

    return torch, Normalizada


def construir(rede):
    from ambiente_piloto_supervisor import construir_manifesto
    m = construir_manifesto('cologne8', continuar_apos_colisao=True, rede_cenario=rede)
    m['formato'] = FORMATO
    m['recompensa']['local'] = '-(fila_local+incremento_excesso_local)/100 por segundo; sem custo prioritario adicional'
    m['recompensa']['atribuicao_por_area'] = True
    m['recompensa']['atribuicao_colisao'] = '-10000 ao supervisor por evento e a cada local cuja area registrada participa; fora de area local so supervisor; nao presume culpa causal'
    m['recompensa']['escala_aprendizado'] = ESCALA
    m['recompensa']['nota_escala'] = 'Divisao uniforme de TODA recompensa por 1000 antes do replay; preserva proporcao e objetivo, nao corrige dominancia relativa por si.'
    m['selecao'] = 'Menor total de viagens nao concluidas na validacao; depois contatos; depois espera media mais atraso de insercao. Teste reservado nao seleciona pesos.'
    m['demanda_base'] = m.pop('demanda')
    m['demanda_episodio'] = 'Arquivo explicito e verificado por hash; novas demandas de treino, validacao e teste'
    root = ET.parse(rede).getroot()
    internos = defaultdict(list)
    for c in root.findall('connection'):
        if c.get('from').startswith(':') and c.get('via'):
            internos[c.get('from') + '_' + c.get('fromLane')].append(c.get('via'))
    areas = defaultdict(set)
    for i, s in enumerate(m['controladores']):
        for entrada in s['entradas']:
            for lane in entrada['faixas']:
                areas[lane['id']].add(i)
        fila = [c['via'] for c in s['conexoes']]
        vistos = set()
        while fila:
            lane = fila.pop()
            if lane in vistos:
                continue
            vistos.add(lane); areas[lane].add(i); fila.extend(internos[lane])
    m['jurisdicao_faixas'] = {lane: sorted(ids) for lane, ids in sorted(areas.items())}
    return m


def preparar_demandas(fonte, pasta, episodios):
    from demandas_piloto_supervisor import gerar
    import numpy as np
    pasta.mkdir(exist_ok=False)
    train = []
    for ep in range(1, episodios + 1):
        rng = np.random.default_rng(100000 + ep)
        train.append(gerar(fonte, pasta/f'treino_ep{ep:04d}.rou.xml', 100000 + ep,
                          float(rng.choice([.8, 1., 1.2])), str(rng.choice(['uniforme', 'inicio', 'meio', 'fim']))))
    val = [gerar(fonte, pasta/f'validacao_{i}.rou.xml', 150000 + i, f, p) for i, (f, p) in
           enumerate([(.9, 'uniforme'), (1.1, 'meio'), (1., 'inicio'), (1.2, 'fim'), (.8, 'duplo')], 1)]
    test = [gerar(fonte, pasta/f'teste_{i}.rou.xml', 170000 + i, f, p) for i, (f, p) in
            enumerate([(.75, 'uniforme'), (1.25, 'meio'), (1., 'fim'), (1.1, 'duplo'), (.9, 'inicio'),
                       (1.2, 'uniforme'), (.8, 'fim'), (1., 'duplo'), (1.1, 'inicio'), (.9, 'meio')], 1)]
    novo(pasta/'indice.json', {'treino': train, 'validacao': val, 'teste': test,
                             'origem_sha256': sha(fonte), 'teste_reservado_antes_treino': True,
                             'limite': 'OD reamostrados do Cologne8; nao e generalizacao a outra cidade'})


def criar_agentes(m, seed, cls):
    return [cls(s['entradas_com_supervisor'], s['n_acoes'], seed*100 + i) for i, s in enumerate(m['controladores'])] + [cls(m['entradas_supervisor'], 9, seed*100 + 99, supervisor=True)]


def score_validacao(rows):
    viagens = [r['viagens']['demanda_janela'] for r in rows]
    return [sum(r['viagens_nao_concluidas'] for r in rows), sum(r['colisoes'] for r in rows),
            statistics.mean(v['espera_todos_inclui_censura']['media'] + v['atraso_insercao']['media'] for v in viagens)]


def salvar(torch, p, xs, m, ep, seed, state, completo=False):
    with p.open('xb') as f:
        torch.save({'formato': FORMATO, 'manifesto': m, 'episodio': ep, 'semente': seed,
                    'completo': completo, 'retomada': state, 'agentes': [a.estado(completo) for a in xs]}, f)


def carregar(torch, p, xs, m, seed, completo=False):
    d = torch.load(p, map_location='cpu', weights_only=True)
    if d['formato'] != FORMATO or d['manifesto'] != m or d['semente'] != seed or len(d['agentes']) != 9 or (completo and not d['completo']):
        raise ValueError('Checkpoint de outro contrato')
    for a, b in zip(xs, d['agentes'], strict=True):
        a.carregar(b, completo)
    return d


def episodio(rodar, m, xs, pasta, route, seed, cfg, treino=False, detalhes=False):
    if sha(route['arquivo']) != route['sha256']:
        raise ValueError('Demanda mudou')
    out = rodar(m, xs, pasta, seed, treinando=treino, modo='hierarquico',
                sumo_home=Path(cfg['sumo_home']), rotas_cenario=route['arquivo'],
                recompensa_base_comum=True, detalhar=detalhes)
    assert not out['terminado_por_colisao'] and out['fim_sumo'] >= 28800
    assert out['demanda_prevista'] == route['viagens'] and len(out['recompensas']) == 9
    return out


def avaliar(rodar, m, xs, folder, routes, base_seed, cfg):
    from treinar_piloto_supervisor import digest
    before = digest(xs)
    counters = [(a.decisoes, a.gradientes, a.memoria.n, a.rng.getstate(), json.dumps(a.np_rng.bit_generator.state)) for a in xs]
    rows = [episodio(rodar, m, xs, folder/f'cenario{i}', r, base_seed+i, cfg) for i, r in enumerate(routes, 1)]
    assert before == digest(xs)
    assert counters == [(a.decisoes, a.gradientes, a.memoria.n, a.rng.getstate(), json.dumps(a.np_rng.bit_generator.state)) for a in xs]
    return rows


def worker(root, seed, retomar=None):
    torch, cls = classe_agente()
    from ambiente_piloto_supervisor import rodar
    from treinar_piloto_supervisor import digest, metrica
    cfg, m, ds = ler(root/'protocolo.json'), ler(root/'manifesto.json'), ler(root/'demandas/indice.json')
    for f, h in cfg['fontes'].items():
        assert sha(root/'fontes_execucao'/f) == h
    for f, h in m['fontes'].items():
        assert sha(PROJETO/f) == h
    folder = root/f'seed{seed}'; folder.mkdir(exist_ok=False)
    xs = criar_agentes(m, seed, cls)
    novo(folder/'inicializacao.json', {'digest_locais': digest(xs[:8]), 'digest_todos': digest(xs),
         'arquiteturas': [[a.entradas, 64, 64, a.acoes] for a in xs], 'aquecimento': [a.aquecimento for a in xs]})
    state = {'melhor': None, 'melhor_ep': None, 'melhor_path': None, 'validacoes': [], 'origens_episodios': {}}
    primeiro = 1; anteriores = []
    if retomar:
        d = carregar(torch, retomar, xs, m, seed, True); state = d['retomada']; primeiro = d['episodio'] + 1
        anteriores = [json.loads(l) for l in (retomar.parent/'historico.jsonl').read_text().splitlines()]
        anteriores = [r for r in anteriores if r['episodio'] < primeiro]
        assert len(anteriores) == primeiro - 1
        novo(folder/'retomada.json', {'checkpoint': str(retomar), 'sha256': sha(retomar), 'proximo_episodio': primeiro})
    with (folder/'historico.jsonl').open('x', encoding='utf-8') as hist:
        for row in anteriores:
            hist.write(json.dumps(row) + '\n')
        hist.flush()
        for ep in range(primeiro, cfg['episodios'] + 1):
            if shutil.disk_usage(root).free < 8*2**30:
                if ep > primeiro:
                    cp = folder/f'estado_ep{ep-1:04d}.pt'
                    if not cp.exists():
                        salvar(torch, cp, xs, m, ep-1, seed, state, True)
                raise RuntimeError('Disco abaixo de 8 GiB: estado preservado; nao iniciar outro episodio')
            route = ds['treino'][ep-1]
            out = episodio(rodar, m, xs, folder/'episodios'/f'ep{ep:04d}', route, 11000+ep, cfg, True, ep in (1, cfg['episodios']))
            state['origens_episodios'][str(ep)] = str(folder/'episodios'/f'ep{ep:04d}')
            row = {'episodio': ep, 'semente': seed, 'metricas': metrica(out), 'gradientes': [a.gradientes for a in xs],
                   'epsilon': [a.epsilon for a in xs], 'perda_media': [statistics.mean(a.perdas) if a.perdas else None for a in xs],
                   'duracao_real_s': out['duracao_real_s'], 'demanda_sha256': route['sha256'],
                   'contatos_sem_jurisdicao_local': out['contatos_sem_jurisdicao_local'],
                   'penalidades_colisao_por_ator': out['penalidades_colisao_por_ator']}
            hist.write(json.dumps(row, allow_nan=False) + '\n'); hist.flush()
            print(json.dumps(row, ensure_ascii=False), flush=True)
            if ep % 25 == 0 or ep == cfg['episodios']:
                path = folder/'validacao'/f'ep{ep:04d}'
                vals = avaliar(rodar, m, xs, path, ds['validacao'], 19000, cfg)
                s = score_validacao(vals)
                if state['melhor'] is None or s < state['melhor']:
                    p = folder/f'politica_ep{ep:04d}.pt'
                    state.update(melhor=s, melhor_ep=ep, melhor_path=str(p))
                    salvar(torch, p, xs, m, ep, seed, None)
                record = {'episodio': ep, 'score': s, 'metricas': [metrica(v) for v in vals], 'pasta': str(path)}
                state['validacoes'].append(record); novo(path/'resumo.json', record)
            if ep in (1, 10, 25, 50) or ep % 100 == 0 or ep == cfg['episodios'] or (root/'PAUSAR_APOS_EPISODIO').exists():
                salvar(torch, folder/f'estado_ep{ep:04d}.pt', xs, m, ep, seed, state, True)
            if (root/'PAUSAR_APOS_EPISODIO').exists():
                novo(folder/'PAUSADO.json', {'episodio': ep}); return
    assert min(a.gradientes for a in xs) > 0
    escolhidos = criar_agentes(m, seed, cls)
    carregar(torch, Path(state['melhor_path']), escolhidos, m, seed)
    tests = avaliar(rodar, m, escolhidos, folder/'teste_reservado', ds['teste'], 20100, cfg)
    novo(folder/'resumo.json', {'semente': seed, 'episodios': cfg['episodios'], 'melhor_ep': state['melhor_ep'],
         'checkpoint': state['melhor_path'], 'sha256_checkpoint': sha(state['melhor_path']),
         'gradientes': [a.gradientes for a in xs], 'validacoes': state['validacoes'],
         'teste': [metrica(v) for v in tests], 'origens_episodios': state['origens_episodios']})


def progresso(root, cfg):
    rows = []
    for seed in cfg['sementes']:
        p = root/f'seed{seed}/historico.jsonl'; last = None
        if p.exists():
            for line in reversed(p.read_text(encoding='utf-8').splitlines()):
                try:
                    last = json.loads(line); break
                except json.JSONDecodeError:
                    pass
        age = time.time()-p.stat().st_mtime if p.exists() else None
        alerts = []
        if age is not None and age > 600 and not (root/f'seed{seed}/resumo.json').exists():
            alerts.append('Sem episodio novo ha mais de 10 minutos; verificar validacao/log')
        if last and last['episodio'] >= 25 and min(last['gradientes']) == 0:
            alerts.append('Ator sem gradientes apos episodio 25')
        rows.append({'semente': seed, 'episodio': last['episodio'] if last else 0,
                     'concluido': (root/f'seed{seed}/resumo.json').exists(), 'ultimo': last,
                     'idade_s': age, 'alertas': alerts})
    return {'utc': datetime.now(timezone.utc).isoformat(), 'total': len(rows)*cfg['episodios'],
            'concluidos': sum(r['episodio'] for r in rows), 'disco_GiB': shutil.disk_usage(root).free/2**30,
            'treinos_e_testes_finalizados': (root/'CONCLUIDO.json').exists(),
            'tudo_concluido': (root/'TUDO_CONCLUIDO.json').exists(),
            'falha': next((ler(root/n) for n in ('FALHA.json','FALHA_PARCIAL.json','FALHA_COORDENADOR.json') if (root/n).exists()), None),
            'trabalhadores': rows}


def principal(args):
    audit = ler(args.auditoria)
    if audit['status'] != 'APTO_TREINO_COM_LIMITACOES' or sha(args.rede) != audit['rede_sha256']:
        raise ValueError('Auditoria ausente ou de outra rede')
    root = args.saida.resolve(); root.mkdir(parents=True, exist_ok=False)
    frozen = root/'fontes_execucao'; frozen.mkdir()
    sources = ['treinar_cologne8_corrigido.py', 'relatar_cologne8_corrigido.py', 'treinar_piloto_supervisor.py',
               'ambiente_piloto_supervisor.py', 'agente_marl_cologne.py', 'esquema_dqn_cologne3.py', 'demandas_piloto_supervisor.py']
    for name in sources:
        shutil.copyfile(Path(__file__).with_name(name), frozen/name)
    rede = args.rede.resolve()
    cfg = {'formato': FORMATO, 'episodios': args.episodios, 'sementes': args.sementes, 'max_processos': 3,
           'sumo_home': str(args.sumo_home.resolve()), 'rede': str(rede), 'rede_sha256': sha(rede),
           'auditoria': str(args.auditoria.resolve()), 'auditoria_sha256': sha(args.auditoria),
           'inicio_utc': datetime.now(timezone.utc).isoformat(), 'fontes': {n: sha(frozen/n) for n in sources},
           'checkpoints': '1,10,25,50 e multiplos de 100; ultimo; pausa solicitada; saidas exclusivas',
           'validacao': '5 demandas novas a cada 25 episodios; selecao pendencias, contatos, espera+insercao',
           'teste': '10 demandas novas reservadas, seeds SUMO 20101..20110; sem selecao por teste',
           'n_atores': 9, 'termina_por_colisao': False, 'colisao_bruta': -10000, 'escala_aprendizado': ESCALA,
           'limite': 'Copia derivada com contactos residuais possiveis; nao comparar medias diretamente ao piloto anterior.'}
    novo(root/'protocolo.json', cfg)
    novo(root/'manifesto.json', construir(rede))
    if args.retomar_raiz:
        old = ler(args.retomar_raiz/'protocolo.json')
        for key in ('episodios', 'sementes', 'rede_sha256', 'escala_aprendizado'):
            assert old[key] == cfg[key]
        for name in sources:
            assert old['fontes'][name] == cfg['fontes'][name]
        (root/'demandas').mkdir(); novo(root/'demandas/indice.json', ler(args.retomar_raiz/'demandas/indice.json'))
        novo(root/'PROTEGIDOS_ANTES.json', ler(args.retomar_raiz/'PROTEGIDOS_ANTES.json'))
    else:
        if shutil.disk_usage(root).free < 18*2**30:
            raise RuntimeError('Exigidos 18 GiB livres para iniciar a rodada longa')
        fonte = PROJETO/'referencias/cologne8_sumo_rl_1.4.5/sumo_rl/nets/RESCO/cologne8/cologne8.rou.xml'
        preparar_demandas(fonte, root/'demandas', args.episodios)
        protected = sorted({p for base in (PROJETO/'resultados', PROJETO/'modelos') for p in base.rglob('*')
                            if p.is_file() and not p.is_relative_to(root)})
        novo(root/'PROTEGIDOS_ANTES.json', {'arquivos': [{'arquivo': str(p), 'sha256': sha(p)} for p in protected]})
    env = os.environ.copy(); env.update(SMARTFLOW_PROJETO=str(PROJETO), PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
    queue = list(args.sementes); running = []; failed = []; heartbeat = 0
    while queue or running:
        while queue and len(running) < 3 and not failed and not (root/'PAUSAR_APOS_EPISODIO').exists():
            seed = queue.pop(0); log = (root/f'seed{seed}.log').open('x', encoding='utf-8')
            cmd = [sys.executable, '-B', '-X', 'utf8', str(frozen/Path(__file__).name), '--worker', str(seed), '--saida', str(root)]
            if args.retomar_raiz:
                candidates = sorted((args.retomar_raiz/f'seed{seed}').glob('estado_ep*.pt'), reverse=True)
                latest = next((p for p in candidates if zipfile.is_zipfile(p)), None)
                if latest:
                    cmd += ['--retomar-checkpoint', str(latest)]
            proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            running.append((proc, log, seed)); print('INICIADO', seed, proc.pid, flush=True)
        for proc, log, seed in list(running):
            if proc.poll() is not None:
                log.close(); running.remove((proc, log, seed)); print('FIM', seed, proc.returncode, flush=True)
                if proc.returncode:
                    failed.append({'semente': seed, 'exit_code': proc.returncode})
                    if not (root/'FALHA_PARCIAL.json').exists():
                        novo(root/'FALHA_PARCIAL.json', {'falhas': failed, 'fila_nao_iniciada': queue})
        if time.monotonic()-heartbeat >= 60:
            status = progresso(root, cfg)
            with (root/'monitoramento.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps(status, allow_nan=False)+'\n')
            print(json.dumps({k: status[k] for k in ('utc', 'concluidos', 'total', 'disco_GiB')}), flush=True)
            heartbeat = time.monotonic()
        if (failed or (root/'PAUSAR_APOS_EPISODIO').exists()) and not running:
            novo(root/('FALHA.json' if failed else 'PAUSADO.json'), {'falhas': failed, 'fila_nao_iniciada': queue}); return
        time.sleep(2)
    novo(root/'CONCLUIDO.json', {'utc': datetime.now(timezone.utc).isoformat(), 'episodios': len(cfg['sementes'])*cfg['episodios']})
    with (root/'analise_execucao.log').open('x', encoding='utf-8') as f:
        subprocess.run([sys.executable, '-B', '-X', 'utf8', str(frozen/'relatar_cologne8_corrigido.py'), str(root)],
                       stdout=f, stderr=subprocess.STDOUT, env=env, check=True)
    plot_python = PROJETO.parent/'.venv-marl-relatorio/Scripts/python.exe'
    if plot_python.exists():
        with (root/'grafico_execucao.log').open('x', encoding='utf-8') as f:
            subprocess.run([str(plot_python), '-B', '-X', 'utf8', str(frozen/'relatar_cologne8_corrigido.py'), str(root), '--grafico'],
                           stdout=f, stderr=subprocess.STDOUT, env=env, check=True)
    protected = ler(root/'PROTEGIDOS_ANTES.json')
    for row in protected['arquivos']:
        assert sha(row['arquivo']) == row['sha256'], row['arquivo']
    novo(root/'PRESERVACAO.json', {'status': 'PRESERVADO', 'arquivos': len(protected['arquivos'])})
    novo(root/'TUDO_CONCLUIDO.json', {'utc': datetime.now(timezone.utc).isoformat(), 'treino': True, 'analise': True, 'preservacao': True})


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--saida', required=True, type=Path)
    p.add_argument('--rede', type=Path)
    p.add_argument('--sumo-home', type=Path)
    p.add_argument('--auditoria', type=Path)
    p.add_argument('--episodios', type=int, default=500)
    p.add_argument('--sementes', nargs='+', type=int, default=list(range(10)))
    p.add_argument('--worker', type=int)
    p.add_argument('--retomar-checkpoint', type=Path)
    p.add_argument('--retomar-raiz', type=Path)
    p.add_argument('--status', action='store_true')
    a = p.parse_args()
    if a.status:
        print(json.dumps(progresso(a.saida, ler(a.saida/'protocolo.json')), ensure_ascii=False, indent=2))
    elif a.worker is not None:
        worker(a.saida.resolve(), a.worker, a.retomar_checkpoint)
    else:
        if not a.rede or not a.sumo_home or not a.auditoria or a.episodios < 1 or len(set(a.sementes)) != len(a.sementes):
            p.error('Forneca rede, SUMO, auditoria, episodios positivos e sementes distintas')
        try:
            principal(a)
        except BaseException:
            if a.saida.exists() and not (a.saida/'FALHA_COORDENADOR.json').exists():
                novo(a.saida/'FALHA_COORDENADOR.json', {'traceback': traceback.format_exc()})
            raise
