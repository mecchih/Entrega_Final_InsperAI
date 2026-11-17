"""Copia (sem mover) os checkpoints do C5 escolhidos na validacao para treinamento_c5/modelos_finais/, com manifesto.

uso: python -B -X utf8 semaforo/integracao_insper/parameter_sharing/treinamento_c5/exportar_modelos_c5.py
"""

import hashlib
import json
from pathlib import Path
import shutil

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[3]
DESTINO = AQUI / "modelos_finais"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    sel = json.loads((AQUI / "resultados" / "validacao" / "selecao_c5.json").read_text(encoding="utf-8"))
    itens = {}
    for sm, v in sorted(sel["selecao"].items()):
        origem = RAIZ / v["checkpoint"]
        alvo = DESTINO / "C5" / f"s{sm}_ep{v['episodio']:04d}.pt"
        alvo.parent.mkdir(parents=True, exist_ok=True)
        if alvo.exists() and sha(alvo) != sha(origem):
            raise RuntimeError(f"{alvo} existe com outro conteudo")
        if not alvo.exists():
            shutil.copy2(origem, alvo)
        itens[sm] = {"arquivo": alvo.relative_to(RAIZ).as_posix(), "origem": origem.relative_to(RAIZ).as_posix(),
                     "sha256": sha(alvo), "validacao_espera_5_cruzamentos": round(v["validacao"]["espera5"], 3),
                     "validacao_espera_corredor": round(v["validacao"]["espera_corredor"], 3)}
    man = {"selecao": "checkpoint de cada semente escolhido so na validacao (221-225), criterio: espera nos 5 cruzamentos",
           "formato": "smartflow_marl_insper_parameter_sharing_c5_v1 (carregar com politica_c5.carregar)",
           "tls": ["476455095", "40278305", "40278183", "300058973", "302806060"], "sementes_modelo": itens}
    (DESTINO / "manifesto.json").write_text(json.dumps(man, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(itens)} checkpoints em {DESTINO.relative_to(RAIZ).as_posix()}")


if __name__ == "__main__":
    main()
