"""Leitura do progresso da rodada longa; nao altera os treinos."""

import argparse
import json
from pathlib import Path
import time


def mostrar(raiz):
    cfg = json.loads((raiz / "protocolo.json").read_text(encoding="utf-8"))
    total = 0
    print(f"Rodada: {raiz.name}")
    for seed in cfg["sementes_modelo"]:
        p = raiz / f"progresso_seed{seed}.jsonl"
        linhas = []
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                try:
                    linhas.append(json.loads(line))
                except json.JSONDecodeError:
                    pass  # ultima linha ainda pode estar sendo gravada
        eps = [x for x in linhas if x["tipo"] == "episodio"]
        if not eps:
            print(f"  seed {seed}: aguardando primeiro episodio")
            continue
        x = eps[-1]
        total += x["episodio"]
        fase = linhas[-1]["tipo"]
        print(f"  seed {seed}: {x['episodio']}/{cfg['episodios']} | {fase} | "
              f"colisoes={x['colisoes']} | nao concluidas={x['nao_concluidas']} | "
              f"episodio={x['segundos_reais']:.1f}s")
    print(f"Episodios registrados: {total}/{len(cfg['sementes_modelo'])*cfg['episodios']}")
    if (raiz / "CONCLUIDO.json").exists():
        print("CONCLUIDO E VERIFICADO. Relatorio: " + str(raiz / "RELATORIO.md"))
        return True
    if (raiz / "falha_coordenador.json").exists():
        print("FALHA: " + (raiz / "falha_coordenador.json").read_text(encoding="utf-8"))
        return True
    if (raiz / "PAUSADO.json").exists():
        print("PAUSADO apos gravar checkpoints completos.")
        return True
    return False


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rodada", type=Path)
    ap.add_argument("--intervalo", type=int, default=0, help="0 mostra uma vez; positivo acompanha")
    args = ap.parse_args()
    while True:
        fim = mostrar(args.rodada)
        if fim or args.intervalo <= 0:
            break
        time.sleep(args.intervalo)
