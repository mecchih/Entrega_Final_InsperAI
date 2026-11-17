"""Reproduz a agregação local a partir da ANALISE.json, sem alterar os dados."""
import argparse
import json
from pathlib import Path


def agregar(data):
    dados = data['esperas_locais_por_entrada']
    chaves = sorted({(x['tls'], x['edge']) for x in dados if x['variante'] == 'com_supervisor'})
    entradas = []
    for tls, edge in chaves:
        medias = {}
        for variante in ('com_supervisor', 'sem_supervisor'):
            casos = [x for x in dados if x['variante'] == variante and x['tls'] == tls and x['edge'] == edge]
            n = sum(x['n'] for x in casos)
            maximos = [x['maximo'] for x in casos if x['maximo'] is not None]
            medias[variante] = {
                'n': n,
                'espera_ponderada': sum(x['n'] * x['media'] for x in casos if x['n']) / n if n else None,
                'maximo': max(maximos) if maximos else None,
            }
        if all(x['n'] for x in medias.values()):
            entradas.append({'tls': tls, 'entrada': edge, 'medias': medias,
                             'delta_s': medias['com_supervisor']['espera_ponderada'] - medias['sem_supervisor']['espera_ponderada']})
    return entradas


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pasta', type=Path)
    args = parser.parse_args()
    analise = json.loads((args.pasta / 'ANALISE.json').read_text(encoding='utf-8'))
    entradas = agregar(analise)
    salvo = json.loads((args.pasta / 'ESPERAS_ENTRADAS_AGREGADAS.json').read_text(encoding='utf-8'))
    assert entradas == salvo['entradas']
    print(json.dumps({'entradas': len(entradas), 'pioraram': sum(x['delta_s'] > 0 for x in entradas),
                      'agregacao_reproduzida': True}, ensure_ascii=False))
