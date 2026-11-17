"""VERSAO 2 (otimizacao final): igual a ../treinar_marl_insper.py, mais a CONFIG experimental
(verde_minimo, colisao, supervisor_s), gravada na configuracao e em cada checkpoint.
Checkpoints da v1 sao carregados com CONFIG_V1.

Treino curto dos modelos Multi-Agent no corredor Insper (cenario intenso).

  independente  3 Double DQN locais, orientacao fixa "equilibrado" (sem supervisor)
  hierarquico   3 Double DQN locais + supervisor (Double DQN 48 -> 4), como no Cologne8

Os dois modelos usam as mesmas sementes de inicializacao local, a mesma
sequencia de demandas de treino, o mesmo numero de episodios e os mesmos
hiperparametros locais (agente_marl_cologne.DoubleDQN). O supervisor usa os
hiperparametros de supervisor do Cologne8 (decaimento de epsilon em 10 mil decisoes).

uso:
    python -B -X utf8 semaforo/integracao_insper/treinar_marl_insper.py --modelo hierarquico --episodios 10 --semente 1
"""

import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import insper_comum as ic  # noqa: E402
import ambiente_marl_insper_v2 as amb  # noqa: E402

DEMANDAS_TREINO = ic.SEMAFORO / "cenarios" / "insper_demanda" / "intenso_treino"
SEMENTES_TREINO = list(range(1001, 1031))  # 30 demandas; avaliacao usa 211-215 (intenso validado)


def cfg_treino(semente):
    cfg = DEMANDAS_TREINO / f"semente_{semente}" / "cenario.sumocfg"
    if not cfg.exists():
        raise FileNotFoundError(f"{cfg}: gere com preparar_demandas_treino()")
    return cfg


def preparar_demandas_treino(sementes=SEMENTES_TREINO, processos=10):
    """Gera as demandas de treino (mesmo metodo e volume do nivel intenso, sementes proprias)."""
    from concurrent.futures import ProcessPoolExecutor
    faltam = [s for s in sementes if not (DEMANDAS_TREINO / f"semente_{s}").exists()]
    with ProcessPoolExecutor(processos) as ex:
        list(ex.map(_gerar_um, faltam))
    return len(faltam)


def _gerar_um(s):
    import gerar_demanda_insper as gd
    gd.gerar("intenso_treino", 2000, s, 12.0)


def salvar(path, agentes, modelo, semente, episodio, completo, config):
    import torch
    with Path(path).open("xb") as f:
        torch.save({"formato": amb.FORMATO, "config": config, "modelo": modelo, "semente_modelo": semente,
                    "episodio": episodio,
                    "completo_para_retomada": completo, "agentes": [a.estado(completo) for a in agentes]}, f)


def carregar(path, modelo=None):
    import torch
    d = torch.load(path, map_location="cpu", weights_only=False)
    if d["formato"] not in (amb.FORMATO, amb.FORMATO_V1) or (modelo and d["modelo"] != modelo):
        raise ValueError("checkpoint de outro formato/modelo")
    d["config"] = dict(amb.CONFIG_V1, **d.get("config", {}))
    agentes = amb.criar_agentes(d["modelo"], d["semente_modelo"])
    for a, e in zip(agentes, d["agentes"], strict=True):
        a.carregar(e, completo=d["completo_para_retomada"])
    return d, agentes


def treinar(modelo, episodios, semente, pasta, checkpoint_cada=25, porta=None, config=None):
    """Retomavel: se existir retomada.pt (checkpoint completo), continua do episodio seguinte."""
    import os
    import shutil
    import torch
    torch.set_num_threads(1)
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    config = dict(amb.CONFIG_V1, **(config or {}))
    agentes = amb.criar_agentes(modelo, semente)
    historico = pasta / "historico.jsonl"
    inicial = 0
    if (pasta / "retomada.pt").exists():
        d, agentes = carregar(pasta / "retomada.pt", modelo)
        if d["semente_modelo"] != semente or not d["completo_para_retomada"] or d["config"] != config:
            raise ValueError("retomada.pt de outro treino")
        inicial = d["episodio"]
        linhas = historico.read_text(encoding="utf-8").splitlines()[:inicial] if historico.exists() else []
        historico.write_text("".join(l + "\n" for l in linhas), encoding="utf-8")
        descartados = pasta / "episodios" / f"_descartados_retomada_ep{inicial:04d}"
        for p in sorted((pasta / "episodios").glob("ep*")):
            if int(p.name[2:]) > inicial:
                descartados.mkdir(parents=True, exist_ok=True)
                shutil.move(str(p), str(descartados / p.name))
        with (pasta / "retomadas.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"retomado_do_episodio": inicial, "hora": time.strftime("%Y-%m-%dT%H:%M:%S")}) + "\n")
        print(f"retomando {modelo} s{semente} do episodio {inicial}", flush=True)
    if not (pasta / "configuracao.json").exists():
        ic.json_novo(pasta / "configuracao.json", {
        "formato": amb.FORMATO, "config": config, "modelo": modelo, "semente_modelo": semente,
        "episodios": episodios,
        "sementes_trafego": [SEMENTES_TREINO[e % len(SEMENTES_TREINO)] for e in range(episodios)],
        "recompensa": amb.RECOMPENSA, "travamento": amb.TRAVAMENTO, "escalas_rede": amb.ESCALAS_REDE,
        "tempos": ic.TEMPOS, "aquecimento_s": amb.AQUECIMENTO,
        "hiperparametros": [{k: v for k, v in a.estado().items() if k not in ("rede",)} for a in agentes]})
    inicio = time.perf_counter()
    for ep in range(inicial + 1, episodios + 1):
        s = SEMENTES_TREINO[(ep - 1) % len(SEMENTES_TREINO)]
        m = amb.rodar_episodio(cfg_treino(s), pasta / "episodios" / f"ep{ep:04d}", s, agentes, modelo,
                               treinando=True, rotulo=f"{modelo}_{semente}_{ep}", porta=porta, config=config)
        linha = {"episodio": ep, "semente_trafego": s, "valido": m["valido"], "motivo_invalido": m["motivo_invalido"],
                 "duracao_real_s": m["duracao_real_s"], "fracao_concluida": m["fracao_concluida"],
                 "espera_corredor_media": m["espera_corredor_s"].get("media"),
                 "espera_rede_media": m["espera_rede_s"].get("media"), "teleportes": m["teleportes"]["total"],
                 "colisoes": m["colisoes"]["eventos"], "recompensas": m["recompensas"],
                 "epsilon": [round(a.epsilon, 4) for a in agentes], "gradientes": [a.gradientes for a in agentes],
                 "perda_media": [round(sum(a.perdas) / len(a.perdas), 5) if a.perdas else None for a in agentes],
                 "intervencoes": m["intervencoes_verde_maximo"]}
        with historico.open("a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
        print(f"{modelo} s{semente} ep{ep} trafego {s}: {m['duracao_real_s']} s, valido={m['valido']}, "
              f"espera corredor {linha['espera_corredor_media']}, tele {linha['teleportes']}, "
              f"eps {linha['epsilon'][0]}, grad {linha['gradientes'][0]}", flush=True)
        if ep % checkpoint_cada == 0 or ep == episodios:
            alvo = pasta / f"politica_ep{ep:04d}.pt"
            if not alvo.exists():
                salvar(alvo, agentes, modelo, semente, ep, completo=False, config=config)
            tmp = pasta / "retomada.tmp"
            tmp.unlink(missing_ok=True)
            salvar(tmp, agentes, modelo, semente, ep, completo=True, config=config)
            os.replace(tmp, pasta / "retomada.pt")
    total = time.perf_counter() - inicio
    durs = [json.loads(l)["duracao_real_s"] for l in historico.read_text(encoding="utf-8").splitlines()]
    ic.json_novo(pasta / "resumo_treino.json", {"modelo": modelo, "episodios": episodios,
                                                "episodios_nesta_execucao": episodios - inicial,
                                                "tempo_desta_execucao_s": round(total, 1),
                                                "soma_duracao_episodios_s": round(sum(durs), 1),
                                                "tempo_medio_por_episodio_s": round(sum(durs) / len(durs), 1),
                                                "episodios_invalidos": sum(not json.loads(l)["valido"] for l in
                                                                           historico.read_text(encoding="utf-8").splitlines())})
    return pasta


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--modelo", choices=["independente", "hierarquico"], required=True)
    ap.add_argument("--episodios", type=int, required=True)
    ap.add_argument("--semente", type=int, default=1)
    ap.add_argument("--checkpoint-cada", type=int, default=25)
    ap.add_argument("--pasta")
    ap.add_argument("--verde-minimo", type=int, default=10)
    ap.add_argument("--colisao", choices=["global", "atribuida"], default="global")
    ap.add_argument("--supervisor-s", type=int, default=30)
    args = ap.parse_args()
    preparar_demandas_treino()
    pasta = Path(args.pasta) if args.pasta else ic.nova_pasta(f"treino_{args.modelo}_s{args.semente}")
    treinar(args.modelo, args.episodios, args.semente, pasta, args.checkpoint_cada,
            config={"verde_minimo": args.verde_minimo, "colisao": args.colisao, "supervisor_s": args.supervisor_s})
    print("treino salvo em", pasta)


if __name__ == "__main__":
    main()
