# Modelo C: Parameter Sharing Multi-Agent Double DQN — resultados

Desenho, compatibilidade da representação e orçamento estão em [LEIA-ME.md](LEIA-ME.md). Resumo do protocolo:
- 3 agentes com **uma** Double DQN, com rede online, rede-alvo e replay compartilhados;
- a mesma configuração do Modelo A otimizado (verde mínimo de 10 s, colisão atribuída);
- as mesmas 150 interações por treino e as mesmas demandas 1001–1030;
- **o mesmo número de passos de gradiente por rede que o Modelo A**;
- 5 sementes de modelo;
- seleção só na validação (221–225);
- testes uma única vez em demandas novas: moderada 261–270, intensa 251–260 e saturada 271–280.

Os testes foram feitos com os pesos congelados.

Tabelas completas: [`resultados/relatorio/tabela_ps.md`](resultados/relatorio/tabela_ps.md). Gráficos: `resultados/relatorio/ps_1..3_*.png`.

## Resumo

| Pergunta | Resposta |
|---|---|
| 1. Compartilhar melhora a eficiência do aprendizado? | **Com o mesmo número de atualizações por rede, não de forma clara.** As curvas de treino de C e A são praticamente idênticas. Na validação, o C foi melhor no 1º checkpoint (22,1 contra 25,8 s no episódio 25), mas oscilou depois. O C chega ao mesmo nível com **1 rede em vez de 3** (1/3 dos parâmetros) e **1/3 dos passos de gradiente totais**. |
| 2. A política compartilhada é competitiva com as DQNs independentes? | **Sim, na demanda de treino.** Validação: 20,36 ± 0,58 contra 20,88 ± 1,39 s, com menor variação entre sementes. Teste intenso não visto: 22,50 contra 21,76 s, Δ +0,74 ± 1,25 s (n.s.). |
| 3. Ela generaliza para outras demandas? | **Parcialmente.** Na moderada funciona e é melhor que o A (−0,81 s, 10/10 demandas), mas fica atrás do atuado com as mesmas regras (11,1 contra 10,2 s). **Na saturada falha em robustez:** 15 de 50 episódios travaram (2 dos 5 modelos travaram em 7/10 demandas), contra 1/50 do A e 1/10 do original. |
| 4. Ela transfere para um cruzamento que não participou do treino? | **Sim, com pequena perda.** Treinada só com Gomes de Carvalho e Quatá, a política controlou Casa do Ator com fila de 2,81 veículos, contra 2,67 do C completo, 2,54 do A e 3,02 do atuado com as mesmas regras. A espera no corredor ficou igual à do C completo: 22,59 contra 22,50 s. |
| Supera o original atuado? | **Não.** Nas demandas moderada e intensa, o original continua bem melhor (5,5 e 15,9 s). |

## 1. Orçamento e treino

| | A_col (por rede; 3 redes) | C (1 rede) | C_transf (1 rede) |
|---|---:|---:|---:|
| Episódios de interação | 150 × 5 sementes | 150 × 5 | 150 × 5 |
| Transições por agente | cerca de 68 mil | cerca de 68 mil (3 agentes) | cerca de 71 mil (2 agentes; Casa do Ator 0) |
| Passos de gradiente por rede | 63.700–67.500 | 65.200–67.100 | 69.300–69.800 |
| Total de gradientes por modelo | cerca de 197 mil (3 redes) | cerca de 66 mil | cerca de 70 mil |
| Episódios de treino inválidos | 5/750 | 10/750 | 1/750 |
| Tempo por episódio | cerca de 36 s | cerca de 38 s | cerca de 39 s |

- **Curvas de treino:** as de C e A coincidem (gráfico `ps_1`), porque o ritmo de exploração por agente é o mesmo.
- **C_transf no treino:** tem espera maior, porque Casa do Ator era controlado pela regra clássica simples durante o treino. Isso afeta só o treino, não o teste.

## 2. Validação (seleção)

Espera média no corredor (s), melhor checkpoint por semente de modelo, sementes 221–225:

| Braço | s1 | s2 | s3 | s4 | s5 | média ± dp |
|---|---|---|---|---|---|---|
| A: independentes | 19,55 (ep75) | 19,77 (ep50) | 21,57 (ep100) | 20,55 (ep125) | 22,93 (ep50) | 20,88 ± 1,39 |
| B: hierárquico, supervisor 15 s | 20,61 | 21,13 | 21,49 | 21,43 | 24,10 | 21,75 ± 1,36 |
| **C: parameter sharing** | 20,16 (ep75) | 20,11 (ep125) | 21,32 (ep150) | 19,82 (ep25) | 20,41 (ep100) | **20,36 ± 0,58** |
| C_transf | 20,81 (ep50) | 21,11 (ep75) | 21,74 (ep50) | 21,86 (ep125) | 19,98 (ep125) | 21,10 ± 0,76 |

- Todos os checkpoints escolhidos atendem aos critérios: 5/5 válidos, 0 violações e 0 colisões nos 3 cruzamentos.
- As sementes de modelo de A e C **não são pareadas**, porque inicializações diferentes não correspondem entre si. A comparação entre eles é feita pareando as demandas de teste.

## 3. Generalização (pesos congelados; 10 demandas novas por nível)

RL: média de 5 modelos ± dp entre modelos. Baselines: ± dp entre demandas. Só episódios válidos entram nas médias.

| Demanda | Original atuado | Atuado c/ regras do RL | A: independentes | C: parameter sharing | C − A (pareado por demanda) |
|---|---:|---:|---:|---:|---:|
| Moderada (1200/h) | **5,47** | 10,20 | 11,90 ± 1,41 | 11,09 ± 0,32 | **−0,81 ± 0,12 (10/10)** |
| Intensa não vista (2000/h) | **15,90** | 25,05 | 21,76 ± 1,27 | 22,50 ± 1,29 | +0,74 ± 1,25 (4/10) |
| Saturada (2400/h) | 42,19 (1/10 inválido) | 49,48 (1/10) | 48,04 (1/50) | *44,83 (15/50 inválidos)* | não comparável |

Na demanda intensa, o B (hierárquico) fez 22,67 ± 0,94 e o C_transf fez 22,59 ± 0,71.

**Saturada: a média do C não deve ser lida como melhor.**
- Os modelos C4 (checkpoint do episódio 25) e C5 (episódio 100) travaram a rede em 7 das 10 demandas cada. O critério de travamento é mais de 80% dos veículos parados por 300 s; esses episódios concluíram só 23–87% das viagens.
- Por isso, nesses dois modelos só sobraram as 3 demandas mais leves (33–36 s), e é isso que puxa a média do C para baixo.
- Os modelos C1–C3 completaram as 10 demandas (ou 9), com 44,0, 49,5 e 60,7 s, contra 44,5–52,4 s dos modelos do A.
- Conclusão: **a política compartilhada é menos robusta na saturação.** Um checkpoint escolhido cedo (episódio 25), ótimo na demanda intensa, falhou fora da distribuição de treino.

**Segurança nos testes:** 0 violações em 460 episódios e 0 colisões dentro dos 3 cruzamentos controlados (as colisões registradas são todas externas). Teletransportes:
- moderada: 0;
- intensa, no total de 50 episódios por braço: B 1, C 3, C_transf 5; original e A: 0;
- saturada: original 36, atuado 29, A 122, C 177, com a maioria nos episódios travados.

## 4. Transferência para um cruzamento não visto (demanda intensa não vista)

Fila média por cruzamento (veículos parados até 100 m):

| Controlador | Gomes de Carvalho | **Casa do Ator** | Quatá | Espera no corredor |
|---|---:|---:|---:|---:|
| Original atuado | 2,00 | 1,88 | 4,44 | 15,90 |
| Atuado c/ regras do RL | 3,33 | 3,02 | 6,76 | 25,05 |
| A: independentes (treinou em Casa do Ator) | 3,16 | 2,54 | 5,62 | 21,76 |
| C: parameter sharing (treinou nos 3) | 3,03 | 2,67 | 5,97 | 22,50 |
| **C_transf (nunca viu Casa do Ator)** | 2,98 | **2,81** | 6,01 | 22,59 |

- A política que nunca recebeu experiências de Casa do Ator, e que só chegou a ele pela representação canônica, controlou o cruzamento com **+0,14 veículo de fila** em relação ao C completo.
- Ela foi melhor que o controle clássico com as mesmas regras (3,02). O desempenho do corredor praticamente não mudou.
- Houve 1 travamento em 50 episódios (modelo 2, demanda 259).
- Ressalva: Casa do Ator tem a mesma estrutura dos outros dois (2 aproximações, 2 fases). A transferência foi para um cruzamento **compatível**, não para um cruzamento arbitrário.

## 5. Limitações

- 5 sementes de modelo e 10 demandas por nível.
- As sementes de A e C não são pareadas por inicialização.
- A eficiência foi comparada com o mesmo número de gradientes **por rede**. Não foi rodada a variante com 1 gradiente por transição (3× mais atualizações), para não confundir compartilhamento com mais treino.
- A recompensa não é normalizada por cruzamento: a Quatá tem recompensas cerca de 2× maiores.
- A demanda é sintética. Valem todas as limitações do Insper (vermelho geral de 2 s e decisão a cada 5 s).

## 6. Recomendação

- O Modelo C é **uma alternativa válida e competitiva** ao A: desempenho equivalente na demanda de treino, com 1/3 dos parâmetros e das atualizações.
- Ele é ligeiramente melhor na demanda moderada e **transfere** para um cruzamento compatível não visto.
- Ele **não** supera o original atuado e é **menos robusto na saturação**.
- Para a entrega, o modelo recomendado continua sendo o **A_col**. O Modelo C deve ser apresentado como **experimento de generalização e transferência**.

## Arquivos

- **Modelos selecionados:** `modelos_finais/C/` e `modelos_finais/C_transf/` (10 políticas, `manifesto.json`). Demonstração:
  ```bash
  python -B -X utf8 semaforo/integracao_insper/demo_insper.py --controle C --modelo 1
  ```
- **Dados:**
  - `resultados/validacao/braco_C*.json`;
  - `resultados/teste_generalizacao/teste_generalizacao.json`;
  - `resultados/treinos/*/historico.jsonl` e `resumo_treino.json`;
  - `resultados/sementes.json`.
- **Testes:** `testar_ps.py`, com 18/18 verificações OK antes do treino (`resultados/20261116T144154_testes/`).
