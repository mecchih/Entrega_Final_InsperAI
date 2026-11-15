"""Compara cada verde/amarelo/vermelho real com a agenda quantizada do QP."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def verificar(raiz):
    raiz = Path(raiz)
    manifesto = json.loads((raiz / "manifesto.json").read_text(encoding="utf-8"))
    esquemas = {s["id"]: s for s in manifesto["controladores"]}
    resultados = []
    for pasta in sorted(raiz.iterdir()):
        if not (pasta.is_dir() and (pasta / "decisoes.jsonl").exists()):
            continue
        metrica = json.loads((pasta / "metricas.json").read_text(encoding="utf-8"))
        eventos = {(e["tls"], e["tempo"]): e for e in
                   (json.loads(l) for l in (pasta / "fases.jsonl").read_text().splitlines())}
        qps = [json.loads(l) for l in (raiz / (pasta.name + "_mpc") / "otimizacoes.jsonl").read_text().splitlines()]
        total = 0
        for qp in qps:
            for tls, verdes in qp["verdes_quantizados"].items():
                t = qp["tempo"]
                for fase, verde in zip(esquemas[tls]["fases"], verdes, strict=True):
                    state = fase["state"]
                    agenda = [(t, state), (t + verde, "".join("y" if s in "Gg" else "r" for s in state)),
                              (t + verde + 3, "r" * len(state))]
                    for instante, estado in agenda:
                        if instante >= metrica["fim_sumo"]:
                            continue
                        assert (tls, instante) in eventos, (pasta.name, tls, instante)
                        assert eventos[tls, instante]["estado"] == estado, (pasta.name, tls, instante)
                        total += 1
                    t += verde + 5
                assert t == qp["tempo"] + 120
        resultados.append({"pasta": pasta.name, "estados_e_instantes_conferidos": total})
    assert resultados
    return {"status": "AGENDA_EXECUTADA_EXATAMENTE", "rodadas": resultados,
            "estados_e_instantes": sum(r["estados_e_instantes_conferidos"] for r in resultados),
            "sha256_verificador": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pasta", type=Path)
    args = ap.parse_args()
    result = verificar(args.pasta)
    arquivo = args.pasta / ("VERIFICACAO_CICLOS_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    with arquivo.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(arquivo)
    print(json.dumps(result))
