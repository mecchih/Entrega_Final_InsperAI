# Etapa C — Multi-Agent no corredor do Insper

## O ambiente

- **Rede:** ruas ao redor do Insper (São Paulo), exportadas do **OpenStreetMap** pelo osmWebWizard do SUMO (`semaforo/cenarios/insper/`).
  - Tem **14 controladores semafóricos**. A IA controla **3 consecutivos** na Rua Ribeirão Claro, que é mão única e tem cerca de 96 m entre os cruzamentos:
    - `476455095`, Gomes de Carvalho;
    - `40278305`, Casa do Ator;
    - `40278183`, Quatá.
  - Os outros 11 continuam no programa original (atuado do SUMO). Um verificador confere a cada passo que ninguém escreve neles.
- **Demanda: tráfego SINTÉTICO calibrado, não contagens reais.**
  - A demanda que vem com o cenário (randomTrips) é baixa.
  - Geramos níveis estratificados no corredor com `gerar_demanda_insper.py`, a partir de candidatos do randomTrips, e os calibramos por simulação (`calibrar_demanda_insper.py`):
    - moderado: 1200 veículos/h no corredor;
    - intenso: 2000 veículos/h no corredor, o nível usado;
    - saturado: 2400 veículos/h no corredor.
  - O nível intenso tem cerca de 2191 veículos por semente, sendo cerca de 191 fora do corredor.
  - Pastas: `semaforo/cenarios/insper_demanda/`, com `LEIA-ME.md` e `niveis.json`.
- **Sementes de tráfego, conferidas por programa contra sobreposição:**
  - treino 1001–1030;
  - validação 221–225;
  - **teste final inédito 241–250**, executado uma única vez.

## Arquitetura

As mesmas classes do Cologne8, adaptadas para 3 semáforos.

- **Modelo A, independente:** 3 Double DQNs locais.
  - Observação de 13 dimensões: fila, veículos e espera em 2 aproximações, fase, idade do verde e objetivo do supervisor.
  - 2 ações: as 2 configurações de verde.
- **Modelo B, hierárquico:** os 3 locais mais 1 supervisor.
  - Observação de 48 dimensões e 4 orientações: equilibrado ou priorizar um dos 3.
  - Decide a cada 30 s (ou 15 s na versão otimizada).
- **Segurança, igual em todos os controladores de RL e nos baselines com "regras do RL":**
  - verde mínimo de 10 s, amarelo de 3 s do programa e vermelho geral de 2 s;
  - decisão a cada 5 s e verde máximo condicional de 60 s.
  - O verificador independente confere o estado executado.
- **Otimização final**, com 3 hipóteses testadas e as mesmas sementes e hiperparâmetros:
  - verde mínimo de 5 s;
  - penalidade de colisão só para contatos atribuíveis ao cruzamento do agente;
  - supervisor a cada 15 s.
- **Treino:** 5 sementes de modelo × 150 episódios por configuração. Checkpoint escolhido **só pela validação**.

## Resultado final

Teste inédito com as sementes 241–250 e as mesmas 10 demandas para todos. RL: média de 5 modelos ± desvio-padrão entre os modelos.

Fonte: `semaforo/integracao_insper/otimizacao_final/resultados/teste_final/teste_final.json`; tabela completa em `.../relatorio/tabela_final.md`.

| Controlador | Espera média no corredor (s) | P95 corredor (s) | Espera média na rede (s) | Bloqueio da saída (s) |
|---|---:|---:|---:|---:|
| **Programa original atuado (SUMO)** | **15,48 ± 3,03** | **53,8** | **40,47** | **34,3** |
| Atuado com as regras do RL (aproximação, verde 10) | 22,25 ± 2,97 | 66,1 | 46,54 | 57,8 |
| Max-Pressure (fila só da faixa imediata) | 54,77 ± 6,20 | 234,6 | 102,41 | 57,5 |
| MARL A anterior (v1) | 20,99 ± 0,86 | 56,3 | 45,63 | 68,8 |
| MARL B anterior (v1) | 21,84 ± 1,16 | 58,7 | 46,39 | 74,7 |
| **MARL A otimizado (colisão atribuída), recomendado** | 21,49 ± 1,32 | 58,5 | 45,97 | 71,6 |
| MARL A com verde de 5 s | 22,83 ± 3,77 | 73,7 | 47,26 | 61,6 |
| MARL B otimizado, supervisor 30 s | 22,04 ± 0,68 | 59,2 | 46,48 | 75,0 |
| MARL B otimizado, supervisor 15 s | 21,84 ± 0,48 | 59,9 | 46,37 | 79,5 |

Todas as 340 avaliações foram válidas, com 100% das viagens concluídas e 0 violações de segurança. Não houve nenhuma colisão nos 3 cruzamentos controlados (as poucas colisões registradas foram externas). Só o Max-Pressure teve teletransportes.

## O que isso significa

- **O programa original atuado foi superior à IA.** Todas as versões do MARL ficaram de 5,5 a 7,3 s piores, com significância, e perderam nas 10 de 10 demandas.
- Contra um controle clássico **submetido às mesmas restrições** (vermelho geral de 2 s, decisão a cada 5 s), o MARL **empata**: fica 0,2 a 1,3 s melhor em média, mas o IC95 contém zero.
- A principal causa provável são as regras operacionais. O programa original decide a cada segundo e perde 3 s por troca; o RL perde 5 s por troca e decide a cada 5 s. O vermelho geral foi mantido por segurança.
- **Otimizações:**

| Hipótese | Resultado |
|---|---|
| Verde mínimo de 5 s | Rejeitado: instável, com um episódio de 106 s |
| Colisão atribuída | Corrige uma contaminação da recompensa (≈ 50% do módulo vinha de colisões externas), mas não mudou o desempenho |
| Supervisor a cada 15 s | Sem ganho sobre 30 s |
| Hierárquico contra independente | Sem ganho |

- **Quarto semáforo** (Ribeirão Claro × Av. Hélio Pellegrino, 27,5 m depois da Quatá):
  - É uma junção complexa: 25 links, ciclovias e 45 pares conflitantes dentro da mesma fase.
  - Controlá-lo com estratégias clássicas não melhorou o MARL (+0,25 a +2,3 s).
  - Decisão: **manter 3 agentes**.

Relatórios completos:
- `semaforo/integracao_insper/otimizacao_final/RELATORIO_OTIMIZACAO.md`;
- `semaforo/integracao_insper/quarto_semaforo/RELATORIO_QUARTO_SEMAFORO.md`;
- `semaforo/integracao_insper/resultados/bateria_principal_20261116/RESULTADOS.md` (bateria anterior).

## Modelo C — Parameter Sharing (experimento adicional, 16/11)

- **Arquitetura:** uma única Double DQN para os 3 agentes, com rede online, rede-alvo e replay compartilhados. Cada agente observa o próprio cruzamento e decide sozinho.
- **Representação canônica:** em Casa do Ator, a ordem das aproximações estava invertida em relação aos outros dois. A correção foi feita no adaptador, sem mudar o ambiente.
- **Orçamento:** o mesmo número de passos de gradiente por rede que o Modelo A. Detalhes em `semaforo/integracao_insper/parameter_sharing/`.

| | A: independentes | C: parameter sharing |
|---|---:|---:|
| Validação (221–225) | 20,88 ± 1,39 | 20,36 ± 0,58 |
| Moderada nova (261–270) | 11,90 | 11,09 (−0,81 s, melhor em 10/10 demandas) |
| Intensa nova (251–260) | 21,76 | 22,50 (+0,74 ± 1,25 s, n.s.) |
| Saturada nova (271–280): episódios travados | 1/50 | **15/50** (2 dos 5 modelos) |

Original atuado nas mesmas demandas: 5,47 / 15,90 / 42,19 s.

- **Transferência:** treinada só com Gomes de Carvalho e Quatá, a política controlou Casa do Ator, que nunca viu, com fila de 2,81 veículos.
  - Compara com 2,67 do C completo, 2,54 do A e 3,02 do clássico com as mesmas regras.
  - A espera no corredor não mudou: 22,59 s.
- **Conclusão:** o C é competitivo com 1/3 dos parâmetros e transfere para um cruzamento compatível, mas é menos robusto na saturação e não supera o original.
- Relatório: `semaforo/integracao_insper/parameter_sharing/RELATORIO_PS.md`.
- Gráficos: `graficos/D1_*`, `D2_*` e `D3_*`.

### Zero-shot C3 → C5 (sem treino)

Os mesmos pesos do Modelo C controlaram 5 cruzamentos: os 3 do corredor mais Fiandeiras × Clodomiro e Fiandeiras × Atílio Innocenti. As sementes de demanda intensa são novas (291–300).

- **Segurança:** 0 violações e 0 colisões nos 5 cruzamentos; os outros 9 semáforos ficaram no programa original.
- **Corredor e rede:** sem mudança significativa (corredor +0,33 ± 1,26 s; rede +0,41 ± 1,14 s).
- **Cruzamentos novos:** a espera **piorou**, +0,55 s por veículo, pior em 10/10 demandas e em todos os 5 checkpoints.
  - A política troca de fase demais em cruzamentos quase vazios: 127 contra 48 trocas.
  - Ficou pior que o original e que o clássico com as mesmas regras.
- **Demanda baixa nos novos:** 65 e 363 veículos por episódio. Isso limita a conclusão.
- **Conclusão:** transferência **funcional**, não **eficiente**.
- Relatório: `semaforo/integracao_insper/parameter_sharing/experimento_c5/RELATORIO_C5.md`. Gráficos: `graficos/E1_*` e `E2_*`.

### C5 treinado do zero (5 agentes, uma DQN compartilhada)

- **Desenho:** a mesma Double DQN do Modelo C, inicializada aleatoriamente e treinada com os 5 agentes desde o primeiro episódio.
  - Hiperparâmetros do C3, com o mesmo número de gradientes por rede (cerca de 68 mil).
  - 5 sementes × 150 episódios, seleção na validação 221–225.
  - Teste único em sementes novas: intensa 331–340 e moderada 341–350.
  - Todos os comparadores rodaram nas mesmas demandas.
- **Segurança:** 0 travamentos, 0 violações e 0 colisões nos 5 cruzamentos, nas duas demandas.

| Espera nos 5 cruzamentos (s/veículo) | Original | C3 (nos 3) | C3 → C5 | Atuado com regras RL nos 5 | C5 treinado |
|---|---:|---:|---:|---:|---:|
| Intensa (331–340) | **6,80** | 9,12 | 9,79 | 9,65 | 9,60 |
| Moderada (341–350) | **2,54** | 4,98 | 5,11 | 4,50 | 5,15 |

- **C5 contra C3 → C5:** −0,19 ± 0,24 s na intensa e +0,03 ± 0,11 s na moderada, sem diferença significativa.
- **Atílio Innocenti piorou com o treino:** 3,37 contra 2,83 s, com 97 contra 60 trocas por episódio.
- **Causa provável:** a demanda nos novos é baixa (59% das decisões em Atílio com o cruzamento vazio), e a recompensa não cobra por trocar de fase.
- **Custo:** +3% de tempo de treino e +70% de experiências, com o mesmo número de gradientes.
- **Conclusão:** o parameter sharing aprende com 5 agentes, mas não aproveita os 2 cruzamentos de baixo volume. O C3 (novos no programa original) continua sendo a melhor configuração de RL, e o original continua vencendo.
- O C5-B (demanda recalibrada) não foi executado por falta de tempo.
- Relatório: `semaforo/integracao_insper/parameter_sharing/treinamento_c5/RELATORIO_TREINO_C5.md`. Gráficos: `graficos/F1_*` a `F4_*`.

## Modelos

- Em `semaforo/integracao_insper/modelos_finais/` estão as 30 políticas do teste final (6 braços × 5 sementes, cerca de 2,5 MB), com `manifesto.json` (origem, SHA-256, configuração).
- **Recomendado:** `modelos_finais/A_col/s1..s5`.
- Hierárquico: `modelos_finais/B_col_s15/`.

## Gráficos

- `graficos/C1_insper_teste_espera_media.png`: espera no corredor e na rede, todos os controladores.
- `graficos/C2_insper_teste_p95.png`: P95.
- `graficos/C3_insper_validacao.png`: evolução da validação ao longo dos checkpoints.
- `graficos/C4_insper_supervisor_30_vs_15.png`: supervisor a 30 s contra 15 s, pareado por semente.
