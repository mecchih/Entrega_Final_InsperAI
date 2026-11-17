"""Copia (sem mover nem alterar) os checkpoints usados no teste final do Insper para modelos_finais/.

Os treinos completos ficam locais (retomada.pt de 27-35 MB e checkpoints intermediarios);
o Git so recebe as 30 politicas avaliadas no teste final (sementes 241-250), cada uma com
~70-110 kB, mais um manifesto com caminho de origem RELATIVO, SHA-256 e configuracao.

uso: python -B -X utf8 semaforo/integracao_insper/exportar_modelos_finais.py
"""

import hashlib
import json
from pathlib import Path
import shutil
import sys

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
TESTE = AQUI / "otimizacao_final" / "resultados" / "teste_final" / "teste_final.json"
DESTINO = AQUI / "modelos_finais"
PAPEL = {
    "A_col": "RECOMENDADO para a apresentacao: independente, verde min 10 s, colisao atribuida",
    "B_col_s15": "hierarquico recomendado (supervisor 15 s), sem ganho sobre o independente",
    "B_col_s30": "hierarquico, supervisor 30 s",
    "A_col_v5": "independente com verde min 5 s (rejeitado: instavel)",
    "A_v1": "independente da bateria anterior (colisao global)",
    "B_v1": "hierarquico da bateria anterior (colisao global, supervisor 30 s)",
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def relativo(caminho):
    """Os caminhos do teste_final.json sao absolutos desta maquina; guarda so a parte do repositorio."""
    partes = Path(caminho.replace("\\", "/")).parts
    k = partes.index("semaforo")
    return Path(*partes[k:])


def main():
    d = json.loads(TESTE.read_text(encoding="utf-8"))
    DESTINO.mkdir(exist_ok=True)
    manifesto = {"origem": "semaforo/integracao_insper/otimizacao_final/resultados/teste_final/teste_final.json",
                 "selecao": "checkpoint de cada semente de modelo escolhido SO na validacao (sementes 221-225)",
                 "teste_final": "sementes de trafego 241-250 (cenario intenso), executado uma unica vez",
                 "bracos": {}}
    for braco, por_semente in d["checkpoints"].items():
        cfg = d["bracos"][braco]
        itens = {}
        for sm, caminho in sorted(por_semente.items()):
            origem = RAIZ / relativo(caminho)
            alvo = DESTINO / braco / f"s{sm}_{origem.stem.replace('politica_', '')}.pt"
            alvo.parent.mkdir(exist_ok=True)
            if alvo.exists():
                if sha(alvo) != sha(origem):
                    raise RuntimeError(f"{alvo} ja existe com conteudo diferente; nada foi sobrescrito")
            else:
                shutil.copy2(origem, alvo)
            itens[sm] = {"arquivo": alvo.relative_to(RAIZ).as_posix(), "origem": relativo(caminho).as_posix(),
                         "sha256": sha(alvo), "bytes": alvo.stat().st_size}
        manifesto["bracos"][braco] = {"papel": PAPEL.get(braco, ""), "modelo": cfg["modelo"], "config": cfg["config"],
                                      "sementes_modelo": itens}
    (DESTINO / "manifesto.json").write_text(json.dumps(manifesto, indent=1, ensure_ascii=False), encoding="utf-8")
    n = sum(len(b["sementes_modelo"]) for b in manifesto["bracos"].values())
    print(f"{n} checkpoints em {DESTINO.relative_to(RAIZ).as_posix()} (manifesto.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
