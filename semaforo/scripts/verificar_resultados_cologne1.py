"""Confere os registros de uma execucao, sem SUMO, PyTorch ou escrita de arquivos."""

import argparse
import bisect
import csv
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

PROJETO = Path(__file__).resolve().parents[1]
EXECUCAO = PROJETO / "resultados/cologne1_derivado/20261110T204551Z_seed1_e699817c"
ORDEM = ["N", "L", "S", "O"]


def ler(path):
    return json.loads(path.read_text(encoding="utf-8"))


def exigir(condition, message):
    if not condition:
        raise ValueError(message)


def perto(a, b, tol=1e-6):
    return math.isclose(a, b, rel_tol=tol, abs_tol=tol)


def conferir(path):
    result, config = ler(path / "resultado.json"), ler(path / "configuracao.json")
    exigir(result["status"] == "OK", "Execucao nao foi concluida com status OK")
    exigir(result["parametros_modelo_inalterados"] and result["arquivos_preexistentes_preservados"],
           "Preservacao nao confirmada no registro da execucao")
    model = PROJETO / "modelos/dqn_fila.pt"
    exigir(hashlib.sha256(model.read_bytes()).hexdigest() == config["checkpoint_sha256"],
           "Checkpoint atual difere do registrado")
    reference = PROJETO / "referencias/sumo_rl_1.4.5/sumo_rl/nets/RESCO/cologne1"
    for name, key in [("cologne1.net.xml", "rede_original_sha256"), ("cologne1.rou.xml", "rotas_sha256")]:
        exigir(hashlib.sha256((reference / name).read_bytes()).hexdigest() == config[key],
               f"Referencia divergente: {name}")
    decisions = [json.loads(line) for line in (path / "decisoes.jsonl").read_text(encoding="utf-8").splitlines()]
    events = [json.loads(line) for line in (path / "fases.jsonl").read_text(encoding="utf-8").splitlines()]
    exigir(len(decisions) == result["decisoes"], "Contagem de decisoes divergente")
    exigir(bool(events), "Registro de fases vazio")
    greens = [m["state"] for m in config["mapeamento"]]
    exigir([m["aproximacao"] for m in config["mapeamento"]] == ORDEM, "Ordem das acoes divergente")
    for index, d in enumerate(decisions):
        expected = [d["filas"][a] / 25 for a in ORDEM] + [d["carros"][a] / 35 for a in ORDEM]
        expected += [int(i == d["verde_antes"]) for i in range(4)] + [min(d["tempo_no_verde"] / 60, 2)]
        exigir(d["id"] == index and d["seed"] == result["seed"], "Identificador/semente divergente")
        exigir(len(d["estado"]) == 13 and all(perto(a, b) for a, b in zip(d["estado"], expected)),
               f"Observacao invalida na decisao {index}")
        exigir(len(d["q"]) == 4 and all(math.isfinite(q) for q in d["q"]), "Valores Q invalidos")
        action = max(range(4), key=lambda i: d["q"][i])
        exigir(d["acao_argmax"] == action and d["aproximacao_alvo"] == ORDEM[action], "Acao nao corresponde ao argmax")
        exigir(not d["intervencao"], "Intervencao externa registrada")
        exigir(d["segundo"] % config["intervalo_decisao_s"] == 0 and d["tempo_no_verde"] >= config["tempos"]["min_green"],
               "Decisao fora do intervalo/minimo de verde")
        actual = greens[action] if d["estagio_executado_agora"] == "verde" else greens[d["verde_antes"]].replace("G", "y")
        exigir(d["state_executado_agora"] == actual, "Sinal executado divergente na decisao")
    for index, event in enumerate(events):
        expected = (greens[event["aproximacao_indice"]] if event["estagio"] == "verde" else
                    greens[event["aproximacao_indice"]].replace("G", "y") if event["estagio"] == "amarelo" else "r" * len(greens[0]))
        exigir(event["state_executado"] == expected, "Estado de luzes divergente no evento")
        if index + 1 < len(events):
            duration = events[index + 1]["segundo"] - event["segundo"]
            expected_time = {"amarelo": config["tempos"]["yellow"], "vermelho_geral": config["tempos"]["all_red"]}.get(event["estagio"])
            exigir(duration == expected_time if expected_time is not None else duration >= config["tempos"]["min_green"], "Tempo de fase invalido")
    times = [e["segundo"] for e in events]
    sums, samples, peak = {a: 0 for a in ORDEM}, 0, 0
    with (path / "serie.csv").open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            event = events[bisect.bisect_right(times, int(row["segundo"]) - 1) - 1]
            exigir(row["state_executado"] == event["state_executado"] and row["estagio_executado"] == event["estagio"], "Serie nao confere com eventos de fase")
            counts = {a: int(row["fila_" + a]) for a in ORDEM}
            for a in ORDEM:
                sums[a] += counts[a]
            peak = max(peak, sum(counts.values()))
            samples += 1
    exigir(samples == result["segundos_simulados"], "Quantidade de amostras por segundo divergente")
    exigir(perto(sum(sums.values()) / samples, result["fila_media_total"]) and peak == result["fila_max_total"], "Metricas de fila divergentes")
    trips = [t for t in ET.parse(path / "tripinfo.xml").getroot().findall("tripinfo") if float(t.get("depart", "-1")) >= 0]
    completed = [t for t in trips if float(t.get("arrival", "-1")) >= 0]
    exigir(len(completed) == result["chegaram_destino_tripinfo"] == result["chegaram_destino_api"], "Chegadas divergentes")
    exigir(len(trips) - len(completed) == result["viagens_interrompidas"], "Viagens interrompidas divergentes")
    waits = sorted(float(t.get("waitingTime")) for t in completed)
    stats = result["espera_viagem_concluidos"]
    exigir(bool(waits) and perto(sum(waits) / len(waits), stats["media_s"]), "Espera media divergente")
    exigir(waits[round(.95 * (len(waits) - 1))] == stats["p95_s"] and max(waits) == stats["max_s"], "Cauda da espera divergente")
    groups = result["espera_viagem_por_aproximacao_inclui_censurados"]
    exigir(sum(g["n"] for g in groups.values()) == len(trips), "Viagens por aproximacao nao fecham")
    return {"status": "OK", "decisoes": len(decisions), "eventos_fase": len(events), "amostras": samples,
            "viagens_concluidas": len(completed), "espera_media_s": stats["media_s"], "p95_s": stats["p95_s"],
            "nota": "Confere evidencias gravadas; nao executa simulacao nem recalcula a rede neural"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execucao", type=Path, default=EXECUCAO)
    args = parser.parse_args()
    try:
        print(json.dumps(conferir(args.execucao.resolve()), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, ET.ParseError) as exc:
        print(f"ERRO: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
