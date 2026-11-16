"""Copia derivada: elimina esperas internas com contPos=0 e confere movimentos/fases."""
import argparse
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def identidade(c):
    return tuple(c.get(k) for k in ('from', 'to', 'fromLane', 'toLane'))


def preparar(fonte, saida, sumo_home):
    fonte, saida = Path(fonte).resolve(), Path(saida).resolve()
    saida.mkdir(parents=True, exist_ok=False)
    original = ET.parse(fonte).getroot()
    internas = {lane for j in original.findall('junction') if j.get('type') == 'internal'
                for lane in j.get('incLanes', '').split() if lane.startswith(':')}
    patch = ET.Element('connections')
    for c in original.findall('connection'):
        if not c.get('from').startswith(':') and c.get('via') in internas:
            attrs = {k: c.get(k) for k in ('from', 'to', 'fromLane', 'toLane')}
            ET.SubElement(patch, 'connection', {**attrs, 'contPos': '0'})
    if not len(patch):
        raise ValueError('Nenhuma espera interna encontrada')
    with (saida/'esperas.con.xml').open('xb') as f:
        ET.ElementTree(patch).write(f, encoding='utf-8', xml_declaration=True)
    raw = saida/'netconvert_raw.net.xml'
    cmd = [str(Path(sumo_home).resolve()/'bin/netconvert.exe'), '--sumo-net-file', str(fonte),
           '--connection-files', str(saida/'esperas.con.xml'), '--output-file', str(raw)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    with (saida/'netconvert.log').open('x', encoding='utf-8') as f:
        f.write(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError('netconvert falhou; consultar log')
    new = ET.parse(raw).getroot()
    old_ext = {e.get('id'): e for e in original.findall('edge') if e.get('function') != 'internal'}
    new_ext = {e.get('id'): e for e in new.findall('edge') if e.get('function') != 'internal'}
    if old_ext.keys() != new_ext.keys():
        raise ValueError('Ruas externas mudaram')
    old_mov = {identidade(c): c for c in original.findall('connection') if c.get('tl')}
    new_mov = {identidade(c): c for c in new.findall('connection') if c.get('tl')}
    if old_mov.keys() != new_mov.keys():
        raise ValueError('Movimentos controlados mudaram')
    tls_new = {t.get('id'): t for t in new.findall('tlLogic')}
    tls_old = {t.get('id'): t for t in original.findall('tlLogic')}
    if tls_new.keys() != tls_old.keys():
        raise ValueError('Quantidade/identidade de TLS mudou')
    # Conserva cada programa por identidade do movimento, inclusive amarelos.
    mapping = defaultdict(dict)
    for key, old_c in old_mov.items():
        new_c = new_mov[key]
        if old_c.get('tl') != new_c.get('tl'):
            raise ValueError('TLS de movimento mudou')
        mapping[old_c.get('tl')].setdefault(int(new_c.get('linkIndex')), set()).add(int(old_c.get('linkIndex')))
    for tid, old_t in tls_old.items():
        target = tls_new[tid]
        target.attrib.clear(); target.attrib.update(old_t.attrib)
        for child in list(target):
            target.remove(child)
        n_links = max(mapping[tid]) + 1
        if set(mapping[tid]) != set(range(n_links)):
            raise ValueError('Mapeamento incompleto de sinais')
        for phase in old_t:
            clone = deepcopy(phase)
            if phase.tag == 'phase':
                chars = []
                for idx in range(n_links):
                    colors = {phase.get('state')[j] for j in mapping[tid][idx]}
                    if len(colors) != 1:
                        raise ValueError('Sinais agrupados com cores incompatíveis')
                    chars.append(colors.pop())
                clone.set('state', ''.join(chars))
            target.append(clone)
    # Confere exatamente as cores de TODOS os movimentos em TODAS as fases.
    for key, old_c in old_mov.items():
        new_c = new_mov[key]; tid = old_c.get('tl')
        for a, b in zip(tls_old[tid].findall('phase'), tls_new[tid].findall('phase'), strict=True):
            assert a.get('state')[int(old_c.get('linkIndex'))] == b.get('state')[int(new_c.get('linkIndex'))]
    arquivo = saida/'cologne8.net.xml'
    with arquivo.open('xb') as f:
        ET.ElementTree(new).write(f, encoding='utf-8', xml_declaration=True)
    changes = []
    for eid, edge in old_ext.items():
        old_lanes = {l.get('id'): dict(l.attrib) for l in edge.findall('lane')}
        new_lanes = {l.get('id'): dict(l.attrib) for l in new_ext[eid].findall('lane')}
        if old_lanes != new_lanes:
            changes.append(eid)
    data = {'rede_original': str(fonte), 'sha256_original': sha(fonte), 'rede': str(arquivo),
            'sha256': sha(arquivo), 'comando': cmd, 'conexoes_sem_espera_interna': len(patch),
            'semaforos': len(tls_old), 'movimentos_controlados': len(old_mov),
            'fases_mapeadas_por_movimento': True, 'ruas_com_atributos_de_faixa_reprocessados': changes,
            'vtype': 'original', 'limite': 'Rede derivada reprocessada, espera por brecha antes da intersecao. Validar contatos e vazao antes do treino.',
            'referencia': 'https://eclipse.dev/sumo/docs/Networks/PlainXML.html#connection_descriptions'}
    with (saida/'PROVENIENCIA.json').open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(json.dumps(data, ensure_ascii=False), flush=True)
    return data


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fonte', required=True, type=Path)
    p.add_argument('--saida', required=True, type=Path)
    p.add_argument('--sumo-home', required=True, type=Path)
    a = p.parse_args()
    preparar(a.fonte, a.saida, a.sumo_home)
