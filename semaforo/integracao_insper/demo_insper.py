"""Demonstracao no SUMO-GUI do corredor Insper (um episodio, sem treino).

Usa o ambiente da otimizacao final (otimizacao_final/ambiente_marl_insper_v2.py) e os
checkpoints de modelos_finais/ (manifesto.json). Toda saida vai para uma pasta nova em
integracao_insper/resultados/<data>_demo_<controle>/.

uso (na raiz do repositorio, SUMO 1.28 com SUMO_HOME definido):
  python -B -X utf8 semaforo/integracao_insper/demo_insper.py --controle original
  python -B -X utf8 semaforo/integracao_insper/demo_insper.py --controle A_col --modelo 1
  python -B -X utf8 semaforo/integracao_insper/demo_insper.py --controle B_col_s15 --modelo 1 --semente 242
  python -B -X utf8 semaforo/integracao_insper/demo_insper.py --controle A_col --sem-gui --limite 900   (verificacao rapida)

--controle: original | atuado_equivalente | <braco de modelos_finais> (A_col, B_col_s15, ...) | C | C_transf.
Demanda: intenso_teste_final (sementes 241-250) por padrao; e trafego SINTETICO calibrado.
"""

import argparse
import json
from pathlib import Path
import sys

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI / "otimizacao_final"))
import insper_comum as ic  # noqa: E402

RAIZ = AQUI.parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--controle", default="original")
    ap.add_argument("--modelo", default="1", help="semente do modelo (1-5) para os bracos de RL")
    ap.add_argument("--semente", type=int, default=241, help="semente da demanda")
    ap.add_argument("--nivel", default="intenso_teste_final")
    ap.add_argument("--limite", type=int, default=None, help="fim da simulacao em s (padrao: ate esvaziar, max 5400)")
    ap.add_argument("--sem-gui", action="store_true")
    ap.add_argument("--atraso", type=int, default=50, help="atraso do sumo-gui em ms por passo")
    args = ap.parse_args()

    import torch
    torch.set_num_threads(1)
    import traci
    import ambiente_marl_insper_v2 as amb
    import treinar_marl_insper_v2 as tr

    agentes, config = None, {}
    if args.controle in ("original", "atuado_equivalente"):
        modo = args.controle
    elif args.controle in ("C", "C_transf"):  # Modelo C (parameter sharing)
        sys.path.insert(0, str(AQUI / "parameter_sharing"))
        import politica_compartilhada as pc
        man = json.loads((AQUI / "parameter_sharing" / "modelos_finais" / "manifesto.json").read_text(encoding="utf-8"))
        item = man["bracos"][args.controle]["sementes_modelo"][args.modelo]
        d, rede = pc.carregar(RAIZ / item["arquivo"])
        agentes, modo, config = pc.visoes_avaliacao(rede), "independente", d["config"]
        print(f"checkpoint {item['arquivo']} (parameter sharing, {config})")
    else:
        man = json.loads((AQUI / "modelos_finais" / "manifesto.json").read_text(encoding="utf-8"))
        item = man["bracos"][args.controle]["sementes_modelo"][args.modelo]
        d, agentes = tr.carregar(RAIZ / item["arquivo"])
        modo, config = d["modelo"], d["config"]
        print(f"checkpoint {item['arquivo']} ({modo}, {config})")
    if not args.sem_gui:
        iniciar = traci.start

        def iniciar_gui(cmd, *a, **k):
            exe = Path(cmd[0])
            gui = exe.with_name(exe.name.replace("sumo", "sumo-gui", 1))
            return iniciar([str(gui)] + list(cmd[1:]) + ["--start", "--delay", str(args.atraso)], *a, **k)
        traci.start = iniciar_gui
    cfg = ic.SEMAFORO / "cenarios" / "insper_demanda" / args.nivel / f"semente_{args.semente}" / "cenario.sumocfg"
    pasta = ic.nova_pasta(f"demo_{args.controle}")
    antes = ic.hashes_cenario()
    m = amb.rodar_episodio(cfg, pasta / "episodio", args.semente, agentes, modo, treinando=False,
                           limite=args.limite or amb.LIMITE, config=config)
    ic.conferir_cenario(antes)
    print(f"valido={m['valido']} espera media no corredor {m['espera_corredor_s'].get('media')} s, "
          f"rede {m['espera_rede_s'].get('media')} s, violacoes {m['seguranca']['violacoes']}, "
          f"colisoes {m['colisoes']['eventos']}, teletransportes {m['teleportes']['total']}; saida em {pasta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
