"""
O motor do projeto.

Aqui mora a parte que nao muda: abrir o SUMO, perguntar ao controlador qual
aproximacao deve ficar verde, trocar as fases com seguranca (amarelo e
vermelho geral entre fases) e medir o resultado.

Qualquer controlador -- tempo fixo, Max-Pressure ou, mais pra frente, o DQN --
entra pelo mesmo encaixe. Isso e o que torna a comparacao justa: todos
enxergam a mesma coisa, decidem no mesmo ritmo e sao medidos do mesmo jeito.
"""

import os
import xml.etree.ElementTree as ET

# libsumo roda o simulador dentro do proprio Python: ~8x mais rapido que o
# traci normal. Em troca, nao abre a janela grafica -- o que e exatamente o
# que queremos durante os experimentos. Para gravar o video da apresentacao,
# e so rodar depois com o traci + sumo-gui.
try:
    import libsumo as trafego

    USANDO_LIBSUMO = True
except ImportError:  # pragma: no cover
    import traci as trafego

    USANDO_LIBSUMO = False


PASTA = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REDE = os.path.join(PASTA, "rede", "cruzamento.net.xml")

# Regras de seguranca do semaforo (iguais para todos os controladores)
AMARELO = 3  # segundos de amarelo ao trocar de fase
VERMELHO_GERAL = 2  # segundos com tudo vermelho, para limpar o cruzamento
VERDE_MINIMO = 10  # ninguem recebe verde por menos que isso
INTERVALO_DECISAO = 5  # de quantos em quantos segundos o controlador decide

# As quatro aproximacoes e as faixas de entrada de cada uma.
# A ordem e a mesma das fases verdes do semaforo gerado pelo netgenerate.
APROXIMACOES = ["N", "L", "S", "O"]
FAIXAS_ENTRADA = {
    "N": ["top0A0_0", "top0A0_1"],
    "L": ["right0A0_0", "right0A0_1"],
    "S": ["bottom0A0_0", "bottom0A0_1"],
    "O": ["left0A0_0", "left0A0_1"],
}
# Vias de saida, usadas pelo Max-Pressure para medir a fila do outro lado
VIAS_SAIDA = {
    "N": ["A0bottom0_0", "A0bottom0_1", "A0left0_0", "A0left0_1",
          "A0right0_0", "A0right0_1"],
    "L": ["A0left0_0", "A0left0_1", "A0top0_0", "A0top0_1",
          "A0bottom0_0", "A0bottom0_1"],
    "S": ["A0top0_0", "A0top0_1", "A0right0_0", "A0right0_1",
          "A0left0_0", "A0left0_1"],
    "O": ["A0right0_0", "A0right0_1", "A0bottom0_0", "A0bottom0_1",
          "A0top0_0", "A0top0_1"],
}
SEMAFORO = "A0"


class Observacao:
    """O que o controlador ve no momento de decidir.

    Importante: tudo aqui e informacao que um semaforo real conseguiria ter
    com sensores no asfalto. Nada de "espiar" o futuro.
    """

    def __init__(self, filas, carros, espera, aprox_verde, tempo_no_verde,
                 filas_saida, segundo, fila_acumulada=0.0, espera_acumulada=0.0):
        self.filas = filas  # carros parados por aproximacao
        self.carros = carros  # carros presentes por aproximacao
        self.espera = espera  # espera acumulada (s) por aproximacao
        self.aprox_verde = aprox_verde  # qual aproximacao esta com verde
        self.tempo_no_verde = tempo_no_verde  # ha quantos segundos
        self.filas_saida = filas_saida  # filas nas vias de saida
        self.segundo = segundo  # momento da simulacao
        # Soma de (carros parados) a cada segundo desde o inicio da rodada.
        # A diferenca entre duas decisoes = "carros x segundos de fila" no
        # intervalo. E isso que faz o agente SENTIR o custo de trocar de fase:
        # durante o amarelo e o vermelho geral ninguem anda, e a conta sobe.
        self.fila_acumulada = fila_acumulada
        self.espera_acumulada = espera_acumulada


class Controlador:
    """Molde de qualquer semaforo. So precisa responder uma pergunta:
    qual aproximacao deve ficar verde agora?"""

    nome = "generico"

    def preparar(self, cenario):
        """Chamado uma vez antes da simulacao (para calcular tempos, etc.)."""
        pass

    def decidir(self, obs):
        raise NotImplementedError

    def reiniciar(self):
        """Chamado no inicio de cada rodada."""
        pass


def _fases_verdes():
    """Descobre no semaforo quais fases sao de verde (e nao amarelo)."""
    logicas = trafego.trafficlight.getAllProgramLogics(SEMAFORO)
    fases = logicas[0].phases
    verdes, amarelas = [], []
    for i, fase in enumerate(fases):
        estado = fase.state
        if "y" in estado.lower():
            amarelas.append(i)
        elif "g" in estado.lower():
            verdes.append(i)
    return verdes, amarelas


def _estado_amarelo(estado_verde):
    """Transforma um estado de verde no amarelo correspondente."""
    return "".join("y" if c in "Gg" else c for c in estado_verde)


def _estado_tudo_vermelho(tamanho):
    return "r" * tamanho


def rodar(controlador, cenario, arquivo_rotas, seed, duracao=3600,
          guardar_serie=False):
    """Roda uma rodada completa e devolve as metricas.

    cenario: nome do cenario (usado pelo controlador para se preparar)
    seed: muda o sorteio de chegada dos carros -- rodadas diferentes,
          mesmo cenario
    """
    tripinfo = os.path.join(PASTA, "resultados", f"_tmp_tripinfo_{os.getpid()}.xml")

    comando = [
        "sumo",
        "-n", REDE,
        "-r", arquivo_rotas,
        "--tripinfo-output", tripinfo,
        "--tripinfo-output.write-unfinished",  # conta tambem quem ficou preso
        "--seed", str(seed),
        "--time-to-teleport", "-1",  # desliga o "teletransporte" de carro preso
        "--waiting-time-memory", "10000",
        "--no-step-log", "true",
        "--no-warnings", "true",
        "--duration-log.disable", "true",
    ]

    trafego.start(comando)
    controlador.preparar(cenario)
    controlador.reiniciar()

    verdes, _ = _fases_verdes()
    logicas = trafego.trafficlight.getAllProgramLogics(SEMAFORO)
    estados_verdes = [logicas[0].phases[i].state for i in verdes]
    tamanho_estado = len(estados_verdes[0])

    # Estado interno do semaforo
    indice_verde = 0  # qual aproximacao esta com verde (0=N, 1=L, 2=S, 3=O)
    tempo_no_verde = 0
    transicao = []  # fila de (estado, segundos) a executar antes do proximo verde
    proximo_verde = None

    trafego.trafficlight.setRedYellowGreenState(SEMAFORO, estados_verdes[0])

    serie_filas = []
    soma_filas = 0
    soma_espera = 0.0
    segundo = 0

    while segundo < duracao:
        # --- executa transicao pendente (amarelo / vermelho geral) ---
        if transicao:
            estado, resta = transicao[0]
            trafego.trafficlight.setRedYellowGreenState(SEMAFORO, estado)
            resta -= 1
            if resta <= 0:
                transicao.pop(0)
                if not transicao:
                    indice_verde = proximo_verde
                    tempo_no_verde = 0
                    trafego.trafficlight.setRedYellowGreenState(
                        SEMAFORO, estados_verdes[indice_verde]
                    )
            else:
                transicao[0] = (estado, resta)
        else:
            tempo_no_verde += 1
            # --- momento de decidir ---
            pode_decidir = (
                tempo_no_verde >= VERDE_MINIMO
                and segundo % INTERVALO_DECISAO == 0
            )
            if pode_decidir:
                obs = _ler_observacao(indice_verde, tempo_no_verde, segundo,
                                      soma_filas, soma_espera)
                escolha = controlador.decidir(obs)
                if escolha != indice_verde:
                    proximo_verde = escolha
                    transicao = [
                        (_estado_amarelo(estados_verdes[indice_verde]), AMARELO),
                        (_estado_tudo_vermelho(tamanho_estado), VERMELHO_GERAL),
                    ]

        trafego.simulationStep()
        segundo += 1

        fila_total = sum(
            trafego.lane.getLastStepHaltingNumber(f)
            for faixas in FAIXAS_ENTRADA.values()
            for f in faixas
        )
        soma_filas += fila_total
        soma_espera += sum(
            trafego.lane.getWaitingTime(f)
            for faixas in FAIXAS_ENTRADA.values()
            for f in faixas
        )
        if guardar_serie:
            serie_filas.append(fila_total)

    # deixa o transito restante escoar, para nao premiar quem empurrou
    # o problema para o fim da simulacao
    extra = 0
    while trafego.simulation.getMinExpectedNumber() > 0 and extra < 1200:
        if transicao:
            estado, resta = transicao[0]
            trafego.trafficlight.setRedYellowGreenState(SEMAFORO, estado)
            resta -= 1
            if resta <= 0:
                transicao.pop(0)
                if not transicao:
                    indice_verde = proximo_verde
                    tempo_no_verde = 0
                    trafego.trafficlight.setRedYellowGreenState(
                        SEMAFORO, estados_verdes[indice_verde]
                    )
            else:
                transicao[0] = (estado, resta)
        else:
            tempo_no_verde += 1
            if tempo_no_verde >= VERDE_MINIMO and extra % INTERVALO_DECISAO == 0:
                obs = _ler_observacao(indice_verde, tempo_no_verde, duracao + extra,
                                      soma_filas, soma_espera)
                escolha = controlador.decidir(obs)
                if escolha != indice_verde:
                    proximo_verde = escolha
                    transicao = [
                        (_estado_amarelo(estados_verdes[indice_verde]), AMARELO),
                        (_estado_tudo_vermelho(tamanho_estado), VERMELHO_GERAL),
                    ]
        trafego.simulationStep()
        extra += 1

    if hasattr(controlador, "encerrar"):
        controlador.encerrar()

    trafego.close()

    metricas = _ler_tripinfo(tripinfo)
    metricas["fila_media"] = soma_filas / duracao
    metricas["segundos_escoamento"] = extra
    if guardar_serie:
        metricas["serie_filas"] = serie_filas
    if os.path.exists(tripinfo):
        os.remove(tripinfo)
    return metricas


def _ler_observacao(indice_verde, tempo_no_verde, segundo,
                    fila_acumulada=0.0, espera_acumulada=0.0):
    filas, carros, espera = {}, {}, {}
    for aprox, faixas in FAIXAS_ENTRADA.items():
        filas[aprox] = sum(
            trafego.lane.getLastStepHaltingNumber(f) for f in faixas
        )
        carros[aprox] = sum(
            trafego.lane.getLastStepVehicleNumber(f) for f in faixas
        )
        espera[aprox] = sum(
            trafego.lane.getWaitingTime(f) for f in faixas
        )
    filas_saida = {}
    for aprox, faixas in VIAS_SAIDA.items():
        filas_saida[aprox] = sum(
            trafego.lane.getLastStepHaltingNumber(f) for f in faixas
        )
    return Observacao(
        filas, carros, espera, APROXIMACOES[indice_verde],
        tempo_no_verde, filas_saida, segundo,
        fila_acumulada, espera_acumulada,
    )


def _ler_tripinfo(caminho):
    """Le o relatorio que o SUMO escreve com a viagem de cada carro."""
    if not os.path.exists(caminho):
        return {"n_carros": 0}

    esperas, duracoes, perdas = [], [], []
    tree = ET.parse(caminho)
    for viagem in tree.getroot():
        esperas.append(float(viagem.get("waitingTime", 0)))
        duracoes.append(float(viagem.get("duration", 0)))
        perdas.append(float(viagem.get("timeLoss", 0)))

    def media(v):
        return sum(v) / len(v) if v else 0.0

    def percentil(v, p):
        if not v:
            return 0.0
        ordenado = sorted(v)
        k = int(round((p / 100.0) * (len(ordenado) - 1)))
        return ordenado[k]

    return {
        "n_carros": len(esperas),
        "espera_media": media(esperas),
        "espera_p95": percentil(esperas, 95),
        "espera_max": max(esperas) if esperas else 0.0,
        "viagem_media": media(duracoes),
        "perda_media": media(perdas),
    }
