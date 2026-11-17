# Investigação do 4º semáforo (Ribeirão Claro × Av. Hélio Pellegrino)

Investigação curta, sem treino de RL. Os modelos treinados, o Cologne8, o cenário original e os experimentos anteriores não foram alterados. Nada foi commitado.

- Código:
  - `ambiente_quarto.py`: cópia da v2 com o parâmetro `quarto`. Com `quarto=None` reproduz exatamente a v2; conferido abaixo.
  - `investigar_quarto.py`.
- Dados: `resultados/estatico_*.json`, `resultados/*_experimento/experimento.json` e `resultados/*_fumaca/`.

## Recomendação: **B — manter três agentes**

- Controlar o 4º semáforo **não melhorou** a espera no corredor em nenhuma combinação com o controle atual (RL A_col ou atuado com as regras do RL).
  - Diferenças de **+0,25 a +3,7 s**.
  - Com o RL nos 3, as estratégias atuado e escoamento pioraram em 5/5 modelos (+2,0 a +2,3 s); a prioridade ficou neutra (+0,25 ± 0,35 s).
- O único ganho apareceu combinando os **programas originais** nos 3 com prioridade máxima à Ribeirão Claro no 4º: −1,95 s, em 5/5 sementes.
  - Isso não melhora a IA. Com o RL, a mesma estratégia dá +0,25 s.
  - Também depende de uma demanda sintética em que a Av. Hélio Pellegrino quase não tem tráfego.
- O 4º semáforo não é o gargalo dos três agentes.

## 1. O 4º semáforo

| Item | Resultado |
|---|---|
| ID | `cluster_13529541823_13529541824_300058941_300063845_#2more` |
| Posição | 27,5 m depois da Quatá (via `234368026#1`, 2 faixas, cabem cerca de 8 carros) |
| Cruzamentos | **1 junção formada por 6 nós do OSM fundidos** (cluster): Av. Hélio Pellegrino nos dois sentidos (3 faixas cada), Ribeirão Claro (2 faixas) e duas ciclovias (Hélio Pellegrino e Faria Lima) |
| Movimentos | **25 links**: 17 de veículos e 8 só de bicicleta. Os 3 do corredor têm 8, 5 e 6. |
| Configurações de verde | **2** (actuated, minDur 5, maxDur 50, amarelo 3 s, sem vermelho geral): (1) Hélio Pellegrino, os dois sentidos, mais as ciclovias; (2) Ribeirão Claro |
| Conflitos | 108 pares conflitantes, dos quais **45 abrem juntos na mesma fase** (cruzamentos ou convergências G/g e g/g resolvidos por preferência). Os 3 do corredor têm **0** conflitos dentro da mesma fase. |
| Veículos do corredor que passam por ele | **1179 por hora** (59% dos 2002 veículos do corredor; validação 221–225). Destinos: Hélio Pellegrino (`369907174#1`) 711; Ribeirão Claro em frente 341; Hélio Pellegrino no outro sentido 101; termina 30. |
| Outras entradas | Só **cerca de 168 veículos por hora** pela Hélio Pellegrino na demanda sintética (117 + 51), que é estratificada no corredor. Na rua real a avenida é a via principal, então a demanda sintética favorece a Ribeirão Claro. |

### Bloqueio da saída do corredor

Bloqueio = a Quatá está verde para a saída enquanto a saída está ≥ 80% ocupada e há veículo na linha de retenção. Dados existentes da validação 221–225:

| Controlador | Bloqueio por episódio | % do tempo de controle |
|---|---:|---:|
| Original | 40,8 s | 1,1% |
| Atuado com as regras do RL | 53,0 s | 1,5% |
| RL (A e B, todos os checkpoints) | 70–77 s | 1,9–2,1% |

A diferença entre RL e original é de cerca de 35 s por episódio de aproximadamente 3500 s. É pequena demais para explicar os cerca de 6 s de espera a mais por veículo.

### Integração segura

- É **possível**, mas o 4º **não pode ser tratado como os outros três**. O verificador de segurança atual rejeita até o programa original desse semáforo (10.440 "violações" na primeira fumaça, arquivada em `resultados/_falhou_verificador_conflitos_mesma_fase/`), porque assume fases sem conflitos internos.
- Para o experimento, os conflitos dentro da mesma fase continuaram como no original (o controlador só usa os estados verdes do próprio programa). O vermelho geral de 2 s e o verificador passaram a valer para os conflitos entre fases (`foes_entre_fases`).
- Resultado: **0 violações em 105 episódios com o 4º controlado** (mais 6 na fumaça), verde ≥ 10 s e vermelho geral = 2 s.
- Esse modelo de segurança é novo. Os 140 episódios são só um teste preliminar, não uma validação formal.
- A interseção é **desproporcionalmente mais complexa** que as outras três: 25 contra 5–8 links, 5 aproximações, ciclovias e conflitos permissivos.

## 2. Experimento clássico (sem RL novo)

Validação exploratória, sementes 221–225. Os testes finais (241–250, 211–215, 231–235) não foram usados. As mesmas demandas valem para todos os controladores.

Estratégias para o 4º, todas com as regras do RL: verde mínimo 10 s, amarelo 3 s, vermelho geral 2 s, decisão a cada 5 s e verde máximo condicional de 60 s.
- `atuado`: o mesmo atuado equivalente dos 3.
- `escoamento`: atuado, mais troca para a Ribeirão Claro quando há ≥ 4 veículos parados na saída do corredor.
- `prioridade`: pede sempre a Ribeirão Claro; a proteção de verde máximo devolve o verde à Hélio Pellegrino a cada 60 s se houver demanda. É o limite superior de priorizar a saída.

**Conferência de equivalência:** com o 4º no programa original, os números reproduzem exatamente a validação anterior: original 14,63; atuado com as regras do RL 21,98; A_col 19,55 / 19,77 / 21,57 / 20,55 / 22,93.

Espera média em segundos. "Δ corredor" é pareado com o mesmo controle dos 3 e o 4º no programa original; "melhor em" conta sementes de tráfego (ou modelos, no caso do RL).

| Controle dos 3 | 4º semáforo | Corredor | Δ corredor | melhor em | Rede | P95 corredor | Bloqueio da saída | Fila Hélio P. (média) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| original | original | **14,63** | — | — | 40,23 | 49,6 | 40,8 | 0,24 |
| original | atuado | 23,59* | +8,95 | 1/4 | 50,06 | 75,9 | 114,2 | 0,35 |
| original | escoamento | 19,43 | +4,79 | 0/5 | 45,31 | 61,6 | 135,8 | 0,40 |
| original | prioridade | **12,69** | **−1,95 ± 1,06** | **5/5** | 40,87 | 42,3 | 96,0 | 1,05 |
| atuado (regras RL) | original | 21,98 | — | — | 46,32 | 63,1 | 53,0 | 0,27 |
| atuado (regras RL) | atuado | 25,58 | +3,60 | 0/5 | 51,07 | 71,2 | 115,2 | 0,39 |
| atuado (regras RL) | escoamento | 25,65 | +3,67 | 2/5 | 50,60 | 73,1 | 98,6 | 0,41 |
| atuado (regras RL) | prioridade | 25,38 | +3,40 | 0/5 | 51,84 | 72,6 | 173,0 | 1,07 |
| RL A_col (5 modelos) | original | 20,87 | — | — | 45,91 | 56,0 | 67,4 | 0,24 |
| RL A_col | atuado | 23,14 | +2,26 ± 0,72 | 0/5 | 48,70 | 62,2 | 106,0 | 0,37 |
| RL A_col | escoamento | 22,87 | +2,00 ± 0,73 | 0/5 | 48,22 | 61,2 | 101,8 | 0,36 |
| RL A_col | prioridade | 21,12 | +0,25 ± 0,35 | 1/5 | 48,51 | 56,6 | 139,2 | 1,11 |

\* Um dos 5 episódios (semente 222) **travou a rede** (inválido: 29% das viagens concluídas). A média é dos 4 válidos.

Nas 140 avaliações: 0 violações, 0 teletransportes nos episódios válidos e 3 colisões externas fora dos cruzamentos controlados.

**Leitura:**
- **O 4º não limita os três agentes.** Com o RL ou com o atuado sob as regras do RL nos 3, nenhuma estratégia para o 4º melhorou a espera no corredor. Todas pioraram também a espera na rede (+2,3 a +5,5 s).
- Submeter o 4º às mesmas regras operacionais (vermelho geral de 2 s, decisão a cada 5 s, verde mínimo de 10 s) custa caro numa junção que recebe cerca de 1300 veículos por hora, e uma combinação chegou a travar a rede. É o mesmo efeito já visto nos 3: as regras operacionais pesam mais que a coordenação.
- O ganho de −1,95 s (original nos 3 + prioridade à Ribeirão no 4º) é um **limite superior otimista**:
  - Só existe porque a demanda sintética quase não carrega a Hélio Pellegrino. A fila da avenida já quadruplica (0,24 → 1,05), e com a demanda real da avenida o custo seria muito maior.
  - Não envolve RL e não se repete quando os 3 são controlados pelo RL (+0,25 s).
- O bloqueio da saída não explica a espera: a estratégia que mais reduziu a espera (original + prioridade) **aumentou** o bloqueio medido (40,8 → 96,0 s).

## 3. Custo e viabilidade de um 4º agente

| Item | O que seria necessário |
|---|---|
| Código | `TLS`, `TRECHOS`, métricas (`bloqueio`, `filas`), recompensa, sensores, bateria e relatórios assumem 3 semáforos. Seria preciso generalizar para N e criar a área de observação de 5 aproximações. |
| Observação local | O formato de 13 dimensões tem 2 aproximações (uma por fase). O 4º tem 3 aproximações de veículos e 2 de bicicletas; seria preciso agregar por fase (Hélio nos dois sentidos juntos). Viável, mas é um formato novo. |
| Ações | 2 configurações de verde, compatível com `ACOES_LOCAL = 2`. |
| Supervisor | Nova arquitetura: observação de 48 → cerca de 64 dimensões e 4 → 5 orientações. A rede tem de ser recriada e treinada do zero. |
| Segurança | Novo modelo de conflitos (permissivos dentro da fase, ciclovias), testes unitários novos e validação formal; hoje existe só o teste preliminar acima. Também seria preciso tratar o travamento visto com o atuado no 4º. |
| Retreino | **Todos** os modelos (A e B), porque a dinâmica, a recompensa e a dimensão do supervisor mudam. Não é possível reaproveitar checkpoints. |
| Custo computacional | Por arquitetura: cerca de 1,5 h para 5 sementes × 150 episódios com 10 processos. A e B juntos: cerca de 3 h, mais validação (~40 min) e teste (~20 min). Somando implementação e testes (~2–3 h), são **6–7 h sem folga**. |
| Riscos para hoje | Bug de segurança no novo modelo de conflitos, travamentos, falta de tempo para validação formal e, principalmente, **ausência de evidência de ganho**: os experimentos clássicos indicam piora. |

## 4. Resposta

**A expansão de três para quatro semáforos não apresenta evidências suficientes de potencial para justificar novos treinamentos.** Recomendação **B**: manter três agentes e consolidar a entrega atual.

Se o tema for retomado depois da entrega:
- antes de qualquer RL, calibrar a demanda da Av. Hélio Pellegrino;
- antes de qualquer RL, validar formalmente o modelo de segurança com conflitos permissivos;
- testar primeiro as regras operacionais (vermelho geral e intervalo de decisão), que são o fator dominante.

## Reprodução

```bash
PY="python -B -X utf8"   # Python com torch, traci e sumolib; SUMO 1.28 com SUMO_HOME definido
$PY semaforo/integracao_insper/quarto_semaforo/investigar_quarto.py estatico
$PY semaforo/integracao_insper/quarto_semaforo/investigar_quarto.py fumaca --processos 8
$PY semaforo/integracao_insper/quarto_semaforo/investigar_quarto.py experimento --processos 12   # ~10 min, 140 episódios
```
