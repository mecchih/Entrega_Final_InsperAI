"""Treino do Modelo C5 (5 agentes, uma DoubleDQN compartilhada) - experimento C5-A, demanda intensa atual.

Mesmo laco do C3 (parameter_sharing/treinar_ps.py): demandas de treino 1001-1030 na mesma ordem,
150 episodios, checkpoint a cada 25, config do A_col (verde minimo 10 s, colisao atribuida).

uso: python -B -X utf8 semaforo/integracao_insper/parameter_sharing/treinamento_c5/treinar_c5.py --semente 1 --pasta <pasta>
"""

import argparse
import json
import os
from pathlib import Path
import sys
import time

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import politica_c5 as p5  # noqa: E402
import insper_comum as ic  # noqa: E402
import ambiente_c5 as env5  # noqa: E402
import treinar_marl_insper_v2 as tr  # noqa: E402

CONFIG = {"verde_minimo": 10, "colisao": "atribuida", "supervisor_s": 30}


def treinar(semente, pasta, episodios=150, checkpoint_cada=25):
    import torch
    torch.set_num_threads(1)
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    config = dict(env5.CONFIG_V1, **CONFIG)
    mapa = p5.ad.mapeamento(p5.TLS5)
    rede, agentes = p5.criar_agentes(semente, mapa)
    historico = pasta / "historico.jsonl"
    inicial = 0
    if (pasta / "retomada.pt").exists():
        d, rede = p5.carregar(pasta / "retomada.pt")
        if d["semente_modelo"] != semente or d["config"] != config:
            raise ValueError("retomada.pt de outro treino")
        agentes = p5.visoes_avaliacao(rede, mapa)
        inicial = d["episodio"]
        linhas = historico.read_text(encoding="utf-8").splitlines()[:inicial] if historico.exists() else []
        historico.write_text("".join(l + "\n" for l in linhas), encoding="utf-8")
    if not (pasta / "configuracao.json").exists():
        ic.json_novo(pasta / "configuracao.json", {
            "formato": p5.FORMATO, "modelo": "parameter_sharing_c5", "experimento": "C5-A (demanda intensa atual)",
            "config": config, "semente_modelo": semente, "episodios": episodios, "controlados": p5.TLS5,
            "inicializacao": "aleatoria (nenhum peso do C3)",
            "sementes_trafego": [tr.SEMENTES_TREINO[e % len(tr.SEMENTES_TREINO)] for e in range(episodios)],
            "orcamento": {"replay": rede.memoria.capacidade, "aquecimento": rede.aquecimento,
                          "decaimento_epsilon": rede.decaimento, "gradiente_a_cada_transicoes": rede.n_aprendizes},
            "mapeamento": {t: {"perm_obs": m["perm_obs"], "acao_real": m["acao_real"]} for t, m in mapa.items()},
            "recompensa": env5.RECOMPENSA, "tempos": ic.TEMPOS})
    inicio = time.perf_counter()
    for ep in range(inicial + 1, episodios + 1):
        s = tr.SEMENTES_TREINO[(ep - 1) % len(tr.SEMENTES_TREINO)]
        g0, t0 = rede.gradientes, list(rede.transicoes_por_agente)
        dec0 = [(a.decisoes, a.decisoes_vazias) for a in agentes]
        m = env5.rodar_episodio(tr.cfg_treino(s), pasta / "episodios" / f"ep{ep:04d}", s, agentes, "independente",
                                treinando=True, rotulo=f"c5_{semente}_{ep}", config=config, controlados=p5.TLS5)
        linha = {"episodio": ep, "semente_trafego": s, "valido": m["valido"], "motivo_invalido": m["motivo_invalido"],
                 "duracao_real_s": m["duracao_real_s"], "fracao_concluida": m["fracao_concluida"],
                 "espera_corredor_media": m["espera_corredor_s"].get("media"),
                 "espera_rede_media": m["espera_rede_s"].get("media"),
                 "espera_cruzamentos": {t: c["espera_s"].get("media") for t, c in m["cruzamentos"].items()},
                 "teleportes": m["teleportes"]["total"], "colisoes": m["colisoes"]["eventos"],
                 "recompensas": m["recompensas"], "recompensa_agregada": round(sum(m["recompensas"]), 4),
                 "trocas": m["trocas"], "epsilon": round(rede.epsilon, 4), "gradientes": rede.gradientes,
                 "gradientes_no_episodio": rede.gradientes - g0,
                 "transicoes_por_agente_no_episodio": [b - a for a, b in zip(t0, rede.transicoes_por_agente)],
                 "decisoes_vazias_por_agente": [a.decisoes_vazias - v for a, (_, v) in zip(agentes, dec0)],
                 "replay": rede.memoria.n,
                 "perda_media": round(sum(rede.perdas) / len(rede.perdas), 5) if rede.perdas else None,
                 "intervencoes": m["intervencoes_verde_maximo"]}
        with historico.open("a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
        print(f"c5 s{semente} ep{ep} trafego {s}: {m['duracao_real_s']} s, valido={m['valido']}, corredor "
              f"{linha['espera_corredor_media']}, eps {linha['epsilon']}, grad {rede.gradientes}, replay {rede.memoria.n}",
              flush=True)
        if ep % checkpoint_cada == 0 or ep == episodios:
            alvo = pasta / f"politica_ep{ep:04d}.pt"
            if not alvo.exists():
                p5.salvar(alvo, rede, semente, ep, False, config)
            tmp = pasta / "retomada.tmp"
            tmp.unlink(missing_ok=True)
            p5.salvar(tmp, rede, semente, ep, True, config)
            os.replace(tmp, pasta / "retomada.pt")
    linhas = [json.loads(l) for l in historico.read_text(encoding="utf-8").splitlines()]
    ic.json_novo(pasta / "resumo_treino.json", {
        "modelo": "parameter_sharing_c5", "episodios": episodios,
        "tempo_desta_execucao_s": round(time.perf_counter() - inicio, 1),
        "tempo_medio_por_episodio_s": round(sum(l["duracao_real_s"] for l in linhas) / len(linhas), 1),
        "episodios_invalidos": sum(not l["valido"] for l in linhas), "decisoes_da_rede": rede.decisoes,
        "gradientes": rede.gradientes, "transicoes_por_agente": rede.transicoes_por_agente,
        "transicoes_total": rede.transicoes})
    return pasta


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--semente", type=int, required=True)
    ap.add_argument("--pasta", required=True)
    ap.add_argument("--episodios", type=int, default=150)
    ap.add_argument("--checkpoint-cada", type=int, default=25)
    a = ap.parse_args()
    tr.preparar_demandas_treino()
    treinar(a.semente, a.pasta, a.episodios, a.checkpoint_cada)


if __name__ == "__main__":
    main()
