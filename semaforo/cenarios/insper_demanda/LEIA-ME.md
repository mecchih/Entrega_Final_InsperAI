# Cenário Insper: demandas sintéticas derivadas

Estas demandas derivam do cenário `semaforo/cenarios/insper/`, que **não foi
alterado**. Todos os scripts conferem o SHA-256 dos arquivos originais no início e
no fim.

Cada `cenario.sumocfg`:
- tem as mesmas opções de simulação do `osm.sumocfg`;
- aponta, por caminho relativo, para a rede, os polígonos e a vista originais;
- muda apenas o arquivo de rotas;
- não traz saídas: o avaliador as passa pela linha de comando.

Todos os testes usaram os **programas semafóricos originais** (atuados), sem IA
e sem controle pelo TraCI.

## Níveis

| Nível | Viagens que cruzam o corredor (veíc/h) | Demais viagens | Total | Sementes |
|---|---:|---|---:|---|
| `original` | ~95 | 183 (densidade 12) | 278 | arquivo original; as sementes 1–5 variam só o SUMO |
| `moderado` | 1.200 | ~189 (densidade 12) | ~1.389 | 101–105 |
| `intenso` | 2.000 | ~190 (densidade 12) | ~2.190 | 211–215 |
| `saturado` | 2.400 | ~190 (densidade 12) | ~2.590 | 311–315 |

"Cruzar o corredor" significa que a rota passa por ao menos um dos semáforos
476455095, 40278305 e 40278183. Cada pasta `<nível>/semente_<n>/` contém:
- `rotas.rou.xml`, com rotas fixas validadas pelo duarouter;
- `cenario.sumocfg`;
- `gerado.json`, com as contagens, a composição por aproximação, os hashes e o histórico do sorteio.

Para ver uma demanda no GUI:

```powershell
sumo-gui -c semaforo/cenarios/insper_demanda/intenso/semente_211/cenario.sumocfg
```

## Como a demanda foi gerada

O script é `semaforo/integracao_insper/gerar_demanda_insper.py`.

1. **Mesmo gerador da demanda original.**
   - É o `randomTrips.py` com as opções do `build.bat`. Com `--seed 42` e densidade 12, ele reproduz exatamente as 278 viagens do `osm.passenger.trips.xml`; isso foi conferido.
   - Para cada semente, ele gera cerca de 27,7 mil candidatas com densidade 1200.
   - O duarouter (`--validate`) descarta as viagens sem rota válida para carros. Por isso todas as rotas respeitam os sentidos permitidos.
2. **Amostragem estratificada.** As candidatas são divididas em dois estratos:
   - `corredor`: cerca de 8,7 mil candidatas, cuja rota cruza um dos três semáforos;
   - `resto`: todas as outras.

   O sorteio é feito sem reposição e é reproduzível: `random.Random("insper-demanda-<semente>")`.

   Dentro de cada estrato, origens, destinos, rotas e horários seguem a distribuição do gerador original. **A única mudança deliberada é o peso do corredor**, que é de 13,6× (moderado), 22,7× (intenso) e 27,1× (saturado) em relação ao resto. O resto fica na densidade original. Esse peso está registrado em `gerado.json`.
3. **Correção de origem.** É uma alteração de O/D, documentada aqui.
   - O `randomTrips` usa como origem vias menores que um carro, como `522284920#0` (1,01 m) e `369907169#0` (0,2 m).
   - Nessas vias o SUMO insere carros sobrepostos quando há fila, o que gera colisões de inserção que não correspondem a nenhum conflito real.
   - Nas viagens afetadas, as vias iniciais com menos de 5 m são retiradas da rota. O carro parte poucos metros adiante, na mesma rota e com o mesmo destino.
   - Isso afeta cerca de 14% das viagens dos níveis derivados (205 de 1.389 no moderado, semente 101).

Por que não multiplicar a rede inteira: na varredura 1, multiplicar toda a
demanda por 6 já congestionou o resto da rede, com 47% dos veículos parados e
22 colisões na junção 1550389898 nas 2 sementes, enquanto as filas do corredor continuavam
pequenas. Multiplicar por 10 paralisou a rede: 55% de viagens concluídas e cerca
de 1.000 teletransportes. Ou seja, multiplicar tudo satura outros pontos antes do
corredor.

## Calibração progressiva

As pastas estão em `semaforo/integracao_insper/resultados/`.

| Varredura | Pastas | Pontos (veíc/h no corredor) | Conclusão |
|---|---|---|---|
| 1 e 2 | `…215149Z_calibracao_demanda` e `…215440Z_calibracao_demanda` | 95 a 6.000, mais a multiplicação de toda a rede | Revelaram as colisões de inserção em `522284920#0` (até cerca de 1.500 por rodada) |
| 3 | `…220035Z_calibracao_demanda` | 300 a 2.800, 2 sementes | Com a correção de origem, **0 colisões em todas as rodadas** |
| 4 | `…220530Z_calibracao_demanda` | 1.600 a 2.600, **10 sementes** | Robustez |

Os critérios foram definidos antes da escolha e estão em `niveis.json`.

A primeira escolha (intenso 2.200 e saturado 2.600) foi reprovada na validação
`…220258Z_validacao_niveis`: a semente 205 do intenso travou, com 38,7% das
viagens concluídas e 452 teletransportes. As demandas reprovadas foram
arquivadas em `demandas_rejeitadas/` daquela pasta.

Travamentos observados depois da correção:

| Demanda no corredor | Rodadas | Rodadas travadas |
|---|---:|---:|
| 300 a 2.000 | 54 (17 delas em 2.000) | 0 |
| 2.200 | 17 | 1 |
| 2.400 | 17 | 0 |
| 2.600 | 17 | 2 |

O sistema tem um joelho de capacidade perto de 2.200 veículos por hora no
corredor. A partir daí, o travamento é raro, mas possível.

## Comparação dos quatro níveis

Validação final em `semaforo/integracao_insper/resultados/20261115T220944Z_validacao_niveis/validacao.json`.
Os valores são a média das 5 sementes, com o intervalo entre parênteses.

| Métrica | original | moderado | intenso | saturado |
|---|---|---|---|---|
| Veículos gerados | 278 | 1.389 (1.388–1.390) | 2.190 (2.189–2.190) | 2.590 (2.589–2.590) |
| Viagens concluídas | 100% | 100% | 100% | 100% |
| Passaram por 476455095 (Gomes de Carvalho) | 44 | 649 (612–686) | 1.088 (1.063–1.125) | 1.298 (1.279–1.326) |
| Passaram por 40278305 (Casa do Ator) | 59 | 821 (803–844) | 1.374 (1.346–1.390) | 1.644 (1.628–1.678) |
| Passaram por 40278183 (Quatá) | 76 | 921 (907–935) | 1.519 (1.493–1.550) | 1.834 (1.814–1.856) |
| Cruzaram 2 ou 3 semáforos (só os 3) | 56 (29) | 753 (444) | 1.265 (726) | 1.512 (878) |
| Espera média no corredor (s) | 2,5 | 5,4 (5,2–5,6) | 14,5 (11,5–18,2) | 40,7 (34,1–46,8) |
| Espera P95 no corredor (s) | 7,7 | 17,6 | 50,5 (37–67) | 131,9 (100–175) |
| Espera média na rede (s) | 34,0 | 30,0 | 40,8 (36,8–43,6) | 74,3 (67,3–81,8) |
| Espera P95 na rede (s) | 106 | 96 | 122 (113–138) | 208 (176–255) |
| Fila média / máxima em 476455095 | 0,02 / 1 | 0,44 / 4 | 1,80 / 15 (8–33) | 12,3 / 37 |
| Fila média / máxima em 40278305 | 0,02 / 2 | 0,51 / 5 | 1,89 / 15 | 5,65 / 24 |
| Fila média / máxima em 40278183 | 0,03 / 2 | 0,88 / 9 | 4,33 / 24 | 9,57 / 30 |
| Tempo com fila ≥ 1 (três semáforos) | 2–3% | 34–47% | 66–88% | 93–98% |
| Tempo com fila ≥ 5 (três semáforos) | 0% | 0–3% | 8–36% | 48–79% |
| Menor grupo verde, por semáforo | 27% / 19% / 44% | 32% / 22% / 33% | 31% / 23% / 32% | 32% / 22% / 33% |
| Fila tomando ≥ 90% do trecho 476→403 / 403→401 (s) | 0 / 0 | 1 / 2 | 45 / 156 | 386 / 618 |
| Verde bloqueado a jusante, por semáforo (s) | 0 / 0 / 0 | 0 / 0 / 9 | 31 / 65 / 37 | 319 / 297 / 62 |
| Fila do semáforo seguinte: média / máxima | 0,05 / 2 | 0,39 / 6 | 0,81 / 7 | 1,11 / 7 |
| Saída do corredor (`234368026#1`): fila máxima / s com ≥ 90% ocupado | 2 / 0 | 6 / 0 | 7 / 1 | 7 / 1 |
| Presos (> 180 s parados) / não atendidos no fim | 0 / 0 | 0 / 0 | 2 (0–9) / 0 | 31 (11–46) / 0 |
| Pico de inserções pendentes | 1 | 2 | 9 (4–26) | 94 (40–150) |
| Parados na rede (pico de 5 min) | 30% | 26% | 35% | 53% |
| Colisões | 1 em 4 das 5 sementes, preexistente | 0 | 0 | 0 |
| Teletransportes | 0 | 0 | 0 (1 em uma semente) | 2 (0–2) |

Como ler a tabela:
- Fila = veículos parados até 100 m antes do semáforo, entre 300 e 3.600 s.
- "Menor grupo verde" é a fração dos veículos atendidos pela fase verde menos usada.
- "Verde bloqueado a jusante" conta os segundos em que um link estava verde, havia veículo na linha de retenção e o trecho seguinte estava ao menos 80% ocupado.
- A espera média na rede é menor no moderado do que no original porque as viagens do corredor são curtas e diluem a média.

**Consistência entre sementes:** para a espera no corredor e para a fila média
de cada um dos três semáforos, os intervalos de níveis vizinhos não se
sobrepõem. O pior valor de um nível é sempre melhor que o melhor valor do nível
seguinte, nas 5 sementes. Os níveis são distintos e ordenados.

## Filas, esperas e bloqueios

- **Gargalos:** os gargalos são **40278183** (Quatá) no moderado e no intenso, e **476455095** (Gomes de Carvalho) no saturado. O 476455095 tem a única aproximação de faixa única (Gomes de Carvalho, 37,7 m), que recebe cerca de 2/3 do fluxo desse semáforo.
- **Interação entre cruzamentos:** aparece a partir do intenso.
  - A fila de 40278183 ocupa o trecho 403→401 durante 70 a 248 s por hora.
  - Os semáforos ficam com o verde bloqueado a jusante durante 31 a 65 s por hora.
  - No saturado, a fila sobe pelo corredor (386 a 618 s com trecho tomado) e o 476455095 fica bloqueado durante cerca de 320 s por hora.
- **Saída do corredor:** o semáforo seguinte, a 27,5 m, absorve bem os níveis aceitos. A fila máxima na via de saída fica em 7 ou 8 veículos, que é a capacidade de 2 faixas × 27,5 m, mas essa via quase nunca fica tomada por mais de 1 s.
- **Travamento perto do joelho:** nas rodadas que travaram (≥ 2.200), o padrão foi:
  - saída ocupada durante 215 a 597 s;
  - 1.350 a 3.711 veículo·s parados dentro do próprio cruzamento 40278183;
  - teletransportes por `wrong lane` na via de saída e na Quatá.

  Ou seja, a fila do semáforo seguinte bloqueia o cruzamento. Esse é o risco estrutural da saída do corredor.
- **Teletransportes:** os poucos que ocorreram nos níveis aceitos são `yield` em `27579109#1/#2`. São cruzamentos sem semáforo na Gomes de Carvalho, a montante do 476455095, onde a fila impede a entrada de quem vem das transversais.

## Problemas preexistentes e problemas da demanda nova

| Problema | Classificação | Evidência |
|---|---|---|
| Colisão na junção 1550389898 (semáforo `joinedS_1389167582_…`, fora do corredor) | **Preexistente** | Ocorre com a demanda original em 4 das 5 sementes. Envolve `veh116`, que parte de `369907169#0`, uma via de 0,2 m. Sumiu nos níveis derivados, que têm a correção de origem. |
| Colisões de inserção em vias de origem < 5 m (`522284920#0`, …) | **Preexistente na rede e no gerador**; só aparece com fila | Até cerca de 1.500 por rodada nas varreduras 1 e 2; 0 depois da correção. |
| Travamento na saída do corredor (40278183 → 27,5 m → semáforo seguinte) | **Demanda nova** (geometria original) | 3 travamentos em 51 rodadas entre 2.200 e 2.600; nenhum em 54 rodadas até 2.000. |
| Teletransportes `yield` a montante do 476455095 (Gomes de Carvalho) | **Demanda nova** | 0 no moderado; 0 ou 1 no intenso; 0 a 2 no saturado. |
| Congestionamento do resto da rede ao multiplicar toda a demanda | Demanda nova (método rejeitado) | Na varredura 1: 6× deixou 47% dos veículos parados e 10× paralisou a rede. |

## Recomendação para o primeiro treinamento

**Nível `intenso` (2.000 veículos por hora no corredor; sementes 211–215).**

Motivos:
- as filas são relevantes nos três cruzamentos, com fila ≥ 1 em 66 a 88% do tempo e fila ≥ 5 em 8 a 36%;
- as duas fases de cada semáforo recebem veículos: o menor grupo tem entre 21% e 32% do fluxo;
- 1.265 veículos por hora passam por dois ou três cruzamentos;
- há interação mensurável, com fila subindo entre cruzamentos e verdes bloqueados a jusante;
- 100% das viagens são concluídas, sem colisões, e a rede fica perto do original (35% de parados no pico, contra 30%);
- nenhum travamento em 17 rodadas com 2.000 veículos por hora, nem em 54 rodadas até 2.000.

Cuidados:
1. O nível ainda está a cerca de 10% do joelho de capacidade. Uma política pior que o programa atuado pode levar a rede ao travamento. O ambiente de treino precisa decidir como tratar teletransportes e travamentos. O Cologne8 interrompe o episódio, e uma semente do intenso já tem 1 teletransporte com o programa original.
2. O `moderado` serve como etapa inicial ou de verificação, se for preciso. O `saturado` deve ficar só para testes de robustez, não para o primeiro treino.
3. As sementes de treino, validação e teste devem ser separadas. As sementes 211–215 são de validação. Gere sementes novas para treinar com o mesmo comando.

## Reprodução

Rode na raiz do repositório, com `SUMO_HOME` definido (SUMO 1.28.0):

```powershell
# validação final: 4 níveis × 5 sementes (gera as demandas que ainda não existem)
python -B -X utf8 semaforo/integracao_insper/calibrar_demanda_insper.py validar --niveis semaforo/cenarios/insper_demanda/niveis.json

# varreduras de calibração (as demandas ficam em resultados/, não no cenário)
python -B -X utf8 semaforo/integracao_insper/calibrar_demanda_insper.py varredura --pontos 300:12 600:12 900:12 1200:12 1500:12 1800:12 2000:12 2200:12 2400:12 2600:12 2800:12 --sementes 9001 9002 --original
python -B -X utf8 semaforo/integracao_insper/calibrar_demanda_insper.py varredura --pontos 1600:12 1800:12 2000:12 2200:12 2400:12 2600:12 --sementes 9101 9102 9103 9104 9105 9106 9107 9108 9109 9110

# gerar só uma demanda (recusa sobrescrever uma pasta existente)
python -B -X utf8 semaforo/integracao_insper/gerar_demanda_insper.py --nivel intenso --corredor 2000 --sementes 216 217
```

As varreduras 1 e 2 usaram a versão do gerador sem a correção de origem e não se
reproduzem com o script atual. A validação final completa leva cerca de 1
minuto com 10 processos.
