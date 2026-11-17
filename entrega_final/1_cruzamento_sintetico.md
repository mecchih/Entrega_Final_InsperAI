# Etapa A — Double DQN no cruzamento sintético

## O ambiente

- Cruzamento sintético de 4 vias com 2 faixas cada (`semaforo/rede/cruzamento.net.xml`) e semáforo de 4 fases, uma aproximação por vez.
- Simulado no SUMO com demanda **gerada por nós** (`semaforo/scripts/gerar_demanda.py`):

| Cenário | Descrição | Veículos/h |
|---|---|---:|
| Equilibrado | Demanda parecida nas quatro aproximações | 1800 |
| Assimétrico | Avenida carregada cruzando uma rua vazia | 1860 |
| Pico | Calmo, depois carregado, depois calmo | 1570 |
| Saturado | Acima da capacidade, de cerca de 2550/h | 2800 |
| Girado | Assimétrico girado 90°; **nunca usado no treino** | — |

**Regras de segurança, iguais para todos os controladores:**
- amarelo de 3 s e vermelho geral de 2 s;
- verde mínimo de 10 s e verde máximo de 60 s (dinâmica C);
- decisão a cada 5 s.

O trânsito escoa até o último veículo depois da hora simulada.

## A DQN

- Double DQN: MLP com entradas → 64 → 64 → 4 (ReLU).
- Memória de 50 mil transições, lote 64, Adam com taxa de aprendizado 5e-4.
- γ = 0,95^(dt/5).
- Rede-alvo atualizada a cada 500 passos de gradiente.
- ε de 100% → 5% em 40 mil decisões.
- 250 episódios de 1 h.
- Checkpoint escolhido pela validação (sementes 201–202). Teste nas sementes 1–10, que nunca são usadas no treino.

| Geração | Recompensa | Entradas | Modelos (`semaforo/modelos/`) |
|---|---|---|---|
| DQN original (histórica, dinâmica A) | fila | 13 | `dqn_fila.pt`, `dqn_fila_seed1.pt`, `dqn_fila_seed2.pt` |
| **A** | fila: −Δ fila acumulada/100 | 13 | `dqn_fila_C_seed{0,1,2}.pt` |
| **B** | fila + excesso de espera acima de 60 s | 13 | `dqn_fila_excesso_C_seed{0,1,2}.pt` |
| **C (final)** | fila + excesso | **17** (13 + maior espera por aproximação) | `dqn_fila_excesso_17_C_seed{0,1,2}.pt` |

As gerações A, B e C foram treinadas e avaliadas na **dinâmica C**, o simulador com a transição corrigida e o verde máximo de 60 s (`semaforo/scripts/simulacao.py`, `DINAMICAS`).

## Resultado final (dinâmica C)

Espera média / P95 em segundos. Cada geração é a média de 3 redes × 10 sementes de teste.

Fontes: `semaforo/resultados/comparacao_17_C/avaliacao.json` e `resumo.json`; para os Max-Pressure de ajuste único, `semaforo/resultados/comparacao_C/avaliacao.json`.

| Controlador | equilibrado | assimétrico | pico | saturado | girado (nunca visto) | média dos 4 de treino |
|---|---|---|---|---|---|---|
| Tempo fixo (Webster) | 28,7 / 60,6 | 33,7 / 76,0 | 52,1 / 168,6 | 93,7 / 196,5 | 35,4 / 78,4 | 52,1 / 125,4 |
| Max-Pressure, ajuste único (original) | 31,9 / 76,3 | 28,3 / 90,9 | 31,5 / 76,6 | 141,5 / 263,6 | 28,4 / 91,9 | 58,3 / 126,9 |
| Max-Pressure teto por cenário (recal. C) | 24,7 / 59,8 | 24,7 / 73,6 | 26,6 / 65,9 | 73,6 / 147,8 | 33,0 / 111,4 | 37,4 / 86,8 |
| DQN geração A | 23,6 / 64,0 | 21,5 / 77,4 | 23,3 / 66,0 | 62,4 / 138,3 | 25,3 / 113,0 | 32,7 / 86,4 |
| DQN geração B | 23,2 / 61,5 | 21,0 / 76,8 | 23,2 / 63,7 | 64,5 / 135,7 | 23,1 / 95,2 | 33,0 / 84,4 |
| **DQN geração C** | **22,7 / 57,7** | **20,7 / 67,1** | **22,8 / 60,1** | 63,7 / 136,8 | **22,1 / 85,9** | **32,5 / 80,5** |

**Leitura:**
- **Espera média:** as três gerações da DQN superam o Webster e o teto Max-Pressure (que conhece o cenário de antemão) em todos os cenários, inclusive no girado, que nunca viram.
- **P95:**
  - No saturado e no pico, as gerações vencem ou empatam com o teto.
  - A geração C teve o menor P95 entre as DQN em 4 dos 5 cenários.
  - No equilibrado, a geração C ficou abaixo do teto (57,7 contra 59,8); A e B ficaram acima.
  - No assimétrico, a geração C tem o menor P95 de todos (67,1).
  - No girado, o Webster ainda tem o menor P95 (78,4 contra 85,9 da geração C).
- **A → B:** a troca de recompensa eliminou veículos não atendidos (A teve 13 em 50 rodadas; B e C, 0). Mas não cumpriu o critério pré-registrado de P95 da rua secundária (`comparacao_excesso_C/resumo.md`).
- **B → C:** com 17 entradas, o P95 da rua secundária caiu 21,9% no assimétrico e 13,5% no girado. A espera média caiu 1,3% a 4,3% (`comparacao_17_C/resumo.md`).

## Resultados históricos (dinâmica A) — use com cuidado

- A tabela de `semaforo/LEIA-ME.md` e o arquivo `semaforo/resultados/avaliacao_final.json` vêm da **dinâmica A**. Ali a DQN original fez 28,3 s de média nos 4 cenários, contra 40,2 s do Webster e 30,1 s do teto.
- A dinâmica A tem um **defeito de transição**: o verde ganha +1 s e só 1 dos 2 s de vermelho geral é executado. Além disso, a DQN original deixou veículos sem atendimento em algumas rodadas (`resultados/seguranca_transicao/resumo.md`).
- Por isso **os números finais da Etapa A são os da dinâmica C, acima**. A dinâmica A só entra como histórico.
- Os valores da "recompensa por tempo de espera" citados no LEIA-ME (44,8 s, 118,8 s) não estão em nenhum JSON versionado.

## Etapa intermediária: Cologne1

- Antes do Multi-Agent, testamos a DQN original (sem retreino) num **Cologne1 derivado**: a rede e a demanda RESCO originais, com o `tlLogic` reescrito para 4 fases.
- Foi uma rodada válida, semente 1:
  - 2015/2015 viagens concluídas, 0 colisões;
  - espera média de 37,4 s e P95 de 191 s, com forte desigualdade entre aproximações.
- Não teve controladores de comparação e não é comparável com a tabela acima.
- Documentação: `semaforo/COLOGNE1.md`, `TESTE_COLOGNE1_DERIVADO.md` e `REGISTRO_COLOGNE1.md`.

## Gráfico

`graficos/A1_cruzamento_geracoes_dqn.png`, gerado por `gerar_grafico_cruzamento.py` a partir do `resumo.json`.
