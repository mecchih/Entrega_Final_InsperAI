# C5 treinado (C5-A) — testes finais com pesos congelados

## Seleção na validação (sementes 221-225)

| Semente | checkpoint | elegível | espera nos 5 (s/veíc.) | corredor | rede |
|---|---:|---|---:|---:|---:|
| C5 s1 | ep150 | True | 9.06 | 19.74 | 45.52 |
| C5 s2 | ep75 | True | 9.50 | 20.57 | 46.02 |
| C5 s3 | ep25 | True | 9.69 | 21.02 | 45.77 |
| C5 s4 | ep75 | True | 9.35 | 20.41 | 45.36 |
| C5 s5 | ep150 | True | 9.50 | 20.51 | 45.17 |
| original | — | — | 6.71 | 14.63 | 40.23 |
| atuado5 | — | — | 10.63 | 23.42 | 47.93 |

## Demanda intensa (2000 veíc/h no corredor), sementes 331-340

RL: média de 5 modelos ± dp entre modelos; baselines: ± dp entre 10 demandas. Só episódios válidos entram nas médias; os inválidos estão contados abaixo.

| Métrica | Original (14 no programa) | Atuado c/ regras RL nos 3 | C3 (nos 3) | C3→C5 sem retreino | Atuado c/ regras RL nos 5 | C5 treinado (5 agentes) |
|---|---:|---:|---:|---:|---:|---:|
| Espera média na Ribeirão Claro (s/veículo) | 14.72 ± 2.70 | 22.21 ± 1.99 | 19.83 ± 0.75 | 21.15 ± 0.60 | 21.10 ± 1.50 | 20.73 ± 0.99 |
| Espera nos 2 cruzamentos novos (s/veículo) | 1.53 ± 0.17 | 1.60 ± 0.20 | 1.56 ± 0.05 | 2.20 ± 0.31 | 1.14 ± 0.33 | 2.18 ± 0.34 |
| Espera nos 5 cruzamentos (s/veículo) | 6.80 ± 1.21 | 10.20 ± 0.91 | 9.12 ± 0.34 | 9.79 ± 0.28 | 9.65 ± 0.70 | 9.60 ± 0.47 |
| Espera média na rede inteira (s/viagem) | 40.62 ± 2.79 | 47.55 ± 2.46 | 45.67 ± 0.71 | 47.01 ± 0.70 | 46.26 ± 2.32 | 46.63 ± 0.89 |
| P95 da espera no corredor (s) | 49.06 ± 9.25 | 66.19 ± 6.13 | 55.16 ± 2.98 | 60.26 ± 2.27 | 61.62 ± 4.33 | 58.68 ± 3.10 |
| P95 da espera na rede (s) | 118.72 ± 6.24 | 129.22 ± 6.35 | 123.59 ± 1.03 | 126.59 ± 1.82 | 125.40 ± 6.02 | 126.00 ± 2.07 |
| Espera em Gomes de Carvalho (s/veículo) | 5.55 ± 1.92 | 9.69 ± 1.88 | 8.80 ± 0.36 | 9.37 ± 0.67 | 9.53 ± 1.19 | 9.45 ± 0.57 |
| Espera em Casa do Ator (s/veículo) | 4.86 ± 1.16 | 7.68 ± 0.89 | 6.84 ± 0.32 | 7.24 ± 0.36 | 7.49 ± 0.58 | 7.27 ± 0.55 |
| Espera em Quatá (s/veículo) | 10.98 ± 1.56 | 15.38 ± 1.97 | 13.63 ± 0.62 | 14.60 ± 0.24 | 14.22 ± 1.46 | 13.99 ± 0.62 |
| Espera em Fiandeiras × Clodomiro (s/veículo) | 1.60 ± 0.20 | 1.66 ± 0.23 | 1.64 ± 0.06 | 2.07 ± 0.21 | 1.20 ± 0.40 | 1.95 ± 0.32 |
| Espera em Fiandeiras × Atílio Innocenti (s/veículo) | 1.14 ± 0.17 | 1.26 ± 0.21 | 1.16 ± 0.04 | 2.83 ± 0.90 | 0.75 ± 0.34 | 3.37 ± 0.65 |
| Fila média em Gomes de Carvalho | 1.55 ± 0.55 | 2.68 ± 0.52 | 2.45 ± 0.10 | 2.59 ± 0.18 | 2.65 ± 0.33 | 2.63 ± 0.16 |
| Fila média em Casa do Ator | 1.73 ± 0.41 | 2.72 ± 0.30 | 2.43 ± 0.11 | 2.57 ± 0.13 | 2.65 ± 0.17 | 2.58 ± 0.19 |
| Fila média em Quatá | 4.41 ± 0.64 | 6.19 ± 0.84 | 5.48 ± 0.24 | 5.85 ± 0.10 | 5.71 ± 0.58 | 5.61 ± 0.25 |
| Fila média em Fiandeiras × Clodomiro | 0.16 ± 0.02 | 0.17 ± 0.03 | 0.17 ± 0.01 | 0.21 ± 0.02 | 0.12 ± 0.04 | 0.20 ± 0.03 |
| Fila média em Fiandeiras × Atílio Innocenti | 0.02 ± 0.00 | 0.02 ± 0.00 | 0.02 ± 0.00 | 0.06 ± 0.02 | 0.01 ± 0.01 | 0.07 ± 0.01 |
| Trocas de fase/episódio em Fiandeiras × Clodomiro | — | — | — | 130.10 ± 9.54 | 51.00 ± 9.26 | 118.26 ± 35.86 |
| Trocas de fase/episódio em Fiandeiras × Atílio Innocenti | — | — | — | 60.06 ± 13.49 | 39.50 ± 10.15 | 97.24 ± 38.46 |
| Viagens concluídas (mín.) | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Colisões totais (nos 5 cruzamentos) | 0 (0) | 0 (0) | 1 (0) | 0 (0) | 0 (0) | 0 (0) |
| Teletransportes | 0 | 0 | 0 | 0 | 0 | 0 |
| Episódios travados | 0/10 | 0/10 | 0/50 | 0/50 | 0/10 | 0/50 |
| Violações de segurança | 0 | 0 | 0 | 0 | 0 | 0 |
| Semáforos não controlados fora do programa | 0 | 0 | 0 | 0 | 0 | 0 |

Comparações pareadas por demanda (média dos 5 modelos em cada demanda; Δ = C5 − referência):

| Métrica | C5 − C3→C5 | IC95 | melhora em | C5 − C3 | IC95 | C5 − original | IC95 | C5 − atuado5 | IC95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Espera média na Ribeirão Claro (s/veículo) | -0.42 | ±0.53 | 7/10 | +0.91 | ±0.72 | +6.02 | ±2.22 | -0.37 | ±1.57 |
| Espera nos 2 cruzamentos novos (s/veículo) | -0.02 | ±0.10 | 6/10 | +0.62 | ±0.26 | +0.65 | ±0.28 | +1.04 | ±0.21 |
| Espera nos 5 cruzamentos (s/veículo) | -0.19 | ±0.24 | 7/10 | +0.48 | ±0.32 | +2.79 | ±1.00 | -0.05 | ±0.70 |
| Espera média na rede inteira (s/viagem) | -0.38 | ±0.38 | 7/10 | +0.96 | ±0.69 | +6.01 | ±1.82 | +0.37 | ±1.55 |
| P95 da espera no corredor (s) | -1.58 | ±1.91 | 7/10 | +3.52 | ±2.53 | +9.62 | ±7.65 | -2.94 | ±5.66 |
| Espera em Gomes de Carvalho (s/veículo) | +0.09 | ±0.35 | 3/10 | +0.65 | ±0.59 | +3.90 | ±1.54 | -0.08 | ±0.86 |
| Espera em Casa do Ator (s/veículo) | +0.02 | ±0.28 | 5/10 | +0.43 | ±0.21 | +2.41 | ±0.96 | -0.22 | ±0.47 |
| Espera em Quatá (s/veículo) | -0.62 | ±0.38 | 9/10 | +0.35 | ±0.51 | +3.01 | ±1.10 | -0.24 | ±1.38 |
| Espera em Fiandeiras × Clodomiro (s/veículo) | -0.12 | ±0.09 | 9/10 | +0.30 | ±0.23 | +0.34 | ±0.23 | +0.74 | ±0.19 |
| Espera em Fiandeiras × Atílio Innocenti (s/veículo) | +0.54 | ±0.34 | 1/10 | +2.21 | ±0.67 | +2.23 | ±0.76 | +2.62 | ±0.57 |
| Trocas de fase/episódio em Fiandeiras × Clodomiro | -11.84 | ±4.69 | 10/10 | — | — | — | — | +67.26 | ±4.82 |
| Trocas de fase/episódio em Fiandeiras × Atílio Innocenti | +37.18 | ±4.40 | 0/10 | — | — | — | — | +57.74 | ±6.60 |

Consistência entre sementes de modelo (média das 10 demandas por modelo):

| Métrica | C5 s1 | C5 s2 | C5 s3 | C5 s4 | C5 s5 | C3→C5 s1 | C3→C5 s2 | C3→C5 s3 | C3→C5 s4 | C3→C5 s5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Espera média na Ribeirão Claro (s/veículo) | 20.15 | 22.27 | 20.57 | 19.69 | 20.99 | 21.65 | 21.19 | 21.79 | 20.37 | 20.75 |
| Espera nos 2 cruzamentos novos (s/veículo) | 1.91 | 2.37 | 2.14 | 1.84 | 2.66 | 2.68 | 1.86 | 1.99 | 2.20 | 2.28 |
| Espera média na rede inteira (s/viagem) | 46.20 | 47.85 | 46.59 | 45.47 | 47.04 | 47.44 | 46.73 | 47.86 | 46.02 | 47.01 |
| Trocas de fase/episódio em Fiandeiras × Clodomiro | 101.80 | 132.20 | 69.50 | 121.70 | 166.10 | 127.20 | 138.30 | 136.60 | 114.80 | 133.60 |
| Trocas de fase/episódio em Fiandeiras × Atílio Innocenti | 150.10 | 54.30 | 66.00 | 114.10 | 101.70 | 51.10 | 83.70 | 58.10 | 52.30 | 55.10 |

## Demanda moderada (1200 veíc/h), sementes 341-350

RL: média de 5 modelos ± dp entre modelos; baselines: ± dp entre 10 demandas. Só episódios válidos entram nas médias; os inválidos estão contados abaixo.

| Métrica | Original (14 no programa) | Atuado c/ regras RL nos 3 | C3 (nos 3) | C3→C5 sem retreino | Atuado c/ regras RL nos 5 | C5 treinado (5 agentes) |
|---|---:|---:|---:|---:|---:|---:|
| Espera média na Ribeirão Claro (s/veículo) | 5.37 ± 0.37 | 9.92 ± 0.36 | 10.84 ± 0.30 | 10.81 ± 0.27 | 9.84 ± 0.45 | 10.96 ± 0.65 |
| Espera nos 2 cruzamentos novos (s/veículo) | 1.28 ± 0.22 | 1.39 ± 0.10 | 1.33 ± 0.07 | 2.64 ± 0.79 | 0.95 ± 0.12 | 2.33 ± 0.64 |
| Espera nos 5 cruzamentos (s/veículo) | 2.54 ± 0.16 | 4.58 ± 0.16 | 4.98 ± 0.14 | 5.11 ± 0.18 | 4.50 ± 0.16 | 5.15 ± 0.34 |
| Espera média na rede inteira (s/viagem) | 29.59 ± 0.81 | 33.61 ± 1.09 | 34.30 ± 0.28 | 34.43 ± 0.36 | 33.21 ± 0.81 | 34.60 ± 0.61 |
| P95 da espera no corredor (s) | 17.55 ± 1.61 | 29.20 ± 1.55 | 34.21 ± 2.06 | 34.18 ± 1.77 | 29.61 ± 1.44 | 35.13 ± 3.16 |
| P95 da espera na rede (s) | 94.87 ± 2.74 | 100.35 ± 2.75 | 100.67 ± 0.50 | 101.15 ± 1.00 | 99.04 ± 1.71 | 101.82 ± 1.02 |
| Espera em Gomes de Carvalho (s/veículo) | 2.44 ± 0.14 | 4.69 ± 0.29 | 5.42 ± 0.43 | 5.45 ± 0.41 | 4.56 ± 0.31 | 5.35 ± 0.37 |
| Espera em Casa do Ator (s/veículo) | 2.11 ± 0.16 | 4.06 ± 0.18 | 4.33 ± 0.20 | 4.33 ± 0.16 | 4.12 ± 0.21 | 4.43 ± 0.27 |
| Espera em Quatá (s/veículo) | 3.41 ± 0.44 | 6.05 ± 0.53 | 6.48 ± 0.21 | 6.41 ± 0.30 | 5.98 ± 0.44 | 6.61 ± 0.58 |
| Espera em Fiandeiras × Clodomiro (s/veículo) | 1.32 ± 0.25 | 1.45 ± 0.12 | 1.39 ± 0.07 | 2.62 ± 0.74 | 1.07 ± 0.12 | 2.21 ± 0.60 |
| Espera em Fiandeiras × Atílio Innocenti (s/veículo) | 1.10 ± 0.23 | 1.11 ± 0.21 | 1.02 ± 0.11 | 2.70 ± 1.14 | 0.38 ± 0.31 | 2.85 ± 0.94 |
| Fila média em Gomes de Carvalho | 0.41 ± 0.03 | 0.79 ± 0.06 | 0.92 ± 0.07 | 0.92 ± 0.07 | 0.77 ± 0.05 | 0.90 ± 0.06 |
| Fila média em Casa do Ator | 0.45 ± 0.04 | 0.88 ± 0.05 | 0.93 ± 0.05 | 0.93 ± 0.03 | 0.89 ± 0.05 | 0.95 ± 0.06 |
| Fila média em Quatá | 0.81 ± 0.12 | 1.45 ± 0.13 | 1.54 ± 0.05 | 1.53 ± 0.07 | 1.42 ± 0.12 | 1.57 ± 0.14 |
| Fila média em Fiandeiras × Clodomiro | 0.09 ± 0.02 | 0.10 ± 0.01 | 0.09 ± 0.00 | 0.17 ± 0.05 | 0.07 ± 0.01 | 0.15 ± 0.04 |
| Fila média em Fiandeiras × Atílio Innocenti | 0.02 ± 0.00 | 0.02 ± 0.00 | 0.01 ± 0.00 | 0.04 ± 0.02 | 0.01 ± 0.00 | 0.04 ± 0.01 |
| Trocas de fase/episódio em Fiandeiras × Clodomiro | — | — | — | 130.12 ± 15.48 | 45.60 ± 4.90 | 125.86 ± 38.22 |
| Trocas de fase/episódio em Fiandeiras × Atílio Innocenti | — | — | — | 51.26 ± 14.52 | 27.00 ± 7.56 | 90.98 ± 36.98 |
| Viagens concluídas (mín.) | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Colisões totais (nos 5 cruzamentos) | 0 (0) | 0 (0) | 0 (0) | 0 (0) | 0 (0) | 0 (0) |
| Teletransportes | 0 | 0 | 0 | 0 | 0 | 0 |
| Episódios travados | 0/10 | 0/10 | 0/50 | 0/50 | 0/10 | 0/50 |
| Violações de segurança | 0 | 0 | 0 | 0 | 0 | 0 |
| Semáforos não controlados fora do programa | 0 | 0 | 0 | 0 | 0 | 0 |

Comparações pareadas por demanda (média dos 5 modelos em cada demanda; Δ = C5 − referência):

| Métrica | C5 − C3→C5 | IC95 | melhora em | C5 − C3 | IC95 | C5 − original | IC95 | C5 − atuado5 | IC95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Espera média na Ribeirão Claro (s/veículo) | +0.15 | ±0.23 | 2/10 | +0.12 | ±0.31 | +5.59 | ±0.18 | +1.12 | ±0.22 |
| Espera nos 2 cruzamentos novos (s/veículo) | -0.32 | ±0.14 | 10/10 | +0.99 | ±0.14 | +1.05 | ±0.27 | +1.38 | ±0.17 |
| Espera nos 5 cruzamentos (s/veículo) | +0.03 | ±0.11 | 4/10 | +0.17 | ±0.14 | +2.61 | ±0.11 | +0.65 | ±0.11 |
| Espera média na rede inteira (s/viagem) | +0.17 | ±0.30 | 2/10 | +0.30 | ±0.25 | +5.01 | ±0.41 | +1.39 | ±0.56 |
| P95 da espera no corredor (s) | +0.95 | ±0.49 | 1/10 | +0.91 | ±0.94 | +17.58 | ±0.87 | +5.52 | ±0.87 |
| Espera em Gomes de Carvalho (s/veículo) | -0.11 | ±0.16 | 9/10 | -0.07 | ±0.19 | +2.91 | ±0.13 | +0.79 | ±0.18 |
| Espera em Casa do Ator (s/veículo) | +0.10 | ±0.11 | 3/10 | +0.10 | ±0.11 | +2.32 | ±0.14 | +0.30 | ±0.14 |
| Espera em Quatá (s/veículo) | +0.20 | ±0.26 | 3/10 | +0.13 | ±0.28 | +3.20 | ±0.26 | +0.63 | ±0.29 |
| Espera em Fiandeiras × Clodomiro (s/veículo) | -0.41 | ±0.19 | 9/10 | +0.82 | ±0.20 | +0.89 | ±0.34 | +1.14 | ±0.18 |
| Espera em Fiandeiras × Atílio Innocenti (s/veículo) | +0.15 | ±0.48 | 4/10 | +1.82 | ±0.48 | +1.75 | ±0.57 | +2.47 | ±0.43 |
| Trocas de fase/episódio em Fiandeiras × Clodomiro | -4.26 | ±3.35 | 9/10 | — | — | — | — | +80.26 | ±3.58 |
| Trocas de fase/episódio em Fiandeiras × Atílio Innocenti | +39.72 | ±5.19 | 0/10 | — | — | — | — | +63.98 | ±5.83 |

Consistência entre sementes de modelo (média das 10 demandas por modelo):

| Métrica | C5 s1 | C5 s2 | C5 s3 | C5 s4 | C5 s5 | C3→C5 s1 | C3→C5 s2 | C3→C5 s3 | C3→C5 s4 | C3→C5 s5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Espera média na Ribeirão Claro (s/veículo) | 10.64 | 10.69 | 11.37 | 10.22 | 11.86 | 11.14 | 10.62 | 10.70 | 11.04 | 10.53 |
| Espera nos 2 cruzamentos novos (s/veículo) | 1.64 | 3.02 | 2.25 | 1.77 | 2.95 | 3.63 | 1.63 | 2.30 | 2.42 | 3.24 |
| Espera média na rede inteira (s/viagem) | 34.16 | 34.41 | 34.91 | 34.00 | 35.51 | 34.87 | 33.89 | 34.38 | 34.58 | 34.41 |
| Trocas de fase/episódio em Fiandeiras × Clodomiro | 120.10 | 129.00 | 67.40 | 140.30 | 172.50 | 120.40 | 149.40 | 142.20 | 111.80 | 126.80 |
| Trocas de fase/episódio em Fiandeiras × Atílio Innocenti | 134.70 | 45.60 | 61.20 | 114.40 | 99.00 | 44.40 | 77.10 | 47.00 | 42.80 | 45.00 |

