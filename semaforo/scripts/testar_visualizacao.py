"""
Testa visualizar_dqn.py abrindo o SUMO-GUI de verdade (em velocidade maxima).

1. Cada rodada no SUMO-GUI reproduz EXATAMENTE as metricas da mesma rodada
   (cenario, controlador, semente) em resultados/comparacao_C/avaliacao.json
   -> a janela mostra a mesma simulacao da avaliacao, na dinamica C.
2. --parar-em e --inicio funcionam e encerram a rodada sem deixar lixo.
3. Nenhum arquivo de modelos/ ou resultados/ muda ou aparece.

Uso (de dentro de scripts/):  python testar_visualizacao.py
"""

import hashlib
import json
import os

import simulacao
import visualizar_dqn

PASTAS = [os.path.join(simulacao.PASTA, p) for p in ("modelos", "resultados")]
AVALIACAO = os.path.join(simulacao.PASTA, "resultados", "comparacao_C", "avaliacao.json")
CHAVES = ["n_carros", "espera_media", "espera_p95", "espera_max", "fila_media",
          "segundos_escoamento", "verde_max_executado_total",
          "intervencoes_seguranca_hora", "intervencoes_seguranca_escoamento"]

CASOS = [  # (argumentos, rotulo na avaliacao, cenario, semente)
    (["--modelo", "dqn_fila_C_seed0.pt"], "DQN C seed0", "pico", 1),
    (["--modelo", "dqn_fila"], "DQN original", "saturado", 2),
    (["--controlador", "webster"], "Webster", "pico", 1),
    (["--controlador", "max-pressure"], "Max-Pressure", "girado", 3),
    (["--controlador", "max-pressure-teto-recal"], "Max-Pressure teto (recal. C)", "assimetrico", 1),
]


def fotografia():
    f = {}
    for pasta in PASTAS:
        for raiz, _, arquivos in os.walk(pasta):
            for a in arquivos:
                c = os.path.join(raiz, a)
                with open(c, "rb") as h:
                    f[c] = hashlib.sha256(h.read()).hexdigest()
    return f


def main():
    antes = fotografia()
    with open(AVALIACAO) as f:
        salvas = {(r["cenario"], r["controlador"], r["seed"]): r["metricas"]
                  for r in json.load(f)["rodadas"]}

    for extra, rotulo, cenario, semente in CASOS:
        m = visualizar_dqn.main(extra + ["--cenario", cenario, "--semente", str(semente),
                                         "--velocidade", "0", "--silencioso"])
        ref = salvas[(cenario, rotulo, semente)]
        dif = {k: (m[k], ref[k]) for k in CHAVES if m[k] != ref[k]}
        assert not dif, f"{rotulo} {cenario} s{semente}: diferente da avaliacao {dif}"
        print(f"OK 1: {rotulo:30s} {cenario:12s} semente {semente}: identica a avaliacao "
              f"(espera {m['espera_media']:.2f} s)\n")

    m = visualizar_dqn.main(["--cenario", "pico", "--inicio", "1200", "--parar-em", "1260",
                             "--velocidade", "20"])
    assert m is None
    print("OK 2: --inicio 1200 --parar-em 1260 encerrou a rodada no minuto 21\n")

    depois = fotografia()
    assert antes == depois, (f"arquivos mudaram: "
                             f"{sorted(set(antes.items()) ^ set(depois.items()))}")
    print(f"OK 3: {len(antes)} arquivos de modelos/ e resultados/ intactos")
    print("\nTUDO OK")


if __name__ == "__main__":
    main()
