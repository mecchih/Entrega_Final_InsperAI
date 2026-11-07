"""
Gera os arquivos de rota (a demanda de carros) para o cruzamento.

Cada cenario define quantos carros por hora entram por cada aproximacao
(Norte, Leste, Sul, Oeste) e como eles se dividem entre seguir reto,
virar a direita e virar a esquerda.

Os carros entram de forma aleatoria (sorteio a cada segundo). Quem decide
o sorteio e a "seed" passada ao SUMO -- ou seja, o MESMO arquivo de rota
gera transitos diferentes com seeds diferentes. Isso e o que permite
rodar o mesmo cenario varias vezes e tirar media.
"""

import os

PASTA_REDE = os.path.join(os.path.dirname(__file__), "..", "rede")

# Via de entrada de cada aproximacao
ENTRADA = {
    "N": "top0A0",
    "L": "right0A0",
    "S": "bottom0A0",
    "O": "left0A0",
}

# Para quem entra por cada aproximacao: onde sai se for reto / direita / esquerda
SAIDAS = {
    "N": {"reto": "A0bottom0", "direita": "A0left0", "esquerda": "A0right0"},
    "L": {"reto": "A0left0", "direita": "A0top0", "esquerda": "A0bottom0"},
    "S": {"reto": "A0top0", "direita": "A0right0", "esquerda": "A0left0"},
    "O": {"reto": "A0right0", "direita": "A0bottom0", "esquerda": "A0top0"},
}

# Como os carros se dividem (tipico de cruzamento urbano)
DIVISAO = {"reto": 0.70, "direita": 0.20, "esquerda": 0.10}

# Quantos carros por hora entram por aproximacao, em cada cenario.
# Cada item da lista e um pedaco de tempo: (inicio_seg, fim_seg, {aprox: carros_por_hora})
CENARIOS = {
    # Transito parecido nas quatro direcoes
    "equilibrado": [
        (0, 3600, {"N": 450, "L": 450, "S": 450, "O": 450}),
    ],
    # Avenida (Leste-Oeste) cheia, rua de bairro (Norte-Sul) vazia.
    # E aqui que semaforo de tempo fixo sofre: ele da verde para rua vazia.
    "assimetrico": [
        (0, 3600, {"N": 180, "L": 750, "S": 180, "O": 750}),
    ],
    # Comeca calmo, carrega no meio (~85% da capacidade), volta a acalmar.
    # E aqui que controlador adaptativo tem mais espaco para ganhar: cheio,
    # mas ainda nao estourado.
    "pico": [
        (0, 1200, {"N": 300, "L": 350, "S": 300, "O": 350}),
        (1200, 2400, {"N": 450, "L": 600, "S": 450, "O": 600}),
        (2400, 3600, {"N": 300, "L": 350, "S": 300, "O": 350}),
    ],
    # De proposito acima da capacidade do cruzamento (~2800 carros/h contra
    # ~2550 de capacidade). Serve para mostrar o teto: quando a demanda passa
    # do que o cruzamento consegue despachar, nenhum semaforo -- nem IA --
    # resolve, porque o gargalo deixou de ser a divisao do verde e passou a
    # ser a capacidade fisica. Resultado importante de ter no relatorio.
    "saturado": [
        (0, 3600, {"N": 600, "L": 800, "S": 600, "O": 800}),
    ],
    # CENARIO GUARDADO: o agente NUNCA treina neste.
    # E o assimetrico girado 90 graus -- agora a rua cheia e a Norte-Sul.
    # Serve para responder uma pergunta especifica: o agente aprendeu a
    # regra geral ("da verde para quem tem fila") ou decorou o mapa
    # ("Leste-Oeste e a avenida")? Se decorou, ele quebra aqui.
    "girado": [
        (0, 3600, {"N": 750, "L": 180, "S": 750, "O": 180}),
    ],
}


def gerar(nome_cenario):
    """Escreve o arquivo .rou.xml de um cenario e devolve o caminho."""
    blocos = CENARIOS[nome_cenario]

    linhas = ['<?xml version="1.0" encoding="UTF-8"?>', "<routes>"]
    linhas.append(
        '    <vType id="carro" accel="2.6" decel="4.5" sigma="0.5" '
        'length="5.0" minGap="2.5" maxSpeed="13.89"/>'
    )
    linhas.append("")

    # Rotas: uma para cada movimento possivel (12 no total)
    for aprox, saidas in SAIDAS.items():
        for movimento, via_saida in saidas.items():
            linhas.append(
                f'    <route id="r_{aprox}_{movimento}" '
                f'edges="{ENTRADA[aprox]} {via_saida}"/>'
            )
    linhas.append("")

    # Fluxos: quantos carros entram em cada rota, por pedaco de tempo
    for i, (inicio, fim, volumes) in enumerate(blocos):
        for aprox, carros_por_hora in volumes.items():
            for movimento, fracao in DIVISAO.items():
                por_segundo = (carros_por_hora * fracao) / 3600.0
                if por_segundo <= 0:
                    continue
                linhas.append(
                    f'    <flow id="f{i}_{aprox}_{movimento}" '
                    f'route="r_{aprox}_{movimento}" type="carro" '
                    f'begin="{inicio}" end="{fim}" '
                    f'probability="{por_segundo:.5f}" '
                    f'departLane="best" departSpeed="max"/>'
                )

    linhas.append("</routes>")

    caminho = os.path.abspath(
        os.path.join(PASTA_REDE, f"demanda_{nome_cenario}.rou.xml")
    )
    with open(caminho, "w") as f:
        f.write("\n".join(linhas) + "\n")
    return caminho


def volume_por_aproximacao(nome_cenario):
    """Carros por hora medios de cada aproximacao -- usado pela formula de Webster."""
    blocos = CENARIOS[nome_cenario]
    duracao_total = sum(fim - inicio for inicio, fim, _ in blocos)
    media = {}
    for aprox in ENTRADA:
        soma = sum(
            volumes[aprox] * (fim - inicio) for inicio, fim, volumes in blocos
        )
        media[aprox] = soma / duracao_total
    return media


if __name__ == "__main__":
    for nome in CENARIOS:
        caminho = gerar(nome)
        print(f"{nome:14s} -> {caminho}")
        print(f"{'':14s}    media carros/h: {volume_por_aproximacao(nome)}")
