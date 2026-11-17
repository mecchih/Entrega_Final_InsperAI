"""Audita uma copia da demanda com comportamento conservador; nao treina redes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
from ambiente_piloto_supervisor import construir_manifesto, rodar
from auditar_colisoes_cologne8 import Auditor

PERFIS = {
    'original': {},
    'gap_veicular': {'minGap': '2.5'},
    'intervalo2': {'tau': '2.0'},
    'conservador': {'jmStoplineGapMinor': '2', 'jmAdvance': '0', 'jmExtraGap': '1',
                    'jmTimegapMinor': '2', 'jmSigmaMinor': '0'},
    'margem4': {'jmStoplineGapMinor': '4', 'jmAdvance': '0', 'jmExtraGap': '2',
                'jmTimegapMinor': '2', 'jmSigmaMinor': '0'},
}


def novo(path, data):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)


def derivar(fonte, saida, perfil):
    tree = ET.parse(fonte)
    tipos = tree.getroot().findall('vType')
    if not tipos:
        raise ValueError('Demanda sem vType explicito')
    for v in tipos:
        v.attrib.update(PERFIS[perfil])
    with Path(saida).open('xb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)
    return {'fonte': str(Path(fonte).resolve()), 'fonte_sha256': hashlib.sha256(Path(fonte).read_bytes()).hexdigest(),
            'arquivo': str(Path(saida).resolve()), 'sha256': hashlib.sha256(Path(saida).read_bytes()).hexdigest(),
            'perfil': perfil, 'alteracoes_vtype': PERFIS[perfil],
            'inalterados': 'esta etapa nao edita rede/fases, viagens, OD, horarios, comprimento ou deteccao de colisoes; atributos veiculares alterados constam explicitamente acima'}


def executar(args):
    root = args.saida.resolve()
    root.mkdir(parents=True, exist_ok=False)
    base = Path(__file__).resolve().parents[1]
    net_original = base/'referencias/cologne8_sumo_rl_1.4.5/sumo_rl/nets/RESCO/cologne8/cologne8.net.xml'
    net = args.rede or net_original
    route = args.rotas or net_original.with_name('cologne8.rou.xml')
    derivacao = derivar(route, root/'demanda_derivada.rou.xml', args.perfil)
    novo(root/'derivacao.json', derivacao)
    manifesto = construir_manifesto('cologne8', continuar_apos_colisao=True, rede_cenario=net if args.rede else None)
    rows = []
    for seed in args.sementes:
        for modo in ('original_fixo', 'max_pressure'):
            auditor = Auditor(net)
            m = rodar(manifesto, [], root/f'{modo}_seed{seed}', seed, modo=modo,
                      sumo_home=args.sumo_home, rotas_cenario=derivacao['arquivo'],
                      recompensa_base_comum=True, controlador_externo=auditor)
            assert len(auditor.eventos) == m['colisoes']
            novo(root/f'{modo}_seed{seed}_contexto.json', {'parametros': auditor.params, 'eventos': auditor.eventos})
            row = {'modo': modo, 'semente': seed, 'colisoes': m['colisoes'],
                   'nao_concluidas': m['viagens_nao_concluidas'],
                   'espera': m['viagens']['demanda_janela']['espera_todos_inclui_censura']['media']}
            rows.append(row)
            print(json.dumps(row), flush=True)
    novo(root/'AUDITORIA.json', {'rodadas': rows, 'derivacao': derivacao,
         'sem_contatos_nas_condicoes_auditadas': all(r['colisoes'] == r['nao_concluidas'] == 0 for r in rows),
         'limite': 'Copia comportamental derivada; ausencia observada de contatos nao garante seguranca universal.'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida', required=True, type=Path)
    parser.add_argument('--sumo-home', required=True, type=Path)
    parser.add_argument('--rotas', type=Path)
    parser.add_argument('--rede', type=Path)
    parser.add_argument('--perfil', choices=PERFIS, default='conservador')
    parser.add_argument('--sementes', nargs='+', type=int, default=[301])
    executar(parser.parse_args())
