# Demonstração visual no SUMO-GUI (Cologne8)

Três janelas do SUMO-GUI lado a lado, com **o mesmo trânsito** (mesma semente)
e controladores diferentes:

| Janela | Controlador | Espera média nesta simulação (semente 1) |
|---|---|---:|
| esquerda | **Tempo fixo**: o programa original do cenário | 30,7 s |
| meio | **Rede que copia**: rede neural supervisionada que imita o semáforo atuado | 16,7 s |
| direita | **MARL**: aprendizado por reforço (nosso) | 8,8 s |

Os modelos foram escolhidos pela validação, não pelo teste. Para o MARL foi
usada a semente de modelo 0, que teve a melhor pontuação de validação entre
as 10 (`politica_ep0375.pt`). Para a rede que copia, a semente 2, pela mesma
regra. Os números acima são exatamente os da avaliação; a demonstração só
acrescenta as janelas e as cores.

## Como rodar (Windows, PowerShell, na raiz do repositório)

```powershell
& '.venv-dqn-inferencia/Scripts/python.exe' -B -X utf8 semaforo/scripts/demo_visual_cologne8.py `
    --sumo-home '../tools/sumo-win64-1.28.0'
```

1. Abrem três janelas, que avançam rápido até o **minuto 10** da hora simulada,
   o começo do pico.
2. No terminal aparece *"Tudo pronto..."*. Comece a gravação, se for gravar,
   e aperte **Enter**.
3. As três janelas rodam juntas, sincronizadas pelo relógio, do minuto 10 ao
   **minuto 25**, a 10× a velocidade real (cerca de 1min30s de demonstração).
4. No fim, as janelas ficam paradas no último instante. Aperte **Enter** de
   novo para fechá-las.

O terminal mostra a cada minuto simulado quantos carros estão parados em cada janela.

### Ajustes úteis

| Opção | Para quê | Padrão |
|---|---|---|
| `--atraso 200` | Mais devagar (ms reais por segundo simulado) | 100 |
| `--inicio 25800 --fim 26700` | Trecho mostrado (25200 = minuto 0) | minutos 10 a 25 |
| `--cruzamento 26110729` | Cruzamento no centro da tela | 26110729 |
| `--zoom 400` | Zoom inicial (menor = mais longe) | 700 |
| `--controladores fixo marl` | Só duas janelas | as três |
| `--semente 3` | Outro trânsito de teste (1 a 10) | 1 |
| `--largura-tela 2560 --altura-tela 1440` | Resolução do monitor | 1920 × 1080 |

Dá para mexer no zoom e arrastar a vista com o mouse em qualquer janela durante a demonstração.

## O que a plateia vê

**Cor de cada carro = quanto tempo ele já ficou parado na viagem:**

- 🟢 verde: menos de 5 s
- 🟡 amarelo: 5 a 30 s
- 🟠 laranja: 30 a 60 s
- 🔴 vermelho: 60 s ou mais

**Por que o minuto 10 e o cruzamento 26110729:** na semente 1, entre os
minutos 10 e 25 está o pico da hora. Na média desse trecho, a rede toda tem
cerca de 26 a 30 carros parados com o tempo fixo, contra 6 a 11 com o
MARL. O cruzamento 26110729 é onde a diferença mais aparece: chega a 37 carros
parados com o tempo fixo e no máximo 14 com o MARL.

## Roteiro sugerido para a fala (cerca de 1 min)

1. *"As três janelas recebem exatamente os mesmos carros, nos mesmos
   horários. A única diferença é quem controla os 8 semáforos."*
2. *"Na esquerda está o semáforo de tempo fixo, como a maioria da cidade.
   No meio, uma rede neural que aprendeu copiando um semáforo com sensor.
   Na direita, o nosso agente, que aprendeu por reforço."*
3. Quando as filas crescerem: *"Repare nas cores: vermelho é quem já
   esperou mais de um minuto. O tempo fixo forma fila porque não enxerga o
   trânsito. A rede que copia reage, mas erra quando cai numa situação que o
   professor nunca mostrou."*
4. *"O nosso agente aprendeu pelas consequências das próprias decisões, e
   por isso consegue segurar o pico."*
5. Feche com o número geral, não só desta simulação: *"Nas 10 simulações de
   teste, ele reduziu a espera média em 22% em relação ao melhor controlador
   clássico."*

Não diga que o MARL é mais seguro: as colisões não melhoraram (ver
[RESULTADOS_COMPARADORES_COLOGNE8.md](RESULTADOS_COMPARADORES_COLOGNE8.md)).

## Vídeo de reserva

Grave antes da apresentação, para o caso de a demonstração ao vivo travar:

- **Ferramenta de Captura do Windows 11:** `Win + Shift + R`, selecione a área
  das três janelas e grave. O vídeo é salvo em MP4.
- **OBS Studio** (gratuito), se quiser mais controle: fonte *Captura de
  tela*, recortada nas três janelas.
- A Xbox Game Bar (`Win + Alt + R`) grava só **uma** janela, então não serve
  para as três juntas.

Dica: grave com `--atraso 150` e acelere na edição se precisar. Coloque os
títulos das janelas na edição ou no slide, porque o SUMO-GUI não mostra o nome
do controlador.

## Como funciona (para quem for mexer)

- `scripts/demo_visual_cologne8.py` abre um processo por janela. Cada processo
  usa o mesmo executor `ambiente_marl_cologne.rodar` da avaliação, com
  `backend="traci"` e `gui=True`.
- O script só acrescenta três coisas, sem mudar a dinâmica: posição e zoom
  das janelas (`--gui-settings-file`, `--window-pos`, `--window-size`), a cor
  dos carros (`vehicle.setColor`, a partir das inscrições que o executor já
  faz) e uma espera entre passos para sincronizar as janelas.
- A rede que copia usa `mlps_numpy.npz`, pesos em NumPy puro exportados do
  scikit-learn, conferidos com zero decisões diferentes em 32 mil estados de
  teste. Não precisa de scikit-learn.
- Teste sem janelas, por exemplo no Linux:
  `python -B semaforo/scripts/demo_visual_cologne8.py --sem-gui --sem-esperar --atraso 0`.
