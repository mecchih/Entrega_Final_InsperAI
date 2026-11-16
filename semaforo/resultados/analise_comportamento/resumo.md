# Analise de comportamento - resumo

Valores = media entre sementes (+- desvio padrao quando indicado). 'Hora' = 0 a 3600 s; o escoamento fica de fora destas tabelas.


## A/B. Trocas e verdes (primeira hora)

| cenario | controlador | trocas/h | % amarelo | % vermelho geral | verde medio (s) | verde mediano (s) | fila ao encerrar verde | % trocas p/ maior fila | % ordem ciclica | espera media (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| equilibrado | Webster | 180.0 +- 0.0 | 15.0 | 5.0 | 16.0 +- 0.0 | 16.0 | 0.0 | 80 | 100 | 26.5 |
| equilibrado | Max-Pressure | 143.0 +- 0.0 | 11.9 | 4.0 | 21.0 +- 0.0 | 21.0 | 0.0 | 100 | 32 | 30.8 |
| equilibrado | DQN original | 228.6 +- 2.1 | 19.1 | 6.3 | 11.7 +- 0.2 | 11.0 | 0.0 | 80 | 22 | 20.3 |
| equilibrado | DQN seed1 | 231.4 +- 1.6 | 19.3 | 6.4 | 11.5 +- 0.1 | 11.0 | 0.0 | 83 | 40 | 19.4 |
| equilibrado | DQN seed2 | 227.8 +- 1.9 | 19.0 | 6.3 | 11.7 +- 0.1 | 11.0 | 0.0 | 81 | 29 | 20.7 |
| equilibrado | Max-Pressure teto | 238.6 +- 0.5 | 19.9 | 6.6 | 11.0 +- 0.0 | 11.0 | 0.0 | 100 | 37 | 20.1 |
| equilibrado | Tempo fixo 30s | 102.0 +- 0.0 | 8.5 | 2.8 | 31.0 +- 0.0 | 31.0 | 0.0 | 86 | 100 | 44.0 |
| assimetrico | Webster | 180.0 +- 0.0 | 15.0 | 5.0 | 16.0 +- 0.0 | 21.0 | 0.0 | 51 | 100 | 28.2 |
| assimetrico | Max-Pressure | 143.0 +- 0.0 | 11.9 | 4.0 | 21.0 +- 0.0 | 21.0 | 0.0 | 100 | 31 | 26.9 |
| assimetrico | DQN original | 216.9 +- 3.1 | 18.1 | 6.0 | 12.6 +- 0.2 | 11.0 | 0.0 | 72 | 15 | 19.8 |
| assimetrico | DQN seed1 | 221.9 +- 1.5 | 18.5 | 6.2 | 12.2 +- 0.1 | 11.0 | 0.0 | 83 | 30 | 17.8 |
| assimetrico | DQN seed2 | 212.4 +- 4.5 | 17.7 | 5.9 | 12.9 +- 0.4 | 11.0 | 0.0 | 75 | 23 | 19.6 |
| assimetrico | Max-Pressure teto | 231.7 +- 3.0 | 19.3 | 6.4 | 11.4 +- 0.2 | 11.0 | 0.0 | 100 | 27 | 19.5 |
| assimetrico | Tempo fixo 30s | 102.0 +- 0.0 | 8.5 | 2.8 | 31.0 +- 0.0 | 31.0 | 0.9 | 40 | 100 | 92.8 |
| pico | Webster | 240.0 +- 0.0 | 20.0 | 6.7 | 11.0 +- 0.0 | 11.0 | 0.2 | 67 | 100 | 29.5 |
| pico | Max-Pressure | 143.0 +- 0.0 | 11.9 | 4.0 | 21.0 +- 0.0 | 21.0 | 0.0 | 100 | 35 | 30.2 |
| pico | DQN original | 224.3 +- 3.6 | 18.7 | 6.2 | 12.0 +- 0.3 | 11.0 | 0.0 | 77 | 24 | 21.3 |
| pico | DQN seed1 | 230.5 +- 2.6 | 19.2 | 6.4 | 11.6 +- 0.2 | 11.0 | 0.0 | 83 | 40 | 20.2 |
| pico | DQN seed2 | 225.9 +- 3.2 | 18.8 | 6.3 | 11.8 +- 0.2 | 11.0 | 0.0 | 81 | 34 | 20.9 |
| pico | Max-Pressure teto | 238.2 +- 0.8 | 19.9 | 6.6 | 11.0 +- 0.0 | 11.0 | 0.0 | 100 | 41 | 20.7 |
| pico | Tempo fixo 30s | 102.0 +- 0.0 | 8.5 | 2.8 | 31.0 +- 0.0 | 31.0 | 0.0 | 82 | 100 | 44.0 |
| saturado | Webster | 96.0 +- 0.0 | 8.0 | 2.7 | 33.5 +- 0.0 | 36.0 | 0.1 | 60 | 100 | 76.6 |
| saturado | Max-Pressure | 143.0 +- 0.0 | 11.9 | 4.0 | 21.0 +- 0.0 | 21.0 | 2.5 | 100 | 34 | 83.5 |
| saturado | DQN original | 130.5 +- 6.9 | 10.9 | 3.6 | 23.7 +- 1.5 | 22.0 | 0.2 | 84 | 17 | 51.8 |
| saturado | DQN seed1 | 117.2 +- 7.2 | 9.8 | 3.3 | 26.8 +- 1.9 | 26.2 | 0.0 | 76 | 29 | 53.2 |
| saturado | DQN seed2 | 121.7 +- 7.7 | 10.1 | 3.4 | 25.7 +- 2.0 | 25.0 | 0.0 | 78 | 13 | 52.0 |
| saturado | Max-Pressure teto | 119.2 +- 0.4 | 9.9 | 3.3 | 26.0 +- 0.0 | 26.0 | 0.0 | 100 | 34 | 60.2 |
| saturado | Tempo fixo 30s | 102.0 +- 0.0 | 8.5 | 2.8 | 31.0 +- 0.0 | 31.0 | 2.8 | 50 | 100 | 110.0 |
| girado | Webster | 180.0 +- 0.0 | 15.0 | 5.0 | 16.0 +- 0.0 | 11.0 | 0.0 | 51 | 100 | 28.9 |
| girado | Max-Pressure | 143.0 +- 0.0 | 11.9 | 4.0 | 21.0 +- 0.0 | 21.0 | 0.0 | 100 | 31 | 27.1 |
| girado | DQN original | 187.4 +- 6.3 | 15.6 | 5.2 | 15.2 +- 0.6 | 11.0 | 0.0 | 75 | 18 | 21.1 |
| girado | DQN seed1 | 204.5 +- 4.2 | 17.0 | 5.7 | 13.6 +- 0.4 | 11.0 | 0.0 | 68 | 28 | 20.5 |
| girado | DQN seed2 | 192.1 +- 3.5 | 16.0 | 5.3 | 14.6 +- 0.4 | 11.0 | 0.0 | 68 | 20 | 22.9 |
| girado | Max-Pressure teto | 143.0 +- 0.0 | 11.9 | 4.0 | 21.0 +- 0.0 | 21.0 | 0.0 | 100 | 31 | 27.1 |
| girado | Tempo fixo 30s | 102.0 +- 0.0 | 8.5 | 2.8 | 31.0 +- 0.0 | 31.0 | 1.3 | 44 | 100 | 101.9 |

## B. Verde por aproximacao (primeira hora)

| cenario | controlador | N: % verde / verde medio (s) | L: % verde / verde medio (s) | S: % verde / verde medio (s) | O: % verde / verde medio (s) |
|---|---|---|---|---|---|
| equilibrado | Webster | 25.0 / 16.0 | 25.0 / 16.0 | 25.0 / 16.0 | 25.0 / 16.0 |
| equilibrado | Max-Pressure | 26.0 / 21.0 | 24.8 / 21.0 | 25.1 / 21.0 | 24.1 / 21.0 |
| equilibrado | DQN original | 24.5 / 11.8 | 21.8 / 11.0 | 26.9 / 12.7 | 26.9 / 11.4 |
| equilibrado | DQN seed1 | 26.6 / 11.8 | 24.1 / 11.2 | 25.9 / 11.8 | 23.4 / 11.3 |
| equilibrado | DQN seed2 | 24.9 / 11.6 | 22.5 / 11.3 | 27.9 / 12.5 | 24.7 / 11.4 |
| equilibrado | Max-Pressure teto | 26.7 / 11.0 | 24.8 / 11.0 | 24.9 / 11.0 | 23.6 / 11.0 |
| equilibrado | Tempo fixo 30s | 25.3 / 31.0 | 25.3 / 31.0 | 25.2 / 31.0 | 24.3 / 31.0 |
| assimetrico | Webster | 17.2 / 11.0 | 32.8 / 21.0 | 17.2 / 11.0 | 32.8 / 21.0 |
| assimetrico | Max-Pressure | 16.0 / 21.0 | 34.8 / 21.0 | 15.3 / 21.0 | 34.0 / 21.0 |
| assimetrico | DQN original | 10.4 / 11.0 | 34.1 / 11.9 | 11.6 / 11.1 | 44.0 / 14.1 |
| assimetrico | DQN seed1 | 12.5 / 11.1 | 36.3 / 11.9 | 11.8 / 11.0 | 39.3 / 13.4 |
| assimetrico | DQN seed2 | 10.6 / 11.0 | 36.6 / 13.0 | 11.5 / 11.2 | 41.3 / 14.1 |
| assimetrico | Max-Pressure teto | 15.0 / 11.1 | 35.9 / 11.5 | 13.3 / 11.0 | 35.7 / 11.6 |
| assimetrico | Tempo fixo 30s | 25.3 / 31.0 | 25.3 / 31.0 | 25.2 / 31.0 | 24.3 / 31.0 |
| pico | Webster | 25.0 / 11.0 | 25.0 / 11.0 | 25.0 / 11.0 | 25.0 / 11.0 |
| pico | Max-Pressure | 25.1 / 21.0 | 26.1 / 21.0 | 23.3 / 21.0 | 25.5 / 21.0 |
| pico | DQN original | 22.0 / 11.6 | 22.6 / 11.2 | 24.9 / 12.8 | 30.5 / 12.3 |
| pico | DQN seed1 | 24.9 / 11.8 | 25.6 / 11.4 | 23.8 / 11.6 | 25.6 / 11.6 |
| pico | DQN seed2 | 22.8 / 11.5 | 24.3 / 11.5 | 25.0 / 12.4 | 27.9 / 11.9 |
| pico | Max-Pressure teto | 25.3 / 11.0 | 26.7 / 11.0 | 22.8 / 11.0 | 25.2 / 11.0 |
| pico | Tempo fixo 30s | 25.3 / 31.0 | 25.3 / 31.0 | 25.2 / 31.0 | 24.3 / 31.0 |
| saturado | Webster | 23.1 / 31.0 | 26.9 / 36.0 | 23.1 / 31.0 | 26.9 / 36.0 |
| saturado | Max-Pressure | 22.0 / 21.0 | 28.2 / 21.0 | 21.8 / 21.0 | 27.9 / 21.0 |
| saturado | DQN original | 21.7 / 24.5 | 27.8 / 23.2 | 22.3 / 21.1 | 28.2 / 25.8 |
| saturado | DQN seed1 | 21.2 / 28.5 | 29.2 / 29.0 | 22.1 / 22.4 | 27.5 / 27.2 |
| saturado | DQN seed2 | 21.6 / 22.4 | 28.1 / 26.4 | 22.7 / 24.6 | 27.6 / 28.8 |
| saturado | Max-Pressure teto | 22.4 / 26.0 | 28.0 / 26.0 | 22.0 / 26.0 | 27.5 / 26.0 |
| saturado | Tempo fixo 30s | 25.3 / 31.0 | 25.3 / 31.0 | 25.2 / 31.0 | 24.3 / 31.0 |
| girado | Webster | 32.8 / 21.0 | 17.2 / 11.0 | 32.8 / 21.0 | 17.2 / 11.0 |
| girado | Max-Pressure | 36.0 / 21.0 | 15.0 / 21.0 | 35.2 / 21.0 | 13.7 / 21.0 |
| girado | DQN original | 37.3 / 15.0 | 8.5 / 11.0 | 43.6 / 18.3 | 10.5 / 11.1 |
| girado | DQN seed1 | 40.4 / 14.6 | 9.7 / 11.0 | 40.5 / 14.1 | 9.3 / 11.0 |
| girado | DQN seed2 | 36.1 / 13.7 | 8.4 / 11.1 | 45.8 / 17.8 | 9.7 / 11.0 |
| girado | Max-Pressure teto | 36.0 / 21.0 | 15.0 / 21.0 | 35.2 / 21.0 | 13.7 / 21.0 |
| girado | Tempo fixo 30s | 25.3 / 31.0 | 25.3 / 31.0 | 25.2 / 31.0 | 24.3 / 31.0 |

## C. Cenario pico, por periodo de 20 min

| controlador | periodo | trocas/h | verde medio (s) | % verde N/L/S/O | espera media dos carros que entraram no periodo (s) |
|---|---|---|---|---|---|
| Webster | 0-20 min (calmo) | 240.0 | 11.0 | 25/25/25/25 | 19.5 |
| Webster | 20-40 min (pico) | 240.0 | 11.0 | 25/25/25/25 | 39.7 |
| Webster | 40-60 min (calmo) | 240.0 | 11.0 | 25/25/25/25 | 22.4 |
| Max-Pressure | 0-20 min (calmo) | 141.0 | 21.0 | 28/25/23/24 | 28.6 |
| Max-Pressure | 20-40 min (pico) | 144.0 | 21.0 | 23/27/23/26 | 32.5 |
| Max-Pressure | 40-60 min (calmo) | 144.0 | 21.0 | 24/26/24/26 | 28.6 |
| DQN original | 0-20 min (calmo) | 225.6 | 11.9 | 24/20/26/30 | 17.9 |
| DQN original | 20-40 min (pico) | 218.7 | 12.5 | 21/26/23/30 | 24.1 |
| DQN original | 40-60 min (calmo) | 228.6 | 11.7 | 22/22/25/31 | 20.2 |
| DQN seed1 | 0-20 min (calmo) | 233.1 | 11.3 | 28/24/24/24 | 17.0 |
| DQN seed1 | 20-40 min (pico) | 224.1 | 12.1 | 22/28/23/27 | 23.4 |
| DQN seed1 | 40-60 min (calmo) | 234.3 | 11.4 | 25/25/25/25 | 18.4 |
| DQN seed2 | 0-20 min (calmo) | 228.6 | 11.5 | 25/23/25/27 | 17.4 |
| DQN seed2 | 20-40 min (pico) | 216.3 | 12.7 | 21/26/24/28 | 23.5 |
| DQN seed2 | 40-60 min (calmo) | 232.8 | 11.4 | 22/24/26/28 | 20.5 |
| Max-Pressure teto | 0-20 min (calmo) | 234.9 | 11.0 | 29/25/23/23 | 17.1 |
| Max-Pressure teto | 20-40 min (pico) | 240.0 | 11.0 | 22/28/22/27 | 25.1 |
| Max-Pressure teto | 40-60 min (calmo) | 239.7 | 11.0 | 25/27/23/25 | 17.3 |
| Tempo fixo 30s | 0-20 min (calmo) | 102.0 | 31.0 | 26/26/24/23 | 41.8 |
| Tempo fixo 30s | 20-40 min (pico) | 102.0 | 31.0 | 25/23/25/26 | 46.4 |
| Tempo fixo 30s | 40-60 min (calmo) | 102.0 | 31.0 | 24/26/26/23 | 42.2 |

## D. Espera por aproximacao (todos os carros da rodada)

| cenario | controlador | aprox | carros | espera media (s) | P95 (s) | max (s) | atraso de entrada (s) | maior tempo sem verde (s) |
|---|---|---|---|---|---|---|---|---|
| equilibrado | Webster | N | 450 | 26.0 | 57.9 | 79.2 | 0.0 | 64.0 |
| equilibrado | Webster | L | 447 | 26.4 | 58.5 | 75.2 | 0.0 | 64.0 |
| equilibrado | Webster | S | 463 | 27.1 | 58.5 | 75.0 | 0.0 | 64.0 |
| equilibrado | Webster | O | 446 | 26.5 | 58.2 | 76.5 | 0.0 | 64.0 |
| equilibrado | Max-Pressure | N | 450 | 30.1 | 74.1 | 112.0 | 0.0 | 124.0 |
| equilibrado | Max-Pressure | L | 447 | 30.7 | 75.4 | 110.2 | 0.0 | 121.5 |
| equilibrado | Max-Pressure | S | 463 | 30.6 | 74.6 | 106.6 | 0.0 | 111.5 |
| equilibrado | Max-Pressure | O | 446 | 32.1 | 77.7 | 121.4 | 0.0 | 131.5 |
| equilibrado | DQN original | N | 450 | 21.0 | 58.1 | 323.5 | 0.0 | 114.5 |
| equilibrado | DQN original | L | 447 | 25.5 | 62.2 | 436.0 | 0.0 | 126.5 |
| equilibrado | DQN original | S | 463 | 18.5 | 54.6 | 87.6 | 0.0 | 99.0 |
| equilibrado | DQN original | O | 446 | 16.2 | 48.6 | 76.1 | 0.0 | 90.0 |
| equilibrado | DQN seed1 | N | 450 | 18.1 | 50.4 | 84.1 | 0.0 | 101.0 |
| equilibrado | DQN seed1 | L | 447 | 19.6 | 52.5 | 207.0 | 0.0 | 107.0 |
| equilibrado | DQN seed1 | S | 463 | 18.5 | 51.6 | 83.7 | 0.0 | 93.0 |
| equilibrado | DQN seed1 | O | 446 | 21.5 | 59.6 | 100.0 | 0.0 | 106.0 |
| equilibrado | DQN seed2 | N | 450 | 20.1 | 55.7 | 93.9 | 0.0 | 113.5 |
| equilibrado | DQN seed2 | L | 447 | 27.1 | 65.3 | 547.6 | 0.0 | 120.0 |
| equilibrado | DQN seed2 | S | 463 | 16.6 | 47.9 | 80.1 | 0.0 | 92.5 |
| equilibrado | DQN seed2 | O | 446 | 19.1 | 53.7 | 198.7 | 0.0 | 106.0 |
| equilibrado | Max-Pressure teto | N | 450 | 18.6 | 47.4 | 81.3 | 0.0 | 91.0 |
| equilibrado | Max-Pressure teto | L | 447 | 19.9 | 48.1 | 82.8 | 0.0 | 97.0 |
| equilibrado | Max-Pressure teto | S | 463 | 20.4 | 50.2 | 80.9 | 0.0 | 92.5 |
| equilibrado | Max-Pressure teto | O | 446 | 21.5 | 53.0 | 87.2 | 0.0 | 100.0 |
| equilibrado | Tempo fixo 30s | N | 450 | 44.3 | 99.0 | 105.8 | 0.0 | 109.0 |
| equilibrado | Tempo fixo 30s | L | 447 | 44.2 | 99.2 | 108.9 | 0.0 | 109.0 |
| equilibrado | Tempo fixo 30s | S | 463 | 44.5 | 99.1 | 106.6 | 0.0 | 109.0 |
| equilibrado | Tempo fixo 30s | O | 446 | 43.1 | 98.8 | 106.7 | 0.0 | 109.0 |
| assimetrico | Webster | N | 175 | 27.7 | 61.3 | 69.8 | 0.0 | 69.0 |
| assimetrico | Webster | L | 750 | 26.5 | 57.7 | 81.0 | 0.0 | 59.0 |
| assimetrico | Webster | S | 184 | 28.2 | 61.7 | 66.4 | 0.0 | 69.0 |
| assimetrico | Webster | O | 751 | 29.9 | 63.5 | 92.1 | 0.1 | 59.0 |
| assimetrico | Max-Pressure | N | 175 | 57.7 | 142.7 | 204.5 | 0.0 | 244.0 |
| assimetrico | Max-Pressure | L | 750 | 19.2 | 49.8 | 78.1 | 0.1 | 84.0 |
| assimetrico | Max-Pressure | S | 184 | 57.7 | 142.9 | 216.8 | 0.0 | 249.0 |
| assimetrico | Max-Pressure | O | 751 | 20.2 | 49.5 | 88.4 | 0.1 | 94.0 |
| assimetrico | DQN original | N | 175 | 58.0 | 147.1 | 322.9 | 0.0 | 254.0 |
| assimetrico | DQN original | L | 750 | 15.4 | 41.1 | 516.2 | 0.0 | 74.5 |
| assimetrico | DQN original | S | 184 | 48.0 | 130.5 | 219.5 | 0.0 | 240.0 |
| assimetrico | DQN original | O | 751 | 8.5 | 29.1 | 50.8 | 0.1 | 58.0 |
| assimetrico | DQN seed1 | N | 175 | 43.0 | 114.3 | 197.0 | 0.0 | 224.0 |
| assimetrico | DQN seed1 | L | 750 | 12.0 | 33.9 | 169.9 | 0.0 | 63.0 |
| assimetrico | DQN seed1 | S | 184 | 43.9 | 117.5 | 200.6 | 0.0 | 240.0 |
| assimetrico | DQN seed1 | O | 751 | 11.6 | 34.1 | 283.7 | 0.1 | 65.5 |
| assimetrico | DQN seed2 | N | 175 | 51.4 | 134.2 | 217.7 | 0.0 | 245.5 |
| assimetrico | DQN seed2 | L | 750 | 15.1 | 39.2 | 850.1 | 0.1 | 70.5 |
| assimetrico | DQN seed2 | S | 184 | 46.4 | 123.1 | 205.8 | 0.0 | 246.5 |
| assimetrico | DQN seed2 | O | 751 | 10.2 | 33.7 | 188.4 | 0.1 | 66.0 |
| assimetrico | Max-Pressure teto | N | 175 | 35.9 | 95.6 | 163.8 | 0.0 | 197.5 |
| assimetrico | Max-Pressure teto | L | 750 | 14.6 | 34.6 | 66.7 | 0.0 | 62.0 |
| assimetrico | Max-Pressure teto | S | 184 | 39.0 | 104.9 | 169.3 | 0.0 | 212.5 |
| assimetrico | Max-Pressure teto | O | 751 | 15.8 | 36.7 | 79.2 | 0.0 | 62.5 |
| assimetrico | Tempo fixo 30s | N | 175 | 41.2 | 97.9 | 105.0 | 0.0 | 109.0 |
| assimetrico | Tempo fixo 30s | L | 750 | 111.9 | 190.0 | 230.5 | 3.4 | 109.0 |
| assimetrico | Tempo fixo 30s | S | 184 | 40.1 | 97.8 | 104.7 | 0.0 | 109.0 |
| assimetrico | Tempo fixo 30s | O | 751 | 97.2 | 180.1 | 235.3 | 4.9 | 109.0 |
| pico | Webster | N | 352 | 20.9 | 47.9 | 72.7 | 0.0 | 49.0 |
| pico | Webster | L | 434 | 38.1 | 90.8 | 119.3 | 0.0 | 49.0 |
| pico | Webster | S | 360 | 22.4 | 50.3 | 75.3 | 0.0 | 49.0 |
| pico | Webster | O | 433 | 33.5 | 80.6 | 114.6 | 0.0 | 49.0 |
| pico | Max-Pressure | N | 352 | 30.7 | 78.9 | 120.1 | 0.0 | 141.5 |
| pico | Max-Pressure | L | 434 | 28.4 | 71.5 | 108.1 | 0.0 | 121.5 |
| pico | Max-Pressure | S | 360 | 33.1 | 80.4 | 126.3 | 0.0 | 136.5 |
| pico | Max-Pressure | O | 433 | 29.4 | 72.7 | 103.9 | 0.0 | 126.5 |
| pico | DQN original | N | 352 | 24.8 | 69.0 | 227.7 | 0.0 | 129.5 |
| pico | DQN original | L | 434 | 25.2 | 64.5 | 541.5 | 0.0 | 116.5 |
| pico | DQN original | S | 360 | 20.2 | 61.6 | 106.1 | 0.0 | 123.5 |
| pico | DQN original | O | 433 | 15.5 | 47.6 | 297.8 | 0.0 | 87.0 |
| pico | DQN seed1 | N | 352 | 20.8 | 61.9 | 109.4 | 0.0 | 128.0 |
| pico | DQN seed1 | L | 434 | 20.0 | 53.7 | 632.9 | 0.0 | 110.5 |
| pico | DQN seed1 | S | 360 | 20.5 | 58.3 | 93.3 | 0.0 | 114.5 |
| pico | DQN seed1 | O | 433 | 19.7 | 53.9 | 197.0 | 0.0 | 105.5 |
| pico | DQN seed2 | N | 352 | 22.7 | 64.1 | 124.0 | 0.0 | 137.5 |
| pico | DQN seed2 | L | 434 | 25.0 | 60.6 | 869.1 | 0.0 | 123.5 |
| pico | DQN seed2 | S | 360 | 19.0 | 56.6 | 101.2 | 0.0 | 116.5 |
| pico | DQN seed2 | O | 433 | 17.0 | 52.4 | 86.7 | 0.0 | 96.5 |
| pico | Max-Pressure teto | N | 352 | 20.3 | 55.1 | 92.0 | 0.0 | 104.5 |
| pico | Max-Pressure teto | L | 434 | 18.7 | 46.8 | 73.5 | 0.0 | 89.5 |
| pico | Max-Pressure teto | S | 360 | 22.8 | 57.8 | 95.9 | 0.0 | 109.0 |
| pico | Max-Pressure teto | O | 433 | 21.3 | 51.3 | 80.6 | 0.0 | 97.5 |
| pico | Tempo fixo 30s | N | 352 | 42.7 | 99.3 | 105.7 | 0.0 | 109.0 |
| pico | Tempo fixo 30s | L | 434 | 44.8 | 100.0 | 111.4 | 0.0 | 109.0 |
| pico | Tempo fixo 30s | S | 360 | 43.6 | 98.7 | 107.2 | 0.0 | 109.0 |
| pico | Tempo fixo 30s | O | 433 | 44.5 | 100.3 | 112.6 | 0.0 | 109.0 |
| saturado | Webster | N | 601 | 56.9 | 116.8 | 155.2 | 0.1 | 119.0 |
| saturado | Webster | L | 802 | 94.6 | 161.3 | 213.3 | 2.0 | 114.0 |
| saturado | Webster | S | 618 | 62.4 | 126.3 | 169.0 | 0.0 | 119.0 |
| saturado | Webster | O | 798 | 83.0 | 153.4 | 206.5 | 3.2 | 114.0 |
| saturado | Max-Pressure | N | 601 | 94.0 | 177.4 | 230.0 | 0.1 | 156.5 |
| saturado | Max-Pressure | L | 802 | 74.2 | 132.0 | 176.6 | 0.1 | 109.0 |
| saturado | Max-Pressure | S | 618 | 93.4 | 170.2 | 232.9 | 0.1 | 154.0 |
| saturado | Max-Pressure | O | 798 | 77.3 | 132.9 | 177.8 | 0.2 | 116.5 |
| saturado | DQN original | N | 601 | 58.5 | 132.9 | 385.4 | 0.0 | 184.0 |
| saturado | DQN original | L | 802 | 54.9 | 107.9 | 457.8 | 0.1 | 132.0 |
| saturado | DQN original | S | 618 | 48.9 | 107.3 | 153.0 | 0.0 | 141.0 |
| saturado | DQN original | O | 798 | 46.4 | 104.4 | 151.1 | 0.1 | 138.5 |
| saturado | DQN seed1 | N | 601 | 69.5 | 160.9 | 223.3 | 0.0 | 220.0 |
| saturado | DQN seed1 | L | 802 | 40.1 | 96.0 | 239.4 | 0.1 | 140.0 |
| saturado | DQN seed1 | S | 618 | 46.5 | 107.3 | 146.4 | 0.1 | 138.0 |
| saturado | DQN seed1 | O | 798 | 59.3 | 124.1 | 174.5 | 0.1 | 143.0 |
| saturado | DQN seed2 | N | 601 | 51.9 | 115.2 | 173.6 | 0.0 | 174.5 |
| saturado | DQN seed2 | L | 802 | 45.6 | 97.2 | 761.6 | 0.1 | 125.5 |
| saturado | DQN seed2 | S | 618 | 50.2 | 114.9 | 166.3 | 0.1 | 162.0 |
| saturado | DQN seed2 | O | 798 | 60.1 | 128.6 | 489.2 | 0.1 | 168.5 |
| saturado | Max-Pressure teto | N | 601 | 66.7 | 141.6 | 187.5 | 0.1 | 169.0 |
| saturado | Max-Pressure teto | L | 802 | 55.0 | 104.7 | 150.7 | 0.1 | 127.0 |
| saturado | Max-Pressure teto | S | 618 | 65.5 | 135.3 | 191.6 | 0.0 | 169.0 |
| saturado | Max-Pressure teto | O | 798 | 56.5 | 106.4 | 151.7 | 0.1 | 130.0 |
| saturado | Tempo fixo 30s | N | 601 | 48.2 | 101.5 | 129.4 | 0.0 | 109.0 |
| saturado | Tempo fixo 30s | L | 802 | 166.0 | 279.4 | 297.7 | 41.8 | 109.0 |
| saturado | Tempo fixo 30s | S | 618 | 49.3 | 102.3 | 133.7 | 0.0 | 109.0 |
| saturado | Tempo fixo 30s | O | 798 | 146.2 | 258.6 | 291.7 | 31.5 | 109.0 |
| girado | Webster | N | 748 | 27.5 | 58.8 | 83.3 | 0.1 | 59.0 |
| girado | Webster | L | 181 | 27.4 | 61.3 | 67.5 | 0.0 | 69.0 |
| girado | Webster | S | 771 | 30.7 | 64.1 | 94.5 | 0.0 | 59.0 |
| girado | Webster | O | 183 | 27.6 | 61.5 | 66.1 | 0.0 | 69.0 |
| girado | Max-Pressure | N | 748 | 18.7 | 49.0 | 83.3 | 0.1 | 89.0 |
| girado | Max-Pressure | L | 181 | 58.0 | 144.3 | 226.5 | 0.0 | 259.0 |
| girado | Max-Pressure | S | 771 | 19.6 | 49.1 | 86.3 | 0.0 | 86.5 |
| girado | Max-Pressure | O | 183 | 62.6 | 159.6 | 267.2 | 0.0 | 301.5 |
| girado | DQN original | N | 748 | 13.0 | 39.0 | 73.7 | 0.1 | 80.0 |
| girado | DQN original | L | 181 | 70.1 | 175.2 | 361.4 | 0.0 | 288.0 |
| girado | DQN original | S | 771 | 9.9 | 34.4 | 59.8 | 0.0 | 68.5 |
| girado | DQN original | O | 183 | 53.6 | 145.8 | 314.9 | 0.0 | 245.5 |
| girado | DQN seed1 | N | 748 | 11.4 | 38.5 | 68.1 | 0.0 | 75.5 |
| girado | DQN seed1 | L | 181 | 60.6 | 156.8 | 429.6 | 0.0 | 242.5 |
| girado | DQN seed1 | S | 771 | 9.8 | 31.4 | 59.4 | 0.0 | 66.5 |
| girado | DQN seed1 | O | 183 | 63.9 | 164.1 | 339.5 | 0.0 | 283.5 |
| girado | DQN seed2 | N | 748 | 12.9 | 37.0 | 67.0 | 0.0 | 69.5 |
| girado | DQN seed2 | L | 181 | 89.5 | 203.2 | 752.7 | 0.0 | 323.0 |
| girado | DQN seed2 | S | 771 | 8.3 | 30.0 | 57.9 | 0.1 | 67.0 |
| girado | DQN seed2 | O | 183 | 60.7 | 166.7 | 331.1 | 0.0 | 265.0 |
| girado | Max-Pressure teto | N | 748 | 18.7 | 49.0 | 83.3 | 0.1 | 89.0 |
| girado | Max-Pressure teto | L | 181 | 58.0 | 144.3 | 226.5 | 0.0 | 259.0 |
| girado | Max-Pressure teto | S | 771 | 19.6 | 49.1 | 86.3 | 0.0 | 86.5 |
| girado | Max-Pressure teto | O | 183 | 62.6 | 159.6 | 267.2 | 0.0 | 301.5 |
| girado | Tempo fixo 30s | N | 748 | 106.1 | 187.8 | 233.8 | 1.1 | 109.0 |
| girado | Tempo fixo 30s | L | 181 | 39.4 | 97.4 | 105.1 | 0.0 | 109.0 |
| girado | Tempo fixo 30s | S | 771 | 126.1 | 221.5 | 252.1 | 19.4 | 109.0 |
| girado | Tempo fixo 30s | O | 183 | 39.6 | 99.0 | 105.1 | 0.0 | 109.0 |

## Escoamento: verde ocioso e carros presos no fim

Escoamento = depois dos 3600 s, ate o ultimo carro sair ou 1200 s. 'Verde ocioso' = decisao de manter o verde numa aproximacao sem fila enquanto outra tem carro parado (5 s por decisao).

| cenario | controlador | rodadas que bateram 1200 s | carros presos (total 10 sementes) | verde ocioso na hora (s) | maior verde ocioso seguido na hora (s) | verde ocioso no escoamento (s) | escoamento medio (s) | espera media so de quem chegou (s) |
|---|---|---|---|---|---|---|---|---|
| equilibrado | Webster | 0/10 | 0 | 889.0 | 5.0 | 16.0 | 92 | 26.5 |
| equilibrado | Max-Pressure | 0/10 | 0 | 1421.5 | 10.0 | 30.0 | 103 | 30.9 |
| equilibrado | DQN original | 4/10 | 7 | 164.5 | 18.0 | 456.0 | 529 | 19.9 |
| equilibrado | DQN seed1 | 1/10 | 1 | 121.5 | 15.5 | 118.5 | 198 | 19.3 |
| equilibrado | DQN seed2 | 4/10 | 14 | 165.0 | 19.5 | 457.0 | 527 | 19.8 |
| equilibrado | Max-Pressure teto | 0/10 | 0 | 0.0 | 0.0 | 0.0 | 80 | 20.1 |
| equilibrado | Tempo fixo 30s | 0/10 | 0 | 1972.5 | 20.0 | 58.5 | 136 | 44.0 |
| assimetrico | Webster | 0/10 | 0 | 795.5 | 10.0 | 14.5 | 98 | 28.1 |
| assimetrico | Max-Pressure | 0/10 | 0 | 1397.5 | 10.0 | 29.0 | 102 | 27.0 |
| assimetrico | DQN original | 4/10 | 6 | 336.5 | 22.5 | 459.5 | 525 | 19.5 |
| assimetrico | DQN seed1 | 3/10 | 4 | 265.5 | 13.0 | 342.5 | 419 | 17.7 |
| assimetrico | DQN seed2 | 7/10 | 18 | 402.5 | 24.0 | 795.5 | 863 | 18.5 |
| assimetrico | Max-Pressure teto | 0/10 | 0 | 99.0 | 18.0 | 55.0 | 139 | 19.5 |
| assimetrico | Tempo fixo 30s | 0/10 | 0 | 1387.5 | 20.0 | 105.5 | 286 | 92.2 |
| pico | Webster | 0/10 | 0 | 0.0 | 0.0 | 0.0 | 77 | 29.4 |
| pico | Max-Pressure | 0/10 | 0 | 1412.5 | 10.0 | 28.5 | 97 | 30.3 |
| pico | DQN original | 6/10 | 10 | 223.0 | 22.5 | 687.5 | 750 | 20.5 |
| pico | DQN seed1 | 6/10 | 7 | 132.0 | 14.0 | 683.5 | 752 | 19.7 |
| pico | DQN seed2 | 7/10 | 14 | 190.0 | 15.5 | 802.0 | 862 | 19.9 |
| pico | Max-Pressure teto | 0/10 | 0 | 0.0 | 0.0 | 0.0 | 78 | 20.7 |
| pico | Tempo fixo 30s | 0/10 | 0 | 1970.0 | 20.0 | 58.0 | 132 | 44.0 |
| saturado | Webster | 0/10 | 0 | 1195.0 | 25.0 | 78.5 | 209 | 76.2 |
| saturado | Max-Pressure | 0/10 | 0 | 424.0 | 10.0 | 38.0 | 201 | 83.5 |
| saturado | DQN original | 5/10 | 8 | 1067.0 | 22.5 | 561.0 | 663 | 51.6 |
| saturado | DQN seed1 | 1/10 | 2 | 1224.5 | 31.5 | 129.0 | 237 | 53.2 |
| saturado | DQN seed2 | 6/10 | 18 | 1178.5 | 29.0 | 688.5 | 783 | 51.3 |
| saturado | Max-Pressure teto | 0/10 | 0 | 1002.5 | 15.0 | 72.0 | 172 | 60.2 |
| saturado | Tempo fixo 30s | 0/10 | 0 | 989.0 | 20.0 | 163.0 | 484 | 109.7 |
| girado | Webster | 0/10 | 0 | 766.5 | 10.0 | 19.0 | 95 | 28.8 |
| girado | Max-Pressure | 0/10 | 0 | 1401.0 | 10.0 | 33.0 | 109 | 27.1 |
| girado | DQN original | 2/10 | 3 | 777.0 | 41.0 | 233.5 | 308 | 21.0 |
| girado | DQN seed1 | 3/10 | 4 | 522.0 | 28.0 | 349.5 | 418 | 20.3 |
| girado | DQN seed2 | 6/10 | 15 | 697.5 | 37.5 | 684.0 | 755 | 22.0 |
| girado | Max-Pressure teto | 0/10 | 0 | 1401.0 | 10.0 | 33.0 | 109 | 27.1 |
| girado | Tempo fixo 30s | 0/10 | 0 | 1311.0 | 20.0 | 124.5 | 320 | 101.4 |

## Transicoes realmente executadas

- equilibrado / Webster: vermelho geral executado com [1] s
- equilibrado / Max-Pressure: vermelho geral executado com [1] s
- equilibrado / DQN original: vermelho geral executado com [1] s
- equilibrado / DQN seed1: vermelho geral executado com [1] s
- equilibrado / DQN seed2: vermelho geral executado com [1] s
- equilibrado / Max-Pressure teto: vermelho geral executado com [1] s
- equilibrado / Tempo fixo 30s: vermelho geral executado com [1] s
- assimetrico / Webster: vermelho geral executado com [1] s
- assimetrico / Max-Pressure: vermelho geral executado com [1] s
- assimetrico / DQN original: vermelho geral executado com [1] s
- assimetrico / DQN seed1: vermelho geral executado com [1] s
- assimetrico / DQN seed2: vermelho geral executado com [1] s
- assimetrico / Max-Pressure teto: vermelho geral executado com [1] s
- assimetrico / Tempo fixo 30s: vermelho geral executado com [1] s
- pico / Webster: vermelho geral executado com [1] s
- pico / Max-Pressure: vermelho geral executado com [1] s
- pico / DQN original: vermelho geral executado com [1] s
- pico / DQN seed1: vermelho geral executado com [1] s
- pico / DQN seed2: vermelho geral executado com [1] s
- pico / Max-Pressure teto: vermelho geral executado com [1] s
- pico / Tempo fixo 30s: vermelho geral executado com [1] s
- saturado / Webster: vermelho geral executado com [1] s
- saturado / Max-Pressure: vermelho geral executado com [1] s
- saturado / DQN original: vermelho geral executado com [1] s
- saturado / DQN seed1: vermelho geral executado com [1] s
- saturado / DQN seed2: vermelho geral executado com [1] s
- saturado / Max-Pressure teto: vermelho geral executado com [1] s
- saturado / Tempo fixo 30s: vermelho geral executado com [1] s
- girado / Webster: vermelho geral executado com [1] s
- girado / Max-Pressure: vermelho geral executado com [1] s
- girado / DQN original: vermelho geral executado com [1] s
- girado / DQN seed1: vermelho geral executado com [1] s
- girado / DQN seed2: vermelho geral executado com [1] s
- girado / Max-Pressure teto: vermelho geral executado com [1] s
- girado / Tempo fixo 30s: vermelho geral executado com [1] s
