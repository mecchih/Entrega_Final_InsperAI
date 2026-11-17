"""Reproduz contatos com programa original e Max-Pressure; nunca altera a rede."""

from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
from ambiente_comparacao_mpc import construir_manifesto, rodar


def salvar(p, obj):
    with Path(p).open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, allow_nan=False, indent=2)


class Auditor:
    def __init__(self, net):
        r = ET.parse(net).getroot()
        self.edges = {e.get('id'): e for e in r.findall('edge')}
        self.junctions = {j.get('id'): j for j in r.findall('junction') if j.get('type') != 'internal'}
        self.connections = [dict(c.attrib) for c in r.findall('connection') if c.get('from') in self.edges
                            and self.edges[c.get('from')].get('function') != 'internal']
        self.by_from = defaultdict(list)
        for c in self.connections:
            self.by_from[c['from'] + '_' + c['fromLane']].append(c)
        self.history = deque(maxlen=8)
        self.last = {}
        self.ativos = set()
        self.eventos = []
        self.params = None
        self.pre = None

    def preparar(self, conn, foto, relogios, agora):
        self.pre = {tls: conn.trafficlight.getRedYellowGreenState(tls) for tls in conn.trafficlight.getIDList()}

    def observar(self, conn, foto, agora):
        if self.params is None:
            self.params = {'versao': list(conn.getVersion()), 'tau_pkw': conn.vehicletype.getTau('pkw'),
                'minGap_pkw': conn.vehicletype.getMinGap('pkw'), 'decel_pkw': conn.vehicletype.getDecel('pkw'),
                'length_pkw': conn.vehicletype.getLength('pkw'), 'step_s': conn.simulation.getDeltaT()}
        tls = {t: conn.trafficlight.getRedYellowGreenState(t) for t in conn.trafficlight.getIDList()}
        cars = {}
        for v in conn.vehicle.getIDList():
            lane, edge = conn.vehicle.getLaneID(v), conn.vehicle.getRoadID(v)
            if edge in self.edges and self.edges[edge].get('function') != 'internal':
                next_tls = list(conn.vehicle.getNextTLS(v))
                self.last[v] = {'lane': lane, 'edge': edge, 'tempo': agora, 'next_tls': next_tls}
            cars[v] = {'lane': lane, 'edge': edge, 'speed': conn.vehicle.getSpeed(v),
                       'ultima_aproximacao': self.last.get(v)}
        raw = list(conn.simulation.getCollisions())
        keys = {tuple(sorted((c.collider, c.victim))) for c in raw}
        for c in raw:
            key = tuple(sorted((c.collider, c.victim)))
            if key in self.ativos:
                continue
            vehicles = []
            for v in key:
                d = dict(cars.get(v, {}))
                d['id'] = v
                if v in cars:
                    d.update(position=list(conn.vehicle.getPosition(v)), angle=conn.vehicle.getAngle(v),
                             speed_mode=conn.vehicle.getSpeedMode(v), lanechange_mode=conn.vehicle.getLaneChangeMode(v))
                approach = d.get('ultima_aproximacao') or {}
                candidates = self.by_from.get(approach.get('lane'), [])
                # Uma lane interna pode ser a primeira ou uma via interna encadeada.
                direct = [x for x in candidates if x.get('via') == d.get('lane')]
                if direct:
                    candidates = direct
                elif approach.get('next_tls'):
                    t, link, _, _ = approach['next_tls'][0]
                    candidates = [x for x in candidates if x.get('tl') == t and int(x.get('linkIndex',-1)) == link]
                d['movimentos_candidatos'] = candidates
                if len(candidates) == 1:
                    mov = candidates[0]
                    jid = self.edges[mov['from']].get('to')
                    j = self.junctions[jid]
                    lanes = j.get('intLanes','').split()
                    d['junction'] = jid
                    d['request_index'] = lanes.index(mov['via']) if mov.get('via') in lanes else None
                    d['cor_antes'] = (self.pre or (self.history[-1]['tls'] if self.history else tls)).get(mov.get('tl'),'')[int(mov['linkIndex'])] if mov.get('tl') else None
                vehicles.append(d)
            foe = None
            if (len(vehicles) == 2 and vehicles[0].get('junction') == vehicles[1].get('junction')
                    and all(v.get('request_index') is not None for v in vehicles)):
                j = self.junctions[vehicles[0]['junction']]
                req = {int(x.get('index')): x for x in j.findall('request')}
                a,b = [v['request_index'] for v in vehicles]
                foe = {'a_foe_b': req[a].get('foes')[::-1][b], 'b_foe_a': req[b].get('foes')[::-1][a],
                       'a_responde_b': req[a].get('response')[::-1][b], 'b_responde_a': req[b].get('response')[::-1][a]}
            self.eventos.append({'tempo':agora,'tipo':c.type,'lane_evento':c.lane,'veiculos':vehicles,
                'tls_antes':self.pre or (self.history[-1]['tls'] if self.history else tls),'tls_depois':tls,
                'foes_xml':foe,'historico': [{'tempo':h['tempo'],'veiculos':{v:h['cars'].get(v) for v in key},'tls':h['tls']} for h in self.history]})
        self.ativos = keys
        self.history.append({'tempo':agora,'cars':cars,'tls':tls})
        self.last = {v:d for v,d in self.last.items() if v in cars}


def executar(pasta, sumo_home):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=False)
    base = Path(__file__).resolve().parents[1]
    net = base/'referencias/cologne8_sumo_rl_1.4.5/sumo_rl/nets/RESCO/cologne8/cologne8.net.xml'
    m = construir_manifesto('cologne8',continuar_apos_colisao=True)
    records = []
    for modo in ('original_fixo','max_pressure'):
        obs = Auditor(net)
        met = rodar(m,[],pasta/modo,301,modo=modo,sumo_home=Path(sumo_home),
                    detalhar=True,controlador_externo=obs)
        assert len(obs.eventos) == met['colisoes']
        salvar(pasta/(modo+'_contexto.json'),{'parametros':obs.params,'eventos':obs.eventos})
        classified=Counter()
        for e in obs.eventos:
            if e['foes_xml']:
                colors=''.join(v.get('cor_antes') or '-' for v in e['veiculos'])
                classified[str((colors,e['foes_xml']['a_foe_b'],e['foes_xml']['a_responde_b'],e['foes_xml']['b_responde_a']))]+=1
        records.append({'modo':modo,'seed':301,'colisoes':met['colisoes'],'parametros':obs.params,
                        'classificacao_cores_foes':dict(classified),'nao_concluidas':met['viagens_nao_concluidas']})
        print(json.dumps(records[-1]),flush=True)
    salvar(pasta/'resumo.json',{'rodadas':records,'fontes':{'net_sha256':hashlib.sha256(net.read_bytes()).hexdigest()},
        'limite':'Contatos no original nao sao prova de culpa da politica. A auditoria classifica movimentos quando univocos; nao presume culpa nos casos ambiguos.'})


if __name__ == '__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('pasta',type=Path)
    ap.add_argument('--sumo-home',required=True,type=Path)
    a=ap.parse_args()
    executar(a.pasta,a.sumo_home)
