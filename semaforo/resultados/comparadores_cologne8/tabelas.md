## Teste final (sementes de trafego 1 a 10)

| Controlador | Simulacoes | Espera media (s) | P95 (s) | Fila media | Colisoes/sim | Nao concluidas | Intervencoes/sim |
|---|---:|---:|---:|---:|---:|---:|---:|
| MARL com supervisor (nosso) | 100 | 9.29 ± 0.68 | 35.4 | 4.94 | 18.5 | 0 | 48.0 |
| Semáforo atuado (calibrado) | 10 | 11.98 ± 1.51 | 51.5 | 6.39 | 16.6 | 0 | 38.6 |
| Max-Pressure por movimento (ajustado) | 10 | 14.45 ± 0.95 | 45.5 | 7.69 | 18.9 | 0 | 43.1 |
| Max-Pressure por faixa (já existente) | 10 | 15.83 ± 1.74 | 50.9 | 8.42 | 18.2 | 0 | 39.9 |
| Rede neural supervisionada (imita o atuado) | 30 | 16.60 ± 1.91 | 77.3 | 8.84 | 21.4 | 0 | 49.3 |
| Q-learning tabular | 30 | 28.80 ± 13.23 | 119.8 | 15.12 | 20.3 | 36 | 114.5 |
| Programa original (transições nativas) | 10 | 30.52 ± 0.58 | 87.5 | 16.01 | 23.6 | 0 | 0.0 |
| Tempo fixo Webster (no executor) | 10 | 43.32 ± 0.61 | 133.5 | 22.71 | 30.2 | 0 | 0.0 |
| Plano original no executor | 10 | 47.03 ± 0.76 | 139.7 | 24.85 | 29.1 | 0 | 0.0 |

Medias por simulacao; ± = desvio padrao entre simulacoes. MARL: 10 modelos x 10 sementes; grupos aprendidos: 3 modelos x 10 sementes; classicos: 10 sementes.

## Comparacao pareada por semente de trafego

Para cada semente, media dos modelos de cada grupo. Negativo = MARL menor (melhor).

| Comparador | Espera: MARL - comparador | Variacao | MARL melhor em | P95: MARL - comparador | Colisoes: MARL - comparador |
|---|---:|---:|---:|---:|---:|
| Semáforo atuado (calibrado) | -2.69 s | -22.4% | 10/10 sementes | -16.1 s | +1.9 |
| Max-Pressure por movimento (ajustado) | -5.16 s | -35.7% | 10/10 sementes | -10.1 s | -0.4 |
| Max-Pressure por faixa (já existente) | -6.54 s | -41.3% | 10/10 sementes | -15.4 s | +0.3 |
| Rede neural supervisionada (imita o atuado) | -7.31 s | -44.0% | 10/10 sementes | -41.9 s | -2.9 |
| Q-learning tabular | -19.51 s | -67.7% | 10/10 sementes | -84.4 s | -1.9 |
| Programa original (transições nativas) | -21.23 s | -69.6% | 10/10 sementes | -52.1 s | -5.1 |
| Tempo fixo Webster (no executor) | -34.02 s | -78.6% | 10/10 sementes | -98.1 s | -11.7 |
| Plano original no executor | -37.74 s | -80.2% | 10/10 sementes | -104.2 s | -10.6 |

## Variacao entre modelos treinados

| Grupo | Semente do modelo | Espera media (s) | P95 (s) | Colisoes/sim |
|---|---:|---:|---:|---:|
| Rede neural supervisionada (imita o atuado) | 0 | 17.68 | 83.1 | 20.5 |
| Rede neural supervisionada (imita o atuado) | 1 | 16.26 | 76.5 | 22.2 |
| Rede neural supervisionada (imita o atuado) | 2 | 15.85 | 72.3 | 21.5 |
| Q-learning tabular | 0 | 28.08 | 111.2 | 17.3 |
| Q-learning tabular | 1 | 33.70 | 131.6 | 23.3 |
| Q-learning tabular | 2 | 24.64 | 116.5 | 20.4 |
