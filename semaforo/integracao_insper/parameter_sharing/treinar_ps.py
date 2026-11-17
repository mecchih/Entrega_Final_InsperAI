"""Treino do Modelo C (Parameter Sharing) no cenario intenso do Insper.

Mesmo laco do Modelo A (otimizacao_final/treinar_marl_insper_v2.py): mesmas demandas de treino
1001-1030 na mesma ordem, mesmo ambiente, mesma config (verde minimo 10 s, colisao atribuida),
150 episodios e checkpoint a cada 25. Muda so o agente: 3 visoes sobre UMA DoubleDQN.

uso:
  python -B -X utf8 semaforo/integracao_insper/parameter_sharing/treinar_ps.py --semente 1 --pasta <pasta>
  ... --aprendizes 0 2      (transferencia: o cruzamento 1, Casa do Ator, fica fora do treino)
"""

import argparse
import json
import os
from pathlib import Path
import sys
import time

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import politica_compartilhada as pc  # noqa: E402
import insper_comum as ic  # noqa: E402
import ambiente_marl_insper_v2 as amb  # noqa: E402
import treinar_marl_insper_v2 as tr  # noqa: E402

CONFIG = {"verde_minimo": 10, "colisao": "atribuida", "supervisor_s": 30}  # = Modelo A otimizado (A_col)


def treinar(semente, pasta, episodios=150, checkpoint_cada=25, aprendizes=(0, 1, 2)):
    import torch
    torch.set_num_threads(1)
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    config = dict(amb.CONFIG_V1, **CONFIG)
    orientacao = pc.orientacao_canonica()
    rede, agentes = pc.criar_agentes(semente, aprendizes, orientacao)
    historico = pasta / "historico.jsonl"
    inicial = 0
    if (pasta / "retomada.pt").exists():
        d, rede = pc.carregar(pasta / "retomada.pt")
        if d["semente_modelo"] != semente or d["aprendizes"] != list(aprendizes) or d["config"] != config:
            raise ValueError("retomada.pt de outro treino")
        _, agentes = pc.criar_agentes(semente, aprendizes, orientacao)
        for a in agentes:
            a.rede = rede
        inicial = d["episodio"]
        linhas = historico.read_text(encoding="utf-8").splitlines()[:inicial] if historico.exists() else []
        historico.write_text("".join(l + "\n" for l in linhas), encoding="utf-8")
        print(f"retomando s{semente} do episodio {inicial}", flush=True)
    if not (pasta / "configuracao.json").exists():
        ic.json_novo(pasta / "configuracao.json", {
            "formato": pc.FORMATO, "modelo": "parameter_sharing", "config": config, "semente_modelo": semente,
            "episodios": episodios, "aprendizes": [pc.TLS[k] for k in aprendizes],
            "fora_do_treino": [t for k, t in enumerate(pc.TLS) if k not in aprendizes],
            "controle_fora_do_treino": "regra_atuada_obs (classico, sem aprendizado)",
            "orientacao_permutada": orientacao,
            "sementes_trafego": [tr.SEMENTES_TREINO[e % len(tr.SEMENTES_TREINO)] for e in range(episodios)],
            "orcamento": {"replay": rede.memoria.capacidade, "aquecimento": rede.aquecimento,
                          "decaimento_epsilon": rede.decaimento, "gradiente_a_cada_transicoes": rede.n_aprendizes},
            "recompensa": amb.RECOMPENSA, "tempos": ic.TEMPOS})
    inicio = time.perf_counter()
    for ep in range(inicial + 1, episodios + 1):
        s = tr.SEMENTES_TREINO[(ep - 1) % len(tr.SEMENTES_TREINO)]
        antes_grad, antes_trans = rede.gradientes, list(rede.transicoes_por_agente)
        m = amb.rodar_episodio(tr.cfg_treino(s), pasta / "episodios" / f"ep{ep:04d}", s, agentes, "independente",
                               treinando=True, rotulo=f"ps_{semente}_{'' .join(map(str, aprendizes))}_{ep}",
                               config=config)
        linha = {"episodio": ep, "semente_trafego": s, "valido": m["valido"], "motivo_invalido": m["motivo_invalido"],
                 "duracao_real_s": m["duracao_real_s"], "fracao_concluida": m["fracao_concluida"],
                 "espera_corredor_media": m["espera_corredor_s"].get("media"),
                 "espera_rede_media": m["espera_rede_s"].get("media"), "teleportes": m["teleportes"]["total"],
                 "colisoes": m["colisoes"]["eventos"], "recompensas": m["recompensas"],
                 "epsilon": round(rede.epsilon, 4), "decisoes_rede": rede.decisoes, "gradientes": rede.gradientes,
                 "gradientes_no_episodio": rede.gradientes - antes_grad,
                 "transicoes_por_agente_no_episodio": [b - a for a, b in zip(antes_trans, rede.transicoes_por_agente)],
                 "replay": rede.memoria.n,
                 "perda_media": round(sum(rede.perdas) / len(rede.perdas), 5) if rede.perdas else None,
                 "intervencoes": m["intervencoes_verde_maximo"]}
        with historico.open("a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
        print(f"ps s{semente} ep{ep} trafego {s}: {m['duracao_real_s']} s, valido={m['valido']}, "
              f"corredor {linha['espera_corredor_media']}, eps {linha['epsilon']}, grad {rede.gradientes}, "
              f"replay {rede.memoria.n}", flush=True)
        if ep % checkpoint_cada == 0 or ep == episodios:
            alvo = pasta / f"politica_ep{ep:04d}.pt"
            if not alvo.exists():
                pc.salvar(alvo, rede, semente, ep, False, config, aprendizes)
            tmp = pasta / "retomada.tmp"
            tmp.unlink(missing_ok=True)
            pc.salvar(tmp, rede, semente, ep, True, config, aprendizes)
            os.replace(tmp, pasta / "retomada.pt")
    linhas = [json.loads(l) for l in historico.read_text(encoding="utf-8").splitlines()]
    ic.json_novo(pasta / "resumo_treino.json", {
        "modelo": "parameter_sharing", "aprendizes": [pc.TLS[k] for k in aprendizes], "episodios": episodios,
        "tempo_desta_execucao_s": round(time.perf_counter() - inicio, 1),
        "tempo_medio_por_episodio_s": round(sum(l["duracao_real_s"] for l in linhas) / len(linhas), 1),
        "episodios_invalidos": sum(not l["valido"] for l in linhas),
        "interacoes_com_simulador_episodios": len(linhas),
        "decisoes_da_rede": rede.decisoes, "gradientes": rede.gradientes,
        "transicoes_por_agente": rede.transicoes_por_agente, "transicoes_total": rede.transicoes})
    return pasta


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--semente", type=int, required=True)
    ap.add_argument("--pasta", required=True)
    ap.add_argument("--episodios", type=int, default=150)
    ap.add_argument("--checkpoint-cada", type=int, default=25)
    ap.add_argument("--aprendizes", type=int, nargs="+", default=[0, 1, 2])
    a = ap.parse_args()
    tr.preparar_demandas_treino()
    treinar(a.semente, a.pasta, a.episodios, a.checkpoint_cada, tuple(sorted(a.aprendizes)))


if __name__ == "__main__":
    main()
