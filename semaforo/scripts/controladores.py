"""
Os semaforos "tradicionais" -- os dois adversarios que a IA vai ter que bater.

1) TempoFixo: o semaforo de sempre. Gira sempre na mesma ordem, com os mesmos
   tempos. Mas os tempos NAO sao inventados: saem da formula de Webster, que e
   como engenheiro de trafego calcula isso de verdade. Isso importa porque um
   semaforo de tempo fixo mal calibrado seria um adversario de araque -- ganhar
   dele nao provaria nada.

2) MaxPressure: o adversario de verdade. Olha as filas e da verde para quem
   esta mais pressionado. Nao treina, nao aprende, nao tem rede neural --
   e ainda assim e dificil de bater, porque tem garantia matematica de manter
   as filas estaveis sempre que isso for possivel.
"""

from simulacao import APROXIMACOES, Controlador, AMARELO, VERMELHO_GERAL, VERDE_MINIMO
from gerar_demanda import volume_por_aproximacao

# Quantos carros uma faixa consegue despachar por hora com verde continuo.
# 1800 e o valor classico de referencia.
FLUXO_SATURACAO_POR_FAIXA = 1800
FAIXAS_POR_APROXIMACAO = 2
FLUXO_SATURACAO = FLUXO_SATURACAO_POR_FAIXA * FAIXAS_POR_APROXIMACAO


class TempoFixo(Controlador):
    """Semaforo comum: ordem fixa, tempos fixos (calculados por Webster)."""

    nome = "Tempo fixo (Webster)"

    def __init__(self):
        self.tempos = None
        self._alvo = 0

    def preparar(self, cenario):
        self.tempos = webster(cenario)

    def reiniciar(self):
        self._alvo = 0

    def decidir(self, obs):
        atual = APROXIMACOES.index(obs.aprox_verde)
        # Ja cumpriu o tempo dessa aproximacao? Entao passa para a proxima.
        if obs.tempo_no_verde >= self.tempos[obs.aprox_verde]:
            return (atual + 1) % len(APROXIMACOES)
        return atual


def webster(cenario):
    """Calcula quanto verde cada aproximacao recebe, pela formula de Webster.

    A ideia da formula, em uma frase: existe um tempo de ciclo que minimiza a
    espera total, e ele depende de quanto tempo o cruzamento "desperdica" em
    amarelo/vermelho geral e de quao perto da saturacao cada aproximacao esta.

    Passo a passo:
      y   = carros que chegam / carros que a via consegue despachar
            (o quao "carregada" cada aproximacao esta, de 0 a 1)
      L   = tempo perdido por ciclo (amarelo + vermelho geral de cada fase)
      C   = (1,5 x L + 5) / (1 - Y)      <- ciclo otimo de Webster
      verde_i = (C - L) x y_i / Y        <- reparte o verde na proporcao da carga
    """
    volumes = volume_por_aproximacao(cenario)
    y = {a: volumes[a] / FLUXO_SATURACAO for a in APROXIMACOES}
    Y = sum(y.values())

    L = len(APROXIMACOES) * (AMARELO + VERMELHO_GERAL)

    if Y >= 0.95:  # cruzamento saturado: a formula estoura
        C = 150.0
    else:
        C = (1.5 * L + 5) / (1 - Y)
    C = min(max(C, 40.0), 150.0)  # limites praticos de um semaforo real

    verde_total = C - L
    tempos = {}
    for a in APROXIMACOES:
        verde = verde_total * y[a] / Y if Y > 0 else verde_total / 4
        verde = max(verde, VERDE_MINIMO)
        # arredonda para multiplo de 5 (meio sempre para cima)
        tempos[a] = int(verde / 5.0 + 0.5) * 5
    return tempos


class MaxPressure(Controlador):
    """Da verde para a aproximacao de maior "pressao".

    Pressao = fila esperando para entrar  -  fila na saida

    Por que descontar a fila de saida? Porque liberar carros para uma via que
    ja esta travada nao resolve nada -- so muda o engarrafamento de lugar.
    Em um cruzamento isolado como o nosso as saidas vivem livres, entao na
    pratica isso vira "da verde para a maior fila". Em uma rede de varios
    cruzamentos, o desconto passa a fazer muita diferenca.

    'custo_troca' existe porque trocar de fase custa 5 segundos de amarelo +
    vermelho geral. Sem isso o controlador fica trocando de fase toda hora e
    desperdica mais do que ganha.
    """

    nome = "Max-Pressure (ajuste unico)"

    def __init__(self, custo_troca=0.0, verde_maximo=60, verde_minimo=18):
        self.custo_troca = custo_troca
        self.verde_maximo = verde_maximo
        self.verde_minimo = verde_minimo

    def decidir(self, obs):
        atual = APROXIMACOES.index(obs.aprox_verde)

        # verde minimo proprio do controlador (acima do minimo de seguranca)
        if obs.tempo_no_verde < self.verde_minimo:
            return atual

        pressoes = {}
        for a in APROXIMACOES:
            # a fila de saida e dividida entre os 3 destinos possiveis
            pressoes[a] = obs.filas[a] - obs.filas_saida[a] / 3.0

        melhor = max(APROXIMACOES, key=lambda a: pressoes[a])
        indice_melhor = APROXIMACOES.index(melhor)

        # Verde ficou longo demais e tem gente esperando? Troca na forca.
        if obs.tempo_no_verde >= self.verde_maximo:
            candidatos = [a for a in APROXIMACOES if a != obs.aprox_verde]
            alvo = max(candidatos, key=lambda a: pressoes[a])
            if pressoes[alvo] > 0:
                return APROXIMACOES.index(alvo)

        # So troca se a outra aproximacao compensar o custo da troca
        if pressoes[melhor] > pressoes[obs.aprox_verde] + self.custo_troca:
            return indice_melhor
        return atual


class VerdeFixoIngenuo(Controlador):
    """Semaforo de tempo fixo SEM calibracao: 30s iguais para todo mundo.

    Esta aqui so para mostrar, no relatorio, o tamanho do erro de usar um
    adversario mal calibrado. E o baseline que a maioria dos trabalhos usa --
    e e justamente por isso que tantos deles reportam ganhos enormes.
    """

    nome = "Tempo fixo sem calibrar (30s)"

    def decidir(self, obs):
        atual = APROXIMACOES.index(obs.aprox_verde)
        if obs.tempo_no_verde >= 30:
            return (atual + 1) % len(APROXIMACOES)
        return atual


# Melhor ajuste do Max-Pressure para CADA cenario, encontrado por varredura.
# Note como o verde minimo ideal muda de 10s para 25s quando o cruzamento
# satura: e justamente esse "pulo" que um semaforo de regra fixa nao
# consegue dar, porque ele nao sabe em que regime esta.
AJUSTE_POR_CENARIO = {
    "equilibrado": {"custo_troca": 0, "verde_minimo": 10},
    "assimetrico": {"custo_troca": 2, "verde_minimo": 10},
    "pico": {"custo_troca": 0, "verde_minimo": 10},
    "saturado": {"custo_troca": 2, "verde_minimo": 25},
}


class MaxPressureAjustado(MaxPressure):
    """Max-Pressure com o ajuste otimo de cada cenario.

    ATENCAO: este controlador TRAPACEIA. Para funcionar, ele precisa saber
    de antemao em qual regime de transito esta -- informacao que um semaforo
    de verdade nao tem as 7h da manha de uma segunda-feira qualquer.

    Ele nao esta aqui como adversario, e sim como TETO: mostra o quanto se
    ganharia se fosse possivel reajustar a regra a cada regime. O espaco
    entre o "ajuste unico" (honesto) e este "ajuste por cenario" (trapaceiro)
    e exatamente o premio que a IA esta tentando ganhar -- sem trapacear,
    deduzindo o regime pelo que os sensores mostram.
    """

    nome = "Max-Pressure ajustado por cenario (teto)"

    def preparar(self, cenario):
        ajuste = AJUSTE_POR_CENARIO.get(cenario, {})
        self.custo_troca = ajuste.get("custo_troca", self.custo_troca)
        self.verde_minimo = ajuste.get("verde_minimo", self.verde_minimo)
