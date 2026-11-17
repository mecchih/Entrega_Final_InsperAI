# C5 treinado do zero — 5 agentes, uma Double DQN compartilhada (experimento C5-A)

Data: 16/11/2026. Experimento adicional da Etapa C, depois do zero-shot C3 → C5 (`../experimento_c5/RELATORIO_C5.md`).
Nada do C3, do zero-shot, do Cologne8 ou dos cenários originais foi alterado.

## Resumo

- **O parameter sharing aprende com 5 agentes.** O treino converge no mesmo ritmo do C3. Nenhum episódio de teste travou, e não houve violação nem colisão nos 5 cruzamentos.
- **Mas o C5 treinado não melhora de forma clara o C3 → C5 sem retreino.**
  - Espera nos 5 cruzamentos, demanda intensa: −0,19 ± 0,24 s (não significativo).
  - Demanda moderada: +0,03 ± 0,11 s.
- **Fiandeiras × Atílio Innocenti piorou com o treino**, e ali as trocas de fase aumentaram: 97 contra 60 por episódio.
- **Os novos agentes não deixaram de trocar fase à toa.** Continuam com 2 a 3 vezes mais trocas do que o controle atuado.
- **Nos 2 cruzamentos novos, controlar com RL é pior do que deixar o programa original:** 2,2 contra 1,5 s por veículo.
- **O C3 (só nos 3, com os novos no programa original) segue sendo a melhor configuração de RL.**
- **O programa original continua vencendo todos os controladores com as regras do RL:** 6,8 contra 9,6 s nos 5 cruzamentos, na demanda intensa.

## 1. O que foi feito

| Item | Valor |
|---|---|
| Agentes | 5 TLS: 476455095 (Gomes de Carvalho), 40278305 (Casa do Ator), 40278183 (Quatá), 300058973 (Fiandeiras × Clodomiro), 302806060 (Fiandeiras × Atílio Innocenti) |
| Rede | Uma Double DQN 13 → 64 → 64 → 2 (5.186 parâmetros), rede-alvo e replay compartilhados, inicialização aleatória (nenhum peso do C3) |
| Representação | Canônica, do adaptador já testado no SUMO: em Casa do Ator, troca de slots e de fase; em 302806060, troca só de fase e de ação. Slot 0 = via principal. |
| Hiperparâmetros | Os do C3: Adam 5e-4, lote 64, Huber, γ = 0,95^(dt/5), alvo a cada 500 gradientes |
| Orçamento | Replay 5 × 50 mil; aquecimento 5 × 2.000; ε em 5 × 40 mil decisões; **1 gradiente a cada 5 transições**, ou seja, o mesmo número de atualizações por rede que o C3 e o Modelo A (não foi aumentado) |
| Treino | 5 sementes de modelo × 150 episódios. Demandas 1001–1030 (as do C3, na mesma ordem). Checkpoint a cada 25. |
| Segurança | A mesma de sempre nos 5: verde mínimo 10 s, amarelo 3 s, vermelho geral 2 s, decisão a cada 5 s, verde máximo condicional 60 s, verificador independente. Os outros 9 semáforos ficaram no programa original. |
| Validação | Demandas 221–225 (intensa). Seleção só por ela. |
| Teste | Sementes **novas**, usadas uma única vez: intensa 331–340 (2000 veíc/h) e moderada 341–350 (1200 veíc/h). Nenhuma coincide com as 127 sementes já usadas. |

O adaptador zero-shot (`experimento_c5/adaptador_c5.py`) recusa treino de propósito; o treino usa uma visão própria (`politica_c5.py`).

### Testes técnicos antes do treino (15/15 OK)

`testar_treino_c5.py` verificou o seguinte:

- **Estrutura e orçamento:** 5 agentes numa só rede; replay de 250 mil, aquecimento de 10 mil, ε em 200 mil decisões; 1 gradiente a cada 5 transições (105 contra cerca de 104 esperados).
- **Inicialização e representação:** pesos aleatórios, diferentes dos do C3; transformações iguais às do adaptador.
- **Execução:** os 5 agentes decidem e escolhem ações diferentes entre si; o replay recebe transições dos 5; o replay guarda a ação **executada** (68 = 68 intervenções do verde máximo).
- **Segurança:** a segurança vale nos 5 cruzamentos; os outros 9 ficam no programa; trocas e métricas por cruzamento são registradas.
- **Infraestrutura:** o checkpoint completo faz ida e volta; a avaliação com pesos congelados não aprende; os arquivos do cenário não mudam (SHA-256).

Também rodou um treino curto de 3 episódios (`resultados/curto_s99`).

## 2. Custo e orçamento observados

| | C3 (3 agentes) | C5 (5 agentes) | Diferença |
|---|---:|---:|---:|
| Experiências no replay ao longo do treino (por modelo) | cerca de 205 mil | cerca de 349 mil | +70% |
| Experiências por agente | cerca de 68 mil | cerca de 70 mil | igual |
| Passos de gradiente (por modelo) | cerca de 66 mil | cerca de 68 mil | igual (por desenho) |
| Capacidade do replay | 150 mil | 250 mil | +67% de memória |
| Tempo por episódio de treino | 37,7 s | 38,5 s | +2% |
| Tempo de treino por semente (150 ep.) | cerca de 94 min | cerca de 97 min | +3% |
| Parâmetros / checkpoint | 5.186 / cerca de 25 kB | 5.186 / cerca de 25 kB | igual |

- O custo é dominado pela simulação no SUMO, que é a mesma; os 2 semáforos a mais quase não pesam.
- As 5 sementes rodaram em paralelo, em cerca de 1 h 37 min de relógio.
- Execução completa: 750 episódios de treino, 160 de validação e 360 de teste.
- Episódios de treino travados (rede parada): 2, 2, 1, 1 e 1 por semente. Estão registrados em `historico.jsonl`, não foram removidos.

## 3. A demanda nos cruzamentos novos é suficiente?

| Agente | Veículos por episódio (teste intenso) | Decisões sem nenhum veículo nas 2 aproximações (treino inteiro) | Recompensa média por episódio (últimos 25) |
|---|---:|---:|---:|
| Gomes de Carvalho | 994 | 5,9% | −152 |
| Casa do Ator | 1271 | 7,4% | −117 |
| Quatá | 1423 | 5,8% | −298 |
| Fiandeiras × Clodomiro | 360 | 24,6% | −10 |
| Fiandeiras × Atílio Innocenti | 68 | **59,1%** | −4,5 |

- **A demanda é suficiente para o agente "existir" no replay, mas não para aprender bem.**
  - Cada agente novo contribui com cerca de 70 mil transições, tantas quanto os do corredor.
  - Em Atílio, porém, 59% delas são de cruzamento vazio.
  - A recompensa dos novos é de 30 a 60 vezes menor em magnitude.
  - O sinal de TD que vem deles é quase nulo, e a rede compartilhada aprende principalmente com os 3 cruzamentos carregados.
- **A recompensa (fila e espera) não cobra nada por trocar de fase num cruzamento vazio.**
  - Trocar sem necessidade sai de graça no treino.
  - O custo só aparece quando um veículo chega durante o amarelo e o vermelho geral, um evento raro com 68 veículos por episódio.
  - Por isso a política herda o padrão dos cruzamentos cheios: trocar com frequência.

**C5-B (demanda recalibrada nos novos) não foi executado.**

- Motivo principal: o prazo da entrega (16/11). Um treino leva cerca de 1 h 40 min, mais validação e teste.
- Além disso, o diagnóstico acima indica que só mais volume não resolve. O que falta é um custo de troca na recompensa ou um viés de manter a fase.
- Recalibrar a demanda também mudaria o cenário, e o C5-B deixaria de ser comparável com o C3 e o zero-shot.
- Fica como trabalho futuro, separado do C5-A.

## 4. Seleção na validação (221–225)

Critério:

- **Elegível:** 5/5 episódios válidos, 0 violações, 0 colisões nos cruzamentos controlados, ≥ 99% das viagens concluídas e ≤ 1 teleporte.
- **Métrica principal:** espera ponderada por veículo nos 5 cruzamentos.
- **Desempate:** empates dentro de 2% vão para o menor P95 da rede; depois, para o checkpoint mais cedo.

| Semente | Escolhido | Espera nos 5 | Corredor | Rede |
|---|---:|---:|---:|---:|
| C5 s1 | ep150 | 9,06 | 19,74 | 45,52 |
| C5 s2 | ep75 | 9,50 | 20,57 | 46,02 |
| C5 s3 | ep25 | 9,69 | 21,02 | 45,77 |
| C5 s4 | ep75 | 9,35 | 20,41 | 45,36 |
| C5 s5 | ep150 | 9,50 | 20,51 | 45,17 |
| Original | — | 6,71 | 14,63 | 40,23 |
| Atuado com regras RL nos 5 | — | 10,63 | 23,42 | 47,93 |

- Dois checkpoints ficaram inelegíveis por travamento na validação: s1 ep25 (1/5) e s4 ep150 (3/5).
- Na s3, ep25 (9,69) e ep75 (9,66) empataram dentro de 2%, e a regra levou ao mais cedo.
- Entre checkpoints, a validação oscila muito: o desvio entre sementes chega a ±2,7 s no ep75. Não há tendência clara depois do episódio 25 (G1, quadro inferior direito).
- Os checkpoints escolhidos foram copiados, não movidos, para `modelos_finais/C5/`, com `manifesto.json` e SHA-256.

## 5. Resultados do teste (pesos congelados, uma única execução)

- Comparadores com as mesmas demandas:
  - Original (programa do SUMO nos 14 semáforos);
  - atuado com as regras do RL nos 3 e nos 5;
  - C3 (Modelo C nos 3, novos no programa);
  - C3 → C5 (os mesmos pesos do C3 nos 5, sem retreino; é o mesmo experimento do zero-shot, **reexecutado** nas sementes novas para que todos usem as mesmas demandas; o resultado anterior, 291–300, não foi alterado).
- RL: média de 5 modelos ± desvio entre modelos. Baselines: ± desvio entre as 10 demandas.
- Δ: pareado por demanda, com IC95 (t de Student, 9 g.l.).
- 0 episódios travados em todos os controladores e níveis; 0 violações; 0 teleportes; 100% das viagens concluídas.
- Houve uma colisão no C3 na demanda intensa, fora dos 5 cruzamentos.
- Tabela completa, com fila e consistência por semente: `resultados/relatorio/tabela_treino_c5.md`.

### Demanda intensa (331–340)

| s/veículo | Original | Atuado 3 | C3 | C3 → C5 | Atuado 5 | **C5** |
|---|---:|---:|---:|---:|---:|---:|
| Corredor (Ribeirão Claro) | **14,72** | 22,21 | 19,83 | 21,15 | 21,10 | 20,73 |
| 5 cruzamentos | **6,80** | 10,20 | 9,12 | 9,79 | 9,65 | 9,60 |
| 2 cruzamentos novos | 1,53 | 1,60 | 1,56 | 2,20 | **1,14** | 2,18 |
| Rede inteira | **40,62** | 47,55 | 45,67 | 47,01 | 46,26 | 46,63 |
| P95 corredor | **49,1** | 66,2 | 55,2 | 60,3 | 61,6 | 58,7 |
| Gomes / Casa do Ator / Quatá | 5,55 / 4,86 / 10,98 | 9,69 / 7,68 / 15,38 | 8,80 / 6,84 / 13,63 | 9,37 / 7,24 / 14,60 | 9,53 / 7,49 / 14,22 | 9,45 / 7,27 / 13,99 |
| Clodomiro / Atílio | 1,60 / 1,14 | 1,66 / 1,26 | 1,64 / 1,16 | 2,07 / 2,83 | 1,20 / 0,75 | 1,95 / 3,37 |
| Trocas/episódio: Clodomiro / Atílio | ciclo fixo | ciclo fixo | ciclo fixo | 130 / 60 | 51 / 40 | 118 / 97 |

| Δ = C5 − referência (IC95) | vs C3 → C5 | vs C3 | vs original | vs atuado 5 |
|---|---:|---:|---:|---:|
| 5 cruzamentos | −0,19 ± 0,24 (melhor em 7/10) | +0,48 ± 0,32 | +2,79 ± 1,00 | −0,05 ± 0,70 |
| Corredor | −0,42 ± 0,53 | +0,91 ± 0,72 | +6,02 ± 2,22 | −0,37 ± 1,57 |
| Rede | −0,38 ± 0,38 | +0,96 ± 0,69 | +6,01 ± 1,82 | +0,37 ± 1,55 |
| Quatá | **−0,62 ± 0,38** (9/10) | +0,35 ± 0,51 | +3,01 ± 1,10 | −0,24 ± 1,38 |
| Clodomiro | **−0,12 ± 0,09** (9/10) | +0,30 ± 0,23 | +0,34 ± 0,23 | +0,74 ± 0,19 |
| Atílio | **+0,54 ± 0,34** (pior em 9/10) | +2,21 ± 0,67 | +2,23 ± 0,76 | +2,62 ± 0,57 |
| Trocas Clodomiro | −11,8 ± 4,7 (10/10) | — | — | +67,3 ± 4,8 |
| Trocas Atílio | +37,2 ± 4,4 (0/10) | — | — | +57,7 ± 6,6 |

### Demanda moderada (341–350), fora da distribuição de treino

| s/veículo | Original | Atuado 3 | C3 | C3 → C5 | Atuado 5 | **C5** |
|---|---:|---:|---:|---:|---:|---:|
| Corredor | **5,37** | 9,92 | 10,84 | 10,81 | 9,84 | 10,96 |
| 5 cruzamentos | **2,54** | 4,58 | 4,98 | 5,11 | 4,50 | 5,15 |
| 2 cruzamentos novos | 1,28 | 1,39 | 1,33 | 2,64 | **0,95** | 2,33 |
| Rede inteira | **29,59** | 33,61 | 34,30 | 34,43 | 33,21 | 34,60 |
| P95 corredor | **17,6** | 29,2 | 34,2 | 34,2 | 29,6 | 35,1 |
| Trocas: Clodomiro / Atílio | ciclo fixo | ciclo fixo | ciclo fixo | 130 / 51 | 46 / 27 | 126 / 91 |

Δ C5 − C3 → C5, na moderada:

- **Empates:** 5 cruzamentos +0,03 ± 0,11; corredor +0,15 ± 0,23; rede +0,17 ± 0,30.
- **Melhor:** cruzamentos novos −0,32 ± 0,14 (10/10).
- **Pior:** P95 do corredor +0,95 ± 0,49.
- **Contra o atuado com regras RL nos 5,** o C5 é pior em tudo: 5 cruzamentos +0,65 ± 0,11; corredor +1,12 ± 0,22.

### Consistência entre sementes de modelo (intensa, média das 10 demandas)

- O corredor varia pouco: de 19,7 a 22,3 s.
- As trocas nos novos variam muito:
  - Clodomiro: de 70 a 166 por episódio;
  - Atílio: de 54 a 150 por episódio.
- O comportamento nos cruzamentos novos depende da inicialização, sinal de que o sinal de aprendizado ali é fraco.

## 6. Respostas às 10 perguntas

1. **O parameter sharing consegue aprender com 5 agentes?**
   - Sim, no sentido técnico. A curva de treino é praticamente a do C3: o corredor cai de cerca de 70 s para cerca de 25 s (G1).
   - As trocas de fase caem de cerca de 250 para 90–140 por episódio, e as recompensas dos 5 agentes melhoram.
   - O teste não teve travamento, violação nem colisão.
   - O aprendizado nos 2 cruzamentos novos, porém, é fraco e instável entre sementes.
2. **O C5 treinado supera o C3 → C5 sem retreino?**
   - Não de forma clara. Nos 5 cruzamentos fez −0,19 ± 0,24 s na intensa e +0,03 ± 0,11 s na moderada, ambos não significativos.
   - Ganhou um pouco em Quatá e Clodomiro, e perdeu em Atílio.
3. **Os novos agentes reduziram as trocas desnecessárias?**
   - Só em Clodomiro, e pouco: de 130 para 118 trocas.
   - Em Atílio aumentaram: de 60 para 97.
   - Nos dois, as trocas ficaram 2 a 3 vezes acima do atuado com as mesmas regras (51 e 40). A recompensa não cobra por trocar, e com 59% de decisões em cruzamento vazio não há sinal para aprender a manter.
4. **Os 3 cruzamentos originais melhoraram ou pioraram?**
   - Contra o C3 → C5, ficaram iguais ou um pouco melhores: Quatá −0,62 s; corredor −0,42 ± 0,53 s, não significativo.
   - Contra o C3, que só controla esses 3, ficaram um pouco **piores** na intensa: corredor +0,91 ± 0,72 s; Casa do Ator +0,43 ± 0,21 s.
   - Na moderada, empataram.
   - Dividir a mesma rede com 2 cruzamentos de outro regime custa um pouco no corredor.
5. **Controlar 5 cruzamentos melhora a espera na rede?**
   - Com RL, não. O C5 tem rede +0,96 ± 0,69 s em relação ao C3 na intensa e +0,30 ± 0,25 s na moderada.
   - Com o controle clássico atuado, passar de 3 para 5 ajuda um pouco: rede 47,55 → 46,26 s; novos 1,60 → 1,14 s.
   - O valor de controlar os novos existe, mas o C5 não o captura.
6. **O C5 supera o programa original?**
   - Não. Nos 5 cruzamentos fez +2,79 ± 1,00 s na intensa e +2,61 ± 0,11 s na moderada.
   - No corredor fez +6,0 e +5,6 s, piores em todas as demandas.
   - Confirma a conclusão da otimização final: com vermelho geral de 2 s e decisão a cada 5 s, nenhum controlador com essas regras chega ao programa original.
7. **O C5 é robusto a demandas diferentes?**
   - É robusto em segurança: 0 travamentos, 0 violações e 100% das viagens concluídas também na moderada, que não foi vista no treino.
   - Não é robusto em eficiência. Na intensa, empata com o atuado nos 5 (−0,05 ± 0,70 s); na moderada, fica pior que ele em todas as métricas (+0,65 ± 0,11 s nos 5 cruzamentos).
   - A demanda saturada não foi testada nesta etapa.
8. **O compartilhamento funciona com cruzamentos de volumes muito diferentes?**
   - Funciona mal. Os volumes vão de 68 a 1423 veículos por episódio, cerca de 20 vezes de diferença, e a recompensa difere de 30 a 60 vezes.
   - A rede aprende a política dos cruzamentos carregados e a aplica aos vazios.
   - Para funcionar, seria preciso normalizar a recompensa por cruzamento, cobrar um custo de troca ou indicar o regime de demanda na observação.
9. **Qual é o custo adicional?**
   - Computacional, pequeno: +2–3% de tempo de treino, +70% de experiências e +67% de memória de replay. A rede e o número de gradientes são os mesmos.
   - De engenharia: mapear a representação canônica de cada cruzamento novo e estender a verificação de segurança.
   - O custo real é de desempenho: em Atílio, a espera passa de 1,14 s (original) para 3,37 s.
10. **Vale expandir para mais cruzamentos?**
    - Não com o desenho atual. Os candidatos restantes também ficam fora do corredor, onde a demanda calibrada é baixa: cerca de 190 veículos/h no resto da rede (ver `../VIABILIDADE_C6.md`). Nos cruzamentos de baixo volume o programa original ou o atuado já ficam perto do ótimo.
    - A expansão só faz sentido depois de mudar a recompensa (custo de troca ou normalização), testando primeiro um C5-B nos mesmos 5 cruzamentos.
    - Para a entrega, a recomendação é manter o C3, com os cruzamentos novos no programa original, e registrar o C5 como experimento.

## 7. Gráficos (`resultados/relatorio/`)

- `g1_evolucao_treino_c5.png`: o treino do C5 contra o do C3 (corredor), a espera e as trocas por cruzamento, e a validação por checkpoint.
- `g2_original_c3_c3c5_c5.png`: Original, C3, C3 → C5 e C5 (com os atuados) no corredor, nos novos, na rede e no P95, nas duas demandas.
- `g3_cinco_cruzamentos.png`: a espera em cada um dos 5 cruzamentos (intensa).
- `g4_trocas_novos.png`: as trocas de fase nos 2 cruzamentos novos (C3 → C5, atuado 5 e C5).

## 8. Arquivos

| Arquivo | Função |
|---|---|
| `politica_c5.py` | Rede compartilhada com 5 aprendizes, visão de treino canônica, salvar e carregar (formato `..._c5_v1`) |
| `treinar_c5.py` | Laço de treino (o mesmo do C3), histórico por episódio com experiências, gradientes, recompensas, trocas e decisões vazias por agente |
| `testar_treino_c5.py` | 15 verificações técnicas |
| `bateria_treino_c5.py` | `demandas`, `comparadores`, `validar` e `testar` (o teste recusa sobrescrever) |
| `relatorio_treino_c5.py` | Tabelas e gráficos; só lê resultados |
| `exportar_modelos_c5.py` | Copia os 5 checkpoints escolhidos para `modelos_finais/C5/`, com manifesto |
| `resultados/treinos/C5_s*/` | `configuracao.json`, `historico.jsonl`, `resumo_treino.json`; os `.pt` e os episódios ficam só na cópia local |
| `resultados/validacao/selecao_c5.json` | Tabela de validação e seleção |
| `resultados/relatorio/` | `tabela_treino_c5.md`, `comparacoes_treino_c5.json` e os 4 gráficos |

## 9. Como reproduzir

Na raiz do repositório, com SUMO 1.28 e o Python com torch:

```bash
python -B -X utf8 semaforo/integracao_insper/parameter_sharing/treinamento_c5/testar_treino_c5.py
python -B -X utf8 semaforo/integracao_insper/parameter_sharing/treinamento_c5/bateria_treino_c5.py demandas
python -B -X utf8 semaforo/integracao_insper/parameter_sharing/treinamento_c5/treinar_c5.py --semente 1 --pasta semaforo/integracao_insper/parameter_sharing/treinamento_c5/resultados/treinos/C5_s1   # 1..5
python -B -X utf8 semaforo/integracao_insper/parameter_sharing/treinamento_c5/bateria_treino_c5.py comparadores --processos 12
python -B -X utf8 semaforo/integracao_insper/parameter_sharing/treinamento_c5/bateria_treino_c5.py validar --processos 12
python -B -X utf8 semaforo/integracao_insper/parameter_sharing/treinamento_c5/bateria_treino_c5.py testar --processos 12
python -B -X utf8 semaforo/integracao_insper/parameter_sharing/treinamento_c5/relatorio_treino_c5.py
python -B -X utf8 semaforo/integracao_insper/parameter_sharing/treinamento_c5/exportar_modelos_c5.py
```

- `validar` e `testar` recusam sobrescrever resultados existentes.
- Para refazer, use outra pasta ou mova a anterior; não apague.
