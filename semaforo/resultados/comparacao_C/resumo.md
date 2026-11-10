# Comparacao final na dinamica C

Dinamica: C: transicao corrigida + verde maximo. Media de 10 sementes de teste (+- desvio padrao). 'Concluidos' = so carros que terminaram a viagem. Trocas/verde/% transicao: so a primeira hora.


## equilibrado

| controlador | espera media oficial (s) | espera media concluidos (s) | P95 concluidos (s) | espera max concluidos (s) | fila media (carros) | viagem media (s) | atendidos | nao atendidos | intervencoes hora | intervencoes escoamento | trocas/h | verde medio (s) | % em transicao | pior aprox. P95 (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Webster | 28.7 | 28.7 +- 0.9 | 60.6 +- 0.8 | 105.7 | 14.2 | 74.9 | 1806.1 | 0.0 | 0.0 | 0.0 | 180.0 | 15.0 | 25.0 | S: 62.1 |
| Max-Pressure | 31.9 | 31.9 +- 0.5 | 76.3 +- 1.4 | 138.9 | 15.8 | 78.0 | 1806.1 | 0.0 | 0.0 | 0.0 | 143.0 | 20.0 | 19.9 | O: 79.9 |
| Max-Pressure teto | 24.3 | 24.3 +- 1.2 | 58.0 +- 2.2 | 104.3 | 12.1 | 70.8 | 1806.1 | 0.0 | 0.0 | 0.0 | 238.6 | 10.0 | 33.1 | O: 60.3 |
| Max-Pressure (recal. C) | 37.7 | 37.7 +- 0.8 | 89.1 +- 1.3 | 150.5 | 18.6 | 83.9 | 1806.1 | 0.0 | 0.0 | 0.0 | 119.0 | 25.0 | 16.5 | O: 90.6 |
| Max-Pressure teto (recal. C) | 24.7 | 24.7 +- 1.5 | 59.8 +- 2.3 | 114.6 | 12.2 | 71.2 | 1806.1 | 0.0 | 0.0 | 0.0 | 236.3 | 10.1 | 32.8 | O: 63.4 |
| DQN original | 22.9 | 22.9 +- 0.8 | 60.7 +- 1.3 | 124.0 | 11.3 | 68.6 | 1806.1 | 0.0 | 0.0 | 0.6 | 226.9 | 10.8 | 31.5 | L: 66.7 |
| DQN seed1 | 23.0 | 23.0 +- 0.8 | 60.4 +- 2.2 | 123.7 | 11.4 | 68.9 | 1806.1 | 0.0 | 0.0 | 0.3 | 230.6 | 10.6 | 32.0 | O: 66.0 |
| DQN seed2 | 23.4 | 23.4 +- 0.8 | 62.8 +- 2.7 | 137.3 | 11.6 | 69.2 | 1806.1 | 0.0 | 0.0 | 0.9 | 226.5 | 10.8 | 31.5 | L: 71.4 |
| DQN C seed0 | 23.4 | 23.4 +- 0.8 | 64.6 +- 3.9 | 127.5 | 11.6 | 69.0 | 1806.1 | 0.0 | 0.0 | 1.0 | 220.2 | 11.3 | 30.6 | O: 72.8 |
| DQN C seed1 | 23.7 | 23.6 +- 0.8 | 62.9 +- 1.4 | 124.4 | 11.7 | 69.5 | 1805.9 | 0.2 | 0.0 | 0.0 | 225.1 | 11.0 | 31.3 | N: 69.7 |
| DQN C seed2 | 23.8 | 23.6 +- 1.0 | 64.3 +- 2.7 | 131.5 | 11.7 | 69.5 | 1805.8 | 0.3 | 0.0 | 0.0 | 217.9 | 11.5 | 30.3 | O: 80.0 |
| **DQN antigas (media das 3)** | 23.1 | 23.1 +- 0.6 | 61.3 +- 1.6 | 128.3 | 11.4 | 68.9 | 1806.1 | 0.0 | 0.0 | 0.6 | 228.0 | 10.7 | 31.7 | - |
| **DQN C (media das 3)** | 23.6 | 23.5 +- 0.8 | 63.9 +- 2.3 | 127.8 | 11.7 | 69.3 | 1805.9 | 0.2 | 0.0 | 0.3 | 221.1 | 11.3 | 30.7 | - |

DQN C - DQN antigas (pareado por semente): espera_media_concluidos: +0.41 (novas menores em 2/10 sementes); espera_p95_concluidos: +2.63 (novas menores em 0/10 sementes); trocas_por_hora: -6.93 (novas menores em 10/10 sementes); verde_medio: +0.52 (novas menores em 0/10 sementes)

## assimetrico

| controlador | espera media oficial (s) | espera media concluidos (s) | P95 concluidos (s) | espera max concluidos (s) | fila media (carros) | viagem media (s) | atendidos | nao atendidos | intervencoes hora | intervencoes escoamento | trocas/h | verde medio (s) | % em transicao | pior aprox. P95 (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Webster | 33.7 | 33.7 +- 6.0 | 76.0 +- 23.2 | 119.0 | 17.2 | 81.9 | 1861.1 | 0.0 | 0.0 | 0.0 | 180.0 | 15.0 | 25.0 | O: 76.1 |
| Max-Pressure | 28.3 | 28.3 +- 0.9 | 90.9 +- 5.0 | 259.6 | 14.4 | 74.7 | 1861.1 | 0.0 | 0.0 | 0.0 | 143.0 | 20.0 | 19.9 | S: 149.1 |
| Max-Pressure teto | 25.9 | 25.9 +- 2.4 | 73.4 +- 9.4 | 201.4 | 13.2 | 74.1 | 1861.1 | 0.0 | 0.0 | 0.0 | 235.1 | 10.2 | 32.7 | S: 131.7 |
| Max-Pressure (recal. C) | 33.1 | 33.1 +- 1.1 | 111.6 +- 6.1 | 281.4 | 16.8 | 79.6 | 1861.1 | 0.0 | 0.0 | 0.0 | 118.9 | 25.0 | 16.5 | S: 179.8 |
| Max-Pressure teto (recal. C) | 24.7 | 24.7 +- 1.2 | 73.6 +- 2.5 | 213.0 | 12.6 | 71.3 | 1861.1 | 0.0 | 0.0 | 0.0 | 179.0 | 15.0 | 24.9 | S: 130.1 |
| DQN original | 22.6 | 22.6 +- 0.8 | 85.4 +- 4.0 | 275.0 | 11.5 | 68.6 | 1861.1 | 0.0 | 0.0 | 0.7 | 218.4 | 11.5 | 30.3 | N: 150.6 |
| DQN seed1 | 20.6 | 20.6 +- 0.8 | 75.1 +- 6.1 | 231.4 | 10.5 | 66.5 | 1861.1 | 0.0 | 0.0 | 0.3 | 220.9 | 11.3 | 30.7 | N: 132.1 |
| DQN seed2 | 21.5 | 21.5 +- 1.0 | 81.5 +- 4.7 | 248.2 | 10.9 | 67.1 | 1861.1 | 0.0 | 0.0 | 0.9 | 212.3 | 12.0 | 29.5 | N: 148.6 |
| DQN C seed0 | 21.1 | 21.1 +- 0.8 | 75.4 +- 4.4 | 223.8 | 10.7 | 66.6 | 1861.1 | 0.0 | 0.1 | 0.6 | 195.0 | 13.4 | 27.1 | N: 134.6 |
| DQN C seed1 | 22.5 | 22.4 +- 0.9 | 88.2 +- 5.0 | 260.8 | 11.4 | 68.1 | 1860.9 | 0.2 | 0.0 | 0.0 | 200.7 | 12.9 | 27.9 | N: 177.0 |
| DQN C seed2 | 21.0 | 20.9 +- 0.9 | 68.4 +- 3.5 | 209.4 | 10.7 | 66.7 | 1860.9 | 0.2 | 0.0 | 0.0 | 194.8 | 13.5 | 27.1 | N: 122.4 |
| **DQN antigas (media das 3)** | 21.6 | 21.6 +- 0.7 | 80.7 +- 4.0 | 251.5 | 11.0 | 67.4 | 1861.1 | 0.0 | 0.0 | 0.6 | 217.2 | 11.6 | 30.2 | - |
| **DQN C (media das 3)** | 21.5 | 21.5 +- 0.6 | 77.3 +- 2.7 | 231.3 | 11.0 | 67.1 | 1861.0 | 0.1 | 0.0 | 0.2 | 196.8 | 13.3 | 27.3 | - |

DQN C - DQN antigas (pareado por semente): espera_media_concluidos: -0.10 (novas menores em 6/10 sementes); espera_p95_concluidos: -3.33 (novas menores em 9/10 sementes); trocas_por_hora: -20.37 (novas menores em 10/10 sementes); verde_medio: +1.70 (novas menores em 0/10 sementes)

## pico

| controlador | espera media oficial (s) | espera media concluidos (s) | P95 concluidos (s) | espera max concluidos (s) | fila media (carros) | viagem media (s) | atendidos | nao atendidos | intervencoes hora | intervencoes escoamento | trocas/h | verde medio (s) | % em transicao | pior aprox. P95 (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Webster | 52.1 | 52.1 +- 8.4 | 168.6 +- 32.9 | 236.7 | 22.8 | 104.7 | 1578.7 | 0.0 | 0.0 | 0.0 | 240.0 | 10.0 | 33.3 | L: 184.0 |
| Max-Pressure | 31.5 | 31.5 +- 0.7 | 76.6 +- 1.3 | 136.8 | 13.7 | 77.4 | 1578.7 | 0.0 | 0.0 | 0.0 | 143.0 | 20.0 | 19.9 | S: 83.8 |
| Max-Pressure teto | 30.3 | 30.3 +- 6.0 | 77.6 +- 15.9 | 149.3 | 13.3 | 78.0 | 1578.7 | 0.0 | 0.0 | 0.0 | 238.2 | 10.0 | 33.1 | S: 84.8 |
| Max-Pressure (recal. C) | 37.5 | 37.5 +- 0.7 | 91.0 +- 2.2 | 163.5 | 16.2 | 83.6 | 1578.7 | 0.0 | 0.0 | 0.0 | 118.5 | 25.0 | 16.5 | S: 99.4 |
| Max-Pressure teto (recal. C) | 26.6 | 26.6 +- 1.4 | 65.9 +- 3.0 | 122.7 | 11.5 | 72.5 | 1578.7 | 0.0 | 0.0 | 0.0 | 178.8 | 15.0 | 24.8 | S: 71.5 |
| DQN original | 23.9 | 23.9 +- 1.3 | 67.2 +- 4.2 | 134.7 | 10.4 | 69.6 | 1578.7 | 0.0 | 0.0 | 0.6 | 224.1 | 11.0 | 31.1 | N: 74.9 |
| DQN seed1 | 23.5 | 23.5 +- 1.6 | 63.8 +- 3.7 | 144.0 | 10.2 | 69.2 | 1578.7 | 0.0 | 0.0 | 1.0 | 229.0 | 10.7 | 31.8 | N: 72.1 |
| DQN seed2 | 23.1 | 23.1 +- 1.4 | 65.5 +- 4.7 | 123.4 | 10.0 | 68.7 | 1578.7 | 0.0 | 0.0 | 0.8 | 223.4 | 11.0 | 31.0 | N: 71.1 |
| DQN C seed0 | 23.0 | 23.0 +- 1.0 | 65.4 +- 3.3 | 133.9 | 10.0 | 68.5 | 1578.7 | 0.0 | 0.0 | 1.0 | 220.4 | 11.3 | 30.6 | N: 71.4 |
| DQN C seed1 | 23.6 | 23.6 +- 1.1 | 68.2 +- 2.4 | 136.3 | 10.3 | 69.2 | 1578.6 | 0.1 | 0.0 | 0.0 | 222.4 | 11.2 | 30.9 | N: 85.8 |
| DQN C seed2 | 23.3 | 23.2 +- 0.9 | 64.3 +- 2.4 | 126.5 | 10.1 | 68.8 | 1578.5 | 0.2 | 0.0 | 0.0 | 220.2 | 11.3 | 30.6 | O: 71.1 |
| **DQN antigas (media das 3)** | 23.5 | 23.5 +- 1.3 | 65.5 +- 3.8 | 134.0 | 10.2 | 69.2 | 1578.7 | 0.0 | 0.0 | 0.8 | 225.5 | 10.9 | 31.3 | - |
| **DQN C (media das 3)** | 23.3 | 23.2 +- 0.9 | 66.0 +- 2.5 | 132.2 | 10.1 | 68.8 | 1578.6 | 0.1 | 0.0 | 0.3 | 221.0 | 11.3 | 30.7 | - |

DQN C - DQN antigas (pareado por semente): espera_media_concluidos: -0.23 (novas menores em 5/10 sementes); espera_p95_concluidos: +0.47 (novas menores em 2/10 sementes); trocas_por_hora: -4.50 (novas menores em 10/10 sementes); verde_medio: +0.35 (novas menores em 0/10 sementes)

## saturado

| controlador | espera media oficial (s) | espera media concluidos (s) | P95 concluidos (s) | espera max concluidos (s) | fila media (carros) | viagem media (s) | atendidos | nao atendidos | intervencoes hora | intervencoes escoamento | trocas/h | verde medio (s) | % em transicao | pior aprox. P95 (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Webster | 93.7 | 93.7 +- 12.7 | 196.5 +- 17.1 | 283.9 | 70.6 | 147.5 | 2818.4 | 0.0 | 0.0 | 0.0 | 96.0 | 32.5 | 13.3 | L: 189.9 |
| Max-Pressure | 141.5 | 141.5 +- 25.0 | 263.6 +- 38.3 | 362.1 | 103.5 | 208.6 | 2818.4 | 0.0 | 0.0 | 0.0 | 143.0 | 20.0 | 19.9 | N: 292.7 |
| Max-Pressure teto | 94.2 | 94.2 +- 26.7 | 178.8 +- 44.7 | 267.3 | 71.5 | 149.9 | 2818.4 | 0.0 | 0.0 | 0.0 | 119.2 | 25.0 | 16.6 | N: 199.2 |
| Max-Pressure (recal. C) | 93.6 | 93.6 +- 26.8 | 175.5 +- 43.5 | 264.1 | 71.1 | 149.2 | 2818.4 | 0.0 | 0.0 | 0.0 | 119.0 | 25.0 | 16.5 | N: 200.7 |
| Max-Pressure teto (recal. C) | 73.6 | 73.6 +- 15.9 | 147.8 +- 24.3 | 229.8 | 56.6 | 125.0 | 2818.4 | 0.0 | 0.0 | 0.0 | 102.0 | 30.0 | 14.2 | N: 168.3 |
| DQN original | 65.7 | 65.7 +- 6.4 | 136.0 +- 12.6 | 212.9 | 50.5 | 116.4 | 2818.4 | 0.0 | 0.0 | 0.2 | 115.3 | 26.4 | 16.0 | N: 155.1 |
| DQN seed1 | 66.0 | 66.0 +- 7.8 | 146.6 +- 21.8 | 257.8 | 50.9 | 116.2 | 2818.4 | 0.0 | 0.2 | 0.3 | 106.8 | 28.9 | 14.8 | N: 184.1 |
| DQN seed2 | 63.3 | 63.3 +- 6.8 | 130.0 +- 13.2 | 221.2 | 48.7 | 113.5 | 2818.4 | 0.0 | 0.0 | 0.9 | 112.9 | 27.0 | 15.7 | O: 144.6 |
| DQN C seed0 | 60.3 | 60.3 +- 6.0 | 134.1 +- 12.2 | 206.9 | 46.4 | 109.7 | 2818.4 | 0.0 | 0.4 | 0.6 | 102.7 | 30.2 | 14.3 | S: 137.3 |
| DQN C seed1 | 61.6 | 61.6 +- 5.8 | 135.0 +- 12.3 | 220.4 | 47.5 | 111.5 | 2818.4 | 0.0 | 0.0 | 0.0 | 111.8 | 27.3 | 15.5 | N: 157.2 |
| DQN C seed2 | 65.2 | 65.2 +- 7.5 | 145.7 +- 17.0 | 233.1 | 50.3 | 115.1 | 2818.4 | 0.0 | 1.4 | 0.0 | 104.5 | 29.6 | 14.5 | N: 162.8 |
| **DQN antigas (media das 3)** | 65.0 | 65.0 +- 6.8 | 137.5 +- 15.4 | 230.6 | 50.1 | 115.4 | 2818.4 | 0.0 | 0.1 | 0.5 | 111.7 | 27.4 | 15.5 | - |
| **DQN C (media das 3)** | 62.4 | 62.4 +- 6.2 | 138.3 +- 13.1 | 220.1 | 48.1 | 112.1 | 2818.4 | 0.0 | 0.6 | 0.2 | 106.3 | 29.0 | 14.8 | - |

DQN C - DQN antigas (pareado por semente): espera_media_concluidos: -2.64 (novas menores em 9/10 sementes); espera_p95_concluidos: +0.73 (novas menores em 4/10 sementes); trocas_por_hora: -5.33 (novas menores em 10/10 sementes); verde_medio: +1.62 (novas menores em 0/10 sementes)

## girado (nunca visto no treino)

| controlador | espera media oficial (s) | espera media concluidos (s) | P95 concluidos (s) | espera max concluidos (s) | fila media (carros) | viagem media (s) | atendidos | nao atendidos | intervencoes hora | intervencoes escoamento | trocas/h | verde medio (s) | % em transicao | pior aprox. P95 (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Webster | 35.4 | 35.4 +- 5.6 | 78.4 +- 19.8 | 118.6 | 18.3 | 83.9 | 1884.1 | 0.0 | 0.0 | 0.0 | 180.0 | 15.0 | 25.0 | S: 83.2 |
| Max-Pressure | 28.4 | 28.4 +- 0.6 | 91.9 +- 3.0 | 263.1 | 14.7 | 74.9 | 1884.1 | 0.0 | 0.0 | 0.0 | 143.0 | 20.0 | 19.9 | O: 160.6 |
| Max-Pressure teto | 28.4 | 28.4 +- 0.6 | 91.9 +- 3.0 | 263.1 | 14.7 | 74.9 | 1884.1 | 0.0 | 0.0 | 0.0 | 143.0 | 20.0 | 19.9 | O: 160.6 |
| Max-Pressure (recal. C) | 33.0 | 33.0 +- 0.6 | 111.4 +- 4.9 | 308.4 | 17.0 | 79.5 | 1884.1 | 0.0 | 0.0 | 0.0 | 119.0 | 25.0 | 16.5 | O: 189.4 |
| Max-Pressure teto (recal. C) | 33.0 | 33.0 +- 0.6 | 111.4 +- 4.9 | 308.4 | 17.0 | 79.5 | 1884.1 | 0.0 | 0.0 | 0.0 | 119.0 | 25.0 | 16.5 | O: 189.4 |
| DQN original | 22.8 | 22.8 +- 1.0 | 93.3 +- 6.0 | 255.3 | 11.8 | 68.2 | 1884.1 | 0.0 | 0.0 | 0.7 | 189.9 | 13.9 | 26.4 | L: 179.1 |
| DQN seed1 | 23.7 | 23.7 +- 1.6 | 102.5 +- 10.2 | 288.5 | 12.3 | 69.3 | 1884.1 | 0.0 | 0.0 | 0.2 | 200.7 | 12.9 | 27.9 | O: 183.7 |
| DQN seed2 | 25.7 | 25.7 +- 2.1 | 117.0 +- 12.2 | 306.4 | 13.3 | 71.3 | 1884.1 | 0.0 | 0.1 | 0.7 | 191.8 | 13.7 | 26.6 | L: 206.1 |
| DQN C seed0 | 24.9 | 24.9 +- 1.1 | 109.6 +- 5.3 | 309.0 | 12.8 | 70.3 | 1884.1 | 0.0 | 0.0 | 0.8 | 183.8 | 14.6 | 25.5 | O: 207.2 |
| DQN C seed1 | 24.1 | 24.1 +- 1.0 | 100.4 +- 7.9 | 294.2 | 12.4 | 69.6 | 1884.1 | 0.0 | 0.0 | 0.0 | 194.6 | 13.5 | 27.0 | O: 196.4 |
| DQN C seed2 | 27.1 | 27.0 +- 1.1 | 129.1 +- 9.5 | 344.2 | 14.0 | 72.5 | 1884.0 | 0.1 | 0.0 | 0.0 | 186.5 | 14.2 | 25.9 | O: 231.9 |
| **DQN antigas (media das 3)** | 24.1 | 24.1 +- 1.4 | 104.3 +- 8.3 | 283.4 | 12.4 | 69.6 | 1884.1 | 0.0 | 0.0 | 0.5 | 194.1 | 13.5 | 27.0 | - |
| **DQN C (media das 3)** | 25.3 | 25.3 +- 0.8 | 113.0 +- 5.6 | 315.8 | 13.1 | 70.8 | 1884.1 | 0.0 | 0.0 | 0.3 | 188.3 | 14.1 | 26.2 | - |

DQN C - DQN antigas (pareado por semente): espera_media_concluidos: +1.24 (novas menores em 1/10 sementes); espera_p95_concluidos: +8.77 (novas menores em 0/10 sementes); trocas_por_hora: -5.83 (novas menores em 10/10 sementes); verde_medio: +0.59 (novas menores em 0/10 sementes)
