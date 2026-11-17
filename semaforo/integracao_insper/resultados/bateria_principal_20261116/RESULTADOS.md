# Bateria principal: Multi-Agent no corredor Insper (cenário intenso)

Rodada de 15/11/2026, das 19:58 às 21:31 (horário de Brasília).

O programa semafórico original atuado obteve a **menor espera média** no teste
final. Os dois modelos Multi-Agent ficaram cerca de 5 s piores no corredor,
porém com muito menos variação entre demandas. O supervisor **não melhorou** o
desempenho em relação aos agentes independentes: a diferença ficou dentro do
ruído entre sementes.

## O que foi executado

| Etapa | Quantidade | Tempo de parede |
|---|---|---|
| Teste de paralelismo | 4, 8 e 12 processos | ~2,5 min |
| Treinos | **10/10 concluídos**: 2 modelos × 5 sementes × 150 episódios = **1.500 episódios** | **93 min** (10 processos) |
| Validação | 10 treinos × 6 checkpoints × 3 sementes + original = **183 episódios** | ~11 min |
| Teste final | 10 modelos + original + Max-Pressure, 5 sementes = **60 episódios** | ~4 min |

O treino levou em média 36,4 a 37,1 s por episódio, com 10 processos simultâneos.

**Paralelismo** (máquina com 8 núcleos físicos e 16 GB de RAM):

| Processos | Episódios por hora |
|---:|---:|
| 4 | 338 |
| 8 | 593 |
| 12 | 735 |

Com 10 processos, todos os treinos rodaram juntos, sem uma segunda leva.

**Retomada:** a cada 25 episódios cada treino salva a política (`politica_epNNNN.pt`) e um checkpoint completo (`retomada.pt`, com replay, otimizador e estado do gerador aleatório). `treinar_marl_insper.py` continua automaticamente a partir dele. Nenhum treino precisou ser retomado.

**Sementes de tráfego:** nenhuma foi usada em mais de uma função.

| Função | Sementes | Pasta de demanda |
|---|---|---|
| Treino | 1001–1030 | `intenso_treino` |
| Validação | 221–223 | `intenso_validacao` |
| Teste final | 231–235 | `intenso_teste` |

Todas foram geradas com o mesmo método e o mesmo volume do nível intenso.
Todos os controladores usaram exatamente as mesmas demandas, a mesma configuração
do SUMO e o mesmo código de métricas (`ambiente_marl_insper.py`).

## Diferença de métrica: 14,5 s × 18,6 s

O valor de 18,6 s da avaliação preliminar **excluía os veículos que não pararam
nenhuma vez**: o dicionário só registrava veículos com espera maior que zero.

A métrica foi corrigida antes da bateria. Agora ela é a média, sobre todos os
veículos que chegaram a uma via de entrada dos 3 cruzamentos, do tempo parado
nas áreas de chegada (100 m) e dentro dos 3 cruzamentos, a partir de 300 s.
Ela inclui os veículos com espera zero.

Conferência no programa original, sementes 211–215
(`resultados/20261115T225710Z_conferencia_metrica_corredor`):
- **14,68 s** com a definição nova (a partir de 300 s);
- **14,47 s** contando desde t = 0, como na calibração (14,5 s).

Os números preliminares (18,6 / 26–33 s) não devem ser misturados com os desta bateria.

## Seleção de checkpoints (validação, sementes 221–223)

O critério foi fixado antes da validação, em `validacao/criterio.json`.

- **Elegível:** 3/3 episódios válidos, 0 violações de segurança, 0 colisões nos cruzamentos controlados, ≥ 99% de viagens concluídas e no máximo 1 teletransporte por episódio.
- **Ordem:** menor espera média no corredor. Se a diferença para o melhor for menor que 2%, vence o menor P95; depois, o menor bloqueio da saída.

Todos os 60 checkpoints foram elegíveis, e nenhum episódio de validação foi
inválido. O original obteve 14,87 s na validação.

| Treino | Checkpoint escolhido | Espera no corredor na validação (s) |
|---|---|---:|
| independente s1 | ep 25 | 19,95 |
| independente s2 | ep 50 | 22,03 |
| independente s3 | ep 100 | 20,35 |
| independente s4 | ep 125 | 22,08 |
| independente s5 | ep 150 | 20,35 |
| hierárquico s1 | ep 150 | 20,84 |
| hierárquico s2 | ep 100 | 22,31 |
| hierárquico s3 | ep 125 | 24,32 |
| hierárquico s4 | ep 125 | 20,58 |
| hierárquico s5 | ep 100 | 21,60 |

A curva de validação (gráfico 2) se estabiliza perto de 23–24 s a partir do
episódio 50 (A) e do episódio 100 (B). O hierárquico começa pior: o supervisor
só passa a aprender depois de cerca de 17 episódios.

## Teste final (sementes 231–235)

Fonte: `relatorio/tabela_final.md`.

- Modelos: média ± dp entre as 5 sementes de treino; cada uma é a média das 5 sementes de teste.
- Original e Max-Pressure: média ± dp entre as 5 sementes de teste.

| Métrica | Original | Max-Pressure | Independente (A) | Hierárquico (B) |
|---|---:|---:|---:|---:|
| **Espera média no corredor (s)** | **17,77 ± 6,18** | 57,08 ± 6,04 | 22,71 ± 1,54 | 22,63 ± 0,60 |
| P95 no corredor (s) | 60,27 ± 21,96 | 219,38 ± 51,63 | 61,43 ± 4,49 | 60,65 ± 1,89 |
| Espera média na rede (s) | 43,44 ± 6,10 | 102,06 ± 6,70 | 47,82 ± 1,41 | 47,60 ± 1,03 |
| P95 na rede (s) | 125,25 ± 14,04 | 344,46 ± 55,30 | 127,89 ± 3,56 | 126,52 ± 1,96 |
| Fila média Gomes de Carvalho / Casa do Ator / Quatá | 2,38 / 2,18 / 4,82 | 13,49 / 4,99 / 7,79 | 2,95 / 2,73 / 6,22 | 2,99 / 2,67 / 6,23 |
| Fila máxima (mesma ordem) | 19,6 / 17,0 / 24,0 | 31,2 / 17,2 / 27,8 | 15,7 / 16,0 / 25,0 | 15,6 / 15,2 / 24,7 |
| Viagens concluídas | 100% | 100% | 100% | 100% |
| Bloqueio da saída do corredor (s) | 40,2 ± 11,8 | 64,8 ± 13,7 | 72,7 ± 9,0 | 73,6 ± 5,4 |
| Teletransportes | 0 | 32 | 0 | 0 |
| Colisões (nos cruzamentos controlados) | 6 (0) | 1 (0) | 0 | 0 |
| Violações de segurança | 0 | 0 | 0 | 0 |
| Avaliações inválidas | 0/5 | 0/5 | 0/25 | 0/25 |

Espera no corredor por semente de teste (s); para A e B, média dos 5 modelos e faixa:

| Semente | Original | A | B |
|---|---:|---|---|
| 231 | 16,8 | 23,7 (22,2–25,7) | 25,2 (22,1–27,5) |
| 232 | **28,5** | 26,3 (22,4–30,0) | **26,0** (23,4–30,5) |
| 233 | 12,7 | 21,1 | 21,0 |
| 234 | 14,9 | 22,3 | 21,7 |
| 235 | 16,0 | 20,2 | 19,3 |

O original é melhor em 4 das 5 sementes. Na semente 232 ele piorou (28,5 s) e
teve 6 contatos na junção 1550389898, fora do corredor. Nessa semente os modelos
Multi-Agent ficaram levemente melhores.

**Supervisor (B) × independentes (A):** a comparação pareada por semente de
treino, nas mesmas demandas de teste, deu B − A = +0,04, −2,36, +1,52, +1,96 e
−1,55 s. A média é −0,08 s.

**Não há ganho do supervisor.** O único efeito observado é uma variação menor
entre sementes de treino (dp de 0,60 contra 1,54 s).

Gráficos em `relatorio/`:
1. `1_treino_recompensas.png`: recompensas e espera ao longo do treino.
2. `2_validacao_checkpoints.png`: espera na validação por checkpoint.
3. `3_teste_espera_media.png`: espera média no teste final.
4. `4_teste_p95.png`: P95 no teste final.
5. `5_teste_filas.png`: filas nos três cruzamentos.

## Eventos registrados (nada foi descartado)

**Treino (1.500 episódios):**
- 9 episódios inválidos:
  - independente: 5 por menos de 95% de viagens concluídas e 2 por travamento (rede parada);
  - hierárquico: 2 por menos de 95% concluídas.
- Teletransportes:
  - 944 episódios sem nenhum, 67 com 1 (ocasional) e 489 com mais de 1 (elevado);
  - 444 dos episódios com teletransportes elevados ocorreram nos episódios 1 a 50, ainda com exploração alta, e só 3 depois do episódio 100.
- 59 colisões, **nenhuma nos cruzamentos controlados**:
  - 50 na junção sem semáforo 5087305044, a montante da Quatá;
  - 9 na 1550389898.
- 0 violações de segurança.

**Validação:** 0 inválidos, 2 teletransportes, 3 colisões fora dos controlados, 0 violações.

**Teste:** veja a tabela acima. O Max-Pressure teve de 3 a 9 teletransportes por semente.

## Possíveis causas do resultado negativo

1. **O programa original é forte nesta demanda.**
   - O controle atuado usa verde mínimo de 5 s e encerra o verde quando o fluxo se esgota.
   - O controlador seguro exige 10 s de verde mínimo e acrescenta 2 s de vermelho geral a cada troca. São regras obrigatórias de segurança, mas elas aumentam o tempo perdido por troca.
   - A comparação é justa quanto às demandas e às métricas, mas não quanto às regras de troca de fase.
2. **Ruído na recompensa.**
   - A penalidade de colisão (−10.000 para todos os agentes) vem de junções que nenhum dos agentes controla, como a 5087305044.
   - Os saltos no gráfico 1 mostram que essa penalidade domina a recompensa. É o mesmo problema de atribuição de crédito já observado no Cologne8.
3. **Orçamento curto.** A exploração chega ao mínimo por volta do episódio 80, sobrando cerca de 70 episódios quase sem exploração. Não houve ajuste de hiperparâmetros.
4. **O supervisor tem pouco a coordenar.**
   - A fila sobe entre os cruzamentos, mas o volume e o espaçamento curto (cerca de 96 m) limitam o efeito de prioridades de 30 s.
   - O supervisor só começa a aprender por volta do episódio 17.
5. **Max-Pressure ruim.** Ele usa só os veículos parados na via imediatamente controlada (como no Cologne8). Isso é inadequado aqui, porque algumas vias de chegada são muito curtas (Quatá com 7,1 m).

## Recomendação para o trabalho final

- Apresentar os resultados como estão, nesta pasta: original melhor em média; Multi-Agent independente e hierárquico equivalentes entre si, cerca de 5 s piores no corredor e cerca de 4 s piores na rede, porém mais estáveis entre demandas (dp de 0,6 a 1,5 s contra 6,2 s).
- Destacar como contribuições:
  - o ambiente seguro (0 violações em 1.743 episódios);
  - a separação das sementes de treino, validação e teste;
  - o registro explícito de episódios inválidos e de teletransportes.
- Não afirmar que o supervisor melhora o desempenho. Os dados não sustentam isso.
- Citar as limitações acima, em especial o tempo perdido imposto pelo controlador seguro e a atribuição da penalidade de colisão. Elas são os próximos passos naturais: uma referência atuada com as mesmas regras de segurança, a penalidade de colisão só para os cruzamentos controlados e mais episódios.
