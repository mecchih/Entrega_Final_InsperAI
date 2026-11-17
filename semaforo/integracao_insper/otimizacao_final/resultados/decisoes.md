# Registro de decisões (somente validação, sementes 221–225)

## 16/11 00:20 — após o lote 1 (A_col, A_col_v5)

Melhor checkpoint por semente do modelo (critério de `bateria_otimizacao.py`), espera média no corredor (s):

| braço | s1 | s2 | s3 | s4 | s5 | média ± dp |
|---|---|---|---|---|---|---|
| A_v1 (anterior) | 20.40 (ep25) | 22.15 (ep50) | 21.57 (ep100) | 21.92 (ep125) | 20.31 (ep150) | 21.27 ± 0.86 |
| A_col (verde 10, colisão atribuída) | 19.55 (ep75) | 19.78 (ep50) | 21.57 (ep100) | 20.55 (ep125) | 22.93 (ep50) | 20.88 ± 1.39 |
| A_col_v5 (verde 5, colisão atribuída) | 22.04 (ep150) | 21.19 (ep150) | 22.14 (ep100) | 21.17 (ep100) | 20.80 (ep150) | 21.46 ± 0.59 |

Baselines na validação: original 14.63; atuado equivalente v10 21.98; atuado equivalente v5 22.99; Max-Pressure (fila só faixa imediata, verde mín. 10) 55.99.

Comparação pareada contra A_v1:
- A_col − A_v1: −0.39 s, melhor em 3/5 sementes. Não atende à regra de melhoria (média melhor E pelo menos 4/5 sementes).
- A_col_v5 − A_v1: +0.20 s, melhor em 2/5 sementes. Pior.

Decisão: os braços hierárquicos usam a configuração local L10 + colisão atribuída.
- O verde mínimo de 5 s não melhorou o A nem o baseline clássico equivalente (22.99 contra 21.98).
- A colisão atribuída é mantida porque corrige um erro de atribuição de recompensa, e não porque demonstrou ganho estatístico.

Lote 2: B_col_s30 contra B_col_s15, 5 sementes × 150 episódios. O supervisor de 10 s só será treinado se o de 15 s superar o de 30 s na validação.

## 16/11 02:10 — após o lote 2 (B_col_s30, B_col_s15)

| braço | s1 | s2 | s3 | s4 | s5 | média ± dp |
|---|---|---|---|---|---|---|
| B_v1 (anterior, sup 30, colisão global) | 20.07 (ep150) | 22.43 (ep100) | 24.07 (ep150) | 20.80 (ep125) | 21.74 (ep100) | 21.82 ± 1.54 |
| B_col_s30 | 23.24 (ep100) | 21.97 (ep125) | 21.68 (ep125) | 21.38 (ep150) | 22.15 (ep75) | 22.08 ± 0.71 |
| B_col_s15 | 20.61 (ep150) | 21.13 (ep125) | 21.49 (ep125) | 21.43 (ep125) | 24.10 (ep50) | 21.75 ± 1.36 |

Comparações pareadas:
- B_col_s15 − B_col_s30: −0.33 s, melhor em 3/5 sementes. Não é melhora pela regra.
- B_col_s30 − B_v1: +0.26 s (2/5 sementes). B_col_s15 − B_v1: −0.07 s (2/5 sementes).
- B_col_s30 − A_col: +1.21 s (1/5 sementes). B_col_s15 − A_col: +0.88 s (1/5 sementes). O supervisor continua sem ganho sobre os agentes independentes.

Decisão: o supervisor de 10 s NÃO será treinado.
- O supervisor de 15 s não superou o de 30 s pelo critério combinado (diferença dentro do ruído, 3/5 sementes).
- Pela instrução de não prolongar experimentos sem evidência de melhoria, não há justificativa para testar 10 s.

Melhor configuração na validação: A_col (20.88 s). Teste final único (sementes 241–250) com A_v1, B_v1, A_col, A_col_v5, B_col_s30, B_col_s15 e os 4 baselines.
