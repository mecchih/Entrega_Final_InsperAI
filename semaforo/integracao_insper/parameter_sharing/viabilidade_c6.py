"""Viabilidade C3 -> C6: caracteriza os 11 semaforos nao controlados do cenario Insper. So leitura.

Nao treina, nao controla nenhum semaforo e nao altera o cenario: le a rede (sumolib), abre o SUMO
por 1 passo so para obter os conflitos internos (getInternalFoes, como insper_comum.foes_traci) e
conta rotas das demandas de validacao (intenso_validacao 221-225).

uso: python -B -X utf8 semaforo/integracao_insper/parameter_sharing/viabilidade_c6.py
"""

from collections import Counter, defaultdict
import datetime
import json
from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
import insper_comum as ic  # noqa: E402

SEMENTES = [221, 222, 223, 224, 225]


def main():
    ic.sumo_home()
    import sumolib
    import traci
    antes = ic.hashes_cenario()
    net = sumolib.net.readNet(str(ic.REDE), withPrograms=True)
    tls_ids = sorted(t.getID() for t in net.getTrafficLights())
    cfg = ic.SEMAFORO / "cenarios" / "insper_demanda" / "intenso_validacao" / "semente_221" / "cenario.sumocfg"
    tmp = tempfile.mkdtemp()
    traci.start([str(ic.sumo_home() / "bin" / "sumo.exe"), "-c", str(cfg), "--end", "1", "--no-step-log", "true",
                 "--tripinfo-output", str(Path(tmp) / "t.xml"), "--log", str(Path(tmp) / "l.log")])
    foes = {}
    for t in tls_ids:
        try:
            foes[t] = ic.foes_traci(traci, t)[0]
        except RuntimeError as e:  # link com mais de um movimento
            foes[t] = str(e)
    traci.close()

    # rotas da validacao: veiculos por aproximacao e veiculos compartilhados com o corredor
    entradas = {t: {i.getEdge().getID() for i, o, li in net.getTLS(t).getConnections()} for t in tls_ids}
    passa = Counter()
    por_aprox = defaultdict(Counter)
    com_corredor = Counter()
    corredor = set().union(*(entradas[t] for t in ic.CONTROLADOS))
    for s in SEMENTES:
        for v in ET.parse(cfg.parents[1] / f"semente_{s}" / "rotas.rou.xml").getroot().iter("vehicle"):
            r = set(v.find("route").get("edges").split())
            c = bool(r & corredor)
            for t in tls_ids:
                hit = r & entradas[t]
                if hit:
                    passa[t] += 1
                    com_corredor[t] += c
                    for e in hit:
                        por_aprox[t][e] += 1

    # distancia (m) pela rede dirigida ate o cruzamento controlado mais proximo, nos dois sentidos
    def dist(a, b):
        na, nb = net.getNode(a), net.getNode(b)
        best = None
        for e1 in na.getOutgoing():
            for e2 in nb.getIncoming():
                p, c = net.getShortestPath(e1, e2)
                if p is not None and (best is None or c < best):
                    best = c
        return round(best, 1) if best is not None else None

    saida = {}
    for t in tls_ids:
        tl = net.getTLS(t)
        con = sorted(tl.getConnections(), key=lambda c: c[2])
        prog = list(tl.getPrograms().values())[0]
        fases = [p.state for p in prog.getPhases()]
        verdes = [p for p in fases if "y" not in p and any(ch in "Gg" for ch in p)]
        n_links = len(fases[0]) if fases else 0
        so_bici = {li for i, o, li in con if i.getPermissions() <= {"bicycle", "pedestrian"}}
        aprox = sorted({i.getEdge().getID() for i, o, li in con if li not in so_bici})
        f = foes[t]
        intra = None if isinstance(f, str) else sum(1 for v in verdes for i in range(n_links) for j in f[i]
                                                    if j > i and v[i] in "Gg" and v[j] in "Gg")
        # relacao aproximacao -> fases verdes que a servem
        servida = {e: [k for k, v in enumerate(verdes) if any(v[li] in "Gg" for i, o, li in con if i.getEdge().getID() == e)]
                   for e in aprox}
        no = net.getNode(t) if t in [n.getID() for n in net.getNodes()] else None
        d_corr = {c: min(x for x in (dist(t, c), dist(c, t)) if x is not None) if no and any(
            x is not None for x in (dist(t, c), dist(c, t))) else None for c in ic.CONTROLADOS} if no else {}
        saida[t] = {
            "controlado_hoje": t in ic.CONTROLADOS, "tipo": prog.getType(), "n_fases": len(fases),
            "n_verdes": len(verdes), "verdes": verdes, "n_links": n_links, "links_so_bicicleta": len(so_bici),
            "aproximacoes_veiculos": {e: {"nome": net.getEdge(e).getName(), "faixas": net.getEdge(e).getLaneNumber(),
                                          "fases_que_servem": servida[e],
                                          "veiculos_por_semente": round(por_aprox[t][e] / len(SEMENTES), 1)} for e in aprox},
            "conflitos_na_mesma_fase": intra if not isinstance(f, str) else f"indefinido: {f}",
            "cluster": t.startswith("cluster") or (no is not None and len(no.getIncoming()) > 4),
            "veiculos_por_semente": round(passa[t] / len(SEMENTES), 1),
            "veiculos_do_corredor_por_semente": round(com_corredor[t] / len(SEMENTES), 1),
            "distancia_m_ate_controlados": d_corr,
            "coordenada": [round(x) for x in no.getCoord()] if no else None,
        }
    ic.conferir_cenario(antes)
    pasta = AQUI / "resultados"
    alvo = pasta / f"viabilidade_c6_{datetime.datetime.now():%Y%m%dT%H%M%S}.json"
    ic.json_novo(alvo, saida)
    for t, d in saida.items():
        print(t[:40], "| ctrl" if d["controlado_hoje"] else "|", d["tipo"], "| verdes", d["n_verdes"], "| links", d["n_links"],
              "| bici", d["links_so_bicicleta"], "| intra", d["conflitos_na_mesma_fase"], "| aprox",
              {e: (v["nome"][:22], v["faixas"], v["fases_que_servem"], v["veiculos_por_semente"]) for e, v in d["aproximacoes_veiculos"].items()},
              "| veic", d["veiculos_por_semente"], "corr", d["veiculos_do_corredor_por_semente"], "| dist", d["distancia_m_ate_controlados"])
    print("salvo em", alvo)


if __name__ == "__main__":
    main()
