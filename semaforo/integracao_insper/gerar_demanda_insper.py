"""Gera demandas sinteticas derivadas do cenario Insper, sem alterar os originais.

Metodo (amostragem estratificada do MESMO gerador da demanda original):
  1. Um conjunto grande de viagens candidatas e gerado com o randomTrips.py
     usando exatamente as opcoes do build.bat original (com --seed 42 e
     densidade 12 elas reproduzem o osm.passenger.trips.xml byte a byte nas
     viagens), so mudando a densidade e a semente. O duarouter (--validate)
     descarta viagens sem rota valida para carros.
  2. As viagens candidatas sao separadas em dois estratos:
       corredor: a rota cruza um link de pelo menos um dos tres semaforos;
       resto:    todas as outras.
  3. Correcao de origem: o randomTrips escolhe como origem vias com menos de
     5 m (comprimento de um carro), por exemplo 522284920#0 com 1,01 m. Nelas o
     SUMO insere carros sobrepostos quando ha fila, gerando "colisoes" de
     insercao. Nessas viagens as primeiras vias da rota (< 5 m) sao retiradas:
     o carro parte poucos metros adiante, na MESMA rota e com o MESMO destino.
  4. Sorteia-se, sem reposicao, `corredor` viagens do estrato corredor e
     `resto` viagens do estrato resto. Dentro de cada estrato, origens,
     destinos, rotas e horarios seguem a distribuicao do gerador original;
     a unica mudanca e o peso relativo do corredor (documentado em gerado.json).

Saida: semaforo/cenarios/insper_demanda/<nivel>/semente_<n>/ com rotas.rou.xml,
cenario.sumocfg (mesmas opcoes do osm.sumocfg; rede, poligonos e vista apontam,
por caminho relativo, para os ORIGINAIS em semaforo/cenarios/insper/) e gerado.json.

uso:
    python -B -X utf8 semaforo/integracao_insper/gerar_demanda_insper.py --nivel teste --corredor 300 --sementes 1 2
"""

import argparse
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import insper_comum as ic  # noqa: E402

DERIVADO = ic.SEMAFORO / "cenarios" / "insper_demanda"
DENSIDADE_ORIGINAL = 12.0
DENSIDADE_CANDIDATAS = 1200.0  # 100x a original: ~27 mil candidatas por semente
ORIGEM_MINIMA_M = 5.0  # via de origem precisa caber um carro (comprimento padrao 5 m)
# Opcoes do build.bat original, na mesma ordem (sem -n/-o/-r/--seed/--insertion-density/--prefix).
OPCOES_RANDOMTRIPS = [
    "--fringe-factor", "5", "-b", "0", "-e", "3600",
    "--trip-attributes", 'departLane="best"', "--fringe-start-attributes", 'departSpeed="max"',
    "--validate", "--remove-loops",
    "--via-edge-types", "highway.motorway,highway.motorway_link,highway.trunk_link,highway.primary_link,"
                        "highway.secondary_link,highway.tertiary_link",
    "--vehicle-class", "passenger", "--vclass", "passenger",
    "--min-distance", "300", "--min-distance.fringe", "10", "--allow-fringe.min-length", "1000", "--lanes",
]


def conferir_build_bat():
    texto = (ic.CENARIO / "build.bat").read_text(encoding="utf-8")
    for opcao in OPCOES_RANDOMTRIPS:
        if opcao.replace('"', '\\"') not in texto and opcao not in texto:
            raise RuntimeError(f"opcao {opcao} nao esta no build.bat original")
    if "--insertion-density 12" not in texto or "--seed 42" not in texto:
        raise RuntimeError("build.bat original mudou")


def links_controlados():
    """(edge de entrada, edge de saida) -> (tls, linkIndex) dos tres semaforos."""
    raiz = ic.ler_rede_xml()
    pares = {}
    for c in raiz.findall("connection"):
        if c.get("tl") in ic.CONTROLADOS:
            pares.setdefault((c.get("from"), c.get("to")), []).append((c.get("tl"), int(c.get("linkIndex"))))
    return pares


def comprimentos():
    raiz = ic.ler_rede_xml()
    return {e.get("id"): float(e.find("lane").get("length")) for e in raiz.findall("edge")
            if e.get("function") != "internal"}


def corrigir_origem(veiculo, comp):
    """Retira do inicio da rota as vias menores que ORIGEM_MINIMA_M. Devolve as vias retiradas."""
    rota = veiculo.find("route")
    edges = rota.get("edges").split()
    retiradas = []
    while len(edges) > 1 and comp[edges[0]] < ORIGEM_MINIMA_M:
        retiradas.append(edges.pop(0))
    if retiradas:
        rota.set("edges", " ".join(edges))
    return retiradas


def classificar(edges, pares):
    """Semaforos controlados cruzados pela rota, em ordem, e a aproximacao de cada um."""
    cruzados = []
    for a, b in zip(edges, edges[1:]):
        if (a, b) in pares:
            cruzados.append((pares[(a, b)][0][0], a))
    return cruzados


_CANDIDATAS = {}


def candidatas(semente):
    """Candidatas da semente, geradas uma vez por processo."""
    if semente not in _CANDIDATAS:
        with tempfile.TemporaryDirectory(prefix="insper_cand_") as tmp:
            _CANDIDATAS[semente] = gerar_candidatas(semente, Path(tmp))
    return _CANDIDATAS[semente]


def gerar_candidatas(semente, pasta):
    """randomTrips + duarouter com as opcoes originais. Deterministico para a mesma semente."""
    ic.sumo_home()
    script = Path(os.environ["SUMO_HOME"]) / "tools" / "randomTrips.py"
    trips, rotas = pasta / "candidatas.trips.xml", pasta / "candidatas.rou.xml"
    cmd = [sys.executable, str(script), "-n", str(ic.REDE), *OPCOES_RANDOMTRIPS,
           "--insertion-density", str(DENSIDADE_CANDIDATAS), "--seed", str(semente),
           "--prefix", f"s{semente}_", "-o", str(trips), "-r", str(rotas)]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=pasta)
    if r.returncode != 0:
        raise RuntimeError(f"randomTrips falhou: {r.stderr[-2000:]}")
    raiz = ET.parse(rotas).getroot()
    sha_bruto = ic.sha(rotas)
    comp = comprimentos()
    deslocadas, ids = Counter(), set()
    for v in raiz:
        if v.tag == "vehicle":
            retiradas = corrigir_origem(v, comp)
            if retiradas:
                deslocadas[" ".join(retiradas)] += 1
                ids.add(v.get("id"))
    return raiz, cmd, sha_bruto, deslocadas, ids


def gerar(nivel, corredor, semente, densidade_resto=DENSIDADE_ORIGINAL, destino=None, sobrescrever=False):
    conferir_build_bat()
    destino = Path(destino) if destino else DERIVADO / nivel / f"semente_{semente}"
    if destino.exists() and not sobrescrever:
        raise FileExistsError(f"{destino} ja existe")
    destino.mkdir(parents=True, exist_ok=sobrescrever)
    pares = links_controlados()
    raiz, cmd, sha_candidatas, deslocadas, ids_deslocados = candidatas(semente)
    tipos = [v for v in raiz if v.tag == "vType"]
    veiculos = [v for v in raiz if v.tag == "vehicle"]
    estrato_corredor, estrato_resto = [], []
    for v in veiculos:
        edges = v.find("route").get("edges").split()
        (estrato_corredor if classificar(edges, pares) else estrato_resto).append(v)
    n_resto = round(len(estrato_resto) * densidade_resto / DENSIDADE_CANDIDATAS)
    if corredor > len(estrato_corredor) or n_resto > len(estrato_resto):
        raise ValueError("candidatas insuficientes; aumente DENSIDADE_CANDIDATAS")
    rng = random.Random(f"insper-demanda-{semente}")
    escolhidos = rng.sample(estrato_corredor, corredor) + rng.sample(estrato_resto, n_resto)
    escolhidos.sort(key=lambda v: (float(v.get("depart")), v.get("id")))
    saida = ET.Element("routes")
    saida.extend(tipos)
    saida.extend(escolhidos)
    ET.indent(saida, space="    ")
    rotas = destino / "rotas.rou.xml"
    with rotas.open("xb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(f"<!-- demanda derivada '{nivel}', semente {semente}; gerada por "
                "semaforo/integracao_insper/gerar_demanda_insper.py -->\n".encode())
        f.write(ET.tostring(saida, encoding="utf-8"))
    escrever_sumocfg(destino / "cenario.sumocfg", "rotas.rou.xml", Path(os.path.relpath(ic.CENARIO, destino)))
    composicao = Counter()
    n_cruzados = Counter()
    for v in escolhidos:
        cruz = classificar(v.find("route").get("edges").split(), pares)
        n_cruzados[len({t for t, _ in cruz})] += 1
        for t, entrada in cruz:
            composicao[f"{t}<-{entrada}"] += 1
    meta = {"nivel": nivel, "semente": semente, "veiculos": len(escolhidos),
            "estrato_corredor": corredor, "estrato_resto": n_resto,
            "densidade_resto_equivalente": densidade_resto,
            "candidatas": {"total": len(veiculos), "corredor": len(estrato_corredor), "resto": len(estrato_resto),
                           "densidade": DENSIDADE_CANDIDATAS, "sha256_rotas": sha_candidatas,
                           "comando": [Path(c).name if i < 2 else c for i, c in enumerate(cmd)]},
            "origens_deslocadas_nas_candidatas": {"total": sum(deslocadas.values()),
                                                   "vias_retiradas": dict(deslocadas.most_common()),
                                                   "regra": f"vias iniciais com menos de {ORIGEM_MINIMA_M} m"},
            "origens_deslocadas_nos_escolhidos": sum(1 for v in escolhidos if v.get("id") in ids_deslocados),
            "peso_relativo_do_corredor": round((corredor / len(estrato_corredor)) /
                                               (n_resto / len(estrato_resto)), 3) if n_resto else None,
            "veiculos_por_numero_de_controlados_cruzados": dict(sorted(n_cruzados.items())),
            "travessias_previstas_por_aproximacao": dict(sorted(composicao.items())),
            "sha256_rede_original": ic.sha(ic.REDE), "sha256_rotas": ic.sha(rotas),
            "sorteio": f"random.Random('insper-demanda-{semente}').sample sem reposicao, por estrato"}
    ic.json_novo(destino / "gerado.json", meta)
    return destino, meta


def escrever_sumocfg(path, rotas, original_rel):
    """Copia as opcoes do osm.sumocfg; troca so as entradas e remove as saidas."""
    raiz = ET.parse(ic.CONFIG).getroot()
    entrada = raiz.find("input")
    entrada.find("net-file").set("value", str(original_rel / "osm.net.xml.gz").replace("\\", "/"))
    entrada.find("route-files").set("value", str(rotas).replace("\\", "/"))
    # output.add.xml fica de fora: escreveria edgeData.xml. Saidas vao pela linha de comando.
    entrada.find("additional-files").set("value", str(original_rel / "osm.poly.xml.gz").replace("\\", "/"))
    raiz.remove(raiz.find("output"))
    gui = raiz.find("gui_only/gui-settings-file")
    if gui is not None:
        gui.set("value", str(original_rel / "osm.view.xml").replace("\\", "/"))
    ET.indent(raiz, space="    ")
    with Path(path).open("xb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(b"<!-- derivado de semaforo/cenarios/insper/osm.sumocfg: mesmas opcoes de simulacao -->\n")
        f.write(ET.tostring(raiz, encoding="utf-8"))


def preparar_original():
    """Nivel 'original': so um sumocfg que aponta para a demanda original, intacta."""
    destino = DERIVADO / "original"
    destino.mkdir(parents=True, exist_ok=True)
    cfg = destino / "cenario.sumocfg"
    if not cfg.exists():
        original = Path(os.path.relpath(ic.CENARIO, destino))
        escrever_sumocfg(cfg, original / "osm.passenger.trips.xml", original)
    return cfg


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--nivel", required=True)
    ap.add_argument("--corredor", type=int, required=True, help="viagens/h que cruzam ao menos um dos tres")
    ap.add_argument("--densidade-resto", type=float, default=DENSIDADE_ORIGINAL)
    ap.add_argument("--sementes", type=int, nargs="+", required=True)
    args = ap.parse_args()
    antes = ic.hashes_cenario()
    for s in args.sementes:
        destino, meta = gerar(args.nivel, args.corredor, s, args.densidade_resto)
        print(destino, meta["veiculos"], "veiculos", meta["veiculos_por_numero_de_controlados_cruzados"])
    ic.conferir_cenario(antes)


if __name__ == "__main__":
    main()
