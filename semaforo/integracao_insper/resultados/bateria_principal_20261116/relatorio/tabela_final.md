# Teste final: sementes 231-235 (cenario intenso)

Modelos: média ± dp entre 5 sementes de treino (cada uma = média das 5 sementes de teste). Original e Max-Pressure: média ± dp entre as 5 sementes de teste. Só episódios válidos entram nas médias.

| Métrica | Original | Max-Pressure | Independente (A) | Hierárquico (B) |
|---|---:|---:|---:|---:|
| Espera média no corredor (s) | 17.77 ± 6.18 | 57.08 ± 6.04 | 22.71 ± 1.54 | 22.63 ± 0.60 |
| P95 corredor (s) | 60.27 ± 21.96 | 219.38 ± 51.63 | 61.43 ± 4.49 | 60.65 ± 1.89 |
| Espera média na rede (s) | 43.44 ± 6.10 | 102.06 ± 6.70 | 47.82 ± 1.41 | 47.60 ± 1.03 |
| P95 rede (s) | 125.25 ± 14.04 | 344.46 ± 55.30 | 127.89 ± 3.56 | 126.52 ± 1.96 |
| Fila média Gomes de Carvalho | 2.38 ± 1.48 | 13.49 ± 0.74 | 2.95 ± 0.37 | 2.99 ± 0.36 |
| Fila média Casa do Ator | 2.18 ± 0.69 | 4.99 ± 0.21 | 2.73 ± 0.12 | 2.67 ± 0.13 |
| Fila média Quatá | 4.82 ± 1.14 | 7.79 ± 2.37 | 6.22 ± 0.49 | 6.23 ± 0.32 |
| Fila máx. Gomes de Carvalho | 19.60 ± 6.69 | 31.20 ± 2.49 | 15.72 ± 2.55 | 15.64 ± 1.70 |
| Fila máx. Casa do Ator | 17.00 ± 2.35 | 17.20 ± 1.48 | 16.04 ± 1.47 | 15.16 ± 1.43 |
| Fila máx. Quatá | 24.00 ± 2.35 | 27.80 ± 6.50 | 24.96 ± 2.27 | 24.68 ± 1.24 |
| Viagens concluídas (%) | 100.00 ± 0.00 | 100.00 ± 0.00 | 100.00 ± 0.00 | 100.00 ± 0.00 |
| Bloqueio da saída (s) | 40.20 ± 11.78 | 64.80 ± 13.72 | 72.72 ± 9.00 | 73.60 ± 5.43 |
| Teletransportes (total) | 0 | 32 | 0 | 0 |
| Colisões (total) | 6 | 1 | 0 | 0 |
| Colisões nos controlados | 0 | 0 | 0 | 0 |
| Violações de segurança | 0 | 0 | 0 | 0 |
| Avaliações inválidas | 0/5 | 0/5 | 0/25 | 0/25 |

## Hierárquico − independente, pareado por semente de treino (espera no corredor, s)

- semente 1: A 22.65 | B 22.69 | B−A +0.04
- semente 2: A 24.91 | B 22.55 | B−A -2.36
- semente 3: A 21.88 | B 23.4 | B−A +1.52
- semente 4: A 20.81 | B 22.78 | B−A +1.96
- semente 5: A 23.27 | B 21.72 | B−A -1.55
