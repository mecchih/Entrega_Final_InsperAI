# Modelo C: Parameter Sharing Multi-Agent Double DQN (corredor Insper)

São três agentes locais com **uma única Double DQN**: a rede online, a rede-alvo, o otimizador e o replay são os mesmos para os três.
- Cada agente recebe a observação do **próprio** cruzamento, decide sozinho e é executado pelo **seu** controlador seguro.
- Cada agente recebe a **própria** recompensa local.
- Não é um agente único com ação global: são 3 decisões independentes por passo de decisão, tomadas pela mesma política.

O que **não** muda e é reaproveitado:
- o ambiente da otimização final (`../otimizacao_final/ambiente_marl_insper_v2.py`, modo `independente`);
- o controlador seguro, os sensores e as métricas;
- a `DoubleDQN` e o `Replay` de `semaforo/scripts/agente_marl_cologne.py`;
- a configuração do Modelo A otimizado: verde mínimo de 10 s, colisão atribuída, amarelo de 3 s, vermelho geral de 2 s e verde máximo condicional de 60 s.

Os Modelos A e B, seus checkpoints, o Cologne8 e os cenários não foram alterados.

## Arquivos

| Arquivo | Função |
|---|---|
| `politica_compartilhada.py` | Rede compartilhada (subclasse da `DoubleDQN` original, sem mudar a rede nem o passo de gradiente), visões por agente, representação canônica, regra clássica do experimento de transferência, salvar/carregar |
| `treinar_ps.py` | Treino (mesmo laço e mesmas demandas do Modelo A) |
| `testar_ps.py` | 18 verificações antes do treino |
| `bateria_ps.py` | Demandas novas de teste, treino paralelo, validação/seleção e testes de generalização |
| `relatorio_ps.py` | Gráficos e tabelas (`resultados/relatorio/`) |
| `RELATORIO_PS.md` | Resultados e conclusões |

## Compatibilidade da representação (verificada antes do treino)

| Item | Verificação | Resultado |
|---|---|---|
| 13 entradas | filas/25 e carros/35 das 2 aproximações, fase verde one-hot (2), idade do verde/60 (teto 2), maior espera/120 (teto 3) por aproximação, objetivo do supervisor (4; constante sem supervisor) | Mesmas fórmulas e escalas nos 3 cruzamentos |
| Ações 0/1 | Em todos os cruzamentos o slot de aproximação *j* é servido pela fase verde *1 − j* (`orientacao_canonica`) | Relação slot ↔ fase consistente |
| Orientação | O slot 0 é a Ribeirão Claro em Gomes de Carvalho e na Quatá, mas é a transversal em Casa do Ator (as aproximações aparecem em ordem alfabética do id da via) | **Incompatibilidade corrigida** (abaixo) |
| Recompensa | Mesma fórmula, −(fila + excesso)/100 por segundo. No treino do A_col (episódios > 100), por episódio: Gomes −132 ± 57, Casa do Ator −103 ± 22, Quatá −265 ± 46 | Mesma unidade e mesma ordem de grandeza (razão ≤ 2,6). Não foi normalizada por cruzamento, para não mudar o objetivo |

**Correção da orientação:**
- A visão de Casa do Ator permuta, antes da rede, os pares do vetor (filas, carros, fase one-hot e maior espera) e traduz a ação (`real = 1 − canônica`).
- No referencial canônico, nos 3 cruzamentos, **slot 0 = Ribeirão Claro (corredor)**, **ação 1 = verde do corredor** e **ação 0 = verde da transversal**.
- A tradução é uma bijeção entre as duas fases verdes do próprio programa. O controlador seguro recebe a ação real e continua impondo todas as regras.
- O replay guarda a ação **executada**, no referencial canônico. Isso foi testado: com a rede pedindo sempre a transversal, o número de ações 1 no replay (45) é igual ao número de intervenções do verde máximo (45).

## Orçamento: separar "compartilhar" de "treinar mais"

Com N agentes aprendizes (3 no C, 2 no C_transf), a rede compartilhada usa:

| | Modelo A (por rede) | Modelo C (rede compartilhada) |
|---|---|---|
| Transições guardadas por episódio | as de 1 cruzamento (cerca de 500) | as dos N cruzamentos (cerca de N × 500) |
| Passos de gradiente | 1 por transição, depois do aquecimento | **1 a cada N transições**, ou seja, **o mesmo número por rede que o Modelo A** |
| Replay | 50 mil | N × 50 mil (a mesma janela de tempo) |
| Aquecimento | 2000 transições | N × 2000 (começa no mesmo episódio) |
| ε de 1 → 0,05 | em 40 mil decisões do agente | em N × 40 mil decisões da rede (o mesmo ritmo por agente) |
| Rede-alvo | a cada 500 gradientes | a cada 500 gradientes |
| Interações com o simulador | 150 episódios | 150 episódios (as mesmas demandas 1001–1030, na mesma ordem) |

Assim a rede do C recebe **o mesmo número de atualizações** que cada rede do A, com lote 64, mas amostradas de dados dos 3 cruzamentos. O número total de passos de gradiente do C é 1/3 do total do A. As contagens reais ficam em `resultados/treinos/*/historico.jsonl` e `resumo_treino.json`.

## Experimento de transferência (C_transf)

- Durante o treino, só Gomes de Carvalho e Quatá alimentam o replay.
- Casa do Ator (`40278305`) é controlado por uma regra clássica simples (`regra_atuada_obs`: mantém o verde enquanto a aproximação servida tem veículos), com as mesmas regras de segurança. Ele **nunca** passa pela rede durante o treino.
- No teste, com os pesos congelados, a política controla os 3, inclusive Casa do Ator, que ela nunca viu.

## Sementes

| Uso | Sementes |
|---|---|
| Treino | 1001–1030 (`intenso_treino`, as mesmas do Modelo A) |
| Validação e seleção | 221–225 (`intenso_validacao`) |
| Teste A, moderada (1200 veículos/h) | 261–270 (`moderado_ps_teste`, novas) |
| Teste B, intensa (2000) | 251–260 (`intenso_ps_teste`, novas) |
| Teste C, saturada (2400) | 271–280 (`saturado_ps_teste`, novas) |

As sementes de teste foram conferidas por programa contra todas as já usadas (`resultados/sementes.json`). Os testes antigos (211–215, 231–235, 241–250) não foram usados.

## Reprodução

```bash
python -B -X utf8 semaforo/integracao_insper/parameter_sharing/testar_ps.py          # 18 verificações, ~5 min
python -B -X utf8 semaforo/integracao_insper/parameter_sharing/bateria_ps.py demandas
python -B -X utf8 semaforo/integracao_insper/parameter_sharing/bateria_ps.py treinar --processos 10   # ~2 h
python -B -X utf8 semaforo/integracao_insper/parameter_sharing/bateria_ps.py validar --processos 12  # ~20 min
python -B -X utf8 semaforo/integracao_insper/parameter_sharing/bateria_ps.py testar --processos 12   # uma vez, ~30 min
py -B -X utf8 semaforo/integracao_insper/parameter_sharing/relatorio_ps.py
```
