"""
Assiste a um controlador comandando o semaforo, ao vivo, no SUMO-GUI.

Nao ha logica de simulacao nova aqui: a rodada e a MESMA simulacao.rodar
usada na avaliacao (dinamica C: amarelo de 3 s + vermelho geral de 2 s e
regra de seguranca do verde maximo). A unica diferenca e que, em vez do
"sumo" sem janela, o comando abre o "sumo-gui" pelo TraCI. Por isso, com a
mesma semente, as metricas no fim sao identicas as de
resultados/comparacao_C/avaliacao.json.

Os pesos das redes so sao LIDOS (agente em modo avaliacao: sem exploracao,
sem memoria, sem gradiente). Nada e gravado em modelos/ nem em resultados/.

Uso (de dentro de scripts/):
  python visualizar_dqn.py                          # DQN C seed0, cenario pico
  python visualizar_dqn.py --modelo dqn_fila_C_seed1.pt --cenario saturado
  python visualizar_dqn.py --controlador webster --cenario pico
  python visualizar_dqn.py --controlador max-pressure --velocidade 10
  python visualizar_dqn.py --listar

Velocidade: --velocidade 1 = tempo real, 10 = dez vezes mais rapido,
0 = o mais rapido possivel. Durante a rodada da para deixar ainda mais
lento no campo "Delay" da barra do SUMO-GUI (ms extras por segundo
simulado) e pausar/continuar no botao de pause/play.
"""

import argparse
import os
import sys
import time

import traci

import gerar_demanda
import simulacao
from simulacao import APROXIMACOES, DINAMICAS

CENARIOS = ["equilibrado", "assimetrico", "pico", "saturado", "girado"]

# apelido na linha de comando -> rotulo usado na avaliacao (avaliar_C.py)
CONTROLADORES = {
    "dqn": None,  # usa --modelo
    "webster": "Webster",
    "max-pressure": "Max-Pressure",
    "max-pressure-teto": "Max-Pressure teto",
    "max-pressure-recal": "Max-Pressure (recal. C)",
    "max-pressure-teto-recal": "Max-Pressure teto (recal. C)",
}
NOME_FASE = {"N": "Norte", "L": "Leste", "S": "Sul", "O": "Oeste"}


def _sumo_gui():
    """Caminho do sumo-gui (SUMO_HOME/bin ou o PATH)."""
    casa = os.environ.get("SUMO_HOME")
    if casa:
        for nome in ("sumo-gui.exe", "sumo-gui"):
            caminho = os.path.join(casa, "bin", nome)
            if os.path.exists(caminho):
                return caminho
    return "sumo-gui"


class TraciComJanela:
    """Faz simulacao.rodar abrir o sumo-gui no lugar do sumo.

    Repassa tudo ao traci; so troca o executavel no start e acrescenta as
    opcoes da janela. Os demais argumentos (rede, rotas, semente, sem
    teletransporte...) sao os mesmos da avaliacao.
    """

    def __init__(self, opcoes_janela):
        self._opcoes = opcoes_janela

    def start(self, comando):
        assert comando[0] == "sumo"
        traci.start([_sumo_gui()] + comando[1:] + self._opcoes)

    def __getattr__(self, nome):
        return getattr(traci, nome)


class Interrompido(Exception):
    pass


class Painel:
    """Instrumentacao de simulacao.rodar: so OBSERVA (nao muda nada).

    Ajusta a camera e a velocidade da janela e escreve no terminal cada
    decisao: fase verde, tempo de verde, filas e o que o controlador fez.
    """

    def __init__(self, atraso_ms, inicio, parar_em, silencioso, agente=None):
        self.atraso_s = atraso_ms / 1000.0
        self._proximo = None  # quando liberar o proximo segundo simulado
        self.inicio_s = inicio
        self.parar_em = parar_em
        self.silencioso = silencioso
        self.agente = agente  # para mostrar os valores Q da DQN
        self.duracao = None
        self.trocas = 0
        self.intervencoes = 0
        self._intervencao_agora = None

    # --- ganchos de simulacao.rodar ----------------------------------------
    def inicio(self, estados_verdes, duracao):
        self.duracao = duracao
        vista = traci.gui.DEFAULT_VIEW
        try:
            traci.gui.setSchema(vista, "real world")
        except traci.TraCIException:
            pass  # esquema inexistente nesta versao do SUMO: fica o padrao
        traci.gui.setOffset(vista, 250, 250)  # centro do cruzamento
        traci.gui.setZoom(vista, 350)
        if not self.silencioso:
            print(f"{'tempo':>7} | {'verde':6} {'ha':>4} | "
                  + " ".join(f"{a:>3}" for a in APROXIMACOES)
                  + " (filas) | decisao", flush=True)

    def passo(self, segundo, estado):
        # ritmo da janela: cada segundo simulado leva atraso_s de relogio
        # (antes de --inicio, roda o mais rapido possivel)
        if self.atraso_s > 0 and segundo >= self.inicio_s:
            agora = time.perf_counter()
            if self._proximo is not None and self._proximo > agora:
                time.sleep(self._proximo - agora)
            self._proximo = max(self._proximo or 0.0, agora) + self.atraso_s
        if self.parar_em is not None and segundo >= self.parar_em:
            raise Interrompido()

    def fim(self, caminho_tripinfo):
        pass

    def intervencao(self, obs, pedido, escolha):
        self.intervencoes += 1
        self._intervencao_agora = APROXIMACOES[pedido]

    def decisao(self, obs, escolha):
        nova = APROXIMACOES[escolha]
        troca = nova != obs.aprox_verde
        self.trocas += troca
        pedido, self._intervencao_agora = self._intervencao_agora, None
        if self.silencioso or obs.segundo < self.inicio_s:
            return
        m, s = divmod(obs.segundo, 60)
        fase = "escoam." if obs.segundo >= self.duracao else f"{m:02d}:{s:02d}"
        acao = f"TROCA -> {NOME_FASE[nova]}" if troca else "mantem"
        if pedido is not None:
            acao += f"  [REGRA DE SEGURANCA: pediu {NOME_FASE[pedido]}]"
        q = ""
        if self.agente is not None:
            import torch
            from dqn import estado_para_vetor
            with torch.no_grad():
                valores = self.agente.rede(
                    torch.from_numpy(estado_para_vetor(obs)).unsqueeze(0))[0]
            q = "  Q: " + " ".join(f"{a}={v:+.2f}" for a, v in zip(APROXIMACOES, valores.tolist()))
        print(f"{fase:>7} | {NOME_FASE[obs.aprox_verde]:6} {obs.tempo_no_verde:>3}s | "
              + " ".join(f"{obs.filas[a]:>3}" for a in APROXIMACOES)
              + f"         | {acao}{q}", flush=True)


def fabricar(apelido, modelo):
    if apelido == "dqn":
        from dqn import AgenteDQN
        nome = modelo[:-3] if modelo.endswith(".pt") else modelo
        caminho = os.path.join(simulacao.PASTA, "modelos", f"{nome}.pt")
        if not os.path.exists(caminho):
            sys.exit(f"Modelo nao encontrado: {caminho}  (veja --listar)")
        agente = AgenteDQN(treinando=False).carregar(nome)  # so leitura
        agente.rede.eval()
        return agente, f"DQN ({nome}.pt)"
    import avaliar_C  # mesmos controladores (e ajustes) da avaliacao na dinamica C
    rotulo = CONTROLADORES[apelido]
    return avaliar_C.fabricar(rotulo), rotulo


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--controlador", choices=list(CONTROLADORES), default="dqn")
    ap.add_argument("--modelo", default="dqn_fila_C_seed0",
                    help="arquivo em modelos/ (com ou sem .pt); so para --controlador dqn")
    ap.add_argument("--cenario", choices=CENARIOS, default="pico")
    ap.add_argument("--semente", type=int, default=1,
                    help="sorteio dos carros (1-10 = sementes de teste da avaliacao)")
    ap.add_argument("--velocidade", type=float, default=5,
                    help="x tempo real (1 = tempo real; 0 = maximo)")
    ap.add_argument("--inicio", type=int, default=0,
                    help="avanca em velocidade maxima ate este segundo (ex.: 1200 = minuto 20)")
    ap.add_argument("--parar-em", type=int, default=None,
                    help="encerra a rodada neste segundo (padrao: vai ate o fim do escoamento)")
    ap.add_argument("--silencioso", action="store_true", help="nao escreve as decisoes no terminal")
    ap.add_argument("--sem-q", action="store_true", help="nao mostra os valores Q da DQN")
    ap.add_argument("--manter-aberto", action="store_true",
                    help="nao fecha a janela no fim (feche-a para encerrar o programa)")
    ap.add_argument("--listar", action="store_true", help="lista modelos e controladores e sai")
    args = ap.parse_args(argv)

    if args.listar:
        pasta = os.path.join(simulacao.PASTA, "modelos")
        print("Modelos (--controlador dqn --modelo <arquivo>):")
        for f in sorted(os.listdir(pasta)):
            if f.endswith(".pt"):
                print("  ", f)
        print("Controladores:", ", ".join(CONTROLADORES))
        print("Cenarios:", ", ".join(CENARIOS))
        return None

    ctrl, rotulo = fabricar(args.controlador, args.modelo)
    atraso = 0 if args.velocidade <= 0 else int(round(1000 / args.velocidade))
    # o ritmo e controlado pelo Painel; o "Delay" da janela comeca em 0 e pode
    # ser aumentado na hora para deixar ainda mais lento
    opcoes = ["--start", "--window-size", "1100,850", "--delay", "0"]
    if not args.manter_aberto:
        opcoes.append("--quit-on-end")

    painel = Painel(atraso, args.inicio, args.parar_em, args.silencioso,
                    agente=ctrl if args.controlador == "dqn" and not args.sem_q else None)
    rotas = gerar_demanda.gerar(args.cenario)  # mesmo arquivo de sempre
    print(f"Controlador: {rotulo} | cenario: {args.cenario} | semente: {args.semente} | "
          f"dinamica {DINAMICAS['C'].nome} | velocidade: "
          f"{'maxima' if atraso == 0 else f'{args.velocidade:g}x'}", flush=True)

    original = simulacao.trafego
    simulacao.trafego = TraciComJanela(opcoes)
    tmp = os.path.join(simulacao.PASTA, "resultados", f"_tmp_tripinfo_{os.getpid()}.xml")
    m = None
    try:
        m = simulacao.rodar(ctrl, args.cenario, rotas, seed=args.semente,
                            instrumentacao=painel, dinamica=DINAMICAS["C"])
    except Interrompido:
        print(f"\nRodada encerrada no segundo {args.parar_em} (--parar-em).")
    except (traci.FatalTraCIError, traci.TraCIException, ConnectionError):
        print("\nJanela do SUMO-GUI fechada: rodada interrompida.")
    finally:
        simulacao.trafego = original
        try:
            traci.close()
        except Exception:
            pass
        if os.path.exists(tmp):  # tripinfo temporario de rodada interrompida
            os.remove(tmp)

    print(f"\nTrocas de fase: {painel.trocas} | intervencoes da regra de seguranca: "
          f"{painel.intervencoes}")
    if m is not None:
        print(f"Espera media: {m['espera_media']:.1f} s | P95: {m['espera_p95']:.0f} s | "
              f"maxima: {m['espera_max']:.0f} s | carros: {m['n_carros']} | "
              f"escoamento: {m['segundos_escoamento']} s | "
              f"maior verde executado: {m['verde_max_executado_total']} s")
    return m


if __name__ == "__main__":
    main()
