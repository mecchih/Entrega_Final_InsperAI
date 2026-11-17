# Diagnostico: veiculos nao atendidos e esperas por direcao

Dinamica C, sementes de teste. Toda rodada reproduzida deu metricas identicas a `comparacao_C/avaliacao.json`.

## 1. Veiculos nao atendidos

11 rodadas (de 550) com 13 veiculos nao atendidos. Em todas o escoamento foi cortado no limite de 1200 s.

| cenario | controlador | semente | carro preso (aprox.) | espera registrada (s) | ciclo final (verde, s de verde -> escolha) | maior verde no escoamento (s) | intervencoes |
|---|---|---|---|---|---|---|---|
| assimetrico | DQN C seed1 | 3 | O | 1180 | L 10->L ; L 15->L ; L 20->S ; S 10->L | 20 | 0 |
| assimetrico | DQN C seed1 | 6 | O | 1171 | L 20->S ; S 10->L ; L 10->L ; L 15->L | 20 | 0 |
| assimetrico | DQN C seed2 | 2 | N | 1183 | L 10->S ; S 10->L | 30 | 0 |
| assimetrico | DQN C seed2 | 4 | N | 1194 | L 10->S ; S 10->L | 15 | 0 |
| equilibrado | DQN C seed1 | 3 | O | 1183 | S 10->L ; L 10->L ; L 15->L ; L 20->S | 20 | 0 |
| equilibrado | DQN C seed1 | 6 | O | 1178 | S 10->L ; L 10->L ; L 15->L ; L 20->S | 20 | 0 |
| equilibrado | DQN C seed2 | 7 | N, O | 1195, 1179 | S 10->L ; L 10->S | 10 | 0 |
| equilibrado | DQN C seed2 | 8 | N | 1184 | S 10->L ; L 10->S | 10 | 0 |
| girado | DQN C seed2 | 2 | N | 1183 | S 10->L ; L 10->S | 45 | 0 |
| pico | DQN C seed1 | 1 | O | 1176 | L 15->L ; L 20->S ; S 10->L ; L 10->L | 20 | 0 |
| pico | DQN C seed2 | 5 | N, O | 1189, 1179 | L 10->S ; S 10->L | 10 | 0 |

Conferencia da contagem: n_carros_igual_entre_controladores_em_cada_cenario_semente = True, concluidos_mais_interrompidos_igual_n_carros = True, sem_atendimento_igual_interrompidos = True, rodadas_com_escoamento_cortado = 11

### Teste do carro sozinho (sem simulador)

Um carro parado sozinho numa aproximacao; verde em outra. Quantas das 12 combinacoes (verde, aproximacao do carro) a rede NUNCA atende (fica num ciclo entre fases vazias)?

| rede | presos com 1 carro | com 2 carros | com 3 carros | atendidos so pela regra de seguranca |
|---|---|---|---|---|
| DQN original | 0/12 | 0/12 | 0/12 | 14 |
| DQN seed1 | 0/12 | 0/12 | 0/12 | 7 |
| DQN seed2 | 0/12 | 0/12 | 0/12 | 14 |
| DQN C seed0 | 0/12 | 0/12 | 0/12 | 18 |
| DQN C seed1 | 3/12 | 0/12 | 0/12 | 0 |
| DQN C seed2 | 3/12 | 0/12 | 0/12 | 0 |

## 2. Esperas por direcao

### girado (secundarias: L, O; demanda N 750, L 180, S 750, O 180 veic/h)

| controlador | N: espera media / P95 (s) | L: espera media / P95 (s) | S: espera media / P95 (s) | O: espera media / P95 (s) | N: % verde / sem verde medio / max (s) | L: % verde / sem verde medio / max (s) | S: % verde / sem verde medio / max (s) | O: % verde / sem verde medio / max (s) |
|---|---|---|---|---|---|---|---|---|
| Webster | 32.5 / 67 | 28.5 / 63 | 41.0 / 83 | 28.6 / 62 | 33.3 / 60 / 60 | 16.7 / 70 / 70 | 33.3 / 60 / 60 | 16.7 / 70 / 70 |
| Max-Pressure teto (recal. C) | 22.9 / 59 | 72.1 / 177 | 23.5 / 60 | 76.4 / 189 | 36.4 / 59 / 125 | 14.8 / 175 / 395 | 35.0 / 60 / 125 | 13.8 / 187 / 365 |
| Max-Pressure | 20.0 / 50 | 59.4 / 150 | 20.8 / 51 | 64.8 / 161 | 36.2 / 50 / 105 | 14.8 / 146 / 280 | 35.3 / 50 / 105 | 13.7 / 158 / 380 |
| DQN original | 14.4 / 41 | 73.5 / 179 | 11.5 / 38 | 55.0 / 154 | 37.5 / 36 / 90 | 8.7 / 141 / 315 | 43.6 / 36 / 85 | 10.2 / 122 / 290 |
| DQN seed1 | 13.5 / 42 | 67.5 / 167 | 11.4 / 35 | 75.2 / 184 | 40.2 / 34 / 100 | 9.3 / 135 / 305 | 41.7 / 32 / 75 | 8.8 / 143 / 330 |
| DQN seed2 | 15.0 / 41 | 95.1 / 206 | 9.6 / 33 | 69.3 / 176 | 36.6 / 36 / 100 | 8.3 / 150 / 340 | 45.9 / 33 / 90 | 9.3 / 136 / 335 |
| DQN C seed0 | 14.6 / 44 | 70.2 / 175 | 10.2 / 34 | 84.0 / 207 | 38.2 / 39 / 95 | 9.3 / 135 / 340 | 43.9 / 34 / 75 | 8.6 / 151 / 400 |
| DQN C seed1 | 16.7 / 45 | 62.6 / 163 | 9.6 / 33 | 77.6 / 196 | 35.2 / 37 / 95 | 10.1 / 126 / 320 | 46.2 / 32 / 95 | 8.5 / 149 / 395 |
| DQN C seed2 | 10.5 / 35 | 82.7 / 195 | 12.8 / 39 | 101.3 / 232 | 44.3 / 33 / 100 | 8.5 / 152 / 385 | 39.0 / 35 / 90 | 8.1 / 167 / 450 |

Rodadas instrumentadas (girado, so carros que entraram na primeira hora; extremo = espera >= 120 s):

| controlador | carros extremos | % deles na secundaria | % que esperaram um unico vermelho longo | secundaria recebe verde apos (s, media / P95) | fila da secundaria nesse momento | fila nas principais nesse momento | % trocas p/ principal com secundaria esperando >= 90 s | verde medio secundaria / principal (s) |
|---|---|---|---|---|---|---|---|---|
| DQN original | 581 | 99.8 | 82.1 | 126 / 231 | 6.2 | 3.6 | 51.0 | 10.0 / 15.4 |
| DQN seed1 | 694 | 100.0 | 80.8 | 136 / 236 | 6.9 | 3.4 | 55.8 | 10.0 / 13.8 |
| DQN seed2 | 909 | 100.0 | 70.2 | 139 / 261 | 7.5 | 3.5 | 60.3 | 10.1 / 14.9 |
| DQN C seed0 | 793 | 99.6 | 75.4 | 136 / 256 | 7.1 | 3.2 | 56.0 | 10.2 / 16.0 |
| DQN C seed1 | 660 | 100.0 | 80.5 | 132 / 251 | 6.7 | 3.7 | 54.2 | 10.2 / 14.5 |
| DQN C seed2 | 1083 | 99.9 | 73.4 | 155 / 281 | 8.4 | 3.0 | 66.7 | 10.8 / 15.2 |
| Webster | 121 | 0.0 | 0.0 | 65 / 66 | 3.1 | 11.8 | 0.0 | 10.0 / 20.0 |
| Max-Pressure teto (recal. C) | 812 | 99.9 | 100.0 | 176 / 271 | 8.6 | 5.4 | 91.8 | 25.0 / 25.3 |

### assimetrico (secundarias: N, S; demanda N 180, L 750, S 180, O 750 veic/h)

| controlador | N: espera media / P95 (s) | L: espera media / P95 (s) | S: espera media / P95 (s) | O: espera media / P95 (s) | N: % verde / sem verde medio / max (s) | L: % verde / sem verde medio / max (s) | S: % verde / sem verde medio / max (s) | O: % verde / sem verde medio / max (s) |
|---|---|---|---|---|---|---|---|---|
| Webster | 28.8 / 63 | 32.3 / 68 | 29.3 / 63 | 37.2 / 76 | 16.7 / 70 / 70 | 33.3 / 60 / 60 | 16.7 / 70 / 70 | 33.3 / 60 / 60 |
| Max-Pressure teto (recal. C) | 47.4 / 125 | 18.2 / 43 | 51.1 / 130 | 19.6 / 46 | 15.5 / 119 / 305 | 35.6 / 41 / 85 | 14.3 / 124 / 265 | 34.6 / 42 / 85 |
| Max-Pressure | 59.2 / 140 | 20.3 / 51 | 60.5 / 149 | 21.2 / 52 | 15.9 / 142 / 280 | 35.0 / 51 / 105 | 14.5 / 149 / 405 | 34.6 / 52 / 105 |
| DQN original | 62.3 / 151 | 17.4 / 44 | 56.4 / 142 | 10.4 / 32 | 10.1 / 134 / 340 | 35.6 / 33 / 80 | 10.8 / 122 / 345 | 43.4 / 29 / 75 |
| DQN seed1 | 50.8 / 132 | 13.6 / 36 | 50.5 / 131 | 13.5 / 39 | 11.6 / 116 / 305 | 37.5 / 31 / 75 | 11.3 / 117 / 305 | 39.6 / 32 / 90 |
| DQN seed2 | 58.8 / 149 | 14.6 / 42 | 51.9 / 144 | 12.3 / 38 | 10.5 / 128 / 290 | 37.4 / 33 / 80 | 11.0 / 119 / 355 | 41.1 / 32 / 115 |
| DQN C seed0 | 51.4 / 135 | 13.5 / 40 | 50.1 / 130 | 14.5 / 42 | 10.9 / 118 / 280 | 38.8 / 35 / 100 | 11.3 / 111 / 310 | 39.1 / 39 / 95 |
| DQN C seed1 | 71.0 / 177 | 10.9 / 34 | 49.6 / 131 | 16.5 / 46 | 9.1 / 144 / 340 | 42.8 / 32 / 90 | 11.3 / 113 / 340 | 36.7 / 38 / 100 |
| DQN C seed2 | 47.6 / 123 | 13.6 / 41 | 44.0 / 118 | 16.8 / 47 | 12.0 / 109 / 280 | 40.1 / 36 / 80 | 12.0 / 104 / 305 | 35.9 / 42 / 90 |

Rodadas instrumentadas (assimetrico, so carros que entraram na primeira hora; extremo = espera >= 120 s):

| controlador | carros extremos | % deles na secundaria | % que esperaram um unico vermelho longo | secundaria recebe verde apos (s, media / P95) | fila da secundaria nesse momento | fila nas principais nesse momento | % trocas p/ principal com secundaria esperando >= 90 s | verde medio secundaria / principal (s) |
|---|---|---|---|---|---|---|---|---|
| DQN original | 405 | 100.0 | 86.9 | 123 / 211 | 5.9 | 3.4 | 50.3 | 10.0 / 11.9 |
| DQN seed1 | 281 | 99.6 | 92.9 | 112 / 196 | 5.2 | 3.2 | 44.7 | 10.1 / 11.7 |
| DQN seed2 | 361 | 99.7 | 91.7 | 119 / 211 | 5.7 | 3.5 | 48.0 | 10.1 / 12.6 |
| DQN C seed0 | 277 | 100.0 | 92.8 | 110 / 201 | 5.2 | 3.9 | 44.0 | 10.1 / 14.9 |
| DQN C seed1 | 494 | 99.6 | 86.8 | 122 / 226 | 5.8 | 3.4 | 51.4 | 10.1 / 13.9 |
| DQN C seed2 | 190 | 100.0 | 95.8 | 102 / 186 | 4.8 | 4.2 | 33.1 | 10.2 / 14.9 |
| Webster | 183 | 0.0 | 0.0 | 66 / 66 | 3.1 | 11.2 | 0.0 | 10.0 / 20.0 |
| Max-Pressure teto (recal. C) | 239 | 100.0 | 98.7 | 117 / 201 | 5.7 | 3.7 | 42.1 | 15.2 / 15.0 |

