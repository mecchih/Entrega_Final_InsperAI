"""
Testes da analise de comportamento (e da instrumentacao do simulador).

Confere que:
  1. os tres modelos carregam e os arquivos .pt nao mudam;
  2. sem instrumentacao, simulacao.rodar() reproduz EXATAMENTE os numeros de
     resultados/avaliacao_final.json;
  3. com instrumentacao, as metricas sao identicas as de sem instrumentacao;
  4. os registros sao consistentes (sequencia de fases, amarelo, verde
     minimo, um amarelo por pedido de troca, esperas por carro);
  5. a contagem de verde/transicao funciona num caso montado a mao;
  6. os verdes medidos do Webster batem com os tempos da formula;
  7. avaliacao_final.json nao foi alterado.

Uso (de dentro de scripts/):  python testar_analise.py [--sementes 1 10]
"""

import argparse
import hashlib
import json
import os
from multiprocessing import Pool

import analisar_comportamento as ac
import gerar_demanda
import simulacao
from controladores import webster

AVALIACAO = os.path.join(simulacao.PASTA, "resultados", "avaliacao_final.json")
# rotulo da analise -> rotulo em avaliacao_final.json
ROTULOS_AVALIACAO = {
    "Webster": "Tempo fixo (Webster)",
    "Max-Pressure": "Max-Pressure (ajuste unico)",
    "Max-Pressure teto": "Max-Pressure por cenario (teto)",
    "Tempo fixo 30s": "Tempo fixo sem calibrar",
    "DQN original": "DQN (recompensa de fila)",
    "DQN seed1": "DQN (recompensa de fila_seed1)",
    "DQN seed2": "DQN (recompensa de fila_seed2)",
}


def sha(caminho):
    with open(caminho, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _comparar(args):
    cenario, rotulo, seed, rotas = args
    puro = simulacao.rodar(ac.fabricar(rotulo), cenario, rotas, seed=seed)
    reg = ac.Registro()
    instr = simulacao.rodar(ac.fabricar(rotulo), cenario, rotas, seed=seed,
                            instrumentacao=reg)
    segs = reg.segmentos()
    ac.checar_consistencia(reg, segs, instr)  # levanta erro se inconsistente
    hora = ac.metricas_periodo(segs, reg.decisoes, 0, 3600)
    esc = ac.metricas_periodo(segs, reg.decisoes, 3600, 3600 + instr["segundos_escoamento"])
    extra = {
        "hora_soma": hora["s_verde"] + hora["s_amarelo"] + hora["s_vermelho_geral"],
        "esc_soma": esc["s_verde"] + esc["s_amarelo"] + esc["s_vermelho_geral"],
        "trocas_total": sum(1 for s in segs if s["tipo"] == "amarelo"),
        "trocas_hora_mais_esc": hora["trocas"] + esc["trocas"],
        "verdes_webster": {a: sorted(set(v)) for a, v in hora["_duracoes_por_aprox"].items()},
        "vermelhos": sorted({s["dur"] for s in segs[:-1] if s["tipo"] == "vermelho"}),
    }
    return cenario, rotulo, seed, puro, instr, extra


def teste_caso_montado():
    """Sequencia conhecida: N verde 0-14 (15 s), amarelo 3, vermelho 1,
    L verde 19-3609 cruza a fronteira da hora (censurado)."""
    reg = ac.Registro()
    verdes = ["GGrr", "rrGG", "GrGr", "rGrG"]
    reg.inicio(verdes, 3600)
    seq = ["GGrr"] * 15 + ["yyrr"] * 3 + ["rrrr"] + ["rrGG"] * 3591
    for t, e in enumerate(seq):
        reg.passo(t, e)
    segs = reg.segmentos()
    assert [(s["tipo"], s["aprox"], s["inicio"], s["dur"]) for s in segs] == [
        ("verde", 0, 0, 15), ("amarelo", 0, 15, 3), ("vermelho", None, 18, 1),
        ("verde", 1, 19, 3591)], segs
    h = ac.metricas_periodo(segs, [], 0, 3600)
    assert h["trocas"] == 1 and h["s_amarelo"] == 3 and h["s_vermelho_geral"] == 1
    assert h["s_verde"] == 15 + 3581 and h["segundos_simulados"] == 3600
    assert h["n_verdes_completos"] == 0  # verde inicial excluido; L censurado
    assert h["n_verdes_censurados"] == 1
    e = ac.metricas_periodo(segs, [], 3600, 3610)
    assert e["s_verde"] == 10 and e["trocas"] == 0
    print("  caso montado a mao: ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sementes", type=int, nargs="*", default=[1, 10])
    ap.add_argument("--processos", type=int, default=6)
    args = ap.parse_args()

    print("1. modelos")
    hashes_antes = {m: sha(os.path.join(simulacao.PASTA, "modelos", f"{m}.pt"))
                    for m in ac.MODELOS_DQN}
    hash_aval = sha(AVALIACAO)
    for rot in ac.ROTULO_MODELO:
        ag = ac.fabricar(rot)
        assert not ag.treinando and ag.epsilon == 0.0
    print("  tres modelos carregados em modo avaliacao: ok")

    print("5. contagem de tempos")
    teste_caso_montado()

    print("2/3/4. simulacoes com e sem instrumentacao")
    with open(AVALIACAO) as f:
        oficial = json.load(f)
    cenarios = list(gerar_demanda.CENARIOS)
    rotas = {c: gerar_demanda.gerar(c) for c in cenarios}
    tarefas = [(c, r, s, rotas[c]) for c in cenarios for r in ROTULOS_AVALIACAO
               for s in args.sementes]
    falhas = 0
    vermelhos = set()
    with Pool(args.processos) as pool:
        for cen, rot, seed, puro, instr, extra in pool.imap_unordered(_comparar, tarefas):
            ref = oficial[f"{cen}|{ROTULOS_AVALIACAO[rot]}"][seed - 1]
            ok_ref = puro == ref
            ok_instr = puro == instr
            ok_tempo = (extra["hora_soma"] == 3600
                        and extra["esc_soma"] == puro["segundos_escoamento"]
                        and extra["trocas_total"] == extra["trocas_hora_mais_esc"])
            ok_web = True
            if rot == "Webster":
                tempos = webster(cen)
                # Um verde executado dura (tempo da formula + 1 s): ver resumo.
                ok_web = all(v == [tempos[a] + 1] for a, v in extra["verdes_webster"].items())
            vermelhos |= set(extra["vermelhos"])
            status = "ok" if ok_ref and ok_instr and ok_tempo and ok_web else "FALHOU"
            if status != "ok":
                falhas += 1
            print(f"  {cen:12s} {rot:18s} seed {seed:2d}: igual ao oficial={ok_ref} "
                  f"igual sem instrumentacao={ok_instr} tempos={ok_tempo} "
                  f"webster={ok_web} -> {status}", flush=True)
    print(f"  vermelho geral executado (s): {sorted(vermelhos)}")

    print("1/7. arquivos preservados")
    for m, h in hashes_antes.items():
        assert sha(os.path.join(simulacao.PASTA, "modelos", f"{m}.pt")) == h, m
    assert sha(AVALIACAO) == hash_aval
    print("  modelos .pt e avaliacao_final.json inalterados: ok")

    print("\nTUDO OK" if falhas == 0 else f"\n{falhas} FALHAS")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
