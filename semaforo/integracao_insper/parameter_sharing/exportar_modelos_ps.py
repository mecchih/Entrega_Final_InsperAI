"""Copia (sem mover) os checkpoints do Modelo C escolhidos na validacao para modelos_finais/, com manifesto.

uso: python -B -X utf8 semaforo/integracao_insper/parameter_sharing/exportar_modelos_ps.py
"""

import hashlib
import json
from pathlib import Path
import shutil

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
DESTINO = AQUI / "modelos_finais"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    man = {"selecao": "checkpoint de cada semente escolhido so na validacao (221-225)", "bracos": {}}
    for b in ("C", "C_transf"):
        sel = json.loads((AQUI / "resultados" / "validacao" / f"braco_{b}.json").read_text(encoding="utf-8"))
        itens = {}
        for sm, v in sorted(sel["selecao"].items()):
            origem = Path(v["checkpoint"])
            alvo = DESTINO / b / f"s{sm}_ep{v['episodio']:04d}.pt"
            alvo.parent.mkdir(parents=True, exist_ok=True)
            if alvo.exists() and sha(alvo) != sha(origem):
                raise RuntimeError(f"{alvo} existe com outro conteudo")
            if not alvo.exists():
                shutil.copy2(origem, alvo)
            itens[sm] = {"arquivo": alvo.relative_to(RAIZ).as_posix(), "origem": origem.relative_to(RAIZ).as_posix(),
                         "sha256": sha(alvo), "validacao_espera_corredor": v["validacao"]["espera_corredor_media"]}
        man["bracos"][b] = {"aprendizes": sel["aprendizes"], "sementes_modelo": itens}
    (DESTINO / "manifesto.json").write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{sum(len(b['sementes_modelo']) for b in man['bracos'].values())} checkpoints em {DESTINO.relative_to(RAIZ).as_posix()}")


if __name__ == "__main__":
    main()
