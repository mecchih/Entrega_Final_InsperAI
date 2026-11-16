"""Verifica viagens, politicas selecionadas e comparadores da rodada v4."""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys

sys.dont_write_bytecode = True


def ler(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def novo(p, data):
    with Path(p).open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)


def executar(root):
    from ambiente_piloto_supervisor import rodar, metricas_viagens
    from treinar_piloto_supervisor import metrica
    import torch
    cfg, m, ds = ler(root/'protocolo.json'), ler(root/'manifesto.json'), ler(root/'demandas/indice.json')
    assert ler(root/'CONCLUIDO.json')['episodios'] == cfg['episodios']*len(cfg['sementes'])
    for name, expected in cfg['fontes'].items():
        assert hashlib.sha256((root/'fontes_execucao'/name).read_bytes()).hexdigest() == expected
    for split in ('treino', 'validacao', 'teste'):
        for route in ds[split]:
            assert hashlib.sha256(Path(route['arquivo']).read_bytes()).hexdigest() == route['sha256']
    rows = []; selected = []; checked = 0; fraction_num = [0.]*9; fraction_den = [0.]*9
    for seed in cfg['sementes']:
        folder = root/f'seed{seed}'; resumo = ler(folder/'resumo.json')
        assert min(resumo['gradientes']) > 0
        checkpoint = Path(resumo['checkpoint'])
        assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == resumo['sha256_checkpoint']
        data = torch.load(checkpoint, map_location='cpu', weights_only=True)
        assert len(data['agentes']) == 9
        for a in data['agentes']:
            assert a['escala_recompensa_aprendizado'] == 1000
            assert all(torch.isfinite(v).all() for v in a['rede'].values())
        assert data['episodio'] == resumo['melhor_ep']
        vals = resumo['validacoes']
        assert min(v['score'] for v in vals) == next(v['score'] for v in vals if v['episodio'] == resumo['melhor_ep'])
        selected.append({'semente': seed, 'episodio': resumo['melhor_ep'], 'checkpoint': str(checkpoint)})
        history = [json.loads(l) for l in (folder/'historico.jsonl').read_text().splitlines()]
        assert [h['episodio'] for h in history] == list(range(1, cfg['episodios']+1))
        for h in history:
            assert h['demanda_sha256'] == ds['treino'][h['episodio']-1]['sha256']
        paths = [Path(p)/'metricas.json' for p in resumo['origens_episodios'].values()]
        for v in vals:
            val_paths = sorted(Path(v['pasta']).glob('cenario*/metricas.json'))
            assert len(val_paths) == len(ds['validacao'])
            paths.extend(val_paths)
        tests = sorted((folder/'teste_reservado').glob('cenario*/metricas.json'), key=lambda p: int(p.parent.name[7:]))
        assert len(tests) == len(ds['teste'])
        paths.extend(tests)
        for p in paths:
            d = ler(p); checked += 1
            assert not d['terminado_por_colisao'] and d['teleportes'] == 0 and d['fim_sumo'] >= 28800
            assert len(d['recompensas']) == len(d['penalidades_colisao_por_ator']) == 9
            assert d['colisoes'] == len(d['eventos_colisao'])
            assert d['viagens'] == metricas_viagens(p.parent/'tripinfo.xml.gz', 28800)
            if p.parent.parent.name == 'episodios':
                for i in range(9):
                    fraction_num[i] += abs(d['penalidades_colisao_por_ator'][i])
                    fraction_den[i] += abs(d['recompensas'][i])
        for i, p in enumerate(tests, 1):
            d = ler(p)
            assert d['semente'] == 20100+i and d['demanda_prevista'] == ds['teste'][i-1]['viagens']
            assert metrica(d) == resumo['teste'][i-1]
            rows.append({'controlador': 'marl_corrigido', 'semente_modelo': seed, 'cenario': i, **detalhes(d)})
    for modo in ('max_pressure', 'original_fixo'):
        for i, route in enumerate(ds['teste'], 1):
            folder = root/'comparadores'/modo/f'cenario{i}'
            if (folder/'metricas.json').exists():
                d = ler(folder/'metricas.json')
            else:
                d = rodar(m, [], folder, 20100+i, modo=modo, sumo_home=Path(cfg['sumo_home']),
                          rotas_cenario=route['arquivo'], recompensa_base_comum=True)
            assert d['viagens'] == metricas_viagens(folder/'tripinfo.xml.gz', 28800)
            assert d['colisoes'] == len(d['eventos_colisao']) and d['teleportes'] == 0
            assert d['demanda_prevista'] == route['viagens']
            rows.append({'controlador': modo, 'semente_modelo': None, 'cenario': i, **detalhes(d)})
    grouped = defaultdict(list)
    assert checked == len(cfg['sementes'])*(cfg['episodios'] + ((cfg['episodios']+24)//25)*len(ds['validacao']) + len(ds['teste']))
    for r in rows:
        grouped[r['controlador']].append(r)
    keys = ['espera', 'p95', 'colisoes', 'nao_concluidas', 'concluidas', 'fila_media', 'fila_maxima',
            'atraso_insercao', 'duracao_viagem']
    medias = {g: {k: statistics.mean(r[k] for r in rs) for k in keys} for g, rs in grouped.items()}
    novo(root/'ANALISE.json', {'medias': medias, 'rodadas': rows, 'checkpoints': selected,
         'simulacoes_marl_conferidas': checked, 'comparadores_conferidos': 2*len(ds['teste']),
         'fracao_colisao_retorno_por_ator_treino': [a/b if b else 0 for a, b in zip(fraction_num, fraction_den)],
         'limites': 'Rede derivada, jurisdicao de punicao e escala numerica novas. Nao comparar diretamente com v2/v3. P95 e media dos percentis das rodadas. Sem braco independente v4: nao isola efeito causal do supervisor.'})
    print(json.dumps({'medias': medias, 'simulacoes_conferidas': checked}, ensure_ascii=False), flush=True)


def detalhes(d):
    from treinar_piloto_supervisor import metrica
    v = d['viagens']['demanda_janela']
    return {**metrica(d), 'fila_media': d['fila_media_rede'], 'fila_maxima': d['fila_max_rede'],
            'atraso_insercao': v['atraso_insercao']['media'], 'duracao_viagem': v['duracao_concluidos']['media'],
            'intervencoes': d['intervencoes'] if d['modo'] != 'original_fixo' else None,
            'espera_por_entrada': d['espera_por_entrada'],
            'contatos_sem_jurisdicao_local': d['contatos_sem_jurisdicao_local'] if d['modo'] != 'original_fixo' else None}


def grafico(root):
    os.environ['MPLCONFIGDIR'] = str(Path(os.environ['SMARTFLOW_PROJETO']).parent/'tmp/cologne8_corrigido/cache_matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    data, cfg = ler(root/'ANALISE.json'), ler(root/'protocolo.json')
    target = root/'curvas_comparacao.png'
    if target.exists():
        raise FileExistsError(target)
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), layout='constrained')
    for seed in cfg['sementes']:
        hist = [json.loads(l) for l in (root/f'seed{seed}/historico.jsonl').read_text().splitlines()]
        axes[0, 0].plot([h['episodio'] for h in hist],
                        [statistics.mean(x['metricas']['espera'] for x in hist[max(0, i-19):i+1]) for i in range(len(hist))], alpha=.5, lw=1)
        vals = ler(root/f'seed{seed}/resumo.json')['validacoes']
        axes[0, 1].plot([v['episodio'] for v in vals], [statistics.mean(x['espera'] for x in v['metricas']) for v in vals], lw=1, alpha=.6)
    axes[0, 0].set_title('Treino: espera media movel (20 episodios)')
    axes[0, 1].set_title('Validacao: espera media, por inicializacao')
    groups = ['marl_corrigido', 'max_pressure', 'original_fixo']; labels = ['MARL v4', 'Max-Pressure', 'Original na copia']
    for ax, key, title in zip(axes[1], ['espera', 'colisoes'], ['Teste: espera media (s)', 'Teste: contatos por rodada']):
        values = [data['medias'][g][key] for g in groups]
        ax.bar(labels, values, color=['#166da6', '#626262', '#8760a3'])
        for i, v in enumerate(values):
            ax.text(i, v, f'{v:.2f}', ha='center', va='bottom')
        ax.set_title(title); ax.set_ylim(0, max(values)*1.15 if max(values) else 1)
    fig.suptitle('Cologne8 derivado — novos treinos e demandas reservadas')
    fig.savefig(target, dpi=160); plt.close(fig)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('pasta', type=Path)
    p.add_argument('--grafico', action='store_true')
    args = p.parse_args()
    (grafico if args.grafico else executar)(args.pasta.resolve())
