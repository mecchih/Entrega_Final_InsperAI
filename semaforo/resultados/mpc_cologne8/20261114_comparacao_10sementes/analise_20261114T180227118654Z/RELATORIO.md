# Resultados do MPC sem RL no Cologne8

O MPC externo adaptado foi executado com parametros congelados nas dez sementes 1 a 10. Esta e uma comparacao exploratoria de controladores completos, com diferencas de observacao e politica. Nao e reproducao exata do manuscrito externo nem evidencia de superioridade sobre MPC em geral.

| Media por simulacao | MARL | Max-Pressure | Original | MPC adaptado |
|---|---:|---:|---:|---:|
| Espera (s) | 9.29 | 15.83 | 30.52 | 38.65 |
| Media dos P95 (s) | 35.43 | 50.85 | 87.55 | 109.12 |
| Fila media | 4.94 | 8.42 | 16.01 | 20.21 |
| Colisoes | 18.46 | 18.20 | 23.60 | 29.50 |
| Viagens concluidas | 2046.00 | 2046.00 | 2046.00 | 2046.00 |
| Viagens nao concluidas | 0.00 | 0.00 | 0.00 | 0.00 |
| Teleportes | 0.00 | 0.00 | 0.00 | 0.00 |

Nos mesmos testes, a espera do MARL foi 75.96% menor que a deste MPC. O MPC teve espera 26.66% maior que o programa original. Assim, a configuracao testada nao se mostrou uma referencia forte de eficiencia. Nao ajustar seus parametros nestas sementes e reapresentar o mesmo teste como independente.

## Resultados por semente

| Seed | Espera (s) | P95 (s) | Fila | Colisoes | Concluidas | Nao concluidas |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 38.86 | 107.00 | 20.28 | 20 | 2046 | 0 |
| 2 | 38.86 | 108.00 | 20.50 | 23 | 2046 | 0 |
| 3 | 38.54 | 107.00 | 19.99 | 37 | 2046 | 0 |
| 4 | 37.97 | 109.00 | 19.78 | 31 | 2046 | 0 |
| 5 | 38.14 | 109.00 | 20.08 | 29 | 2046 | 0 |
| 6 | 40.07 | 114.00 | 20.93 | 42 | 2046 | 0 |
| 7 | 38.34 | 108.75 | 20.24 | 22 | 2046 | 0 |
| 8 | 38.61 | 109.00 | 19.94 | 29 | 2046 | 0 |
| 9 | 39.03 | 110.75 | 20.36 | 39 | 2046 | 0 |
| 10 | 38.12 | 108.75 | 19.95 | 23 | 2046 | 0 |

## Verificacoes e custo computacional

Os testes completos tiveram 331 QPs validos. Construcao e solucao: media 0.559s, P95 0.727s, maximo 1.122s por atualizacao global. Incluem verificacao numerica do solver, nao a simulacao inteira. Nao medimos comunicacao de rede nem operacao em tempo real.

O ciclo configurado e de 120s; os ciclos fisicos medidos entre retornos a fase zero tiveram minimo 120s e maximo 120s. Nesta rodada coincidiram com o ciclo planejado. O adaptador aplica alvos por idade de verde e preserva relogios locais; outras inicializacoes ou offsets precisam ser auditados novamente, sem presumir essa coincidencia.

Colisoes permanecem relevantes mesmo com transicoes legais. A funcao objetivo deste MPC e de eficiencia; nao aprende a penalidade de -10000 e nao modela conflitos microscopicos ou acidentes. A contagem segue o mesmo protocolo historico, com collision.action=warn.

## Incerteza e limites

Bootstrap cruzado de 10 mil replicas (seed 74291), reamostrando inicializacoes do MARL e sementes de trafego. O mesmo MPC e reutilizado para cada inicializacao pareada; nao sao cem demandas independentes. Delta positivo significa MPC maior que MARL.

| Medida | Delta MPC menos MARL | IC95 |
|---|---:|---:|
| espera_s | 29.363 | [28.848, 29.889] |
| p95_s | 73.695 | [71.880, 75.560] |
| colisoes | 11.040 | [7.060, 15.360] |

O perfil OD e os horarios sao os mesmos entre sementes. As diferencas incluem controle ciclico versus selecao livre de fase, sensoriamento global das 149 vias no MPC, estimacao de giros e destinos e modelo fluido com capacidade fixa. Os resultados nao isolam a contribuicao do supervisor nem demonstram generalizacao para outra demanda ou seguranca fisica.

As medias locais por entrada e seus tamanhos amostrais sao diagnosticos diferentes da espera total da viagem. Os valores por entrada estao em estatisticas.json. O P95 da tabela e media dos percentis por execucao, nao um percentil agrupado.

## O que manter e o proximo experimento

Manter fontes externas intactas com licenca e commit, estado causal, saidas novas, verificacao das fases e transicoes, rastros do otimizador, parametros congelados e comparacao pareada. Preservar inclusive esta configuracao com resultado desfavoravel.

Antes de propor um MPC mais forte: verificar previsoes versus filas observadas, adequar a execucao ao modelo de ciclos, calibrar saturacao e comprimentos de ciclo somente no conjunto de treino/validacao e auditar G/g, prioridades e colisoes. Depois reservar novas demandas de teste. Reusar as sementes 1 a 10 apos ajustar olhando estes resultados seria uma analise exploratoria, nao novo teste independente.
