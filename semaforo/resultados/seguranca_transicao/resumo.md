# Seguranca e transicao - resumo

Modos: A: original; B: original + verde maximo; C: transicao corrigida + verde maximo.
Valores = media de 10 sementes. 'Concluidos' = so carros que terminaram a viagem. A espera de um carro interrompido e um limite inferior e NAO entra nas colunas 'concluidos'.


## 1. Atendimento e espera

| cenario | controlador | modo | espera media concl. (s) | P95 concl. (s) | max concl. (s) | espera media oficial (s) | concluidos | interrompidos (total) | sem atendimento (total) | aguardando entrada (total) | rodadas cortadas | pior aprox.: espera media / P95 (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| equilibrado | Webster | A | 26.5 +- 0.7 | 58.4 | 91.0 | 26.5 | 1806 | 0 | 0 | 0 | 0/10 | S: 27.1 / 58.5 |
| equilibrado | Webster | B | 26.5 +- 0.7 | 58.4 | 91.0 | 26.5 | 1806 | 0 | 0 | 0 | 0/10 | S: 27.1 / 58.5 |
| equilibrado | Webster | C | 28.7 +- 0.9 | 60.6 | 105.7 | 28.7 | 1806 | 0 | 0 | 0 | 0/10 | S: 29.5 / 62.1 |
| equilibrado | Max-Pressure | A | 30.8 +- 0.4 | 74.5 | 126.2 | 30.8 | 1806 | 0 | 0 | 0 | 0/10 | O: 32.1 / 77.7 |
| equilibrado | Max-Pressure | B | 30.8 +- 0.4 | 74.5 | 126.2 | 30.8 | 1806 | 0 | 0 | 0 | 0/10 | O: 32.1 / 77.7 |
| equilibrado | Max-Pressure | C | 31.9 +- 0.5 | 76.3 | 138.9 | 31.9 | 1806 | 0 | 0 | 0 | 0/10 | O: 33.1 / 79.9 |
| equilibrado | Max-Pressure teto | A | 20.1 +- 0.5 | 49.9 | 97.8 | 20.1 | 1806 | 0 | 0 | 0 | 0/10 | O: 21.5 / 53.0 |
| equilibrado | Max-Pressure teto | B | 20.1 +- 0.5 | 49.9 | 97.8 | 20.1 | 1806 | 0 | 0 | 0 | 0/10 | O: 21.5 / 53.0 |
| equilibrado | Max-Pressure teto | C | 24.3 +- 1.2 | 58.0 | 104.3 | 24.3 | 1806 | 0 | 0 | 0 | 0/10 | O: 26.0 / 60.3 |
| equilibrado | DQN original | A | 19.8 +- 0.5 | 56.6 | 120.8 | 20.3 | 1805 | 7 | 7 | 0 | 4/10 | L: 24.2 / 61.9 |
| equilibrado | DQN original | B | 19.9 +- 0.5 | 56.7 | 126.7 | 19.9 | 1806 | 0 | 0 | 0 | 0/10 | L: 24.3 / 62.2 |
| equilibrado | DQN original | C | 22.9 +- 0.8 | 60.7 | 124.0 | 22.9 | 1806 | 0 | 0 | 0 | 0/10 | L: 27.6 / 66.7 |
| equilibrado | DQN seed1 | A | 19.3 +- 0.5 | 54.0 | 109.4 | 19.4 | 1806 | 1 | 1 | 0 | 1/10 | O: 21.5 / 59.6 |
| equilibrado | DQN seed1 | B | 19.3 +- 0.5 | 54.0 | 109.4 | 19.3 | 1806 | 0 | 0 | 0 | 0/10 | O: 21.5 / 59.6 |
| equilibrado | DQN seed1 | C | 23.0 +- 0.8 | 60.4 | 123.7 | 23.0 | 1806 | 0 | 0 | 0 | 0/10 | O: 25.9 / 66.0 |
| equilibrado | DQN seed2 | A | 19.8 +- 0.7 | 56.1 | 114.6 | 20.7 | 1805 | 14 | 14 | 0 | 4/10 | L: 23.7 / 64.3 |
| equilibrado | DQN seed2 | B | 19.8 +- 0.6 | 56.3 | 119.0 | 19.8 | 1806 | 0 | 0 | 0 | 0/10 | L: 24.0 / 65.3 |
| equilibrado | DQN seed2 | C | 23.4 +- 0.8 | 62.8 | 137.3 | 23.4 | 1806 | 0 | 0 | 0 | 0/10 | L: 28.6 / 71.4 |
| assimetrico | Webster | A | 28.2 +- 2.7 | 62.5 | 97.9 | 28.2 | 1861 | 0 | 0 | 0 | 0/10 | O: 29.9 / 63.5 |
| assimetrico | Webster | B | 28.2 +- 2.7 | 62.5 | 97.9 | 28.2 | 1861 | 0 | 0 | 0 | 0/10 | O: 29.9 / 63.5 |
| assimetrico | Webster | C | 33.7 +- 6.0 | 76.0 | 119.0 | 33.7 | 1861 | 0 | 0 | 0 | 0/10 | O: 37.2 / 76.1 |
| assimetrico | Max-Pressure | A | 26.9 +- 0.8 | 87.0 | 229.3 | 26.9 | 1861 | 0 | 0 | 0 | 0/10 | S: 57.7 / 142.9 |
| assimetrico | Max-Pressure | B | 26.9 +- 0.8 | 87.0 | 229.3 | 26.9 | 1861 | 0 | 0 | 0 | 0/10 | S: 57.7 / 142.9 |
| assimetrico | Max-Pressure | C | 28.3 +- 0.9 | 90.9 | 259.6 | 28.3 | 1861 | 0 | 0 | 0 | 0/10 | S: 60.5 / 149.1 |
| assimetrico | Max-Pressure teto | A | 19.5 +- 1.1 | 55.8 | 188.8 | 19.5 | 1861 | 0 | 0 | 0 | 0/10 | S: 39.0 / 104.9 |
| assimetrico | Max-Pressure teto | B | 19.5 +- 1.1 | 55.8 | 188.8 | 19.5 | 1861 | 0 | 0 | 0 | 0/10 | S: 39.0 / 104.9 |
| assimetrico | Max-Pressure teto | C | 25.9 +- 2.4 | 73.4 | 201.4 | 25.9 | 1861 | 0 | 0 | 0 | 0/10 | S: 51.2 / 131.7 |
| assimetrico | DQN original | A | 19.4 +- 0.6 | 77.6 | 243.6 | 19.8 | 1860 | 6 | 6 | 0 | 4/10 | N: 57.3 / 147.1 |
| assimetrico | DQN original | B | 19.4 +- 0.6 | 77.9 | 243.6 | 19.4 | 1861 | 0 | 0 | 0 | 0/10 | N: 57.3 / 146.5 |
| assimetrico | DQN original | C | 22.6 +- 0.8 | 85.4 | 275.0 | 22.6 | 1861 | 0 | 0 | 0 | 0/10 | N: 62.3 / 150.6 |
| assimetrico | DQN seed1 | A | 17.6 +- 0.7 | 64.1 | 214.0 | 17.8 | 1861 | 4 | 4 | 0 | 3/10 | S: 43.9 / 117.5 |
| assimetrico | DQN seed1 | B | 17.6 +- 0.7 | 64.5 | 214.0 | 17.6 | 1861 | 0 | 0 | 0 | 0/10 | S: 43.9 / 117.5 |
| assimetrico | DQN seed1 | C | 20.6 +- 0.8 | 75.1 | 231.4 | 20.6 | 1861 | 0 | 0 | 0 | 0/10 | N: 50.8 / 132.1 |
| assimetrico | DQN seed2 | A | 18.4 +- 0.9 | 73.4 | 230.5 | 19.6 | 1859 | 18 | 18 | 0 | 7/10 | N: 51.4 / 134.2 |
| assimetrico | DQN seed2 | B | 18.5 +- 0.9 | 73.7 | 230.5 | 18.5 | 1861 | 0 | 0 | 0 | 0/10 | N: 51.4 / 134.2 |
| assimetrico | DQN seed2 | C | 21.5 +- 1.0 | 81.5 | 248.2 | 21.5 | 1861 | 0 | 0 | 0 | 0/10 | N: 58.8 / 148.6 |
| pico | Webster | A | 29.5 +- 4.1 | 80.0 | 129.4 | 29.5 | 1579 | 0 | 0 | 0 | 0/10 | L: 38.1 / 90.8 |
| pico | Webster | B | 29.5 +- 4.1 | 80.0 | 129.4 | 29.5 | 1579 | 0 | 0 | 0 | 0/10 | L: 38.1 / 90.8 |
| pico | Webster | C | 52.1 +- 8.4 | 168.6 | 236.7 | 52.1 | 1579 | 0 | 0 | 0 | 0/10 | L: 76.5 / 184.0 |
| pico | Max-Pressure | A | 30.2 +- 0.7 | 74.2 | 135.5 | 30.2 | 1579 | 0 | 0 | 0 | 0/10 | S: 33.1 / 80.4 |
| pico | Max-Pressure | B | 30.2 +- 0.7 | 74.2 | 135.5 | 30.2 | 1579 | 0 | 0 | 0 | 0/10 | S: 33.1 / 80.4 |
| pico | Max-Pressure | C | 31.5 +- 0.7 | 76.6 | 136.8 | 31.5 | 1579 | 0 | 0 | 0 | 0/10 | S: 34.1 / 83.8 |
| pico | Max-Pressure teto | A | 20.7 +- 1.1 | 52.7 | 101.9 | 20.7 | 1579 | 0 | 0 | 0 | 0/10 | S: 22.8 / 57.8 |
| pico | Max-Pressure teto | B | 20.7 +- 1.1 | 52.7 | 101.9 | 20.7 | 1579 | 0 | 0 | 0 | 0/10 | S: 22.8 / 57.8 |
| pico | Max-Pressure teto | C | 30.3 +- 6.0 | 77.6 | 149.3 | 30.3 | 1579 | 0 | 0 | 0 | 0/10 | S: 33.1 / 84.8 |
| pico | DQN original | A | 20.5 +- 1.2 | 61.3 | 126.0 | 21.3 | 1578 | 10 | 10 | 0 | 6/10 | N: 24.4 / 68.8 |
| pico | DQN original | B | 20.6 +- 1.2 | 61.4 | 131.3 | 20.6 | 1579 | 0 | 0 | 0 | 0/10 | N: 24.4 / 69.0 |
| pico | DQN original | C | 23.9 +- 1.3 | 67.2 | 134.7 | 23.9 | 1579 | 0 | 0 | 0 | 0/10 | L: 28.3 / 68.7 |
| pico | DQN seed1 | A | 19.7 +- 1.0 | 56.2 | 113.1 | 20.2 | 1578 | 7 | 7 | 0 | 6/10 | N: 20.8 / 61.9 |
| pico | DQN seed1 | B | 19.7 +- 1.0 | 56.5 | 115.1 | 19.7 | 1579 | 0 | 0 | 0 | 0/10 | N: 20.8 / 61.9 |
| pico | DQN seed1 | C | 23.5 +- 1.6 | 63.8 | 144.0 | 23.5 | 1579 | 0 | 0 | 0 | 0/10 | N: 24.7 / 72.1 |
| pico | DQN seed2 | A | 19.9 +- 0.9 | 58.8 | 128.2 | 20.9 | 1577 | 14 | 14 | 0 | 7/10 | N: 22.7 / 64.1 |
| pico | DQN seed2 | B | 19.9 +- 0.8 | 59.1 | 130.4 | 19.9 | 1579 | 0 | 0 | 0 | 0/10 | N: 22.7 / 64.1 |
| pico | DQN seed2 | C | 23.1 +- 1.4 | 65.5 | 123.4 | 23.1 | 1579 | 0 | 0 | 0 | 0/10 | N: 25.9 / 71.1 |
| saturado | Webster | A | 76.6 +- 10.1 | 164.3 | 250.9 | 76.6 | 2818 | 0 | 0 | 0 | 0/10 | L: 94.6 / 161.3 |
| saturado | Webster | B | 76.6 +- 10.1 | 164.3 | 250.9 | 76.6 | 2818 | 0 | 0 | 0 | 0/10 | L: 94.6 / 161.3 |
| saturado | Webster | C | 93.7 +- 12.7 | 196.5 | 283.9 | 93.7 | 2818 | 0 | 0 | 0 | 0/10 | L: 119.3 / 189.9 |
| saturado | Max-Pressure | A | 83.5 +- 26.5 | 155.9 | 243.8 | 83.5 | 2818 | 0 | 0 | 0 | 0/10 | N: 94.0 / 177.4 |
| saturado | Max-Pressure | B | 83.5 +- 26.5 | 155.9 | 243.8 | 83.5 | 2818 | 0 | 0 | 0 | 0/10 | N: 94.0 / 177.4 |
| saturado | Max-Pressure | C | 141.5 +- 25.0 | 263.6 | 362.1 | 141.5 | 2818 | 0 | 0 | 0 | 0/10 | N: 167.0 / 292.7 |
| saturado | Max-Pressure teto | A | 60.2 +- 8.7 | 122.6 | 203.1 | 60.2 | 2818 | 0 | 0 | 0 | 0/10 | N: 66.7 / 141.6 |
| saturado | Max-Pressure teto | B | 60.2 +- 8.7 | 122.6 | 203.1 | 60.2 | 2818 | 0 | 0 | 0 | 0/10 | N: 66.7 / 141.6 |
| saturado | Max-Pressure teto | C | 94.2 +- 26.7 | 178.8 | 267.3 | 94.2 | 2818 | 0 | 0 | 0 | 0/10 | N: 105.7 / 199.2 |
| saturado | DQN original | A | 51.5 +- 4.7 | 112.7 | 192.4 | 51.8 | 2818 | 8 | 8 | 0 | 5/10 | N: 58.1 / 132.8 |
| saturado | DQN original | B | 51.5 +- 4.7 | 112.7 | 192.4 | 51.5 | 2818 | 0 | 0 | 0 | 0/10 | N: 58.1 / 132.8 |
| saturado | DQN original | C | 65.7 +- 6.4 | 136.0 | 212.9 | 65.7 | 2818 | 0 | 0 | 0 | 0/10 | N: 75.2 / 155.1 |
| saturado | DQN seed1 | A | 53.1 +- 5.7 | 123.8 | 223.6 | 53.2 | 2818 | 2 | 2 | 0 | 1/10 | N: 69.5 / 160.9 |
| saturado | DQN seed1 | B | 53.1 +- 5.7 | 123.8 | 223.6 | 53.1 | 2818 | 0 | 0 | 0 | 0/10 | N: 69.5 / 160.9 |
| saturado | DQN seed1 | C | 66.0 +- 7.8 | 146.6 | 257.8 | 66.0 | 2818 | 0 | 0 | 0 | 0/10 | N: 85.2 / 184.1 |
| saturado | DQN seed2 | A | 51.3 +- 5.4 | 113.7 | 190.7 | 52.0 | 2817 | 18 | 18 | 0 | 6/10 | O: 59.7 / 128.4 |
| saturado | DQN seed2 | B | 51.2 +- 5.1 | 114.0 | 195.1 | 51.2 | 2818 | 0 | 0 | 0 | 0/10 | O: 59.7 / 128.7 |
| saturado | DQN seed2 | C | 63.3 +- 6.8 | 130.0 | 221.2 | 63.3 | 2818 | 0 | 0 | 0 | 0/10 | O: 76.0 / 144.6 |
| girado | Webster | A | 28.9 +- 2.4 | 61.7 | 96.9 | 28.9 | 1884 | 0 | 0 | 0 | 0/10 | S: 30.7 / 64.1 |
| girado | Webster | B | 28.9 +- 2.4 | 61.7 | 96.9 | 28.9 | 1884 | 0 | 0 | 0 | 0/10 | S: 30.7 / 64.1 |
| girado | Webster | C | 35.4 +- 5.6 | 78.4 | 118.6 | 35.4 | 1884 | 0 | 0 | 0 | 0/10 | S: 41.0 / 83.2 |
| girado | Max-Pressure | A | 27.1 +- 0.7 | 90.8 | 278.4 | 27.1 | 1884 | 0 | 0 | 0 | 0/10 | O: 62.6 / 159.6 |
| girado | Max-Pressure | B | 27.1 +- 0.7 | 90.8 | 278.4 | 27.1 | 1884 | 0 | 0 | 0 | 0/10 | O: 62.6 / 159.6 |
| girado | Max-Pressure | C | 28.4 +- 0.6 | 91.9 | 263.1 | 28.4 | 1884 | 0 | 0 | 0 | 0/10 | O: 64.8 / 160.6 |
| girado | Max-Pressure teto | A | 27.1 +- 0.7 | 90.8 | 278.4 | 27.1 | 1884 | 0 | 0 | 0 | 0/10 | O: 62.6 / 159.6 |
| girado | Max-Pressure teto | B | 27.1 +- 0.7 | 90.8 | 278.4 | 27.1 | 1884 | 0 | 0 | 0 | 0/10 | O: 62.6 / 159.6 |
| girado | Max-Pressure teto | C | 28.4 +- 0.6 | 91.9 | 263.1 | 28.4 | 1884 | 0 | 0 | 0 | 0/10 | O: 64.8 / 160.6 |
| girado | DQN original | A | 20.9 +- 1.1 | 88.9 | 269.6 | 21.1 | 1884 | 3 | 3 | 0 | 2/10 | L: 69.5 / 175.2 |
| girado | DQN original | B | 21.0 +- 1.1 | 89.2 | 269.6 | 21.0 | 1884 | 0 | 0 | 0 | 0/10 | L: 69.5 / 175.0 |
| girado | DQN original | C | 22.8 +- 1.0 | 93.3 | 255.3 | 22.8 | 1884 | 0 | 0 | 0 | 0/10 | L: 73.5 / 179.1 |
| girado | DQN seed1 | A | 20.2 +- 0.7 | 90.1 | 259.1 | 20.5 | 1884 | 4 | 4 | 0 | 3/10 | O: 63.2 / 163.7 |
| girado | DQN seed1 | B | 20.3 +- 0.7 | 90.5 | 259.1 | 20.3 | 1884 | 0 | 0 | 0 | 0/10 | O: 63.2 / 163.7 |
| girado | DQN seed1 | C | 23.7 +- 1.6 | 102.5 | 288.5 | 23.7 | 1884 | 0 | 0 | 0 | 0/10 | O: 75.2 / 183.7 |
| girado | DQN seed2 | A | 22.0 +- 1.3 | 100.2 | 318.9 | 22.9 | 1883 | 15 | 15 | 0 | 6/10 | L: 80.6 / 197.1 |
| girado | DQN seed2 | B | 22.0 +- 1.3 | 99.7 | 318.9 | 22.0 | 1884 | 0 | 0 | 0 | 0/10 | L: 80.4 / 195.7 |
| girado | DQN seed2 | C | 25.7 +- 2.1 | 117.0 | 306.4 | 25.7 | 1884 | 0 | 0 | 0 | 0/10 | L: 95.1 / 206.1 |

## 2. Comportamento do semaforo e regra de seguranca

| cenario | controlador | modo | vermelho geral executado (s) | trocas/h | verde medio (s) | % transicao | verde max hora (s) | verde max total (s) | intervencoes/rodada hora | intervencoes/rodada escoamento | escoamento (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| equilibrado | Webster | A | [1] | 180.0 | 16.0 | 20.0 | 16 | 16 | 0.0 | 0.0 | 92 |
| equilibrado | Webster | B | [1] | 180.0 | 16.0 | 20.0 | 16 | 16 | 0.0 | 0.0 | 92 |
| equilibrado | Webster | C | [2] | 180.0 | 15.0 | 25.0 | 15 | 15 | 0.0 | 0.0 | 95 |
| equilibrado | Max-Pressure | A | [1] | 143.0 | 21.0 | 15.9 | 30 | 41 | 0.0 | 0.0 | 103 |
| equilibrado | Max-Pressure | B | [1] | 143.0 | 21.0 | 15.9 | 30 | 41 | 0.0 | 0.0 | 103 |
| equilibrado | Max-Pressure | C | [2] | 143.0 | 20.0 | 19.9 | 28 | 40 | 0.0 | 0.0 | 103 |
| equilibrado | Max-Pressure teto | A | [1] | 238.6 | 11.0 | 26.5 | 30 | 41 | 0.0 | 0.0 | 80 |
| equilibrado | Max-Pressure teto | B | [1] | 238.6 | 11.0 | 26.5 | 30 | 41 | 0.0 | 0.0 | 80 |
| equilibrado | Max-Pressure teto | C | [2] | 238.6 | 10.0 | 33.1 | 28 | 40 | 0.0 | 0.0 | 86 |
| equilibrado | DQN original | A | [1] | 228.6 | 11.7 | 25.4 | 31 | 1160 | 0.0 | 0.0 | 529 |
| equilibrado | DQN original | B | [1] | 228.6 | 11.7 | 25.4 | 31 | 61 | 0.0 | 0.5 | 113 |
| equilibrado | DQN original | C | [2] | 226.9 | 10.8 | 31.5 | 30 | 60 | 0.0 | 0.6 | 121 |
| equilibrado | DQN seed1 | A | [1] | 231.4 | 11.5 | 25.7 | 26 | 1165 | 0.0 | 0.0 | 198 |
| equilibrado | DQN seed1 | B | [1] | 231.4 | 11.5 | 25.7 | 26 | 61 | 0.0 | 0.1 | 90 |
| equilibrado | DQN seed1 | C | [1, 2] | 230.6 | 10.6 | 32.0 | 25 | 60 | 0.0 | 0.3 | 113 |
| equilibrado | DQN seed2 | A | [1] | 227.8 | 11.7 | 25.3 | 34 | 1165 | 0.0 | 0.0 | 527 |
| equilibrado | DQN seed2 | B | [1] | 227.8 | 11.7 | 25.3 | 34 | 61 | 0.0 | 0.5 | 111 |
| equilibrado | DQN seed2 | C | [2] | 226.5 | 10.8 | 31.5 | 32 | 60 | 0.0 | 0.9 | 145 |
| assimetrico | Webster | A | [1] | 180.0 | 16.0 | 20.0 | 21 | 21 | 0.0 | 0.0 | 98 |
| assimetrico | Webster | B | [1] | 180.0 | 16.0 | 20.0 | 21 | 21 | 0.0 | 0.0 | 98 |
| assimetrico | Webster | C | [2] | 180.0 | 15.0 | 25.0 | 20 | 20 | 0.0 | 0.0 | 100 |
| assimetrico | Max-Pressure | A | [1] | 143.0 | 21.0 | 15.9 | 28 | 36 | 0.0 | 0.0 | 102 |
| assimetrico | Max-Pressure | B | [1] | 143.0 | 21.0 | 15.9 | 28 | 36 | 0.0 | 0.0 | 102 |
| assimetrico | Max-Pressure | C | [2] | 143.0 | 20.0 | 19.9 | 26 | 35 | 0.0 | 0.0 | 102 |
| assimetrico | Max-Pressure teto | A | [1] | 231.7 | 11.4 | 25.7 | 37 | 61 | 0.0 | 0.0 | 139 |
| assimetrico | Max-Pressure teto | B | [1] | 231.7 | 11.4 | 25.7 | 37 | 61 | 0.0 | 0.0 | 139 |
| assimetrico | Max-Pressure teto | C | [2] | 235.1 | 10.2 | 32.7 | 36 | 60 | 0.0 | 0.0 | 141 |
| assimetrico | DQN original | A | [1] | 216.9 | 12.6 | 24.1 | 34 | 1155 | 0.0 | 0.0 | 525 |
| assimetrico | DQN original | B | [1] | 216.9 | 12.6 | 24.1 | 34 | 61 | 0.0 | 0.5 | 108 |
| assimetrico | DQN original | C | [2] | 218.4 | 11.5 | 30.3 | 35 | 60 | 0.0 | 0.7 | 131 |
| assimetrico | DQN seed1 | A | [1] | 221.9 | 12.2 | 24.7 | 24 | 1160 | 0.0 | 0.0 | 419 |
| assimetrico | DQN seed1 | B | [1] | 221.9 | 12.2 | 24.7 | 24 | 61 | 0.0 | 0.3 | 104 |
| assimetrico | DQN seed1 | C | [2] | 220.9 | 11.3 | 30.7 | 24 | 60 | 0.0 | 0.3 | 125 |
| assimetrico | DQN seed2 | A | [1] | 212.4 | 12.9 | 23.6 | 36 | 1160 | 0.0 | 0.0 | 863 |
| assimetrico | DQN seed2 | B | [1] | 212.4 | 12.9 | 23.6 | 36 | 61 | 0.0 | 1.0 | 142 |
| assimetrico | DQN seed2 | C | [2] | 212.3 | 12.0 | 29.5 | 36 | 60 | 0.0 | 0.9 | 138 |
| pico | Webster | A | [1] | 240.0 | 11.0 | 26.7 | 11 | 11 | 0.0 | 0.0 | 77 |
| pico | Webster | B | [1] | 240.0 | 11.0 | 26.7 | 11 | 11 | 0.0 | 0.0 | 77 |
| pico | Webster | C | [1, 2] | 240.0 | 10.0 | 33.3 | 10 | 10 | 0.0 | 0.0 | 77 |
| pico | Max-Pressure | A | [1] | 143.0 | 21.0 | 15.9 | 32 | 46 | 0.0 | 0.0 | 97 |
| pico | Max-Pressure | B | [1] | 143.0 | 21.0 | 15.9 | 32 | 46 | 0.0 | 0.0 | 97 |
| pico | Max-Pressure | C | [2] | 143.0 | 20.0 | 19.9 | 30 | 45 | 0.0 | 0.0 | 98 |
| pico | Max-Pressure teto | A | [1] | 238.2 | 11.0 | 26.5 | 32 | 46 | 0.0 | 0.0 | 78 |
| pico | Max-Pressure teto | B | [1] | 238.2 | 11.0 | 26.5 | 32 | 46 | 0.0 | 0.0 | 78 |
| pico | Max-Pressure teto | C | [2] | 238.2 | 10.0 | 33.1 | 30 | 45 | 0.0 | 0.0 | 78 |
| pico | DQN original | A | [1] | 224.3 | 12.0 | 24.9 | 34 | 1175 | 0.0 | 0.0 | 750 |
| pico | DQN original | B | [1] | 224.3 | 12.0 | 24.9 | 34 | 61 | 0.0 | 0.7 | 122 |
| pico | DQN original | C | [2] | 224.1 | 11.0 | 31.1 | 30 | 60 | 0.0 | 0.6 | 116 |
| pico | DQN seed1 | A | [1] | 230.5 | 11.6 | 25.6 | 26 | 1155 | 0.0 | 0.0 | 752 |
| pico | DQN seed1 | B | [1] | 230.5 | 11.6 | 25.6 | 26 | 61 | 0.0 | 0.6 | 118 |
| pico | DQN seed1 | C | [1, 2] | 229.0 | 10.7 | 31.8 | 23 | 60 | 0.0 | 1.0 | 147 |
| pico | DQN seed2 | A | [1] | 225.9 | 11.8 | 25.1 | 32 | 1170 | 0.0 | 0.0 | 862 |
| pico | DQN seed2 | B | [1] | 225.9 | 11.8 | 25.1 | 32 | 61 | 0.0 | 0.7 | 114 |
| pico | DQN seed2 | C | [2] | 223.4 | 11.0 | 31.0 | 30 | 60 | 0.0 | 0.8 | 120 |
| saturado | Webster | A | [1] | 96.0 | 33.5 | 10.7 | 36 | 36 | 0.0 | 0.0 | 209 |
| saturado | Webster | B | [1] | 96.0 | 33.5 | 10.7 | 36 | 36 | 0.0 | 0.0 | 209 |
| saturado | Webster | C | [2] | 96.0 | 32.5 | 13.3 | 35 | 35 | 0.0 | 0.0 | 297 |
| saturado | Max-Pressure | A | [1] | 143.0 | 21.0 | 15.9 | 26 | 33 | 0.0 | 0.0 | 201 |
| saturado | Max-Pressure | B | [1] | 143.0 | 21.0 | 15.9 | 26 | 33 | 0.0 | 0.0 | 201 |
| saturado | Max-Pressure | C | [2] | 143.0 | 20.0 | 19.9 | 25 | 30 | 0.0 | 0.0 | 362 |
| saturado | Max-Pressure teto | A | [1] | 119.2 | 26.0 | 13.2 | 33 | 61 | 0.0 | 0.0 | 172 |
| saturado | Max-Pressure teto | B | [1] | 119.2 | 26.0 | 13.2 | 33 | 61 | 0.0 | 0.0 | 172 |
| saturado | Max-Pressure teto | C | [2] | 119.2 | 25.0 | 16.6 | 32 | 60 | 0.0 | 0.0 | 238 |
| saturado | DQN original | A | [1] | 130.5 | 23.7 | 14.5 | 46 | 1125 | 0.0 | 0.0 | 663 |
| saturado | DQN original | B | [1] | 130.5 | 23.7 | 14.5 | 46 | 61 | 0.0 | 0.5 | 155 |
| saturado | DQN original | C | [2] | 115.3 | 26.4 | 16.0 | 51 | 60 | 0.0 | 0.2 | 165 |
| saturado | DQN seed1 | A | [1] | 117.2 | 26.8 | 13.0 | 51 | 1120 | 0.0 | 0.0 | 237 |
| saturado | DQN seed1 | B | [1] | 117.2 | 26.8 | 13.0 | 51 | 61 | 0.0 | 0.1 | 134 |
| saturado | DQN seed1 | C | [2] | 106.8 | 28.9 | 14.8 | 54 | 60 | 0.2 | 0.3 | 176 |
| saturado | DQN seed2 | A | [1] | 121.7 | 25.7 | 13.5 | 50 | 1135 | 0.0 | 0.0 | 783 |
| saturado | DQN seed2 | B | [1] | 121.7 | 25.7 | 13.5 | 50 | 61 | 0.1 | 1.1 | 192 |
| saturado | DQN seed2 | C | [2] | 112.9 | 27.0 | 15.7 | 54 | 60 | 0.0 | 0.9 | 203 |
| girado | Webster | A | [1] | 180.0 | 16.0 | 20.0 | 21 | 21 | 0.0 | 0.0 | 95 |
| girado | Webster | B | [1] | 180.0 | 16.0 | 20.0 | 21 | 21 | 0.0 | 0.0 | 95 |
| girado | Webster | C | [2] | 180.0 | 15.0 | 25.0 | 20 | 20 | 0.0 | 0.0 | 109 |
| girado | Max-Pressure | A | [1] | 143.0 | 21.0 | 15.9 | 30 | 41 | 0.0 | 0.0 | 109 |
| girado | Max-Pressure | B | [1] | 143.0 | 21.0 | 15.9 | 30 | 41 | 0.0 | 0.0 | 109 |
| girado | Max-Pressure | C | [2] | 143.0 | 20.0 | 19.9 | 28 | 40 | 0.0 | 0.0 | 110 |
| girado | Max-Pressure teto | A | [1] | 143.0 | 21.0 | 15.9 | 30 | 41 | 0.0 | 0.0 | 109 |
| girado | Max-Pressure teto | B | [1] | 143.0 | 21.0 | 15.9 | 30 | 41 | 0.0 | 0.0 | 109 |
| girado | Max-Pressure teto | C | [2] | 143.0 | 20.0 | 19.9 | 28 | 40 | 0.0 | 0.0 | 110 |
| girado | DQN original | A | [1] | 187.4 | 15.2 | 20.8 | 52 | 1160 | 0.0 | 0.0 | 308 |
| girado | DQN original | B | [1] | 187.8 | 15.1 | 20.9 | 52 | 61 | 0.1 | 0.2 | 94 |
| girado | DQN original | C | [2] | 189.9 | 13.9 | 26.4 | 42 | 60 | 0.0 | 0.7 | 126 |
| girado | DQN seed1 | A | [1] | 204.5 | 13.6 | 22.7 | 39 | 1170 | 0.0 | 0.0 | 418 |
| girado | DQN seed1 | B | [1] | 204.5 | 13.6 | 22.7 | 39 | 61 | 0.0 | 0.3 | 98 |
| girado | DQN seed1 | C | [1, 2] | 200.7 | 12.9 | 27.9 | 40 | 60 | 0.0 | 0.2 | 108 |
| girado | DQN seed2 | A | [1] | 192.1 | 14.6 | 21.3 | 48 | 1160 | 0.0 | 0.0 | 755 |
| girado | DQN seed2 | B | [1] | 192.5 | 14.6 | 21.4 | 48 | 61 | 0.1 | 0.7 | 129 |
| girado | DQN seed2 | C | [2] | 191.8 | 13.7 | 26.6 | 46 | 60 | 0.1 | 0.7 | 128 |

## 3. Diferenca pareada contra o modo A (mesma semente)

| cenario | controlador | modo | dif. espera media concl. (s) | sementes melhor/pior | dif. P95 concl. (s) | sementes melhor/pior |
|---|---|---|---|---|---|---|
| equilibrado | Webster | B | +0.0 | 0/0 | +0.0 | 0/0 |
| equilibrado | Webster | C | +2.2 | 0/10 | +2.2 | 0/10 |
| equilibrado | Max-Pressure | B | +0.0 | 0/0 | +0.0 | 0/0 |
| equilibrado | Max-Pressure | C | +1.0 | 0/10 | +1.8 | 1/9 |
| equilibrado | Max-Pressure teto | B | +0.0 | 0/0 | +0.0 | 0/0 |
| equilibrado | Max-Pressure teto | C | +4.2 | 0/10 | +8.1 | 0/10 |
| equilibrado | DQN original | B | +0.0 | 0/4 | +0.1 | 0/1 |
| equilibrado | DQN original | C | +3.0 | 0/10 | +4.1 | 0/10 |
| equilibrado | DQN seed1 | B | +0.0 | 0/1 | +0.0 | 0/0 |
| equilibrado | DQN seed1 | C | +3.7 | 0/10 | +6.4 | 0/10 |
| equilibrado | DQN seed2 | B | +0.1 | 0/4 | +0.2 | 0/2 |
| equilibrado | DQN seed2 | C | +3.7 | 0/10 | +6.7 | 0/10 |
| assimetrico | Webster | B | +0.0 | 0/0 | +0.0 | 0/0 |
| assimetrico | Webster | C | +5.6 | 0/10 | +13.5 | 0/10 |
| assimetrico | Max-Pressure | B | +0.0 | 0/0 | +0.0 | 0/0 |
| assimetrico | Max-Pressure | C | +1.3 | 0/10 | +3.9 | 3/7 |
| assimetrico | Max-Pressure teto | B | +0.0 | 0/0 | +0.0 | 0/0 |
| assimetrico | Max-Pressure teto | C | +6.4 | 0/10 | +17.6 | 0/10 |
| assimetrico | DQN original | B | +0.0 | 0/4 | +0.3 | 0/3 |
| assimetrico | DQN original | C | +3.2 | 0/10 | +7.8 | 0/9 |
| assimetrico | DQN seed1 | B | +0.0 | 0/3 | +0.4 | 0/2 |
| assimetrico | DQN seed1 | C | +3.0 | 0/10 | +11.0 | 0/10 |
| assimetrico | DQN seed2 | B | +0.1 | 2/5 | +0.3 | 0/2 |
| assimetrico | DQN seed2 | C | +3.0 | 0/10 | +8.1 | 1/9 |
| pico | Webster | B | +0.0 | 0/0 | +0.0 | 0/0 |
| pico | Webster | C | +22.6 | 0/10 | +88.6 | 0/10 |
| pico | Max-Pressure | B | +0.0 | 0/0 | +0.0 | 0/0 |
| pico | Max-Pressure | C | +1.3 | 0/10 | +2.4 | 0/10 |
| pico | Max-Pressure teto | B | +0.0 | 0/0 | +0.0 | 0/0 |
| pico | Max-Pressure teto | C | +9.6 | 0/10 | +24.9 | 0/10 |
| pico | DQN original | B | +0.1 | 0/6 | +0.1 | 0/1 |
| pico | DQN original | C | +3.4 | 0/10 | +5.9 | 0/10 |
| pico | DQN seed1 | B | +0.0 | 0/6 | +0.3 | 0/3 |
| pico | DQN seed1 | C | +3.8 | 0/10 | +7.6 | 0/10 |
| pico | DQN seed2 | B | +0.1 | 0/7 | +0.3 | 0/3 |
| pico | DQN seed2 | C | +3.2 | 0/10 | +6.7 | 0/10 |
| saturado | Webster | B | +0.0 | 0/0 | +0.0 | 0/0 |
| saturado | Webster | C | +17.1 | 0/10 | +32.2 | 0/10 |
| saturado | Max-Pressure | B | +0.0 | 0/0 | +0.0 | 0/0 |
| saturado | Max-Pressure | C | +58.0 | 0/10 | +107.7 | 0/10 |
| saturado | Max-Pressure teto | B | +0.0 | 0/0 | +0.0 | 0/0 |
| saturado | Max-Pressure teto | C | +34.0 | 0/10 | +56.2 | 0/10 |
| saturado | DQN original | B | +0.0 | 0/5 | +0.0 | 0/0 |
| saturado | DQN original | C | +14.1 | 0/10 | +23.3 | 0/10 |
| saturado | DQN seed1 | B | +0.0 | 0/1 | +0.0 | 0/0 |
| saturado | DQN seed1 | C | +12.9 | 0/10 | +22.8 | 0/10 |
| saturado | DQN seed2 | B | -0.1 | 2/6 | +0.3 | 0/2 |
| saturado | DQN seed2 | C | +12.0 | 0/10 | +16.3 | 0/10 |
| girado | Webster | B | +0.0 | 0/0 | +0.0 | 0/0 |
| girado | Webster | C | +6.5 | 0/10 | +16.7 | 0/10 |
| girado | Max-Pressure | B | +0.0 | 0/0 | +0.0 | 0/0 |
| girado | Max-Pressure | C | +1.4 | 1/9 | +1.1 | 5/5 |
| girado | Max-Pressure teto | B | +0.0 | 0/0 | +0.0 | 0/0 |
| girado | Max-Pressure teto | C | +1.4 | 1/9 | +1.1 | 5/5 |
| girado | DQN original | B | +0.0 | 0/3 | +0.3 | 0/3 |
| girado | DQN original | C | +1.8 | 1/9 | +4.4 | 2/8 |
| girado | DQN seed1 | B | +0.0 | 0/3 | +0.4 | 0/2 |
| girado | DQN seed1 | C | +3.5 | 0/10 | +12.4 | 0/10 |
| girado | DQN seed2 | B | +0.0 | 1/6 | -0.5 | 1/3 |
| girado | DQN seed2 | C | +3.8 | 0/10 | +16.8 | 1/9 |

## 4. Espera por aproximacao (so concluidos): media / P95 (s)

| cenario | controlador | modo | N | L | S | O | maior tempo sem verde na hora (s, pior aprox.) |
|---|---|---|---|---|---|---|---|
| equilibrado | Webster | A | 26.0 / 57.9 | 26.4 / 58.5 | 27.1 / 58.5 | 26.5 / 58.2 | 64.0 |
| equilibrado | Webster | B | 26.0 / 57.9 | 26.4 / 58.5 | 27.1 / 58.5 | 26.5 / 58.2 | 64.0 |
| equilibrado | Webster | C | 28.0 / 60.7 | 28.5 / 61.1 | 29.5 / 62.1 | 28.5 / 60.4 | 65.0 |
| equilibrado | Max-Pressure | A | 30.1 / 74.1 | 30.7 / 75.4 | 30.6 / 74.6 | 32.1 / 77.7 | 131.5 |
| equilibrado | Max-Pressure | B | 30.1 / 74.1 | 30.7 / 75.4 | 30.6 / 74.6 | 32.1 / 77.7 | 131.5 |
| equilibrado | Max-Pressure | C | 30.7 / 74.2 | 32.3 / 78.0 | 31.5 / 77.1 | 33.1 / 79.9 | 142.5 |
| equilibrado | Max-Pressure teto | A | 18.6 / 47.4 | 19.9 / 48.1 | 20.4 / 50.2 | 21.5 / 53.0 | 100.0 |
| equilibrado | Max-Pressure teto | B | 18.6 / 47.4 | 19.9 / 48.1 | 20.4 / 50.2 | 21.5 / 53.0 | 100.0 |
| equilibrado | Max-Pressure teto | C | 22.7 / 55.4 | 24.0 / 56.6 | 24.7 / 58.7 | 26.0 / 60.3 | 104.0 |
| equilibrado | DQN original | A | 20.5 / 58.0 | 24.2 / 61.9 | 18.5 / 54.6 | 16.2 / 48.6 | 126.5 |
| equilibrado | DQN original | B | 20.5 / 58.1 | 24.3 / 62.2 | 18.5 / 54.6 | 16.2 / 48.6 | 126.5 |
| equilibrado | DQN original | C | 23.7 / 62.2 | 27.6 / 66.7 | 21.2 / 58.3 | 19.1 / 53.1 | 121.0 |
| equilibrado | DQN seed1 | A | 18.1 / 50.4 | 19.4 / 52.4 | 18.5 / 51.6 | 21.5 / 59.6 | 107.0 |
| equilibrado | DQN seed1 | B | 18.1 / 50.4 | 19.4 / 52.5 | 18.5 / 51.6 | 21.5 / 59.6 | 107.0 |
| equilibrado | DQN seed1 | C | 21.7 / 58.6 | 23.3 / 59.4 | 21.5 / 57.5 | 25.9 / 66.0 | 109.5 |
| equilibrado | DQN seed2 | A | 20.1 / 55.7 | 23.7 / 64.3 | 16.6 / 47.9 | 18.9 / 53.7 | 120.0 |
| equilibrado | DQN seed2 | B | 20.1 / 55.7 | 24.0 / 65.3 | 16.6 / 47.9 | 18.9 / 53.7 | 120.0 |
| equilibrado | DQN seed2 | C | 22.9 / 59.5 | 28.6 / 71.4 | 19.5 / 55.5 | 23.1 / 62.6 | 120.5 |
| assimetrico | Webster | A | 27.7 / 61.3 | 26.5 / 57.7 | 28.2 / 61.7 | 29.9 / 63.5 | 69.0 |
| assimetrico | Webster | B | 27.7 / 61.3 | 26.5 / 57.7 | 28.2 / 61.7 | 29.9 / 63.5 | 69.0 |
| assimetrico | Webster | C | 28.8 / 62.7 | 32.3 / 68.3 | 29.3 / 63.1 | 37.2 / 76.1 | 70.0 |
| assimetrico | Max-Pressure | A | 57.7 / 142.7 | 19.2 / 49.8 | 57.7 / 142.9 | 20.2 / 49.5 | 249.0 |
| assimetrico | Max-Pressure | B | 57.7 / 142.7 | 19.2 / 49.8 | 57.7 / 142.9 | 20.2 / 49.5 | 249.0 |
| assimetrico | Max-Pressure | C | 59.2 / 140.3 | 20.3 / 51.0 | 60.5 / 149.1 | 21.2 / 51.5 | 305.0 |
| assimetrico | Max-Pressure teto | A | 35.9 / 95.6 | 14.6 / 34.6 | 39.0 / 104.9 | 15.8 / 36.7 | 212.5 |
| assimetrico | Max-Pressure teto | B | 35.9 / 95.6 | 14.6 / 34.6 | 39.0 / 104.9 | 15.8 / 36.7 | 212.5 |
| assimetrico | Max-Pressure teto | C | 49.8 / 131.3 | 19.4 / 42.3 | 51.2 / 131.7 | 20.6 / 44.3 | 224.0 |
| assimetrico | DQN original | A | 57.3 / 147.1 | 14.7 / 41.0 | 48.0 / 130.5 | 8.5 / 29.1 | 254.0 |
| assimetrico | DQN original | B | 57.3 / 146.5 | 14.7 / 41.1 | 48.0 / 130.5 | 8.5 / 29.1 | 254.0 |
| assimetrico | DQN original | C | 62.3 / 150.6 | 17.4 / 44.3 | 56.4 / 141.5 | 10.4 / 32.3 | 272.5 |
| assimetrico | DQN seed1 | A | 43.0 / 114.3 | 11.7 / 33.9 | 43.9 / 117.5 | 11.2 / 34.1 | 240.0 |
| assimetrico | DQN seed1 | B | 43.0 / 114.3 | 11.7 / 33.9 | 43.9 / 117.5 | 11.3 / 34.1 | 240.0 |
| assimetrico | DQN seed1 | C | 50.8 / 132.1 | 13.6 / 35.7 | 50.5 / 130.8 | 13.5 / 39.3 | 249.5 |
| assimetrico | DQN seed2 | A | 51.4 / 134.2 | 12.4 / 38.9 | 46.4 / 123.1 | 10.0 / 33.7 | 246.5 |
| assimetrico | DQN seed2 | B | 51.4 / 134.2 | 12.6 / 39.2 | 46.4 / 123.1 | 10.0 / 33.7 | 246.5 |
| assimetrico | DQN seed2 | C | 58.8 / 148.6 | 14.6 / 41.9 | 51.9 / 143.9 | 12.3 / 37.8 | 261.0 |
| pico | Webster | A | 20.9 / 47.9 | 38.1 / 90.8 | 22.4 / 50.3 | 33.5 / 80.6 | 49.0 |
| pico | Webster | B | 20.9 / 47.9 | 38.1 / 90.8 | 22.4 / 50.3 | 33.5 / 80.6 | 49.0 |
| pico | Webster | C | 24.9 / 56.1 | 76.5 / 184.0 | 29.1 / 68.5 | 67.6 / 163.1 | 50.0 |
| pico | Max-Pressure | A | 30.7 / 78.9 | 28.4 / 71.5 | 33.1 / 80.4 | 29.4 / 72.7 | 141.5 |
| pico | Max-Pressure | B | 30.7 / 78.9 | 28.4 / 71.5 | 33.1 / 80.4 | 29.4 / 72.7 | 141.5 |
| pico | Max-Pressure | C | 32.8 / 81.9 | 29.3 / 73.5 | 34.1 / 83.8 | 30.7 / 75.2 | 137.5 |
| pico | Max-Pressure teto | A | 20.3 / 55.1 | 18.7 / 46.8 | 22.8 / 57.8 | 21.3 / 51.3 | 109.0 |
| pico | Max-Pressure teto | B | 20.3 / 55.1 | 18.7 / 46.8 | 22.8 / 57.8 | 21.3 / 51.3 | 109.0 |
| pico | Max-Pressure teto | C | 31.0 / 84.6 | 27.8 / 69.9 | 33.1 / 84.8 | 30.1 / 72.5 | 119.0 |
| pico | DQN original | A | 24.4 / 68.8 | 23.3 / 64.1 | 20.2 / 61.6 | 14.9 / 47.6 | 129.5 |
| pico | DQN original | B | 24.4 / 69.0 | 23.4 / 64.5 | 20.2 / 61.6 | 14.9 / 47.6 | 129.5 |
| pico | DQN original | C | 26.9 / 74.9 | 28.3 / 68.7 | 23.7 / 68.2 | 17.2 / 51.3 | 140.5 |
| pico | DQN seed1 | A | 20.8 / 61.9 | 18.4 / 53.3 | 20.5 / 58.3 | 19.5 / 53.9 | 128.0 |
| pico | DQN seed1 | B | 20.8 / 61.9 | 18.5 / 53.7 | 20.5 / 58.3 | 19.5 / 53.9 | 128.0 |
| pico | DQN seed1 | C | 24.7 / 72.1 | 21.7 / 57.9 | 23.6 / 64.3 | 24.3 / 63.0 | 143.5 |
| pico | DQN seed2 | A | 22.7 / 64.1 | 21.2 / 59.5 | 19.0 / 56.6 | 17.0 / 52.4 | 137.5 |
| pico | DQN seed2 | B | 22.7 / 64.1 | 21.5 / 60.6 | 19.0 / 56.6 | 17.0 / 52.4 | 137.5 |
| pico | DQN seed2 | C | 25.9 / 71.1 | 24.1 / 63.8 | 22.3 / 67.4 | 20.5 / 60.0 | 137.5 |
| saturado | Webster | A | 56.9 / 116.8 | 94.6 / 161.3 | 62.4 / 126.3 | 83.0 / 153.4 | 119.0 |
| saturado | Webster | B | 56.9 / 116.8 | 94.6 / 161.3 | 62.4 / 126.3 | 83.0 / 153.4 | 119.0 |
| saturado | Webster | C | 61.9 / 123.1 | 119.3 / 189.9 | 75.6 / 144.8 | 103.8 / 182.8 | 120.0 |
| saturado | Max-Pressure | A | 94.0 / 177.4 | 74.2 / 132.0 | 93.4 / 170.2 | 77.3 / 132.9 | 156.5 |
| saturado | Max-Pressure | B | 94.0 / 177.4 | 74.2 / 132.0 | 93.4 / 170.2 | 77.3 / 132.9 | 156.5 |
| saturado | Max-Pressure | C | 167.0 / 292.7 | 123.4 / 215.9 | 162.0 / 284.3 | 125.2 / 211.6 | 167.5 |
| saturado | Max-Pressure teto | A | 66.7 / 141.6 | 55.0 / 104.7 | 65.5 / 135.3 | 56.5 / 106.4 | 169.0 |
| saturado | Max-Pressure teto | B | 66.7 / 141.6 | 55.0 / 104.7 | 65.5 / 135.3 | 56.5 / 106.4 | 169.0 |
| saturado | Max-Pressure teto | C | 105.7 / 199.2 | 85.6 / 151.6 | 105.6 / 194.7 | 85.7 / 146.5 | 188.0 |
| saturado | DQN original | A | 58.1 / 132.8 | 54.1 / 107.8 | 48.9 / 107.3 | 46.4 / 104.4 | 184.0 |
| saturado | DQN original | B | 58.1 / 132.8 | 54.1 / 107.9 | 48.9 / 107.3 | 46.4 / 104.4 | 184.0 |
| saturado | DQN original | C | 75.2 / 155.1 | 65.8 / 128.2 | 61.1 / 130.7 | 62.2 / 130.2 | 193.5 |
| saturado | DQN seed1 | A | 69.5 / 160.9 | 39.9 / 96.0 | 46.5 / 107.3 | 59.3 / 124.1 | 220.0 |
| saturado | DQN seed1 | B | 69.5 / 160.9 | 39.9 / 96.0 | 46.5 / 107.3 | 59.3 / 124.1 | 220.0 |
| saturado | DQN seed1 | C | 85.2 / 184.1 | 45.2 / 106.3 | 57.1 / 121.9 | 79.7 / 154.4 | 234.5 |
| saturado | DQN seed2 | A | 51.9 / 115.2 | 43.4 / 96.7 | 50.2 / 114.9 | 59.7 / 128.4 | 174.5 |
| saturado | DQN seed2 | B | 51.7 / 115.5 | 43.8 / 96.4 | 49.8 / 114.9 | 59.7 / 128.7 | 171.0 |
| saturado | DQN seed2 | C | 61.4 / 127.3 | 51.6 / 108.7 | 64.0 / 132.8 | 76.0 / 144.6 | 160.0 |
| girado | Webster | A | 27.5 / 58.8 | 27.4 / 61.3 | 30.7 / 64.1 | 27.6 / 61.5 | 69.0 |
| girado | Webster | B | 27.5 / 58.8 | 27.4 / 61.3 | 30.7 / 64.1 | 27.6 / 61.5 | 69.0 |
| girado | Webster | C | 32.5 / 66.8 | 28.5 / 62.7 | 41.0 / 83.2 | 28.6 / 62.5 | 70.0 |
| girado | Max-Pressure | A | 18.7 / 49.0 | 58.0 / 144.3 | 19.6 / 49.1 | 62.6 / 159.6 | 301.5 |
| girado | Max-Pressure | B | 18.7 / 49.0 | 58.0 / 144.3 | 19.6 / 49.1 | 62.6 / 159.6 | 301.5 |
| girado | Max-Pressure | C | 20.0 / 50.0 | 59.4 / 150.3 | 20.8 / 50.9 | 64.8 / 160.6 | 280.0 |
| girado | Max-Pressure teto | A | 18.7 / 49.0 | 58.0 / 144.3 | 19.6 / 49.1 | 62.6 / 159.6 | 301.5 |
| girado | Max-Pressure teto | B | 18.7 / 49.0 | 58.0 / 144.3 | 19.6 / 49.1 | 62.6 / 159.6 | 301.5 |
| girado | Max-Pressure teto | C | 20.0 / 50.0 | 59.4 / 150.3 | 20.8 / 50.9 | 64.8 / 160.6 | 280.0 |
| girado | DQN original | A | 13.0 / 39.0 | 69.5 / 175.2 | 9.9 / 34.4 | 52.5 / 144.7 | 288.0 |
| girado | DQN original | B | 13.0 / 39.0 | 69.5 / 175.0 | 9.9 / 34.4 | 52.6 / 145.2 | 288.0 |
| girado | DQN original | C | 14.4 / 40.9 | 73.5 / 179.1 | 11.5 / 38.0 | 55.0 / 154.2 | 267.0 |
| girado | DQN seed1 | A | 11.4 / 38.5 | 58.7 / 156.2 | 9.8 / 31.4 | 63.2 / 163.7 | 283.5 |
| girado | DQN seed1 | B | 11.4 / 38.5 | 58.8 / 155.8 | 9.8 / 31.4 | 63.2 / 163.7 | 283.5 |
| girado | DQN seed1 | C | 13.5 / 42.3 | 67.5 / 166.8 | 11.4 / 35.1 | 75.2 / 183.7 | 277.5 |
| girado | DQN seed2 | A | 12.9 / 37.0 | 80.6 / 197.1 | 8.3 / 30.0 | 60.0 / 166.5 | 323.0 |
| girado | DQN seed2 | B | 12.8 / 37.2 | 80.4 / 195.7 | 8.3 / 30.1 | 59.8 / 164.4 | 323.0 |
| girado | DQN seed2 | C | 15.0 / 41.1 | 95.1 / 206.1 | 9.6 / 32.9 | 69.3 / 176.4 | 295.0 |
