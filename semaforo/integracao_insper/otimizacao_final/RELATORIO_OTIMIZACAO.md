# Otimização final do MARL no corredor Insper

Corredor de 3 semáforos na Rua Ribeirão Claro (mão única): 476455095 (Gomes de Carvalho) → 40278305 (Casa do Ator) → 40278183 (Quatá), com cerca de 96 m entre cruzamentos. Cenário de demanda **intenso** (2000 veículos/h no corredor).

Este trabalho fica em `semaforo/integracao_insper/otimizacao_final/`.
- A bateria anterior (`resultados/bateria_principal_20261116/`), o cenário original do Insper e o Cologne8 não foram alterados.
- Os scripts v1 também não foram alterados; a versão nova é uma cópia (`*_v2.py`).
- Nada foi commitado.

## Resumo

- **Nenhuma das três mudanças melhorou o MARL de forma consistente**, e **nenhum controlador superou o programa original atuado**.
- No teste final inédito (sementes 241–250, 10 demandas, mesmas demandas para todos), a espera média no corredor foi:

| Controlador | Espera média no corredor (s) |
|---|---:|
| Original atuado | **15.48** |
| Melhor MARL no teste (A anterior) | 20.99 |
| MARL selecionado na validação (A com colisão atribuída) | 21.49 |
| Baseline clássico com as mesmas restrições do RL (verde mínimo 10) | 22.25 |

- O MARL ficou 5,5–7,3 s pior que o original em **10 de 10 demandas** e empatou estatisticamente com o baseline clássico com as mesmas restrições.
- A comparação com esse baseline indica que a perda vem principalmente das **regras operacionais em conjunto** (vermelho geral de 2 s, decisão a cada 5 s), e não da aprendizagem nem do verde mínimo. A ressalva é que o baseline é uma aproximação.

Resultado por hipótese:

| Hipótese | Resultado |
|---|---|
| Verde mínimo de 5 s | Rejeitada. Não melhorou e introduziu instabilidade (um episódio catastrófico no teste). |
| Contaminação da recompensa por colisões externas | Confirmada (≈ 50% do módulo da recompensa local) e corrigida. A correção não mudou o desempenho de forma mensurável. |
| Supervisor a 15 s | Sem ganho significativo sobre 30 s (−0,21 ± 1,28 s, 3/5 sementes). |
| Hierárquico vs independente | O hierárquico continua sem ganho sobre o independente. |
## 1. Hipóteses investigadas e o que a investigação mostrou

### Problema 1 — restrições operacionais

| | Original atuado (SUMO) | RL (v1) |
|---|---|---|
| Verde mínimo | 5 s (minDur) | 10 s |
| Verde máximo | 50 s (maxDur) | 60 s (condicional: só troca se houver demanda no vermelho) |
| Amarelo | 3 s | 3 s (do próprio programa) |
| Vermelho geral | nenhum | 2 s |
| Tempo perdido por troca | 3 s | 5 s |
| Frequência de decisão | a cada segundo (detectores, max-gap) | a cada 5 s |

- Na bateria anterior o original fez cerca de 204–269 verdes por semáforo por episódio, com duração média de 10–15 s. O RL v1 fez cerca de 108–153, com duração média de 17–27 s. O original troca mais e com verdes mais curtos.
- Mudança testada: verde mínimo de 5 s, igual ao minDur do programa. Ela passou nas verificações de segurança: verde ≥ 5 s, amarelo de 3 s e vermelho geral de 2 s em todas as trocas, sem nenhum par de verdes conflitantes.
- **O vermelho geral de 2 s foi mantido.** Não fiz a análise de segurança exigida para removê-lo (tempos de travessia, velocidades e geometria das áreas de conflito). Esses 2 s continuam sendo uma desvantagem estrutural de 2 s por troca em relação ao original.
- A decisão a cada 5 s também continua sendo uma diferença em relação ao original.

### Problema 2 — penalidade de colisão contaminada

- Na v1, cada novo contato em **qualquer ponto da rede** custava −10000 a **todos** os atores.
- Nos 1500 episódios de treino da bateria anterior houve 59 contatos:
  - 50 na junção 5087305044, uma confluência sem semáforo a montante da Quatá, dentro da área de observação de 100 m. A relação com o semáforo é incerta.
  - 9 na junção 1550389898, um semáforo externo a cerca de 400 m que também registra colisões sob o programa original.
  - 0 dentro dos três cruzamentos controlados.
- Esses contatos ocorreram em apenas 50 de 1500 episódios, mas somaram cerca de **49,7% do módulo total da recompensa local**. A contaminação ficou confirmada.

Nova recompensa (`colisao = "atribuida"`), implementada em `classificar_colisao` / `penalidade_colisao` no ambiente v2:

| classe do contato | critério espacial | penalidade (−10000) |
|---|---|---|
| `controlado` | dentro de um dos 3 cruzamentos, ou numa via que entra ou sai dele | só o(s) agente(s) local(is) desse cruzamento, mais o supervisor |
| `externa_area_observacao` | via ou junção sem semáforo dentro das áreas de 100 m | nenhuma (registrada) |
| `externa_distante` | resto da rede | nenhuma (registrada) |

- A causalidade não é inferida pela proximidade.
  - A classe `externa_area_observacao` registra explicitamente a incerteza: o contato fica nas métricas de segurança e nos relatórios, mas não gera penalidade.
  - Um contato `controlado` é penalizado mesmo que a causa seja o modelo de mudança de faixa do SUMO, e não o semáforo. Essa é a opção conservadora.
- A penalidade de teletransporte (−10 por ator) não mudou. Os teletransportes ocorrem quase todos na via a montante da Gomes de Carvalho (27579109#1/#2), por transbordamento da fila da aproximação controlada.
- No treino novo, as colisões externas continuaram ocorrendo nas mesmas junções: 29 em A_col, todas na 5087305044. Agora elas não geram penalidade. O módulo da recompensa local por treino caiu de 1,66 M (A_v1) para 0,75 M (A_col), com o mesmo número de colisões.

### Problema 3 — supervisor lento

- O supervisor escolhe a cada 30 s uma de 4 orientações. Ele não comanda fases diretamente.
- Ele afeta os locais de duas formas: pelo one-hot de orientação na observação deles e pelo termo de recompensa 0,5·custo do semáforo priorizado.
- A observação do supervisor inclui as vias entre os cruzamentos, então ele vê os veículos em trânsito.
- Mudança testada: supervisor a cada **15 s** (dobra as transições; o epsilon decai em cerca de 42 episódios em vez de cerca de 83).
- 10 s fica implementado e testado (120 decisões por episódio curto), mas só seria treinado se 15 s superasse 30 s.
- A frequência do supervisor não afeta a segurança: ele não troca fases, e o controlador seguro continua impondo verde mínimo, amarelo, vermelho geral e verde máximo.
- 30 s continua disponível (`supervisor_s = 30`).

## 2. O que mudou no código (v2)

- `ambiente_marl_insper_v2.py`: ambiente com `config = {verde_minimo ∈ {5, 10}, colisao ∈ {global, atribuida}, supervisor_s ∈ {10, 15, 30}}`. O padrão (`CONFIG_V1`) reproduz exatamente a v1, o que foi verificado com checkpoints antigos (resultados idênticos).
  - Novo modo `atuado_equivalente`, descrito abaixo.
  - Registro de colisões por classe, local dos teletransportes, tempo de entreverdes e número de trocas.
- `treinar_marl_insper_v2.py`: grava a config no `configuracao.json` e em cada checkpoint. A retomada recusa checkpoints de outra config; checkpoints v1 são lidos com `CONFIG_V1`.
- `bateria_otimizacao.py`: braços, conferência programática das sementes, treino, validação, seleção e teste final único.
- `testar_otimizacao.py`: 39/39 verificações OK antes de qualquer treino:
  - equivalência v1/v2;
  - segurança sob as configs novas (há verdes de 5 s, nenhum conflito);
  - os outros 11 semáforos continuam no programa original;
  - dimensões 13/48 e gradientes;
  - número de decisões do supervisor a 15 s e 10 s;
  - salvar/carregar checkpoint com a config;
  - o replay guarda a ação executada (após a proteção de verde máximo);
  - os baselines são seguros.
- `relatorio_otimizacao.py`: gráficos e tabelas, só lendo resultados.

**Baseline clássico com as mesmas restrições (`atuado_equivalente`)** — é uma **aproximação**, não uma reprodução, do actuated do SUMO.
- Decide a cada 5 s depois do verde mínimo, com o mesmo amarelo de 3 s, vermelho geral de 2 s e verde máximo condicional de 60 s do RL.
- Mantém o verde se algum veículo que vai cruzar por um link verde está a no máximo 3 s da linha de retenção (ou parado a até 30 m, fila em descarga). Caso contrário, troca se há demanda no vermelho.
- Há duas versões: verde mínimo 10 (`atuado_eq_v10`) e 5 (`atuado_eq_v5`).
- **Max-Pressure** foi incluído com o rótulo preciso "fila só da faixa imediata, verde mínimo 10, mesmas regras de segurança". Não é o Max-Pressure clássico com pressão a jusante completa.

## 3. Desenho experimental

- Os braços usam as mesmas 5 sementes de modelo (1–5), as mesmas demandas de treino (1001–1030, na mesma ordem), 150 episódios e hiperparâmetros idênticos. Só muda o que o nome do braço indica. Nenhum checkpoint foi reaproveitado entre configs.

| braço | modelo | verde mín. | colisão | supervisor | testa |
|---|---|---|---|---|---|
| A_v1 | independente | 10 | global | — | anterior (só leitura) |
| B_v1 | hierárquico | 10 | global | 30 s | anterior (só leitura) |
| A_col | independente | 10 | atribuída | — | Exp. 2: recompensa (vs A_v1) |
| A_col_v5 | independente | 5 | atribuída | — | Exp. 1: verde mínimo (vs A_col) |
| B_col_s30 | hierárquico | 10 | atribuída | 30 s | Exp. 3: supervisor (vs A_col) |
| B_col_s15 | hierárquico | 10 | atribuída | 15 s | Exp. 3: frequência (vs B_col_s30) |

- **Sementes de tráfego** (conferidas por programa contra todas as já usadas; registradas em `resultados/sementes.json`):
  - treino 1001–1030;
  - validação 221–225. As sementes 221–223 já eram de validação. As sementes 224 e 225 foram usadas só em episódios curtos de verificação de código, nunca para escolher configuração;
  - **teste final inédito 241–250**, executado uma única vez no fim. As sementes de teste antigas (211–215, 231–235) não foram usadas.
- **Seleção** (somente na validação):
  - Elegibilidade do checkpoint: 5/5 episódios válidos, 0 violações, 0 colisões nos cruzamentos controlados, ≥ 99% das viagens concluídas e ≤ 1 teletransporte por episódio.
  - Ordem: menor espera média no corredor; em empate < 2%, menor P95; depois menor bloqueio da saída; depois o checkpoint mais antigo.
  - Uma mudança só conta como melhora se a média for melhor **e** pelo menos 4 de 5 sementes de modelo melhorarem (comparação pareada).
- **Métrica principal**: espera média no corredor. São os segundos parados nas áreas de 100 m de aproximação e dentro das 3 junções, após 300 s de aquecimento, divididos por todos os veículos que entraram por uma via de entrada direta (inclui os veículos com espera zero). É a mesma definição da bateria anterior.
- O original foi recalculado nas sementes novas.

## 4. Decisões tomadas na validação

Detalhes em `resultados/decisoes.md`.

| braço (melhor checkpoint por semente) | espera no corredor, validação (s) | pareado | decisão |
|---|---|---|---|
| A_v1 | 21.27 ± 0.86 | — | — |
| A_col | 20.88 ± 1.39 | −0.39 vs A_v1, 3/5 sementes | mantida como correção, mas **não** é melhora pela regra |
| A_col_v5 | 21.46 ± 0.59 | +0.20 vs A_v1, 2/5 sementes | verde de 5 s rejeitado |
| B_v1 | 21.82 ± 1.54 | — | — |
| B_col_s30 | 22.08 ± 0.71 | +1.21 vs A_col, 1/5 sementes | supervisor sem ganho |
| B_col_s15 | 21.75 ± 1.36 | −0.33 vs B_col_s30, 3/5 sementes | não é melhora; 10 s não treinado |
| original atuado | 14.63 | | |
| atuado equivalente v10 / v5 | 21.98 / 22.99 | | |
| Max-Pressure (fila imediata) | 55.99 | | |

- Os braços hierárquicos usaram a configuração local de verde 10 com colisão atribuída, porque o verde de 5 s não melhorou nem o RL nem o baseline clássico equivalente.
- O supervisor de 10 s não foi treinado: o de 15 s não superou o de 30 s pelo critério, e a instrução era não prolongar experimentos sem evidência de melhoria.

Checkpoints selecionados (episódio de treino por semente de modelo 1–5; arquivos `politica_epXXXX.pt`):

| braço | s1 | s2 | s3 | s4 | s5 | pasta |
|---|---|---|---|---|---|---|
| A_v1 | 25 | 50 | 100 | 125 | 150 | `../resultados/bateria_principal_20261116/treinos/independente_s*` |
| B_v1 | 150 | 100 | 150 | 125 | 100 | `../resultados/bateria_principal_20261116/treinos/hierarquico_s*` |
| A_col | 75 | 50 | 100 | 125 | 50 | `resultados/treinos/A_col_s*` |
| A_col_v5 | 150 | 150 | 100 | 100 | 150 | `resultados/treinos/A_col_v5_s*` |
| B_col_s30 | 100 | 125 | 125 | 150 | 75 | `resultados/treinos/B_col_s30_s*` |
| B_col_s15 | 150 | 125 | 125 | 125 | 50 | `resultados/treinos/B_col_s15_s*` |

Os caminhos completos estão em `resultados/teste_final/teste_final.json` (`checkpoints`).

## 5. Resultados do teste final (sementes 241–250, executado uma vez)

- Todas as 340 avaliações foram válidas, com 100% das viagens concluídas e 0 violações de segurança.
- Teletransportes: 0 para todos os controladores, exceto o Max-Pressure (69).
- Nenhuma colisão nos 3 cruzamentos controlados. As colisões registradas são externas:
  - 9 na classe `externa_area_observacao`, na confluência 5087305044;
  - 1 na classe `externa_distante`.
- Tabela completa, com todas as métricas, variabilidade e ICs: `resultados/relatorio/tabela_final.md`.

Controladores de RL: média das 5 sementes de modelo, cada uma a média das 10 demandas; ± desvio-padrão entre as sementes de modelo. Baselines: ± desvio-padrão entre as 10 demandas.

| Controlador | Espera corredor (s) | P95 corredor (s) | Espera rede (s) | P95 rede (s) | Bloqueio saída (s) | Entreverdes 3 TLS (s) |
|---|---:|---:|---:|---:|---:|---:|
| **Original atuado (SUMO)** | **15.48 ± 3.03** | **53.8 ± 10.9** | **40.47 ± 2.51** | **119.0 ± 6.0** | **34.3** | 2225 |
| Atuado c/ regras RL (verde 10) — aproximação | 22.25 ± 2.97 | 66.1 ± 13.3 | 46.54 ± 2.91 | 125.3 ± 6.8 | 57.8 | 1733 |
| Atuado c/ regras RL (verde 5) — aproximação | 22.01 ± 1.81 | 67.0 ± 5.8 | 46.50 ± 1.71 | 127.9 ± 4.9 | 43.1 | 1916 |
| Max-Pressure (fila só faixa imediata, verde 10) | 54.77 ± 6.20 | 234.6 ± 22.1 | 102.41 ± 9.20 | 347.5 ± 28.6 | 57.5 | 3124 |
| A anterior (v1) | 20.99 ± 0.86 | 56.3 ± 2.3 | 45.63 ± 1.00 | 121.8 ± 2.6 | 68.8 | 1990 |
| B anterior (v1) | 21.84 ± 1.16 | 58.7 ± 3.8 | 46.39 ± 1.13 | 123.1 ± 1.8 | 74.7 | 1963 |
| **A otimizado: colisão atribuída** (selecionado na validação) | 21.49 ± 1.32 | 58.5 ± 3.5 | 45.97 ± 1.15 | 123.7 ± 2.4 | 71.6 | 1944 |
| A: colisão atribuída + verde 5 | 22.83 ± 3.77 | 73.7 ± 33.5 | 47.26 ± 3.05 | 136.5 ± 30.5 | 61.6 | 2409 |
| B otimizado: colisão atribuída, sup 30 s | 22.04 ± 0.68 | 59.2 ± 1.6 | 46.48 ± 0.60 | 124.2 ± 1.2 | 75.0 | 2002 |
| **B otimizado: colisão atribuída, sup 15 s** | 21.84 ± 0.48 | 59.9 ± 2.0 | 46.37 ± 0.48 | 124.3 ± 1.9 | 79.5 | 1985 |

- O original recalculado nas sementes novas dá **15,48 s**. A referência de 17,8 s das sementes 231–235 não foi usada.
- Filas médias, em veículos parados até 100 m: o original tem 2,2 / 1,8 / 4,0 (Gomes de Carvalho / Casa do Ator / Quatá); o RL tem 3,0–3,5 / 2,2–2,6 / 5,5–5,8.
- A fila máxima é parecida em todos (15–24 veículos), exceto no Max-Pressure (31 na Gomes de Carvalho).
- O original gasta mais tempo total em entreverdes (2225 s) que o RL (cerca de 1950 s), mas com 3 s por troca. Isso equivale a cerca de 740 trocas contra cerca de 390 do RL (5 s por troca): o original troca quase o dobro, com verdes mais curtos.
- O RL também passa mais tempo com a saída do corredor bloqueada (69–80 s contra 34 s).

### Comparações pareadas (Δ = depois − antes, pareada por semente de modelo; IC95 com t de 4 g.l.)

| Comparação | Δ espera corredor (s) | IC95 | sementes que melhoraram |
|---|---:|---:|---:|
| Recompensa: A_col − A_v1 | +0.50 | ±1.81 | 2/5 |
| Verde mínimo: A_col_v5 − A_col | +1.33 | ±3.29 | 2/5 |
| Supervisor: B_col_s30 − A_col | +0.55 | ±2.21 | 2/5 |
| Supervisor: B_col_s15 − A_col | +0.34 | ±1.52 | 1/5 |
| Frequência: B_col_s15 − B_col_s30 | −0.21 | ±1.28 | 3/5 |
| B otimizado (s15) − B anterior | −0.00 | ±1.21 | 1/5 |
| B anterior − A anterior | +0.85 | ±1.96 | 2/5 |

Todos os intervalos contêm zero. Pelo critério definido antes do teste (média melhor e pelo menos 4/5 sementes), **nenhuma mudança é uma melhora**.

### RL contra os baselines, pareado por demanda (10 demandas; média dos 5 modelos em cada demanda)

| Controlador | Δ vs original (s) | IC95 | Δ vs atuado com regras RL (mesmo verde) | IC95 |
|---|---:|---:|---:|---:|
| A anterior | +5.51 | ±2.01 | −1.26 (v10) | ±1.51 |
| A otimizado (col.) | +6.01 | ±2.20 | −0.76 (v10) | ±1.79 |
| A col. + verde 5 | +7.34 | ±4.48 | +0.82 (v5) | ±4.36 |
| B otimizado sup 30 | +6.56 | ±2.50 | −0.21 (v10) | ±2.07 |
| B otimizado sup 15 | +6.35 | ±2.46 | −0.42 (v10) | ±2.00 |
| B anterior | +6.36 | ±2.27 | −0.42 (v10) | ±1.44 |

- **O RL perde para o original em todas as 10 demandas** (0/10 vitórias), com diferença significativa (IC95 longe de zero).
- Contra o baseline clássico com as mesmas restrições, o RL fica ligeiramente melhor em média (−0,2 a −1,3 s), mas **sem significância** (os ICs contêm zero). Portanto a IA **não vence de forma demonstrável** nem o controle clássico com restrições equivalentes; só empata com ele.

### Variabilidade

Desvio-padrão da espera no corredor (s):

| Controlador | entre sementes de modelo | entre sementes de tráfego |
|---|---:|---:|
| Original | — | 3.03 |
| A anterior | 0.86 | 1.11 |
| A otimizado | 1.32 | 2.01 |
| A col. + verde 5 | 3.77 | 5.59 |
| B otimizado s30 | 0.68 | 1.43 |
| B otimizado s15 | 0.48 | 0.88 |

O verde de 5 s é instável:
- O modelo da semente 5 (ep150) teve **um episódio catastrófico na demanda 241**: espera média no corredor de 106 s, P95 de 843 s e fila de 58 veículos na Gomes de Carvalho. Ainda assim o episódio é válido (sem teletransportes e com 100% concluídas).
- Nas outras 9 demandas esse modelo ficou em 18,5–24 s.
- Na validação o mesmo checkpoint teve 20,8 s. O teste revelou uma falha de robustez que a validação de 5 demandas não captou.
- No treino, o A_col_v5 também teve mais episódios inválidos: 27/750 por não conclusão, contra 5/750 no A_col.

## 6. Respostas às perguntas

1. **O verde mínimo de 10 s realmente prejudicava a IA?**
   - Não há evidência disso. Com 5 s, nem o RL nem o baseline clássico melhoraram: no teste, o atuado equivalente foi 22,25 s com verde 10 e 22,01 s com verde 5; o RL A foi 21,49 s com verde 10 e 22,83 s com verde 5.
   - O que pesa é o conjunto das regras operacionais: o clássico submetido às regras do RL perde 6,8 s para o original.
   - Isso aponta para o vermelho geral de 2 s (5 s perdidos por troca contra 3 s) e para a decisão a cada 5 s, que não foram alterados.
   - Ressalva: o baseline equivalente é uma aproximação do actuated do SUMO, então parte desses 6,8 s pode vir da própria heurística.
2. **Reduzir para 5 s melhorou?**
   - Não. A diferença foi de +1,33 ± 3,29 s contra o A com verde 10 (2/5 sementes melhores).
   - O verde de 5 s fez o RL trocar mais (481 contra 388 trocas), mais episódios de treino ficaram inválidos (27 contra 5), e houve um episódio de teste catastrófico.
3. **A recompensa era afetada por colisões externas?**
   - Sim. Os contatos fora dos cruzamentos controlados somavam cerca de 50% do módulo da recompensa local na v1, embora tenham ocorrido em apenas cerca de 3% dos episódios.
   - Nenhum contato da v1 ocorreu dentro dos cruzamentos controlados.
4. **Corrigir essa penalização melhorou o aprendizado?**
   - Não de forma mensurável. Na validação: −0,39 s, 3/5 sementes. No teste: +0,50 ± 1,81 s, 2/5 sementes.
   - A correção remove um erro conceitual e reduz o módulo total da recompensa local (de 1,66 M para 0,75 M), mas não mudou a política aprendida de forma detectável.
   - Provável explicação: as penalidades externas eram raras e não ligadas às ações, então funcionavam como ruído e não como sinal sistemático.
5. **O supervisor de 15 s funcionou melhor que o de 30 s?**
   - Diferença pequena e não significativa: −0,21 ± 1,28 s no teste e −0,33 s na validação, em 3/5 sementes nos dois casos.
   - O de 15 s é um pouco mais estável entre sementes (dp 0,48 contra 0,68), mas não é melhor. Por isso o de 10 s não foi treinado.
6. **A arquitetura hierárquica superou os agentes independentes?**
   - Não. Com as mesmas regras e a mesma recompensa: B s30 − A = +0,55 ± 2,21 s e B s15 − A = +0,34 ± 1,52 s. O mesmo vale para as versões anteriores: B − A = +0,85 ± 1,96 s.
   - O hierárquico é um pouco mais consistente entre sementes, mas não é melhor em média.
7. **A nova IA superou o controle original atuado?**
   - Não. Nenhuma versão superou o original (15,48 s): todas ficaram 5,5–7,3 s piores, com significância, e perderam em 10/10 demandas.
   - Contra o clássico com restrições equivalentes houve empate estatístico (o RL fica 0,2–1,3 s melhor em média, mas os ICs contêm zero). **A IA não vence o original; no máximo empata com um clássico submetido às mesmas restrições.**
8. **As melhorias são consistentes entre sementes?**
   - Não houve melhoria consistente. Nenhuma comparação atingiu 4/5 sementes.
   - O verde de 5 s foi o caso mais inconsistente (dp 3,77 entre modelos, 5,59 entre demandas).
9. **Houve custo em P95, segurança ou viagens concluídas?**
   - Viagens concluídas: 100% em todos os controladores.
   - Segurança: 0 violações e 0 colisões nos cruzamentos controlados em todas as avaliações.
   - Exceção no treino: uma colisão lateral dentro da junção 40278183, durante mudança de faixa na mesma via interna, no A_col_v5 (semente 2, episódio 56). Houve 0 violações de sinal nesse episódio, então é um conflito do modelo de mudança de faixa do SUMO, e não verdes conflitantes. Ela foi classificada como `controlado` e penalizada.
   - P95: o verde de 5 s piorou muito o P95 (73,7 ± 33,5 s contra 58,5). Os demais otimizados ficaram com P95 parecido com as versões anteriores (58–60 s), e todos os RL acima do original (53,8 s).
   - Saída do corredor: todos os RL bloqueiam mais a saída que o original (69–80 s contra 34 s).
10. **Qual configuração usar na entrega final?** Ver seção 8.

## 7. Limitações

- O **vermelho geral de 2 s** foi mantido por segurança. Sem uma análise de áreas de conflito não dá para dizer quanto do déficit de cerca de 6,8 s ele explica. É o próximo experimento natural, condicionado a essa análise.
- A **decisão a cada 5 s** continua sendo uma desvantagem em relação ao actuated, que decide a cada segundo. Ela não foi testada.
- `atuado_equivalente` é uma **aproximação** do actuated do SUMO (gap de 3 s por veículo, sem detectores de laço), não uma reprodução. O Max-Pressure observa só a fila da faixa imediata e não é o Max-Pressure clássico com pressão a jusante.
- A classificação de colisões é **espacial**. Contatos na confluência 5087305044, dentro da área de observação, podem ter relação indireta com as filas do corredor; essa incerteza está registrada, mas não é resolvida.
- A amostra é pequena: 5 sementes de modelo, 5 demandas de validação e 10 de teste. O episódio catastrófico do verde de 5 s mostra que 5 demandas de validação não bastam para detectar falhas raras.
- O treino é curto: 150 episódios, com o epsilon chegando a 0,05 por volta do episódio 83 para os locais. As curvas de validação ficam praticamente estáveis do episódio 50 ao 150 (gráfico 3), sem sinal de que mais episódios ajudariam.
- Há um só nível de demanda (intenso). Os resultados não foram verificados em outros níveis.

## 8. Recomendação

- **Para a operação do corredor, o controle a usar é o programa original atuado do SUMO.** Ele foi o melhor em todas as métricas de espera, filas e bloqueio, em todas as demandas de teste.
- **Para apresentar o MARL**, a versão recomendada é o **Multi-Agent independente com colisão atribuída (A_col, verde mínimo 10 s, vermelho geral 2 s)**, com os checkpoints selecionados na validação acima.
  - Foi o melhor na validação (20,88 s) e corrige o erro conceitual da recompensa.
  - No teste ele é estatisticamente equivalente ao A anterior (21,49 contra 20,99 s, Δ +0,50 ± 1,81 s). Não deve ser apresentado como "melhor" que o anterior.
  - Por ter a recompensa correta, é a versão tecnicamente válida.
- Se a apresentação quiser mostrar a arquitetura hierárquica, use **B_col_s15**. É a mais estável entre sementes, mas sem ganho sobre a independente.
- **Não usar** o verde mínimo de 5 s.
- Mensagem honesta para a apresentação: o MARL aprende uma política equivalente a um controle clássico atuado submetido às mesmas restrições de segurança, mas essas restrições (principalmente os 5 s perdidos por troca e a decisão a cada 5 s) o deixam cerca de 6 s atrás do actuated original.

## 9. Arquivos para a apresentação

- Gráficos em `resultados/relatorio/`:
  - `1_teste_espera_media.png` (espera média no corredor e na rede, todos os controladores);
  - `2_teste_p95.png`;
  - `3_validacao_evolucao.png`;
  - `4_supervisor_30_vs_15.png`;
  - `5_efeito_recompensa_verde.png`;
  - `6_teste_filas.png`;
  - `7_treino_curvas.png` (espera e recompensa no treino, mostrando a queda do módulo da recompensa com a colisão atribuída).
- Tabelas: `resultados/relatorio/tabela_final.md` e `resultados/relatorio/comparacoes.json`.
- Dados brutos:
  - `resultados/teste_final/teste_final.json` (por semente);
  - `resultados/validacao/braco_*.json` e `baseline_*.json`;
  - `resultados/decisoes.md` (decisões tomadas na validação, antes do teste).

## 10. Reprodução

Na raiz do repositório, com o Python do Anaconda (torch e traci) e o SUMO 1.28:

```bash
PY="python -B -X utf8"   # Python com torch, traci e sumolib; SUMO 1.28 com SUMO_HOME definido
D=semaforo/integracao_insper/otimizacao_final
$PY $D/testar_otimizacao.py                                    # 39 verificações (equivalência v1/v2, segurança, replay)
$PY $D/bateria_otimizacao.py demandas                          # gera validação 221-225 e teste 241-250; confere sobreposições
$PY $D/bateria_otimizacao.py treinar --bracos A_col A_col_v5 --processos 10
$PY $D/bateria_otimizacao.py validar --bracos A_v1 B_v1 A_col A_col_v5 --baselines --processos 12
$PY $D/bateria_otimizacao.py comparar --bracos A_v1 A_col A_col_v5
$PY $D/bateria_otimizacao.py treinar --bracos B_col_s30 B_col_s15 --processos 10
$PY $D/bateria_otimizacao.py validar --bracos B_col_s30 B_col_s15 --processos 12
$PY $D/bateria_otimizacao.py comparar --bracos B_col_s30 B_col_s15
$PY $D/bateria_otimizacao.py testar --bracos A_v1 B_v1 A_col A_col_v5 B_col_s30 B_col_s15 --processos 12   # uma vez só
py -B -X utf8 $D/relatorio_otimizacao.py                       # gráficos e tabelas (matplotlib do py 3.14)
```

- Treino individual: `$PY $D/treinar_marl_insper_v2.py --modelo independente --semente 1 --episodios 150 --verde-minimo 10 --colisao atribuida --supervisor-s 30 --pasta <nova pasta>`.
- Tempos nesta máquina (Ryzen 9 8945HS, 16 GB):
  - cada lote de 10 treinos de 150 episódios leva cerca de 1,5 h com 10 processos;
  - validação de 4 braços mais baselines: cerca de 35 min;
  - teste final: cerca de 17 min.
- `testar` recusa rodar de novo se `resultados/teste_final/` já existir.
