"""Demonstração visual no SUMO-GUI: tempo fixo x rede que copia x MARL, lado a lado.

Abre uma janela do SUMO-GUI por controlador, todas com o MESMO trânsito
(mesma semente). As janelas avançam rápido até o pico de congestionamento,
esperam você apertar Enter e então rodam juntas, sincronizadas pelo relógio.

Cores dos carros (tempo total parado na viagem até agora):
  verde < 5 s | amarelo 5–30 s | laranja 30–60 s | vermelho >= 60 s

Uso no Windows (PowerShell, na raiz do repositório):
  & '.venv-dqn-inferencia/Scripts/python.exe' -B -X utf8 semaforo/scripts/demo_visual_cologne8.py `
      --sumo-home '../tools/sumo-win64-1.28.0'

Os controladores e o executor são os mesmos do experimento
RESULTADOS_COMPARADORES_COLOGNE8.md; só a exibição é nova.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
os.environ.setdefault("SMARTFLOW_PROJETO", str(AQUI.parent))
PROJETO = Path(os.environ["SMARTFLOW_PROJETO"]).resolve()

RODADA_MARL = PROJETO / "resultados/marl_cologne8/20261113T011843Z_continuo_10seeds_9f8d757b"
# Modelos escolhidos pela regra de validação (não pelo teste): MARL seed 0 teve a melhor
# pontuação de validação entre as 10; na rede que copia, a seed 2.
MARL_CHECKPOINT = RODADA_MARL / "modelo_seed0" / "politica_ep0375.pt"
COPIA_PESOS = PROJETO / "resultados/comparadores_cologne8/modelos/imitacao_seed2/mlps_numpy.npz"

TITULOS = {"fixo": "TEMPO FIXO (programa original)", "copia": "REDE QUE COPIA (supervisionada)",
           "marl": "MARL (aprendizado por reforço)"}
CORES = [(5, (0, 190, 0, 255)), (30, (255, 210, 0, 255)), (60, (255, 130, 0, 255)), (float("inf"), (220, 0, 0, 255))]


def sumo_home_padrao():
    if os.environ.get("SUMO_HOME"):
        return Path(os.environ["SUMO_HOME"])
    return PROJETO.parent.parent / "tools" / "sumo-win64-1.28.0"


# ------------------------------------------------------------------ processo filho (uma janela)
def criar_agentes(nome, manifesto):
    C = manifesto["controladores"]
    if nome == "fixo":
        import comparadores_cologne8 as cc
        return [cc.Base(s) for s in C] + [None], "original_fixo"
    if nome == "copia":
        import comparadores_cologne8 as cc
        mlps = cc.carregar_imitacao_numpy(COPIA_PESOS, C)
        return [cc.Imitacao(s, modelo=m) for s, m in zip(C, mlps)] + [None], cc.MODO
    if nome == "marl":
        import torch
        from treinar_marl_cologne import criar_agentes as criar_marl
        torch.set_num_threads(1)
        d = torch.load(MARL_CHECKPOINT, map_location="cpu", weights_only=True)

        def normalizar(x):  # o mesmo manifesto gerado no Windows ou no Linux muda só a barra dos caminhos
            return json.loads(json.dumps(x).replace("\\\\", "/"))
        if d["formato"] != manifesto["formato"] or normalizar(d["manifesto"]) != normalizar(manifesto):
            raise ValueError("O checkpoint do MARL foi treinado com outro protocolo ou cenário")
        agentes = criar_marl(manifesto, d["semente_modelo"])
        for a, dados in zip(agentes, d["agentes"], strict=True):
            a.carregar(dados, False)
        return agentes, "hierarquico"
    raise ValueError(nome)


class FimDemo(Exception):
    pass


def filho(a):
    from ambiente_marl_cologne import construir_manifesto, rodar
    barreira = Path(a.barreira)
    manifesto = construir_manifesto("cologne8", continuar_apos_colisao=True)
    agentes, modo = criar_agentes(a.filho, manifesto)

    if a.sem_gui:
        import libsumo as conn
    else:
        import traci as conn
    import traci.constants as tc

    largura = a.largura_tela // a.total
    config = Path(tempfile.mkdtemp(prefix="demo_gui_")) / "visual.xml"
    no = manifesto_no(a.cruzamento)
    config.write_text(
        '<viewsettings>\n  <scheme name="standard"/>\n  <delay value="0"/>\n'
        f'  <viewport zoom="{a.zoom}" x="{no[0]:.1f}" y="{no[1]:.1f}"/>\n</viewsettings>\n', encoding="utf-8")

    iniciar_original, passo_original = conn.start, conn.simulationStep

    def iniciar(cmd, *args, **kw):
        if not a.sem_gui:
            cmd = list(cmd) + ["--gui-settings-file", str(config),
                               "--window-size", f"{largura},{a.altura_tela - 80}",
                               "--window-pos", f"{a.posicao * largura},0"]
        return iniciar_original(cmd, *args, **kw)

    estado = {"cor": {}, "pronto": False, "t0": None, "ultimo_log": 0}

    def colorir():
        for vid, v in conn.vehicle.getAllSubscriptionResults().items():
            espera = v.get(tc.VAR_ACCUMULATED_WAITING_TIME)
            if espera is None:
                continue
            faixa = next(i for i, (lim, _) in enumerate(CORES) if espera < lim)
            if estado["cor"].get(vid) != faixa:
                conn.vehicle.setColor(vid, CORES[faixa][1])
                estado["cor"][vid] = faixa

    def passo(*args, **kw):
        r = passo_original(*args, **kw)
        t = conn.simulation.getTime()
        colorir()
        if t >= a.inicio and not estado["pronto"]:
            estado["pronto"] = True
            (barreira / f"pronto_{a.filho}").write_text(str(t), encoding="utf-8")
            while not (barreira / "comecar").exists():
                time.sleep(0.05)
            estado["t0"] = float((barreira / "comecar").read_text(encoding="utf-8"))
        if estado["t0"] is not None:
            alvo = estado["t0"] + (t - a.inicio) * a.atraso / 1000.0
            folga = alvo - time.time()
            if folga > 0:
                time.sleep(folga)
            if t - estado["ultimo_log"] >= 60:
                parados = sum(1 for v in conn.vehicle.getAllSubscriptionResults().values()
                              if v.get(tc.VAR_SPEED, 1.0) < 0.1)
                print(f"[{a.filho:>5}] minuto {(t - 25200) / 60:4.1f}: {parados} carros parados", flush=True)
                estado["ultimo_log"] = t
        if a.fim and t >= a.fim:
            (barreira / f"fim_{a.filho}").write_text(str(t), encoding="utf-8")
            while not (barreira / "encerrar").exists():
                time.sleep(0.1)
            raise FimDemo()
        return r

    conn.start, conn.simulationStep = iniciar, passo
    pasta = Path(tempfile.mkdtemp(prefix=f"demo_{a.filho}_")) / "rodada"
    try:
        rodar(manifesto, agentes, pasta, a.semente, treinando=False, duracao=3600, escoamento=1200,
              backend="libsumo" if a.sem_gui else "traci", sumo_home=None if a.sem_gui else a.sumo_home,
              gui=not a.sem_gui, modo=modo)
    except FimDemo:
        pass
    except Exception as e:  # janela fechada à mão no meio da demonstração
        if estado["t0"] is None and not estado["pronto"]:
            raise
        print(f"[{a.filho}] encerrado: {type(e).__name__}", flush=True)
    finally:
        for nome in (f"pronto_{a.filho}", f"fim_{a.filho}"):
            if not (barreira / nome).exists():
                (barreira / nome).write_text("encerrado", encoding="utf-8")
        try:
            conn.close()
        except Exception:
            pass


def manifesto_no(no_id):
    import sumolib
    net = PROJETO / "referencias/cologne8_sumo_rl_1.4.5/sumo_rl/nets/RESCO/cologne8/cologne8.net.xml"
    return sumolib.net.readNet(str(net)).getNode(no_id).getCoord()


# ------------------------------------------------------------------ lançador
def esperar(barreira, prefixo, nomes, processos):
    while not all((barreira / f"{prefixo}_{n}").exists() for n in nomes):
        if any(p.poll() not in (None, 0) for p in processos):
            raise SystemExit("Uma das janelas terminou com erro; veja as mensagens acima.")
        time.sleep(0.2)


def principal(a):
    if not a.sem_gui:
        a.sumo_home = str(Path(a.sumo_home or sumo_home_padrao()).resolve())
        gui = Path(a.sumo_home) / "bin" / "sumo-gui.exe"
        if not gui.exists():
            raise SystemExit(f"Não encontrei {gui}. Passe --sumo-home com a pasta do SUMO 1.28.0.")
    barreira = Path(tempfile.mkdtemp(prefix="demo_barreira_"))
    print("Janelas, da esquerda para a direita:")
    for i, n in enumerate(a.controladores):
        print(f"  {i + 1}. {TITULOS[n]}")
    print(f"Mesmo trânsito em todas (semente {a.semente}). Avançando até o minuto "
          f"{(a.inicio - 25200) / 60:.0f}, o começo do pico...")
    processos = []
    for i, n in enumerate(a.controladores):
        cmd = [sys.executable, "-B", "-X", "utf8", __file__, "--filho", n, "--barreira", str(barreira),
               "--posicao", str(i), "--total", str(len(a.controladores)), "--semente", str(a.semente),
               "--inicio", str(a.inicio), "--fim", str(a.fim), "--atraso", str(a.atraso),
               "--cruzamento", a.cruzamento, "--zoom", str(a.zoom),
               "--largura-tela", str(a.largura_tela), "--altura-tela", str(a.altura_tela)]
        cmd += ["--sem-gui"] if a.sem_gui else ["--sumo-home", a.sumo_home]
        processos.append(subprocess.Popen(cmd))
    try:
        esperar(barreira, "pronto", a.controladores, processos)
        if not a.sem_esperar:
            input("\nTudo pronto. Comece a gravar a tela e aperte Enter para iniciar a demonstração... ")
        (barreira / "comecar").write_text(str(time.time() + 1.0), encoding="utf-8")
        print(f"Rodando do minuto {(a.inicio - 25200) / 60:.0f} ao {(a.fim - 25200) / 60:.0f} "
              f"({a.atraso} ms por segundo simulado).")
        esperar(barreira, "fim", a.controladores, processos)
        if not a.sem_esperar:
            input("\nFim da demonstração. As janelas ficam paradas no último instante. "
                  "Aperte Enter para fechá-las... ")
        (barreira / "encerrar").write_text("1", encoding="utf-8")
        for p in processos:
            p.wait(timeout=60)
    finally:
        for p in processos:
            if p.poll() is None:
                p.terminate()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--controladores", nargs="+", default=["fixo", "copia", "marl"], choices=list(TITULOS))
    ap.add_argument("--semente", type=int, default=1, help="semente de trânsito (teste: 1 a 10)")
    ap.add_argument("--sumo-home", default=None, help="pasta do SUMO 1.28.0 (padrão: ../tools/sumo-win64-1.28.0)")
    ap.add_argument("--inicio", type=float, default=25800, help="tempo SUMO onde a demonstração começa (25800 = minuto 10)")
    ap.add_argument("--fim", type=float, default=26700, help="tempo SUMO onde ela termina (26700 = minuto 25)")
    ap.add_argument("--atraso", type=float, default=100, help="ms reais por segundo simulado (100 = 10x mais rápido)")
    ap.add_argument("--cruzamento", default="26110729", help="cruzamento no centro da tela")
    ap.add_argument("--zoom", type=float, default=700)
    ap.add_argument("--largura-tela", type=int, default=1920)
    ap.add_argument("--altura-tela", type=int, default=1080)
    ap.add_argument("--sem-esperar", action="store_true", help="não pede Enter (para testes)")
    ap.add_argument("--sem-gui", action="store_true", help="roda sem janelas, com libsumo (para testes)")
    ap.add_argument("--filho", choices=list(TITULOS), help=argparse.SUPPRESS)
    ap.add_argument("--barreira", help=argparse.SUPPRESS)
    ap.add_argument("--posicao", type=int, default=0, help=argparse.SUPPRESS)
    ap.add_argument("--total", type=int, default=1, help=argparse.SUPPRESS)
    a = ap.parse_args()
    filho(a) if a.filho else principal(a)
