# Zero-shot C3 → C5 (intensa, sementes novas 291-300; pesos congelados)

RL: média dos 5 checkpoints do Modelo C ± dp entre checkpoints (cada um = média das 10 demandas). Baselines: ± dp entre demandas. Só episódios válidos entram nas médias.

| Métrica | Original (14 no programa) | C3: Modelo C nos 3 | C3→C5: mesmo checkpoint nos 5 | Atuado c/ regras RL nos 3 | Atuado c/ regras RL nos 5 |
|---|---:|---:|---:|---:|---:|
| Espera média no corredor original (s/veículo) | 15.06 ± 2.34 | 20.34 ± 1.06 | 20.59 ± 1.17 | 23.03 ± 3.15 | 21.72 ± 4.24 |
| Espera média na rede inteira (s/viagem) | 40.93 ± 2.23 | 45.60 ± 1.15 | 45.95 ± 1.12 | 47.58 ± 3.20 | 46.76 ± 4.73 |
| P95 da espera no corredor (s) | 50.49 ± 9.18 | 56.63 ± 4.39 | 57.41 ± 3.10 | 67.48 ± 10.19 | 62.59 ± 12.57 |
| P95 da espera na rede (s) | 120.36 ± 5.19 | 123.42 ± 2.64 | 123.13 ± 2.81 | 127.61 ± 7.77 | 126.46 ± 11.42 |
| Espera nos 2 cruzamentos novos (s/veículo) | 1.52 ± 0.14 | 1.61 ± 0.07 | 2.18 ± 0.37 | 1.55 ± 0.12 | 1.04 ± 0.23 |
| Espera em Gomes de Carvalho (s/veículo) | 5.64 ± 1.06 | 9.28 ± 0.61 | 9.51 ± 0.96 | 10.12 ± 1.84 | 10.06 ± 3.75 |
| Espera em Casa do Ator (s/veículo) | 4.97 ± 1.00 | 6.79 ± 0.36 | 6.83 ± 0.37 | 7.60 ± 1.09 | 7.47 ± 1.17 |
| Espera em Quatá (s/veículo) | 11.18 ± 1.82 | 13.88 ± 0.68 | 14.00 ± 0.69 | 16.05 ± 2.58 | 14.48 ± 2.26 |
| Espera em Fiandeiras × Clodomiro (novo) (s/veículo) | 1.58 ± 0.17 | 1.70 ± 0.08 | 2.00 ± 0.21 | 1.60 ± 0.14 | 1.08 ± 0.32 |
| Espera em Fiandeiras × Atílio Innocenti (novo) (s/veículo) | 1.16 ± 0.20 | 1.15 ± 0.05 | 3.12 ± 1.32 | 1.23 ± 0.26 | 0.81 ± 0.50 |
| Fila média em Gomes de Carvalho | 1.58 ± 0.31 | 2.60 ± 0.17 | 2.66 ± 0.28 | 2.81 ± 0.51 | 2.82 ± 1.07 |
| Fila média em Casa do Ator | 1.77 ± 0.38 | 2.42 ± 0.13 | 2.43 ± 0.13 | 2.68 ± 0.40 | 2.66 ± 0.46 |
| Fila média em Quatá | 4.50 ± 0.75 | 5.61 ± 0.28 | 5.65 ± 0.28 | 6.44 ± 1.05 | 5.85 ± 0.94 |
| Fila média em Fiandeiras × Clodomiro (novo) | 0.16 ± 0.02 | 0.17 ± 0.01 | 0.20 ± 0.02 | 0.16 ± 0.02 | 0.11 ± 0.03 |
| Fila média em Fiandeiras × Atílio Innocenti (novo) | 0.02 ± 0.00 | 0.02 ± 0.00 | 0.06 ± 0.02 | 0.02 ± 0.01 | 0.01 ± 0.01 |
| Veículos que passaram por Gomes de Carvalho (por episódio) | 1003.20 ± 22.02 | 1003.19 ± 0.48 | 1003.19 ± 0.48 | 1003.40 ± 22.21 | 1003.40 ± 22.21 |
| Veículos que passaram por Casa do Ator (por episódio) | 1275.00 ± 20.25 | 1275.38 ± 0.84 | 1275.38 ± 0.84 | 1275.00 ± 20.25 | 1275.00 ± 20.25 |
| Veículos que passaram por Quatá (por episódio) | 1435.90 ± 13.54 | 1435.39 ± 1.60 | 1435.93 ± 1.37 | 1435.00 ± 15.25 | 1436.00 ± 14.35 |
| Veículos que passaram por Fiandeiras × Clodomiro (novo) (por episódio) | 363.30 ± 19.25 | 363.17 ± 0.28 | 363.28 ± 0.28 | 363.30 ± 19.25 | 363.40 ± 19.38 |
| Veículos que passaram por Fiandeiras × Atílio Innocenti (novo) (por episódio) | 65.20 ± 6.20 | 65.14 ± 0.14 | 65.14 ± 0.14 | 65.20 ± 6.20 | 65.20 ± 6.20 |
| Viagens concluídas (mín.) | 1.000 | 0.551 | 0.626 | 1.000 | 1.000 |
| Colisões totais | 0 | 3 | 1 | 0 | 0 |
| Colisões nos 5 cruzamentos | 0 | 0 | 0 | 0 | 0 |
| Colisões nos controlados | 0 | 0 | 0 | 0 | 0 |
| Teletransportes | 0 | 5 | 3 | 0 | 0 |
| Episódios travados/inválidos | 0/10 | 1/50 | 1/50 | 0/10 | 0/10 |
| Violações de segurança | 0 | 0 | 0 | 0 | 0 |
| Semáforos não controlados fora do programa | 0 | 0 | 0 | 0 | 0 |

## Comparações pareadas por demanda (10 demandas; Δ = segundo − primeiro)

| Métrica | C5 − C3 | IC95 | demandas em que C5 melhora | C5 − original | IC95 | C3 − original | IC95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Espera média no corredor original (s/veículo) | +0.33 | ±1.26 | 4/10 | +5.61 | ±1.86 | +5.27 | ±1.51 |
| Espera média na rede inteira (s/viagem) | +0.41 | ±1.14 | 5/10 | +5.06 | ±1.79 | +4.65 | ±1.38 |
| P95 da espera no corredor (s) | +1.10 | ±5.05 | 4/10 | +7.16 | ±7.17 | +6.06 | ±5.96 |
| Espera nos 2 cruzamentos novos (s/veículo) | +0.55 | ±0.16 | 0/10 | +0.65 | ±0.14 | +0.10 | ±0.11 |
| Espera em 476455095 (s/veículo) | +0.28 | ±0.63 | 4/10 | +3.92 | ±0.82 | +3.65 | ±0.81 |
| Espera em 40278305 (s/veículo) | +0.06 | ±0.42 | 4/10 | +1.87 | ±0.58 | +1.81 | ±0.51 |
| Espera em 40278183 (s/veículo) | +0.18 | ±0.91 | 6/10 | +2.86 | ±1.46 | +2.69 | ±1.17 |
| Espera em 300058973 (s/veículo) | +0.29 | ±0.17 | 1/10 | +0.42 | ±0.15 | +0.12 | ±0.15 |
| Espera em 302806060 (s/veículo) | +1.96 | ±0.59 | 0/10 | +1.95 | ±0.55 | -0.01 | ±0.17 |

## Consistência entre os 5 checkpoints (C5 − C3 no mesmo checkpoint, média das 10 demandas)

| Checkpoint | corredor | rede | novos | Fiandeiras×Clodomiro | Fiandeiras×Atílio |
|---|---:|---:|---:|---:|---:|
| C s1 | -0.89 | -0.87 | +1.09 | +0.70 | +3.23 |
| C s2 | +0.43 | +0.59 | +0.07 | +0.03 | +0.30 |
| C s3 | +1.64 | +1.74 | +0.18 | +0.05 | +0.82 |
| C s4 | -0.91 | -0.30 | +0.66 | +0.32 | +2.53 |
| C s5 | +0.99 | +0.59 | +0.81 | +0.42 | +2.96 |
