# Modelo C (Parameter Sharing): testes de generalização com pesos congelados

RL: média de 5 modelos ± dp entre modelos (cada modelo = média das demandas válidas). Baselines: ± dp entre demandas. Inválidos = episódios com travamento ou < 95% das viagens concluídas (fora das médias).

## Moderada (1200 veíc/h, 261-270)

| Controlador | Espera corredor (s) | P95 corredor (s) | Espera rede (s) | Bloqueio saída (s) | Concluídas mín. | Teleportes | Colisões (nos 3) | Violações | Inválidos |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Original atuado (SUMO) | 5.47 ± 0.33 | 18.10 ± 0.99 | 29.58 ± 1.08 | 6.70 ± 3.80 | 1.000 | 0 | 0 (0) | 0 | 0/10 |
| Atuado c/ regras do RL | 10.20 ± 0.42 | 31.04 ± 2.10 | 33.24 ± 1.10 | 25.30 ± 7.39 | 1.000 | 0 | 0 (0) | 0 | 0/10 |
| A: independentes | 11.90 ± 1.41 | 37.25 ± 3.81 | 34.84 ± 1.27 | 22.94 ± 1.34 | 1.000 | 0 | 0 (0) | 0 | 0/50 |
| C: parameter sharing | 11.09 ± 0.32 | 34.90 ± 1.88 | 34.27 ± 0.19 | 28.94 ± 3.80 | 1.000 | 0 | 0 (0) | 0 | 0/50 |

| Comparação pareada por demanda (Δ espera corredor, s) | Δ médio | IC95 | demandas em que melhora |
|---|---:|---:|---:|
| C: parameter sharing − A independentes | -0.81 | ±0.12 | 10/10 |
| C: parameter sharing − original atuado | +5.62 | ±0.20 | 0/10 |

## Intensa não vista (2000 veíc/h, 251-260)

| Controlador | Espera corredor (s) | P95 corredor (s) | Espera rede (s) | Bloqueio saída (s) | Concluídas mín. | Teleportes | Colisões (nos 3) | Violações | Inválidos |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Original atuado (SUMO) | 15.90 ± 2.51 | 55.02 ± 10.23 | 41.71 ± 2.99 | 40.90 ± 12.78 | 1.000 | 0 | 4 (0) | 0 | 0/10 |
| Atuado c/ regras do RL | 25.05 ± 5.73 | 77.00 ± 27.34 | 49.34 ± 5.83 | 58.30 ± 17.15 | 1.000 | 0 | 0 (0) | 0 | 0/10 |
| A: independentes | 21.76 ± 1.27 | 60.75 ± 5.80 | 46.59 ± 1.09 | 71.44 ± 7.46 | 1.000 | 0 | 3 (0) | 0 | 0/50 |
| B: hierárquico (sup 15 s) | 22.67 ± 0.94 | 62.40 ± 2.12 | 47.30 ± 0.82 | 79.44 ± 2.49 | 1.000 | 1 | 3 (0) | 0 | 0/50 |
| C: parameter sharing | 22.50 ± 1.29 | 63.91 ± 4.11 | 47.22 ± 1.06 | 72.86 ± 3.76 | 1.000 | 3 | 2 (0) | 0 | 0/50 |
| C transf.: Casa do Ator fora do treino | 22.59 ± 0.71 | 65.42 ± 2.71 | 47.47 ± 0.83 | 76.22 ± 8.94 | 0.971 | 5 | 3 (0) | 0 | 1/50 |

| Comparação pareada por demanda (Δ espera corredor, s) | Δ médio | IC95 | demandas em que melhora |
|---|---:|---:|---:|
| C: parameter sharing − A independentes | +0.74 | ±1.25 | 4/10 |
| C: parameter sharing − original atuado | +6.60 | ±1.92 | 0/10 |
| C transf.: Casa do Ator fora do treino − A independentes | +0.90 | ±0.56 | 1/10 |
| C transf.: Casa do Ator fora do treino − original atuado | +6.76 | ±1.57 | 0/10 |
| B: hierárquico (sup 15 s) − A independentes | +0.91 | ±0.69 | 2/10 |
| B: hierárquico (sup 15 s) − original atuado | +6.78 | ±1.33 | 0/10 |

## Saturada (2400 veíc/h, 271-280)

| Controlador | Espera corredor (s) | P95 corredor (s) | Espera rede (s) | Bloqueio saída (s) | Concluídas mín. | Teleportes | Colisões (nos 3) | Violações | Inválidos |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Original atuado (SUMO) | 42.19 ± 10.84 | 141.25 ± 40.82 | 75.55 ± 16.55 | 51.00 ± 17.01 | 0.913 | 36 | 1 (0) | 0 | 1/10 |
| Atuado c/ regras do RL | 49.48 ± 5.19 | 146.34 ± 21.77 | 82.33 ± 9.57 | 58.78 ± 13.22 | 0.913 | 29 | 1 (0) | 0 | 1/10 |
| A: independentes | 48.04 ± 3.85 | 149.89 ± 21.48 | 79.27 ± 4.82 | 74.63 ± 7.20 | 0.727 | 122 | 2 (0) | 0 | 1/50 |
| C: parameter sharing | 44.83 ± 10.83 | 134.76 ± 52.41 | 73.65 ± 13.26 | 75.98 ± 2.14 | 0.208 | 177 | 2 (0) | 0 | 15/50 |

| Comparação pareada por demanda (Δ espera corredor, s) | Δ médio | IC95 | demandas em que melhora |
|---|---:|---:|---:|
| C: parameter sharing − A independentes | +1.67 | ±5.25 | 5/10 |
| C: parameter sharing − original atuado | +7.76 | ±5.42 | 1/9 |

## Transferência (demanda intensa não vista): fila média por cruzamento

| Controlador | Gomes de Carvalho | Casa do Ator (fora do treino no C transf.) | Quatá |
|---|---:|---:|---:|
| Original atuado (SUMO) | 2.00 ± 0.81 | 1.88 ± 0.28 | 4.44 ± 0.77 |
| Atuado c/ regras do RL | 3.33 ± 0.74 | 3.02 ± 0.39 | 6.76 ± 2.16 |
| A: independentes | 3.16 ± 0.44 | 2.54 ± 0.14 | 5.62 ± 0.27 |
| C: parameter sharing | 3.03 ± 0.41 | 2.67 ± 0.16 | 5.97 ± 0.30 |
| C transf.: Casa do Ator fora do treino | 2.98 ± 0.14 | 2.81 ± 0.11 | 6.01 ± 0.22 |

## Validação (sementes 221-225; checkpoints escolhidos só aqui)

| Braço | s1 | s2 | s3 | s4 | s5 | média ± dp |
|---|---|---|---|---|---|---|
| A: independentes | 19.55 (ep75) | 19.77 (ep50) | 21.57 (ep100) | 20.55 (ep125) | 22.93 (ep50) | 20.88 ± 1.39 |
| B: hierárquico (sup 15 s) | 20.61 (ep150) | 21.13 (ep125) | 21.49 (ep125) | 21.43 (ep125) | 24.10 (ep50) | 21.75 ± 1.36 |
| C: parameter sharing | 20.16 (ep75) | 20.11 (ep125) | 21.32 (ep150) | 19.82 (ep25) | 20.41 (ep100) | 20.36 ± 0.58 |
| C transf.: Casa do Ator fora do treino | 20.81 (ep50) | 21.11 (ep75) | 21.74 (ep50) | 21.86 (ep125) | 19.98 (ep125) | 21.10 ± 0.76 |
