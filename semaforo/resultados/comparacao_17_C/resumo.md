# Experimento 2: DQN de 17 entradas (observa a espera) - dinamica C

Media de 10 sementes de teste (+- dp). Esperas, P95 e maximos INCLUEM veiculos nao atendidos. Nao atendidos e intervencoes: total nas 10 sementes (nos grupos, das 3 redes). Espera max: a maior. Linhas em negrito: media das 3 redes de cada geracao.

## equilibrado

| controlador | espera media (s) | espera media concluidos (s) | P95 geral (s) | P95 N (s) | P95 L (s) | P95 S (s) | P95 O (s) | pior P95 aprox. (s) | P95 secundarias (s) | espera max c/ nao atendidos (s) | nao atendidos | trocas/h | intervencoes hora | intervencoes escoamento |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Webster | 28.7 +- 0.9 | 28.7 | 60.6 +- 0.8 | 60.7 | 61.1 | 62.1 | 60.4 | 64.7 +- 5.0 | - | 120 | 0 | 180.0 | 0 | 0 |
| Max-Pressure teto (recal. C) | 24.7 +- 1.5 | 24.7 | 59.8 +- 2.3 | 57.6 | 57.1 | 60.1 | 63.4 | 64.8 +- 5.4 | - | 159 | 0 | 236.3 | 0 | 0 |
| DQN C seed0 | 23.4 +- 0.8 | 23.4 | 64.6 +- 3.9 | 66.0 | 61.1 | 54.3 | 72.8 | 73.9 +- 6.3 | - | 157 | 0 | 220.2 | 0 | 10 |
| DQN C seed1 | 23.7 +- 1.0 | 23.6 | 63.0 +- 1.5 | 69.7 | 55.4 | 52.9 | 68.9 | 71.2 +- 3.1 | - | 1183 | 2 | 225.1 | 0 | 0 |
| DQN C seed2 | 23.8 +- 1.2 | 23.6 | 64.3 +- 2.7 | 53.6 | 62.8 | 55.1 | 80.1 | 80.1 +- 5.8 | - | 1195 | 3 | 217.9 | 0 | 0 |
| DQN excesso C seed0 | 23.4 +- 0.9 | 23.4 | 61.2 +- 1.4 | 50.3 | 62.4 | 63.8 | 65.5 | 67.9 +- 2.6 | - | 143 | 0 | 229.9 | 0 | 0 |
| DQN excesso C seed1 | 23.1 +- 0.6 | 23.1 | 62.1 +- 1.9 | 57.1 | 60.0 | 57.5 | 71.3 | 71.3 +- 5.1 | - | 156 | 0 | 225.8 | 0 | 0 |
| DQN excesso C seed2 | 23.2 +- 0.7 | 23.2 | 61.2 +- 2.1 | 63.1 | 68.3 | 58.1 | 53.9 | 69.0 +- 5.4 | - | 151 | 0 | 224.0 | 0 | 0 |
| DQN excesso17 C seed0 | 22.8 +- 0.8 | 22.8 | 58.9 +- 2.5 | 55.9 | 63.4 | 50.9 | 63.5 | 66.0 +- 4.2 | - | 136 | 0 | 221.6 | 0 | 0 |
| DQN excesso17 C seed1 | 22.7 +- 0.7 | 22.7 | 56.6 +- 2.0 | 61.1 | 59.3 | 49.9 | 53.6 | 61.8 +- 2.7 | - | 136 | 0 | 227.0 | 0 | 0 |
| DQN excesso17 C seed2 | 22.5 +- 0.6 | 22.5 | 57.7 +- 2.0 | 58.2 | 57.4 | 57.6 | 56.5 | 61.2 +- 2.6 | - | 115 | 0 | 223.4 | 0 | 0 |
| **A: fila, 13 entradas** | 23.6 +- 0.8 | 23.5 | 64.0 +- 2.3 | 63.1 | 59.8 | 54.1 | 73.9 | 75.1 +- 3.8 | - | 1195 | 5 | 221.1 | 0 | 10 |
| **B: fila_excesso, 13 entradas** | 23.2 +- 0.4 | 23.2 | 61.5 +- 0.9 | 56.8 | 63.6 | 59.8 | 63.6 | 69.4 +- 2.2 | - | 156 | 0 | 226.6 | 0 | 0 |
| **C: fila_excesso, 17 entradas** | 22.7 +- 0.6 | 22.7 | 57.7 +- 1.7 | 58.4 | 60.0 | 52.8 | 57.9 | 63.0 +- 2.3 | - | 136 | 0 | 224.0 | 0 | 0 |

- **C - B** (pareado por semente): espera media (s) -0.6 (-2.4%), melhor/pior em 9/1; P95 geral (s) -3.8 (-6.1%), melhor/pior em 10/0; pior P95 aprox. (s) -6.4 (-9.2%), melhor/pior em 10/0; espera max c/ nao atendidos (s) -7.8 (-6.7%), melhor/pior em 7/3; nao atendidos +0.0, melhor/pior em 0/0; trocas/h -2.6 (-1.1%), melhor/pior em 10/0
- **C - A** (pareado por semente): espera media (s) -0.9 (-4.0%), melhor/pior em 10/0; P95 geral (s) -6.2 (-9.7%), melhor/pior em 10/0; pior P95 aprox. (s) -12.1 (-16.1%), melhor/pior em 10/0; espera max c/ nao atendidos (s) -160.1 (-59.7%), melhor/pior em 9/1; nao atendidos -0.2 (-100.0%), melhor/pior em 4/0; trocas/h +2.9 (+1.3%), melhor/pior em 0/10
- **B - A** (pareado por semente): espera media (s) -0.4 (-1.6%), melhor/pior em 8/2; P95 geral (s) -2.5 (-3.9%), melhor/pior em 8/2; pior P95 aprox. (s) -5.7 (-7.5%), melhor/pior em 10/0; espera max c/ nao atendidos (s) -152.3 (-56.8%), melhor/pior em 9/1; nao atendidos -0.2 (-100.0%), melhor/pior em 4/0; trocas/h +5.5 (+2.5%), melhor/pior em 0/10

Variabilidade entre as 3 sementes de treino (media de cada rede; min - max):

- A: fila, 13 entradas: espera media (s) 23.4 - 23.8 (dp 0.2); P95 geral (s) 63.0 - 64.6 (dp 0.9); pior P95 aprox. (s) 71.2 - 80.1 (dp 4.6); espera max c/ nao atendidos (s) 127.5 - 339.8 (dp 121.9); nao atendidos 0.0 - 0.3 (dp 0.2)
- B: fila_excesso, 13 entradas: espera media (s) 23.1 - 23.4 (dp 0.2); P95 geral (s) 61.2 - 62.1 (dp 0.5); pior P95 aprox. (s) 67.9 - 71.3 (dp 1.7); espera max c/ nao atendidos (s) 113.0 - 118.7 (dp 2.9); nao atendidos 0.0 - 0.0 (dp 0.0)
- C: fila_excesso, 17 entradas: espera media (s) 22.5 - 22.8 (dp 0.1); P95 geral (s) 56.6 - 58.9 (dp 1.2); pior P95 aprox. (s) 61.2 - 66.0 (dp 2.6); espera max c/ nao atendidos (s) 100.7 - 118.5 (dp 9.2); nao atendidos 0.0 - 0.0 (dp 0.0)

## assimetrico

| controlador | espera media (s) | espera media concluidos (s) | P95 geral (s) | P95 N (s) | P95 L (s) | P95 S (s) | P95 O (s) | pior P95 aprox. (s) | P95 secundarias (s) | espera max c/ nao atendidos (s) | nao atendidos | trocas/h | intervencoes hora | intervencoes escoamento |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Webster | 33.7 +- 6.0 | 33.7 | 76.0 +- 23.2 | 62.7 | 68.3 | 63.1 | 76.1 | 85.8 +- 28.6 | 62.9 +- 1.1 | 198 | 0 | 180.0 | 0 | 0 |
| Max-Pressure teto (recal. C) | 24.7 +- 1.2 | 24.7 | 73.6 +- 2.5 | 124.6 | 42.9 | 130.1 | 45.7 | 137.4 +- 12.1 | 127.3 +- 7.7 | 286 | 0 | 179.0 | 0 | 0 |
| DQN C seed0 | 21.1 +- 0.8 | 21.1 | 75.4 +- 4.4 | 134.6 | 40.2 | 130.3 | 42.2 | 140.6 +- 8.2 | 132.4 +- 9.5 | 275 | 0 | 195.0 | 1 | 6 |
| DQN C seed1 | 22.5 +- 0.9 | 22.4 | 88.3 +- 5.0 | 177.0 | 33.8 | 131.3 | 46.3 | 177.1 +- 22.7 | 154.2 +- 12.2 | 1180 | 2 | 200.7 | 0 | 0 |
| DQN C seed2 | 21.0 +- 1.0 | 20.9 | 68.5 +- 3.5 | 123.0 | 41.0 | 118.1 | 46.7 | 132.5 +- 12.7 | 120.5 +- 8.8 | 1194 | 2 | 194.8 | 0 | 0 |
| DQN excesso C seed0 | 20.7 +- 0.5 | 20.7 | 75.4 +- 3.2 | 130.1 | 37.4 | 142.7 | 40.1 | 146.9 +- 11.1 | 136.4 +- 7.0 | 309 | 0 | 211.9 | 0 | 0 |
| DQN excesso C seed1 | 21.1 +- 1.1 | 21.1 | 72.4 +- 6.4 | 137.5 | 38.2 | 128.5 | 45.8 | 140.8 +- 13.0 | 133.0 +- 16.0 | 273 | 0 | 208.6 | 0 | 0 |
| DQN excesso C seed2 | 21.3 +- 0.9 | 21.3 | 82.5 +- 6.2 | 144.1 | 41.0 | 137.8 | 35.3 | 148.9 +- 8.7 | 140.9 +- 8.8 | 285 | 0 | 199.6 | 0 | 0 |
| DQN excesso17 C seed0 | 20.7 +- 0.8 | 20.7 | 62.1 +- 1.8 | 107.0 | 41.7 | 87.8 | 45.7 | 107.0 +- 9.2 | 97.4 +- 5.4 | 199 | 0 | 202.2 | 0 | 0 |
| DQN excesso17 C seed1 | 20.9 +- 0.7 | 20.9 | 70.4 +- 3.6 | 123.3 | 43.1 | 101.9 | 39.2 | 123.3 +- 6.4 | 112.6 +- 5.4 | 230 | 0 | 199.4 | 0 | 0 |
| DQN excesso17 C seed2 | 20.6 +- 0.7 | 20.6 | 68.9 +- 2.7 | 115.6 | 41.7 | 105.0 | 42.0 | 118.7 +- 11.1 | 110.3 +- 6.0 | 200 | 0 | 193.5 | 0 | 1 |
| **A: fila, 13 entradas** | 21.5 +- 0.6 | 21.5 | 77.4 +- 2.6 | 144.9 | 38.3 | 126.6 | 45.1 | 150.1 +- 8.9 | 135.7 +- 6.4 | 1194 | 4 | 196.8 | 1 | 6 |
| **B: fila_excesso, 13 entradas** | 21.0 +- 0.6 | 21.0 | 76.8 +- 3.3 | 137.2 | 38.9 | 136.3 | 40.4 | 145.5 +- 8.8 | 136.8 +- 8.7 | 309 | 0 | 206.7 | 0 | 0 |
| **C: fila_excesso, 17 entradas** | 20.7 +- 0.6 | 20.7 | 67.1 +- 2.0 | 115.3 | 42.2 | 98.2 | 42.3 | 116.3 +- 7.3 | 106.8 +- 3.3 | 230 | 0 | 198.4 | 0 | 1 |

- **C - B** (pareado por semente): espera media (s) -0.3 (-1.4%), melhor/pior em 7/3; P95 geral (s) -9.6 (-12.5%), melhor/pior em 10/0; P95 secundarias (s) -30.0 (-21.9%), melhor/pior em 10/0; pior P95 aprox. (s) -29.2 (-20.1%), melhor/pior em 10/0; espera max c/ nao atendidos (s) -68.0 (-28.4%), melhor/pior em 10/0; nao atendidos +0.0, melhor/pior em 0/0; trocas/h -8.3 (-4.0%), melhor/pior em 10/0
- **C - A** (pareado por semente): espera media (s) -0.8 (-3.8%), melhor/pior em 9/1; P95 geral (s) -10.3 (-13.3%), melhor/pior em 10/0; P95 secundarias (s) -28.9 (-21.3%), melhor/pior em 10/0; pior P95 aprox. (s) -33.7 (-22.5%), melhor/pior em 10/0; espera max c/ nao atendidos (s) -184.6 (-51.9%), melhor/pior em 10/0; nao atendidos -0.1 (-100.0%), melhor/pior em 4/0; trocas/h +1.5 (+0.8%), melhor/pior em 3/7
- **B - A** (pareado por semente): espera media (s) -0.5 (-2.4%), melhor/pior em 8/2; P95 geral (s) -0.6 (-0.8%), melhor/pior em 6/4; P95 secundarias (s) +1.1 (+0.8%), melhor/pior em 3/6; pior P95 aprox. (s) -4.5 (-3.0%), melhor/pior em 9/1; espera max c/ nao atendidos (s) -116.7 (-32.8%), melhor/pior em 6/4; nao atendidos -0.1 (-100.0%), melhor/pior em 4/0; trocas/h +9.9 (+5.0%), melhor/pior em 0/10

Variabilidade entre as 3 sementes de treino (media de cada rede; min - max):

- A: fila, 13 entradas: espera media (s) 21.0 - 22.5 (dp 0.9); P95 geral (s) 68.5 - 88.3 (dp 10.1); P95 secundarias (s) 120.5 - 154.2 (dp 17.0); pior P95 aprox. (s) 132.5 - 177.1 (dp 23.8); espera max c/ nao atendidos (s) 223.8 - 446.9 (dp 117.1); nao atendidos 0.0 - 0.2 (dp 0.1)
- B: fila_excesso, 13 entradas: espera media (s) 20.7 - 21.3 (dp 0.3); P95 geral (s) 72.4 - 82.5 (dp 5.2); P95 secundarias (s) 133.0 - 140.9 (dp 4.0); pior P95 aprox. (s) 140.8 - 148.9 (dp 4.2); espera max c/ nao atendidos (s) 231.9 - 247.0 (dp 7.6); nao atendidos 0.0 - 0.0 (dp 0.0)
- C: fila_excesso, 17 entradas: espera media (s) 20.6 - 20.9 (dp 0.2); P95 geral (s) 62.1 - 70.4 (dp 4.4); P95 secundarias (s) 97.4 - 112.6 (dp 8.2); pior P95 aprox. (s) 107.0 - 123.3 (dp 8.4); espera max c/ nao atendidos (s) 160.8 - 179.1 (dp 9.4); nao atendidos 0.0 - 0.0 (dp 0.0)

## pico

| controlador | espera media (s) | espera media concluidos (s) | P95 geral (s) | P95 N (s) | P95 L (s) | P95 S (s) | P95 O (s) | pior P95 aprox. (s) | P95 secundarias (s) | espera max c/ nao atendidos (s) | nao atendidos | trocas/h | intervencoes hora | intervencoes escoamento |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Webster | 52.1 +- 8.4 | 52.1 | 168.6 +- 32.9 | 56.1 | 184.0 | 68.5 | 163.1 | 197.0 +- 30.8 | - | 278 | 0 | 240.0 | 0 | 0 |
| Max-Pressure teto (recal. C) | 26.6 +- 1.4 | 26.6 | 65.9 +- 3.0 | 68.1 | 61.4 | 71.5 | 63.6 | 73.1 +- 4.3 | - | 161 | 0 | 178.8 | 0 | 0 |
| DQN C seed0 | 23.0 +- 1.0 | 23.0 | 65.4 +- 3.3 | 71.4 | 58.5 | 63.2 | 67.5 | 73.1 +- 4.7 | - | 160 | 0 | 220.4 | 0 | 10 |
| DQN C seed1 | 23.6 +- 1.1 | 23.6 | 68.2 +- 2.4 | 85.8 | 52.6 | 62.0 | 65.3 | 85.8 +- 5.7 | - | 1176 | 1 | 222.4 | 0 | 0 |
| DQN C seed2 | 23.3 +- 0.9 | 23.2 | 64.3 +- 2.4 | 63.3 | 58.6 | 63.3 | 71.2 | 72.5 +- 5.1 | - | 1189 | 2 | 220.2 | 0 | 0 |
| DQN excesso C seed0 | 23.2 +- 1.0 | 23.2 | 63.7 +- 2.4 | 60.4 | 60.8 | 70.9 | 62.4 | 72.4 +- 3.6 | - | 144 | 0 | 227.0 | 0 | 0 |
| DQN excesso C seed1 | 22.8 +- 1.4 | 22.8 | 62.5 +- 4.0 | 64.4 | 56.6 | 62.2 | 66.4 | 68.8 +- 4.7 | - | 134 | 0 | 224.4 | 0 | 0 |
| DQN excesso C seed2 | 23.6 +- 0.9 | 23.6 | 65.0 +- 3.1 | 75.0 | 64.9 | 66.4 | 51.5 | 75.7 +- 6.4 | - | 172 | 0 | 220.6 | 0 | 0 |
| DQN excesso17 C seed0 | 22.8 +- 0.9 | 22.8 | 59.8 +- 3.4 | 60.8 | 59.0 | 56.4 | 60.6 | 63.4 +- 3.7 | - | 128 | 0 | 221.4 | 0 | 0 |
| DQN excesso17 C seed1 | 22.7 +- 1.2 | 22.7 | 59.8 +- 3.0 | 69.6 | 58.5 | 55.9 | 55.2 | 69.6 +- 5.3 | - | 141 | 0 | 224.9 | 0 | 0 |
| DQN excesso17 C seed2 | 22.9 +- 1.2 | 22.9 | 60.8 +- 3.3 | 65.8 | 55.8 | 66.6 | 57.6 | 68.8 +- 5.3 | - | 161 | 0 | 218.3 | 0 | 1 |
| **A: fila, 13 entradas** | 23.3 +- 0.9 | 23.2 | 66.0 +- 2.5 | 73.5 | 56.6 | 62.8 | 68.0 | 77.1 +- 4.5 | - | 1189 | 3 | 221.0 | 0 | 10 |
| **B: fila_excesso, 13 entradas** | 23.2 +- 1.0 | 23.2 | 63.7 +- 2.8 | 66.6 | 60.8 | 66.5 | 60.1 | 72.3 +- 3.2 | - | 172 | 0 | 224.0 | 0 | 0 |
| **C: fila_excesso, 17 entradas** | 22.8 +- 1.0 | 22.8 | 60.1 +- 2.5 | 65.4 | 57.8 | 59.6 | 57.8 | 67.3 +- 3.3 | - | 161 | 0 | 221.5 | 0 | 1 |

- **C - B** (pareado por semente): espera media (s) -0.4 (-1.9%), melhor/pior em 9/1; P95 geral (s) -3.6 (-5.6%), melhor/pior em 10/0; pior P95 aprox. (s) -5.0 (-7.0%), melhor/pior em 10/0; espera max c/ nao atendidos (s) -9.8 (-7.9%), melhor/pior em 8/2; nao atendidos +0.0, melhor/pior em 0/0; trocas/h -2.5 (-1.1%), melhor/pior em 10/0
- **C - A** (pareado por semente): espera media (s) -0.5 (-2.3%), melhor/pior em 7/3; P95 geral (s) -5.8 (-8.8%), melhor/pior em 10/0; pior P95 aprox. (s) -9.9 (-12.8%), melhor/pior em 10/0; espera max c/ nao atendidos (s) -88.2 (-43.5%), melhor/pior em 9/1; nao atendidos -0.1 (-100.0%), melhor/pior em 2/0; trocas/h +0.5 (+0.2%), melhor/pior em 3/7
- **B - A** (pareado por semente): espera media (s) -0.1 (-0.5%), melhor/pior em 5/5; P95 geral (s) -2.2 (-3.4%), melhor/pior em 10/0; pior P95 aprox. (s) -4.8 (-6.3%), melhor/pior em 8/1; espera max c/ nao atendidos (s) -78.4 (-38.6%), melhor/pior em 8/2; nao atendidos -0.1 (-100.0%), melhor/pior em 2/0; trocas/h +3.0 (+1.4%), melhor/pior em 0/10

Variabilidade entre as 3 sementes de treino (media de cada rede; min - max):

- A: fila, 13 entradas: espera media (s) 23.0 - 23.6 (dp 0.3); P95 geral (s) 64.3 - 68.2 (dp 2.0); pior P95 aprox. (s) 72.5 - 85.8 (dp 7.5); espera max c/ nao atendidos (s) 133.9 - 241.1 (dp 59.8); nao atendidos 0.0 - 0.2 (dp 0.1)
- B: fila_excesso, 13 entradas: espera media (s) 22.8 - 23.6 (dp 0.4); P95 geral (s) 62.5 - 65.0 (dp 1.3); pior P95 aprox. (s) 68.8 - 75.7 (dp 3.5); espera max c/ nao atendidos (s) 115.0 - 135.0 (dp 10.1); nao atendidos 0.0 - 0.0 (dp 0.0)
- C: fila_excesso, 17 entradas: espera media (s) 22.7 - 22.9 (dp 0.1); P95 geral (s) 59.8 - 60.8 (dp 0.6); pior P95 aprox. (s) 63.4 - 69.6 (dp 3.4); espera max c/ nao atendidos (s) 112.8 - 117.0 (dp 2.2); nao atendidos 0.0 - 0.0 (dp 0.0)

## saturado

| controlador | espera media (s) | espera media concluidos (s) | P95 geral (s) | P95 N (s) | P95 L (s) | P95 S (s) | P95 O (s) | pior P95 aprox. (s) | P95 secundarias (s) | espera max c/ nao atendidos (s) | nao atendidos | trocas/h | intervencoes hora | intervencoes escoamento |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Webster | 93.7 +- 12.7 | 93.7 | 196.5 +- 17.1 | 123.1 | 189.9 | 144.8 | 182.8 | 214.3 +- 3.4 | - | 321 | 0 | 96.0 | 0 | 0 |
| Max-Pressure teto (recal. C) | 73.6 +- 15.9 | 73.6 | 147.8 +- 24.3 | 168.3 | 124.6 | 163.8 | 129.1 | 172.7 +- 38.4 | - | 313 | 0 | 102.0 | 0 | 0 |
| DQN C seed0 | 60.3 +- 6.0 | 60.3 | 134.1 +- 12.2 | 130.4 | 136.1 | 137.3 | 129.0 | 144.9 +- 16.9 | - | 238 | 0 | 102.7 | 4 | 6 |
| DQN C seed1 | 61.6 +- 5.8 | 61.6 | 135.0 +- 12.3 | 157.2 | 117.8 | 145.7 | 114.6 | 159.2 +- 18.4 | - | 294 | 0 | 111.8 | 0 | 0 |
| DQN C seed2 | 65.2 +- 7.5 | 65.2 | 145.7 +- 17.0 | 162.8 | 130.7 | 117.1 | 157.1 | 172.4 +- 20.0 | - | 295 | 0 | 104.5 | 14 | 0 |
| DQN excesso C seed0 | 64.3 +- 6.3 | 64.3 | 131.7 +- 13.0 | 161.0 | 124.5 | 129.1 | 115.4 | 161.0 +- 22.5 | - | 262 | 0 | 114.9 | 0 | 0 |
| DQN excesso C seed1 | 62.4 +- 7.0 | 62.4 | 131.7 +- 12.5 | 151.3 | 117.3 | 144.8 | 111.0 | 156.3 +- 20.0 | - | 299 | 0 | 112.3 | 0 | 0 |
| DQN excesso C seed2 | 66.9 +- 8.4 | 66.9 | 143.7 +- 17.6 | 175.8 | 129.0 | 116.6 | 134.2 | 175.8 +- 29.0 | - | 337 | 0 | 111.1 | 1 | 0 |
| DQN excesso17 C seed0 | 63.5 +- 7.5 | 63.5 | 130.9 +- 13.9 | 153.1 | 115.4 | 135.5 | 118.1 | 154.0 +- 24.6 | - | 283 | 0 | 113.2 | 0 | 0 |
| DQN excesso17 C seed1 | 62.8 +- 8.6 | 62.8 | 136.0 +- 22.3 | 156.5 | 142.7 | 114.9 | 127.2 | 160.1 +- 34.6 | - | 289 | 0 | 107.2 | 2 | 0 |
| DQN excesso17 C seed2 | 64.8 +- 6.8 | 64.8 | 143.6 +- 18.5 | 173.2 | 109.5 | 160.1 | 121.7 | 177.1 +- 29.6 | - | 352 | 0 | 108.9 | 1 | 0 |
| **A: fila, 13 entradas** | 62.4 +- 6.2 | 62.4 | 138.3 +- 13.1 | 150.1 | 128.2 | 133.4 | 133.6 | 158.8 +- 17.0 | - | 295 | 0 | 106.3 | 18 | 6 |
| **B: fila_excesso, 13 entradas** | 64.5 +- 7.2 | 64.5 | 135.7 +- 13.9 | 162.7 | 123.6 | 130.2 | 120.2 | 164.4 +- 23.1 | - | 337 | 0 | 112.8 | 1 | 0 |
| **C: fila_excesso, 17 entradas** | 63.7 +- 7.4 | 63.7 | 136.8 +- 17.3 | 160.9 | 122.5 | 136.8 | 122.3 | 163.7 +- 27.6 | - | 352 | 0 | 109.8 | 3 | 0 |

- **C - B** (pareado por semente): espera media (s) -0.8 (-1.3%), melhor/pior em 8/2; P95 geral (s) +1.1 (+0.8%), melhor/pior em 4/5; pior P95 aprox. (s) -0.6 (-0.4%), melhor/pior em 5/5; espera max c/ nao atendidos (s) +4.8 (+2.2%), melhor/pior em 4/6; nao atendidos +0.0, melhor/pior em 0/0; trocas/h -3.0 (-2.7%), melhor/pior em 10/0
- **C - A** (pareado por semente): espera media (s) +1.3 (+2.1%), melhor/pior em 2/8; P95 geral (s) -1.4 (-1.0%), melhor/pior em 8/2; pior P95 aprox. (s) +4.9 (+3.1%), melhor/pior em 3/6; espera max c/ nao atendidos (s) +8.6 (+3.9%), melhor/pior em 3/7; nao atendidos +0.0, melhor/pior em 0/0; trocas/h +3.4 (+3.2%), melhor/pior em 0/10
- **B - A** (pareado por semente): espera media (s) +2.2 (+3.5%), melhor/pior em 1/9; P95 geral (s) -2.6 (-1.9%), melhor/pior em 7/3; pior P95 aprox. (s) +5.5 (+3.5%), melhor/pior em 2/8; espera max c/ nao atendidos (s) +3.7 (+1.7%), melhor/pior em 4/6; nao atendidos +0.0, melhor/pior em 0/0; trocas/h +6.4 (+6.1%), melhor/pior em 0/10

Variabilidade entre as 3 sementes de treino (media de cada rede; min - max):

- A: fila, 13 entradas: espera media (s) 60.3 - 65.2 (dp 2.5); P95 geral (s) 134.1 - 145.7 (dp 6.5); pior P95 aprox. (s) 144.9 - 172.4 (dp 13.8); espera max c/ nao atendidos (s) 206.9 - 233.1 (dp 13.1); nao atendidos 0.0 - 0.0 (dp 0.0)
- B: fila_excesso, 13 entradas: espera media (s) 62.4 - 66.9 (dp 2.3); P95 geral (s) 131.7 - 143.7 (dp 6.9); pior P95 aprox. (s) 156.3 - 175.8 (dp 10.2); espera max c/ nao atendidos (s) 217.8 - 233.5 (dp 8.4); nao atendidos 0.0 - 0.0 (dp 0.0)
- C: fila_excesso, 17 entradas: espera media (s) 62.8 - 64.8 (dp 1.0); P95 geral (s) 130.9 - 143.6 (dp 6.4); pior P95 aprox. (s) 154.0 - 177.1 (dp 12.0); espera max c/ nao atendidos (s) 216.4 - 250.9 (dp 19.3); nao atendidos 0.0 - 0.0 (dp 0.0)

## girado (nunca visto no treino)

| controlador | espera media (s) | espera media concluidos (s) | P95 geral (s) | P95 N (s) | P95 L (s) | P95 S (s) | P95 O (s) | pior P95 aprox. (s) | P95 secundarias (s) | espera max c/ nao atendidos (s) | nao atendidos | trocas/h | intervencoes hora | intervencoes escoamento |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Webster | 35.4 +- 5.6 | 35.4 | 78.4 +- 19.8 | 66.8 | 62.7 | 83.2 | 62.5 | 88.5 +- 25.8 | 62.6 +- 0.8 | 164 | 0 | 180.0 | 0 | 0 |
| Max-Pressure teto (recal. C) | 33.0 +- 0.6 | 33.0 | 111.4 +- 4.9 | 58.9 | 176.9 | 59.6 | 189.4 | 196.7 +- 16.9 | 183.2 +- 10.4 | 382 | 0 | 119.0 | 0 | 0 |
| DQN C seed0 | 24.9 +- 1.1 | 24.9 | 109.6 +- 5.3 | 44.0 | 174.7 | 34.4 | 207.2 | 207.2 +- 21.4 | 190.9 +- 10.7 | 374 | 0 | 183.8 | 0 | 8 |
| DQN C seed1 | 24.1 +- 1.0 | 24.1 | 100.4 +- 7.9 | 44.8 | 163.1 | 33.2 | 196.4 | 198.1 +- 27.6 | 179.8 +- 18.4 | 383 | 0 | 194.6 | 0 | 0 |
| DQN C seed2 | 27.1 +- 1.0 | 27.0 | 129.1 +- 9.5 | 34.7 | 195.2 | 38.7 | 231.9 | 237.5 +- 23.0 | 213.6 +- 14.2 | 1183 | 1 | 186.5 | 0 | 0 |
| DQN excesso C seed0 | 23.2 +- 1.4 | 23.2 | 97.6 +- 8.8 | 31.5 | 166.7 | 37.7 | 171.2 | 184.2 +- 14.7 | 168.9 +- 15.3 | 332 | 0 | 210.2 | 0 | 0 |
| DQN excesso C seed1 | 23.7 +- 1.6 | 23.7 | 99.7 +- 8.3 | 41.3 | 169.1 | 35.0 | 178.1 | 187.0 +- 30.8 | 173.6 +- 19.0 | 314 | 0 | 191.4 | 0 | 0 |
| DQN excesso C seed2 | 22.5 +- 1.3 | 22.5 | 88.3 +- 6.9 | 39.6 | 171.3 | 34.2 | 136.5 | 172.2 +- 14.5 | 153.9 +- 10.0 | 307 | 0 | 205.7 | 0 | 0 |
| DQN excesso17 C seed0 | 23.2 +- 1.5 | 23.2 | 94.6 +- 7.2 | 40.0 | 179.7 | 39.8 | 141.2 | 179.7 +- 16.8 | 160.4 +- 10.3 | 402 | 0 | 193.6 | 1 | 0 |
| DQN excesso17 C seed1 | 21.7 +- 1.1 | 21.7 | 81.3 +- 7.6 | 45.6 | 131.3 | 34.9 | 131.9 | 141.0 +- 17.7 | 131.6 +- 14.4 | 253 | 0 | 204.2 | 0 | 0 |
| DQN excesso17 C seed2 | 21.5 +- 1.4 | 21.5 | 81.7 +- 5.5 | 38.0 | 151.4 | 39.5 | 123.6 | 152.0 +- 16.8 | 137.5 +- 11.1 | 257 | 0 | 199.8 | 0 | 0 |
| **A: fila, 13 entradas** | 25.3 +- 0.8 | 25.3 | 113.0 +- 5.6 | 41.2 | 177.7 | 35.4 | 211.8 | 214.3 +- 17.9 | 194.8 +- 10.2 | 1183 | 1 | 188.3 | 0 | 8 |
| **B: fila_excesso, 13 entradas** | 23.1 +- 1.3 | 23.1 | 95.2 +- 6.9 | 37.5 | 169.0 | 35.6 | 161.9 | 181.1 +- 12.0 | 165.5 +- 11.8 | 332 | 0 | 202.4 | 0 | 0 |
| **C: fila_excesso, 17 entradas** | 22.1 +- 1.1 | 22.1 | 85.9 +- 4.9 | 41.2 | 154.1 | 38.1 | 132.2 | 157.6 +- 11.5 | 143.2 +- 8.2 | 402 | 0 | 199.2 | 1 | 0 |

- **C - B** (pareado por semente): espera media (s) -1.0 (-4.3%), melhor/pior em 9/1; P95 geral (s) -9.3 (-9.8%), melhor/pior em 10/0; P95 secundarias (s) -22.3 (-13.5%), melhor/pior em 10/0; pior P95 aprox. (s) -23.6 (-13.0%), melhor/pior em 10/0; espera max c/ nao atendidos (s) -40.9 (-14.6%), melhor/pior em 10/0; nao atendidos +0.0, melhor/pior em 0/0; trocas/h -3.2 (-1.6%), melhor/pior em 7/2
- **C - A** (pareado por semente): espera media (s) -3.2 (-12.7%), melhor/pior em 10/0; P95 geral (s) -27.2 (-24.0%), melhor/pior em 10/0; P95 secundarias (s) -51.6 (-26.5%), melhor/pior em 10/0; pior P95 aprox. (s) -56.7 (-26.5%), melhor/pior em 10/0; espera max c/ nao atendidos (s) -107.7 (-31.1%), melhor/pior em 10/0; nao atendidos -0.0 (-100.0%), melhor/pior em 1/0; trocas/h +10.9 (+5.8%), melhor/pior em 0/10
- **B - A** (pareado por semente): espera media (s) -2.2 (-8.8%), melhor/pior em 10/0; P95 geral (s) -17.8 (-15.8%), melhor/pior em 10/0; P95 secundarias (s) -29.3 (-15.0%), melhor/pior em 10/0; pior P95 aprox. (s) -33.1 (-15.5%), melhor/pior em 10/0; espera max c/ nao atendidos (s) -66.8 (-19.3%), melhor/pior em 9/1; nao atendidos -0.0 (-100.0%), melhor/pior em 1/0; trocas/h +14.1 (+7.5%), melhor/pior em 0/10

Variabilidade entre as 3 sementes de treino (media de cada rede; min - max):

- A: fila, 13 entradas: espera media (s) 24.1 - 27.1 (dp 1.6); P95 geral (s) 100.4 - 129.1 (dp 14.7); P95 secundarias (s) 179.8 - 213.6 (dp 17.2); pior P95 aprox. (s) 198.1 - 237.5 (dp 20.6); espera max c/ nao atendidos (s) 294.2 - 436.1 (dp 78.0); nao atendidos 0.0 - 0.1 (dp 0.1)
- B: fila_excesso, 13 entradas: espera media (s) 22.5 - 23.7 (dp 0.6); P95 geral (s) 88.3 - 99.7 (dp 6.1); P95 secundarias (s) 153.9 - 173.6 (dp 10.3); pior P95 aprox. (s) 172.2 - 187.0 (dp 7.9); espera max c/ nao atendidos (s) 261.6 - 302.7 (dp 21.0); nao atendidos 0.0 - 0.0 (dp 0.0)
- C: fila_excesso, 17 entradas: espera media (s) 21.5 - 23.2 (dp 1.0); P95 geral (s) 81.3 - 94.6 (dp 7.6); P95 secundarias (s) 131.6 - 160.4 (dp 15.2); pior P95 aprox. (s) 141.0 - 179.7 (dp 19.9); espera max c/ nao atendidos (s) 202.7 - 285.0 (dp 42.1); nao atendidos 0.0 - 0.0 (dp 0.0)

## Teste do carro sozinho

| rede | geracao | entradas | presos | atendidos so pela regra |
|---|---|---|---|---|
| DQN C seed0 | A: fila, 13 entradas | 13 | 0/36 | 18 |
| DQN C seed1 | A: fila, 13 entradas | 13 | 3/36 | 0 |
| DQN C seed2 | A: fila, 13 entradas | 13 | 3/36 | 0 |
| DQN excesso C seed0 | B: fila_excesso, 13 entradas | 13 | 0/36 | 0 |
| DQN excesso C seed1 | B: fila_excesso, 13 entradas | 13 | 0/36 | 0 |
| DQN excesso C seed2 | B: fila_excesso, 13 entradas | 13 | 0/36 | 0 |
| DQN excesso17 C seed0 | C: fila_excesso, 17 entradas | 17 | 0/36 | 0 |
| DQN excesso17 C seed1 | C: fila_excesso, 17 entradas | 17 | 0/36 | 0 |
| DQN excesso17 C seed2 | C: fila_excesso, 17 entradas | 17 | 0/36 | 2 |

## Criterios (C comparado com B)

- 1_zero_nao_atendidos: True
- 2_zero_ciclos_carro_sozinho: True
- 3_p95_secundarias_assimetrico_cai_20pct: True
- 3_p95_secundarias_assimetrico_variacao_pct: -21.944681369562566
- 4_p95_secundarias_girado_cai_20pct: False
- 4_p95_secundarias_girado_variacao_pct: -13.47567730889314
- 5_espera_media_aumenta_no_maximo_5pct: True
- 5_espera_media_variacao_pct: {'equilibrado': -2.4464973358032798, 'assimetrico': -1.438564009108241, 'pico': -1.8847371165827462, 'saturado': -1.3085411199325838, 'girado': -4.323392726531783}
- 6_espera_media_abaixo_de_webster_e_mp_teto: True
- 7_saturado_variacao_pct: {'espera_media': -1.3085411199325838, 'espera_p95': 0.8351756325227214, 'pior_p95_aprox': -0.3853173798418159}
- 7_saturado_deterioracao_relevante: False
- 7_limiar_deterioracao_pct: {'espera_media': 5.0, 'espera_p95': 10.0}
- 8_sementes_melhoraram_pioraram:
  - equilibrado: espera media (s): 9 melhoraram, 1 pioraram, 0 empates; P95 geral (s): 10 melhoraram, 0 pioraram, 0 empates; pior P95 aprox. (s): 10 melhoraram, 0 pioraram, 0 empates; espera max c/ nao atendidos (s): 7 melhoraram, 3 pioraram, 0 empates; nao atendidos: 0 melhoraram, 0 pioraram, 10 empates
  - assimetrico: espera media (s): 7 melhoraram, 3 pioraram, 0 empates; P95 geral (s): 10 melhoraram, 0 pioraram, 0 empates; P95 secundarias (s): 10 melhoraram, 0 pioraram, 0 empates; pior P95 aprox. (s): 10 melhoraram, 0 pioraram, 0 empates; espera max c/ nao atendidos (s): 10 melhoraram, 0 pioraram, 0 empates; nao atendidos: 0 melhoraram, 0 pioraram, 10 empates
  - pico: espera media (s): 9 melhoraram, 1 pioraram, 0 empates; P95 geral (s): 10 melhoraram, 0 pioraram, 0 empates; pior P95 aprox. (s): 10 melhoraram, 0 pioraram, 0 empates; espera max c/ nao atendidos (s): 8 melhoraram, 2 pioraram, 0 empates; nao atendidos: 0 melhoraram, 0 pioraram, 10 empates
  - saturado: espera media (s): 8 melhoraram, 2 pioraram, 0 empates; P95 geral (s): 4 melhoraram, 5 pioraram, 1 empates; pior P95 aprox. (s): 5 melhoraram, 5 pioraram, 0 empates; espera max c/ nao atendidos (s): 4 melhoraram, 6 pioraram, 0 empates; nao atendidos: 0 melhoraram, 0 pioraram, 10 empates
  - girado: espera media (s): 9 melhoraram, 1 pioraram, 0 empates; P95 geral (s): 10 melhoraram, 0 pioraram, 0 empates; P95 secundarias (s): 10 melhoraram, 0 pioraram, 0 empates; pior P95 aprox. (s): 10 melhoraram, 0 pioraram, 0 empates; espera max c/ nao atendidos (s): 10 melhoraram, 0 pioraram, 0 empates; nao atendidos: 0 melhoraram, 0 pioraram, 10 empates
- aviso: Cumprir estes criterios nas sementes testadas nao e garantia matematica de ausencia de starvation.
