# Experimento 1: recompensa fila + excesso de espera (dinamica C)

W = 60 s, beta = 1. Media de 10 sementes de teste (+- dp). Esperas incluem os veiculos nao atendidos (limite inferior), exceto 'concluidos'. Nao atendidos e intervencoes: total nas 10 sementes. Espera max: maior das 10 sementes.

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
| **DQN C fila (media das 3)** | 23.6 +- 0.8 | 23.5 | 64.0 +- 2.3 | 63.1 | 59.8 | 54.1 | 73.9 | 75.1 +- 3.8 | - | 1195 | 5 | 221.1 | 0 | 10 |
| **DQN C fila_excesso (media das 3)** | 23.2 +- 0.4 | 23.2 | 61.5 +- 0.9 | 56.8 | 63.6 | 59.8 | 63.6 | 69.4 +- 2.2 | - | 156 | 0 | 226.6 | 0 | 0 |

fila_excesso - fila (pareado por semente; media das 3 redes): espera media (s): -0.38 (-1.6%), menor em 8/10; P95 geral (s): -2.47 (-3.9%), menor em 8/10; pior P95 aprox. (s): -5.67 (-7.5%), menor em 10/10; espera max c/ nao atendidos (s): -152.30 (-56.8%), menor em 9/10; nao atendidos: -0.17 (-100.0%), menor em 4/10; trocas/h: +5.50 (+2.5%), menor em 0/10

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
| **DQN C fila (media das 3)** | 21.5 +- 0.6 | 21.5 | 77.4 +- 2.6 | 144.9 | 38.3 | 126.6 | 45.1 | 150.1 +- 8.9 | 135.7 +- 6.4 | 1194 | 4 | 196.8 | 1 | 6 |
| **DQN C fila_excesso (media das 3)** | 21.0 +- 0.6 | 21.0 | 76.8 +- 3.3 | 137.2 | 38.9 | 136.3 | 40.4 | 145.5 +- 8.8 | 136.8 +- 8.7 | 309 | 0 | 206.7 | 0 | 0 |

fila_excesso - fila (pareado por semente; media das 3 redes): espera media (s): -0.51 (-2.4%), menor em 8/10; P95 geral (s): -0.63 (-0.8%), menor em 6/10; pior P95 aprox. (s): -4.53 (-3.0%), menor em 9/10; P95 secundarias (s): +1.07 (+0.8%), menor em 3/10; espera max c/ nao atendidos (s): -116.67 (-32.8%), menor em 6/10; nao atendidos: -0.13 (-100.0%), menor em 4/10; trocas/h: +9.87 (+5.0%), menor em 0/10

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
| **DQN C fila (media das 3)** | 23.3 +- 0.9 | 23.2 | 66.0 +- 2.5 | 73.5 | 56.6 | 62.8 | 68.0 | 77.1 +- 4.5 | - | 1189 | 3 | 221.0 | 0 | 10 |
| **DQN C fila_excesso (media das 3)** | 23.2 +- 1.0 | 23.2 | 63.7 +- 2.8 | 66.6 | 60.8 | 66.5 | 60.1 | 72.3 +- 3.2 | - | 172 | 0 | 224.0 | 0 | 0 |

fila_excesso - fila (pareado por semente; media das 3 redes): espera media (s): -0.11 (-0.5%), menor em 5/10; P95 geral (s): -2.23 (-3.4%), menor em 10/10; pior P95 aprox. (s): -4.83 (-6.3%), menor em 8/10; espera max c/ nao atendidos (s): -78.37 (-38.6%), menor em 8/10; nao atendidos: -0.10 (-100.0%), menor em 2/10; trocas/h: +3.00 (+1.4%), menor em 0/10

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
| **DQN C fila (media das 3)** | 62.4 +- 6.2 | 62.4 | 138.3 +- 13.1 | 150.1 | 128.2 | 133.4 | 133.6 | 158.8 +- 17.0 | - | 295 | 0 | 106.3 | 18 | 6 |
| **DQN C fila_excesso (media das 3)** | 64.5 +- 7.2 | 64.5 | 135.7 +- 13.9 | 162.7 | 123.6 | 130.2 | 120.2 | 164.4 +- 23.1 | - | 337 | 0 | 112.8 | 1 | 0 |

fila_excesso - fila (pareado por semente; media das 3 redes): espera media (s): +2.16 (+3.5%), menor em 1/10; P95 geral (s): -2.57 (-1.9%), menor em 7/10; pior P95 aprox. (s): +5.53 (+3.5%), menor em 2/10; espera max c/ nao atendidos (s): +3.73 (+1.7%), menor em 4/10; nao atendidos: +0.00, menor em 0/10; trocas/h: +6.43 (+6.1%), menor em 0/10

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
| **DQN C fila (media das 3)** | 25.3 +- 0.8 | 25.3 | 113.0 +- 5.6 | 41.2 | 177.7 | 35.4 | 211.8 | 214.3 +- 17.9 | 194.8 +- 10.2 | 1183 | 1 | 188.3 | 0 | 8 |
| **DQN C fila_excesso (media das 3)** | 23.1 +- 1.3 | 23.1 | 95.2 +- 6.9 | 37.5 | 169.0 | 35.6 | 161.9 | 181.1 +- 12.0 | 165.5 +- 11.8 | 332 | 0 | 202.4 | 0 | 0 |

fila_excesso - fila (pareado por semente; media das 3 redes): espera media (s): -2.23 (-8.8%), menor em 10/10; P95 geral (s): -17.83 (-15.8%), menor em 10/10; pior P95 aprox. (s): -33.13 (-15.5%), menor em 10/10; P95 secundarias (s): -29.27 (-15.0%), menor em 10/10; espera max c/ nao atendidos (s): -66.83 (-19.3%), menor em 9/10; nao atendidos: -0.03 (-100.0%), menor em 1/10; trocas/h: +14.13 (+7.5%), menor em 0/10

## Teste do carro sozinho (redes novas)

- DQN excesso C seed0: 0/36 combinacoes presas; 0 atendidas so pela regra de seguranca
- DQN excesso C seed1: 0/36 combinacoes presas; 0 atendidas so pela regra de seguranca
- DQN excesso C seed2: 0/36 combinacoes presas; 0 atendidas so pela regra de seguranca

## Criterios definidos antes do treino

- 1_zero_nao_atendidos: True
- 1_zero_ciclos_carro_sozinho: True
- 2_p95_secundarias_cai_20pct: False
- 2_p95_secundarias_variacao_pct: {'assimetrico': 0.7859511236645005, 'girado': -15.027813436029096}
- 2_espera_max_cai: False
- 3_espera_media_piora_no_maximo_5pct: True
- 3_espera_media_variacao_pct: {'equilibrado': -1.6106982707455486, 'assimetrico': -2.3614010214769765, 'pico': -0.456507876136599, 'saturado': 3.4635305388696147, 'girado': -8.78327025046429}
- 3_abaixo_de_webster_e_mp_teto: True
