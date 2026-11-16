"""
Teste de ponta a ponta de avaliar_excesso.py ANTES de existirem os modelos novos.

Truque: numa pasta temporaria, copias de dqn_fila_C_seed{i}.pt fazem o papel de
dqn_fila_excesso_C_seed{i}.pt ("dublês"). Como sao as mesmas redes, tudo tem de
sair igual ao que ja sabemos:

  1. as rodadas dos dublês = rodadas das DQN C em comparacao_C/avaliacao.json;
  2. diferencas pareadas fila_excesso - fila = 0 em todas as metricas;
  3. teste do carro sozinho = o do diagnostico (seed0: 0 presos; seed1 e seed2: 3);
  4. avaliacao.json, resumo.json, resumo.md gravados na pasta de saida pedida;
  5. nada muda em modelos/ nem em resultados/.

Uso (de dentro de scripts/):
  python testar_avaliar_excesso.py [--saida PASTA]   # PASTA fica para o --so-graficos
"""

import argparse
import hashlib
import json
import os
import shutil
import tempfile

import dqn
import simulacao
import avaliar_excesso as ae

AVALIACAO_C = ae.AVALIACAO_C
CHAVES = ["n_carros", "espera_media", "espera_p95", "espera_max", "fila_media",
          "segundos_escoamento", "veiculos_sem_atendimento", "verde_max_executado_total",
          "intervencoes_seguranca_hora", "intervencoes_seguranca_escoamento"]
SEMENTES = [1, 3]  # a 3 tem carro preso com a DQN C seed1 (equilibrado e assimetrico)


def hashes_projeto():
    out = {}
    for pasta in ("modelos", "resultados"):
        for raiz, _, arqs in os.walk(os.path.join(simulacao.PASTA, pasta)):
            for a in arqs:
                c = os.path.join(raiz, a)
                with open(c, "rb") as h:
                    out[c] = hashlib.sha256(h.read()).hexdigest()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", default=None)
    args = ap.parse_args()
    antes = hashes_projeto()
    tmp = tempfile.mkdtemp(prefix="teste_avaliar_excesso_")
    saida = args.saida or os.path.join(tmp, "saida")
    pasta_original = dqn.PASTA_MODELOS
    try:
        modelos = os.path.join(tmp, "modelos")
        os.makedirs(modelos)
        for i in range(3):
            shutil.copy(os.path.join(pasta_original, f"dqn_fila_C_seed{i}.pt"),
                        os.path.join(modelos, f"dqn_fila_excesso_C_seed{i}.pt"))
        dqn.PASTA_MODELOS = modelos  # so neste processo (por isso --processos 1)
        ae.main(["--processos", "1", "--sementes", *map(str, SEMENTES), "--saida", saida])
    finally:
        dqn.PASTA_MODELOS = pasta_original

    with open(os.path.join(saida, "avaliacao.json")) as f:
        nova = json.load(f)
    with open(AVALIACAO_C) as f:
        ref = {(r["cenario"], r["controlador"], r["seed"]): r for r in json.load(f)["rodadas"]}
    dubles = [r for r in nova["rodadas"] if r["controlador"] in ae.DQN_EXCESSO]
    assert len(dubles) == 5 * 3 * len(SEMENTES), len(dubles)
    assert all(r["origem"] == "rodada agora" for r in dubles)
    for r in dubles:
        orig = ref[(r["cenario"], r["controlador"].replace("excesso ", ""), r["seed"])]
        dif = {k: (r["metricas"][k], orig["metricas"][k]) for k in CHAVES
               if r["metricas"][k] != orig["metricas"][k]}
        assert not dif, (r["cenario"], r["controlador"], r["seed"], dif)
        assert r["esperas_por_aprox"] == orig["esperas_por_aprox"]
        assert r["hora"]["trocas_por_hora"] == orig["hora"]["trocas_por_hora"]
    reuso = [r for r in nova["rodadas"] if r["controlador"] not in ae.DQN_EXCESSO]
    assert len(reuso) == 5 * 5 * len(SEMENTES) and all(
        r["origem"] == "comparacao_C/avaliacao.json" for r in reuso)
    presos = sum(r["metricas"]["veiculos_sem_atendimento"] for r in dubles)
    print(f"OK 1: {len(dubles)} rodadas dos dublês (rodadas agora) identicas as das DQN C em "
          f"comparacao_C (inclusive {presos} veiculo(s) nao atendido(s)); "
          f"{len(reuso)} rodadas de referencia reaproveitadas")

    with open(os.path.join(saida, "resumo.json")) as f:
        res = json.load(f)
    for cen in nova["cenarios"]:
        comp = res["resumo"][f"{cen}|excesso_vs_fila"]
        assert all(v["diferenca_media"] == 0 for v in comp.values()), (cen, comp)
        assert res["resumo"][f"{cen}|DQN C fila (media das 3)"] == \
            res["resumo"][f"{cen}|DQN C fila_excesso (media das 3)"]
    print("OK 2: diferencas pareadas fila_excesso - fila = 0 em todas as metricas e cenarios; "
          "linhas dos grupos identicas")

    auto = res["carro_sozinho"]
    with open(os.path.join(simulacao.PASTA, "resultados", "diagnostico_equilibrio",
                           "automato.json")) as f:
        diag = json.load(f)
    for i in range(3):
        d = diag[f"DQN C seed{i}"]
        esperado = sum(d[f"presos_com_{n}_carro{'s' if n > 1 else ''}"] for n in (1, 2, 3))
        assert auto[f"DQN excesso C seed{i}"]["presos"] == esperado, (i, auto, esperado)
    crit = res["criterios"]
    assert crit["1_zero_ciclos_carro_sozinho"] is False and crit["1_zero_nao_atendidos"] is False
    print(f"OK 3: carro sozinho igual ao diagnostico "
          f"({[auto[k]['presos'] for k in sorted(auto)]} presos de 36) e criterios calculados "
          f"(como sao as mesmas redes, os de sucesso dao False, como devem)")

    for arq in ("avaliacao.json", "resumo.json", "resumo.md"):
        assert os.path.exists(os.path.join(saida, arq)), arq
    with open(os.path.join(saida, "resumo.md"), encoding="utf-8") as f:
        md = f.read()
    assert "DQN C fila_excesso (media das 3)" in md and "Criterios definidos" in md
    print(f"OK 4: avaliacao.json, resumo.json e resumo.md gravados em {saida}")

    if args.saida is None:
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        shutil.rmtree(os.path.join(tmp, "modelos"), ignore_errors=True)
    depois = hashes_projeto()
    assert antes == depois, sorted(set(antes.items()) ^ set(depois.items()))
    print(f"OK 5: {len(antes)} arquivos de modelos/ e resultados/ intactos, nenhum criado")
    print("\nTUDO OK")


if __name__ == "__main__":
    main()
