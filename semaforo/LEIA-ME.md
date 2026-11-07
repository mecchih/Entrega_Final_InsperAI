# Semáforo Inteligente — base do projeto

Estado atual: **tudo funcionando — baselines, DQN treinado e avaliado.**
O agente bate todos os semáforos tradicionais e generaliza para um cenário
que nunca viu.

## Para rodar

```bash
pip install eclipse-sumo sumolib traci libsumo

pip install torch

cd scripts
python3 gerar_demanda.py            # cria os arquivos de trânsito
python3 comparar.py                 # só os semáforos tradicionais (~1 min)
python3 treinar_dqn.py fila 250     # treina o agente (~7 min)
python3 avaliar.py dqn_fila         # medição final (~2 min)
```

## O que tem aqui

```
rede/
  cruzamento.net.xml       cruzamento de 4 vias, 2 faixas cada,
                           semáforo de 4 fases (uma aproximação por vez)
  demanda_*.rou.xml        os 4 cenários de trânsito (gerados pelo script)

scripts/
  gerar_demanda.py         define e escreve os cenários de trânsito
  simulacao.py             o motor: roda o SUMO, troca as fases com
                           segurança (amarelo + vermelho geral) e mede
  controladores.py         os semáforos tradicionais
  dqn.py                   o agente que aprende (rede, memória, treino)
  treinar_dqn.py           o laço de treinamento
  avaliar.py               a medição final de todos contra todos
  comparar.py              só os tradicionais (útil para debug rápido)

modelos/
  dqn_fila.pt              os pesos do agente bom
  dqn_espera.pt            os pesos do agente com a recompensa ruim

resultados/
  baselines.json           números brutos dos tradicionais
  treino_*.json            histórico de treino episódio por episódio
  avaliacao_final.json     números brutos da medição final
```

## Decisões que já estão tomadas (e por quê)

**4 fases, uma aproximação por vez.** Todo movimento fica protegido (ninguém
cruza com ninguém), o que simplifica a análise e dá ao agente uma escolha
limpa entre 4 opções.

**Amarelo de 3s + vermelho geral de 2s em toda troca.** Sem isso a simulação
não representa um semáforo real e o resultado não valeria nada. Esses 5
segundos por troca são o que faz "trocar de fase" ter custo — e é daí que
sai toda a dificuldade do problema.

**Verde mínimo de 10s.** Segurança: pedestre e motorista não conseguem
reagir a um verde mais curto.

**Decisão a cada 5 segundos.** Todos os controladores decidem no mesmo
ritmo, inclusive o DQN que vem depois. Comparação justa.

**libsumo em vez de traci.** Roda o simulador dentro do Python: ~8x mais
rápido, sem janela gráfica. Uma hora de trânsito simulada em 0,5 segundo.
Para gravar o vídeo da apresentação, trocar para traci + sumo-gui.

**Deixa o trânsito escoar no fim.** Depois da hora simulada, a simulação
continua até o último carro sair. Sem isso, um semáforo poderia "ganhar"
só empurrando a fila para depois do fim da medição.

## Os 4 cenários

| cenário | o que é | carros/h |
|---|---|---|
| equilibrado | trânsito parecido nas 4 direções | 1800 |
| assimétrico | avenida cheia cruzando rua de bairro vazia | 1860 |
| pico | calmo → carregado (~85% da capacidade) → calmo | 1570 |
| saturado | demanda acima da capacidade do cruzamento, de propósito | 2800 |

Capacidade física do cruzamento: ~2550 carros/h.

## Os controladores já implementados

1. **Tempo fixo sem calibrar (30s)** — está aqui só para mostrar o tamanho
   do erro de usar adversário fraco. Não use como baseline principal.
2. **Tempo fixo (Webster)** — o semáforo de sempre, com os tempos calculados
   pela fórmula que engenheiro de trafégo usa de verdade. **Este é o baseline
   honesto.**
3. **Max-Pressure (ajuste único)** — adaptativo por regra, um ajuste só para
   todos os cenários. É o que daria para instalar na rua.
4. **Max-Pressure ajustado por cenário** — trapaceia: sabe de antemão em que
   regime está. Não é adversário, é **teto de referência**.

## O achado que define o projeto

Varrendo os parâmetros do Max-Pressure, o verde mínimo ideal **vira do avesso**
conforme o trânsito:

| verde mínimo | trânsito normal | saturado |
|---|---|---|
| 10s | **ótimo** (0,75) | desastre (2,48) |
| 18s | ruim (1,15) | ruim (1,07) |
| 25s | ruim (1,36) | **ótimo** (0,80) |

(valores relativos ao tempo fixo calibrado; menor é melhor)

Ou seja: **uma regra fixa tem que escolher um lado e perder no outro.**
O meio-termo (18s) é medíocre nos dois.

É esse buraco que justifica o aprendizado por reforço: o agente vê o estado
do cruzamento e pode mudar de comportamento conforme o regime — sem precisar
que alguém lhe conte em qual regime está.

**Meta quantificada do DQN:** fechar os 28% a 35% de espera que separam o
Max-Pressure de ajuste único do teto ajustado por cenário.

## Os resultados

Espera média em segundos, 10 sementes por célula, as mesmas para todos.
O cenário "girado" o agente **nunca viu** no treino.

| controlador | equilibrado | assimétrico | pico | saturado | **média** | girado (guardado) |
|---|---|---|---|---|---|---|
| Tempo fixo sem calibrar | 44,0 | 92,8 | 44,0 | 110,0 | **72,7** | 101,9 |
| Tempo fixo (Webster) | 26,5 | 28,2 | 29,5 | 76,6 | **40,2** | 28,9 |
| Max-Pressure (ajuste único) | 30,8 | 26,9 | 30,2 | 83,5 | **42,9** | 27,1 |
| Max-Pressure por cenário (teto) | 20,1 | 19,5 | 20,7 | 60,2 | **30,1** | 27,1 |
| **DQN (recompensa de fila)** | 20,3 | 19,8 | 21,3 | **51,8** | **28,3** | **21,1** |

Três coisas aconteceram:

**1. O agente empatou com o teto nos três cenários normais e o superou na
saturação** (51,8s contra 60,2s, −14%). Ou seja: ele não só descobriu sozinho
o ajuste que teve de ser encontrado por varredura, ele achou uma política
melhor que qualquer ajuste fixo de regra — porque pode mudar de
comportamento no meio da hora, coisa que nenhum ajuste fixo faz.

**2. Generalizou.** No cenário girado (avenida cheia virada 90°, nunca visto),
o agente fez 21,1s contra 27,1s de todo o resto. Ele aprendeu a regra
("dá verde para quem tem fila"), não o mapa ("Leste-Oeste é a avenida").
Esse é o resultado que mais vale no relatório.

**3. O tempo fixo calibrado é adversário melhor que o Max-Pressure de ajuste
único** (40,2s contra 42,9s). Contraintuitivo e importante: um adaptativo mal
ajustado perde de um tempo fixo bem calculado.

### Ressalva honesta: a cauda

O DQN ganha na **média** e perde no **p95** (os 5% que esperam mais).
No cenário assimétrico: 77,9s de p95 contra 55,8s do teto. Ele otimiza
o que a recompensa pede — a fila total — e para isso aceita deixar alguns
carros da rua secundária esperando bem mais.

Isso não é um bug, é o que foi pedido a ele. Se equidade importar,
a recompensa tem que mudar. Vale uma seção no relatório.

## A comparação das duas recompensas

| recompensa | média nos 4 cenários | saturado |
|---|---|---|
| fila × tempo | **28,3s** | **51,8s** |
| tempo de espera acumulado | 44,8s | 118,8s |

A recompensa intuitiva (tempo de espera) é **muito** pior, e desaba
especificamente na saturação. A causa foi medida, não suposta:

| cenário | magnitude recomp. FILA | magnitude recomp. ESPERA |
|---|---|---|
| equilibrado | 1,31 | 2,78 |
| saturado | 3,79 | **16,46** |
| razão máx/mín | 2,9x | **5,9x** |

O tempo de espera acumulado cresce de forma quase quadrática (cada carro
parado contribui com a espera *inteira* dele, a cada segundo). Na saturação
a recompensa fica ~16, contra ~2,8 no trânsito leve. Resultado: os episódios
saturados dominam o gradiente e atropelam o aprendizado dos outros regimes —
a rede tenta representar duas escalas muito diferentes com os mesmos pesos
e não consegue nenhuma das duas.

**Lição transferível:** em aprendizado por reforço, a *escala* da recompensa
entre regimes importa mais que a semântica dela. Uma recompensa "mais certa
conceitualmente" pode treinar muito pior só por causa da faixa de valores.

## Como o treino foi feito (para o relatório)

- Rede: 13 entradas → 64 → 64 → 4 saídas, ReLU. Pequena de propósito.
- Double DQN, memória de 50 mil transições, lote de 64, γ = 0,95,
  Adam com lr 5e-4, rede-alvo atualizada a cada 500 passos.
- Desconto ajustado pela duração real do intervalo (γ^(dt/5)), porque trocar
  de fase gasta mais segundos que manter.
- Exploração de 100% → 5% ao longo de 40 mil decisões.
- 250 episódios de 1 hora = ~120 mil decisões, ~84 mil passos de gradiente,
  **7 minutos de CPU**. Sem GPU.
- Sementes de treino 1000+; de teste 1 a 10. Nunca se cruzam.
- Checkpoint salvo pelo melhor desempenho em validação, não pelo último
  episódio — desempenho de DQN oscila.

## O que ainda falta

1. **O treino não tinha estabilizado** no episódio 250 (ainda melhorava).
   Rodar 500-750 episódios provavelmente ganha mais.
2. **Repetir com várias sementes de treino** (3 a 5). Hoje temos 1 treino só.
   Sem isso não se sabe quanto do resultado é sorte da inicialização.
3. **Gráficos:** curva de aprendizado e barras da comparação final.
4. **Vídeo da apresentação:** rodar com `traci` + `sumo-gui` para mostrar
   o trânsito acontecendo, tempo fixo ao lado do DQN.
5. **Equidade:** uma terceira recompensa que penalize a cauda, para ver se
   dá para ganhar na média sem piorar o p95.
