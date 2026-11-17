# Teste final inédito (sementes 241-250, cenário intenso)

RL: média das 5 sementes de modelo (cada uma = média das 10 demandas); ± dp entre sementes de modelo. Baselines: média ± dp entre as 10 demandas. Só avaliações válidas entram nas médias.

| Controlador | Espera média corredor (s) | P95 corredor (s) | Espera média rede (s) | P95 rede (s) | Fila média Gomes de Carvalho | Fila média Casa do Ator | Fila média Quatá | Fila máx. Gomes de Carvalho | Fila máx. Casa do Ator | Fila máx. Quatá | Concluídas (%) | Bloqueio saída (s) | Entreverdes 3 TLS (s) | Trocas de fase 3 TLS | Teleportes | Colisões (nos 3) | Violações | Inválidas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Original atuado (SUMO) | 15.48 ± 3.03 | 53.84 ± 10.92 | 40.47 ± 2.51 | 119.02 ± 5.98 | 2.21 ± 1.03 | 1.81 ± 0.31 | 4.02 ± 0.43 | 16.80 ± 5.67 | 15.00 ± 3.80 | 22.00 ± 1.94 | 100.00 ± 0.00 | 34.30 ± 13.04 | 2225.40 ± 78.93 | — | 0 | 0 (0) | 0 | 0/10 |
| Atuado c/ regras RL (verde 10) | 22.25 ± 2.97 | 66.09 ± 13.26 | 46.54 ± 2.91 | 125.27 ± 6.82 | 2.99 ± 0.70 | 2.75 ± 0.32 | 5.83 ± 0.75 | 15.90 ± 4.91 | 16.90 ± 2.85 | 24.50 ± 4.03 | 100.00 ± 0.00 | 57.80 ± 9.04 | 1733.00 ± 52.66 | 345.90 ± 10.51 | 0 | 0 (0) | 0 | 0/10 |
| Atuado c/ regras RL (verde 5) | 22.01 ± 1.81 | 67.00 ± 5.79 | 46.50 ± 1.71 | 127.92 ± 4.86 | 2.76 ± 0.64 | 2.56 ± 0.27 | 6.13 ± 0.65 | 15.10 ± 4.01 | 16.20 ± 3.52 | 26.70 ± 3.83 | 100.00 ± 0.00 | 43.10 ± 10.91 | 1915.50 ± 61.48 | 382.40 ± 12.28 | 0 | 1 (0) | 0 | 0/10 |
| Max-Pressure (fila só faixa imediata) | 54.77 ± 6.20 | 234.62 ± 22.14 | 102.41 ± 9.20 | 347.49 ± 28.64 | 13.64 ± 0.71 | 4.58 ± 0.19 | 6.44 ± 1.74 | 31.20 ± 2.97 | 16.20 ± 1.03 | 25.10 ± 7.08 | 100.00 ± 0.00 | 57.50 ± 12.73 | 3124.00 ± 59.01 | 624.10 ± 11.91 | 69 | 1 (0) | 0 | 0/10 |
| A anterior (v1) | 20.99 ± 0.86 | 56.29 ± 2.28 | 45.63 ± 1.00 | 121.79 ± 2.59 | 3.00 ± 0.27 | 2.41 ± 0.08 | 5.47 ± 0.29 | 15.00 ± 1.14 | 14.26 ± 0.77 | 22.26 ± 1.17 | 100.00 ± 0.00 | 68.82 ± 4.24 | 1990.22 ± 52.30 | 397.38 ± 10.51 | 0 | 2 (0) | 0 | 0/50 |
| B anterior (v1) | 21.84 ± 1.16 | 58.72 ± 3.77 | 46.39 ± 1.13 | 123.05 ± 1.82 | 3.11 ± 0.37 | 2.51 ± 0.05 | 5.70 ± 0.33 | 16.14 ± 1.48 | 14.54 ± 0.46 | 23.76 ± 1.70 | 100.00 ± 0.00 | 74.66 ± 11.29 | 1963.10 ± 72.60 | 391.94 ± 14.55 | 0 | 1 (0) | 0 | 0/50 |
| A: colisão atribuída | 21.49 ± 1.32 | 58.53 ± 3.47 | 45.97 ± 1.15 | 123.65 ± 2.41 | 3.17 ± 0.47 | 2.45 ± 0.10 | 5.52 ± 0.30 | 15.70 ± 1.01 | 14.10 ± 0.86 | 22.72 ± 1.59 | 100.00 ± 0.00 | 71.60 ± 8.21 | 1943.70 ± 49.49 | 388.08 ± 9.87 | 0 | 1 (0) | 0 | 0/50 |
| A: col. atribuída + verde 5 | 22.83 ± 3.77 | 73.74 ± 33.53 | 47.26 ± 3.05 | 136.53 ± 30.52 | 3.49 ± 1.31 | 2.17 ± 0.05 | 5.82 ± 0.27 | 16.22 ± 1.93 | 14.32 ± 0.51 | 24.38 ± 1.11 | 100.00 ± 0.00 | 61.56 ± 7.24 | 2408.88 ± 77.96 | 481.36 ± 15.67 | 0 | 2 (0) | 0 | 0/50 |
| B: col. atribuída, sup 30 s | 22.04 ± 0.68 | 59.21 ± 1.58 | 46.48 ± 0.60 | 124.19 ± 1.15 | 3.24 ± 0.23 | 2.59 ± 0.23 | 5.61 ± 0.26 | 16.76 ± 0.97 | 14.98 ± 1.06 | 23.92 ± 1.34 | 100.00 ± 0.00 | 74.98 ± 6.40 | 2002.40 ± 53.03 | 399.86 ± 10.65 | 0 | 1 (0) | 0 | 0/50 |
| B: col. atribuída, sup 15 s | 21.84 ± 0.48 | 59.94 ± 2.04 | 46.37 ± 0.48 | 124.30 ± 1.88 | 3.10 ± 0.21 | 2.49 ± 0.11 | 5.72 ± 0.20 | 15.94 ± 1.82 | 15.40 ± 0.69 | 23.50 ± 1.07 | 100.00 ± 0.00 | 79.50 ± 2.58 | 1984.86 ± 82.91 | 396.30 ± 16.60 | 0 | 1 (0) | 0 | 0/50 |

## Variabilidade e vitórias por demanda

| Controlador | Espera corredor | dp entre sementes de modelo | dp entre sementes de tráfego | vence o original em (sementes de tráfego) |
|---|---:|---:|---:|---:|
| Original atuado (SUMO) | 15.48 | None | 3.03 | 0/10 |
| Atuado c/ regras RL (verde 10) | 22.25 | None | 2.97 | 0/10 |
| Atuado c/ regras RL (verde 5) | 22.01 | None | 1.81 | 0/10 |
| Max-Pressure (fila só faixa imediata) | 54.77 | None | 6.20 | 0/10 |
| A anterior (v1) | 20.99 | 0.86 | 1.11 | 0/10 |
| B anterior (v1) | 21.84 | 1.16 | 1.94 | 0/10 |
| A: colisão atribuída | 21.49 | 1.32 | 2.01 | 0/10 |
| A: col. atribuída + verde 5 | 22.83 | 3.77 | 5.59 | 0/10 |
| B: col. atribuída, sup 30 s | 22.04 | 0.68 | 1.43 | 0/10 |
| B: col. atribuída, sup 15 s | 21.84 | 0.48 | 0.88 | 0/10 |

## Comparações pareadas entre configurações

| Comparação (B − A, pareada por semente de modelo) | Δ espera corredor (s) | IC95 | melhor em |
|---|---:|---:|---:|
| A: colisão atribuída − A anterior (v1) | +0.50 | ±1.81 | 2/5 |
| A: col. atribuída + verde 5 − A: colisão atribuída | +1.33 | ±3.29 | 2/5 |
| B anterior (v1) − A anterior (v1) | +0.85 | ±1.96 | 2/5 |
| B: col. atribuída, sup 30 s − A: colisão atribuída | +0.55 | ±2.21 | 2/5 |
| B: col. atribuída, sup 15 s − A: colisão atribuída | +0.34 | ±1.52 | 1/5 |
| B: col. atribuída, sup 30 s − B anterior (v1) | +0.20 | ±1.77 | 3/5 |
| B: col. atribuída, sup 15 s − B anterior (v1) | -0.00 | ±1.21 | 1/5 |
| B: col. atribuída, sup 15 s − B: col. atribuída, sup 30 s | -0.21 | ±1.28 | 3/5 |
| A: col. atribuída + verde 5 − A anterior (v1) | +1.84 | ±4.88 | 2/5 |

## RL contra baselines, pareado por demanda (média dos 5 modelos em cada demanda)

| Controlador | Δ vs original atuado (s) | IC95 (10 demandas) | Δ vs atuado c/ regras RL (mesmo verde) | IC95 |
|---|---:|---:|---:|---:|
| A anterior (v1) | +5.51 | ±2.01 | -1.26 (verde 10) | ±1.51 |
| B anterior (v1) | +6.36 | ±2.27 | -0.42 (verde 10) | ±1.44 |
| A: colisão atribuída | +6.01 | ±2.20 | -0.76 (verde 10) | ±1.79 |
| A: col. atribuída + verde 5 | +7.34 | ±4.48 | +0.82 (verde 5) | ±4.36 |
| B: col. atribuída, sup 30 s | +6.56 | ±2.50 | -0.21 (verde 10) | ±2.07 |
| B: col. atribuída, sup 15 s | +6.35 | ±2.46 | -0.42 (verde 10) | ±2.00 |
