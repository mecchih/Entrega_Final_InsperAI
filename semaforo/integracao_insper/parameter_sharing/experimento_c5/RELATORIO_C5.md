# Experimento zero-shot C3 → C5

**Pergunta:** a Double DQN compartilhada do Modelo C, treinada só com os 3 cruzamentos da Ribeirão Claro, consegue controlar 5 cruzamentos, incluindo 2 que nunca viu, **sem mudar os pesos**?

**Resposta curta:**
- Ela **controla** os 5 com segurança e com decisões válidas.
- Ela **não piora** de forma significativa o corredor nem a rede.
- Nos dois cruzamentos novos ela é **pior** que o programa original e que um controle clássico com as mesmas regras: troca de fase demais em cruzamentos com pouco tráfego.
- Houve transferência **funcional**, não **eficiente**.
- A demanda disponível nos novos cruzamentos é baixa (65 e 363 veículos por episódio), o que limita as conclusões.

Nada foi treinado: o hash dos pesos é idêntico antes e depois, há 0 passos de gradiente e o replay não é usado. Os Modelos A, B e C, o Cologne8, os cenários, as demandas existentes e os resultados históricos não foram alterados. Nada foi commitado.

## 1. Arquivos

| Arquivo | Função |
|---|---|
| `ambiente_c5.py` | Cópia da v2 com `controlados=` e `medidos=` configuráveis (detalhes abaixo). Com os padrões, reproduz exatamente a v2 (testado). |
| `adaptador_c5.py` | Mapeamento canônico **derivado da rede** para cada cruzamento e `VisaoC5` (rede congelada; recusa treino e replay) |
| `testar_c5.py` | 17 verificações |
| `bateria_c5.py` | Demandas novas, piloto e avaliação final |
| `relatorio_c5.py` | Tabela e gráficos (`resultados/relatorio/`) |

O que mudou em `ambiente_c5.py` em relação à v2:
- Pontos onde a v2 assumia 3 cruzamentos e que agora seguem as listas: controladores seguros, proteção de escrita, verificadores, conflitos, áreas de observação (com checagem de sobreposição), colisões, recompensas, "outros" (14 − controlados), encerramento e registro.
- **A métrica do corredor e o bloqueio da saída continuam restritos aos 3 originais**, para comparar com os resultados anteriores.
- Novas métricas: por cruzamento (espera por veículo, fila, número de veículos, colisões) e fila por aproximação.
- A observação local é a base de 9 entradas do cruzamento mais o código "sem supervisor" [1, 0, 0, 0], que é exatamente o que o Modelo C viu.

## 2. Observações e ações (referencial canônico)

O referencial canônico tem quatro regras:
- slot 0 = via principal;
- slot 1 = transversal;
- na fase one-hot, a posição 1 = verde da via principal;
- **ação canônica 1 = verde da via principal; ação 0 = verde da transversal.**

A via principal é a Ribeirão Claro nos 3 originais e a Rua Fiandeiras nos 2 novos (a via de maior volume em cada um). A transformação é calculada a partir do programa e das ligações de cada semáforo:

| Cruzamento | Via principal | Slot da principal | Fase real que a serve | Transformação | Ação canônica 1 → fase real |
|---|---|---:|---:|---|---:|
| 476455095 Gomes de Carvalho | Ribeirão Claro | 0 | 1 | identidade | 1 |
| 40278305 Casa do Ator | Ribeirão Claro | 1 | 0 | troca slots e fases | 0 |
| 40278183 Quatá | Ribeirão Claro | 0 | 1 | identidade | 1 |
| 300058973 Fiandeiras × Clodomiro | Fiandeiras | 0 | 1 | identidade | 1 |
| **302806060 Fiandeiras × Atílio Innocenti** | Fiandeiras | 0 | **0** | **troca só a fase one-hot e a ação** | **0** |

- A normalização é a mesma para todos: fila/25, carros/35, idade do verde/60 (teto 2), maior espera/120 (teto 3).
- Cada agente vê só a própria área de 100 m. O ambiente recusa áreas sobrepostas e não houve nenhuma.

## 3. Testes (`testar_c5.py`): 17/17 OK

Saída em `resultados/20261116T181057_testes/`.

| Verificação | Resultado |
|---|---|
| Mapeamento derivado da rede (tabela acima) | OK |
| Para os 3 originais, a transformação é idêntica à do Modelo C | OK |
| `302806060`: só a fase e a ação invertidas; `300058973`: identidade | OK |
| A observação canônica do `302806060` mostra o verde real da fase 0 como verde da principal | OK |
| **Semântica no SUMO** (TraCI e controlador seguro): ação canônica 1 deixa verde **só** a via principal e 0 deixa verde **só** a transversal, nos 5 cruzamentos; 0 violações; os outros 9 no programa original | OK (10/10 combinações) |
| `ambiente_c5` com os 3 originais reproduz **exatamente** a v2 (mesmo checkpoint), medindo ou não os 2 novos | OK |
| Os 5 agentes usam o mesmo objeto de rede | OK |
| 13 entradas finitas por decisão | OK (160, 152, 166, 149 e 214 decisões) |
| Observações diferentes entre os 5 | OK |
| Ações diferentes entre agentes | OK |
| Pesos idênticos antes e depois (SHA-256 `97c121e79252…`), 0 gradientes, replay vazio | OK |
| Segurança nos 5: verde ≥ 10 s, amarelo 3 s, vermelho geral 2 s, sem conflitos | OK |
| Os outros 9 semáforos no programa original | OK |
| Métricas por cruzamento registradas | OK |
| `sumo.log` sem erros | OK |
| Original medindo os 5: 14 semáforos intactos e corredor igual ao da medição sem os novos | OK |
| Cenário inalterado (SHA-256) | OK |

**Problema encontrado e corrigido no próprio teste:**
- Na primeira execução, o teste de semântica acusou 5 "violações", e as 10 combinações estavam corretas.
- Eram artefatos do verificador do teste, criado no instante da assunção do controle, quando ele não conhece a duração do verde e do amarelo em curso. É o mesmo defeito já corrigido no ambiente.
- O verificador do teste passou a observar desde t = 0. A execução falha está arquivada em `resultados/_falhou_verificador_criado_na_assuncao_*`.

## 4. Checkpoints, demandas e sementes

- **Checkpoints:** os 5 finais do Modelo C, sem nova seleção: `../modelos_finais/C/s1_ep0075.pt`, `s2_ep0125.pt`, `s3_ep0150.pt`, `s4_ep0025.pt` e `s5_ep0100.pt`. O mesmo checkpoint é usado em C3 e em C5.
- **Demanda:** intensa (2000 veículos/h no corredor), com o mesmo gerador do nível intenso. Sementes **novas 291–300** (`semaforo/cenarios/insper_demanda/intenso_c5_teste/`), conferidas contra 117 sementes já usadas (`resultados/sementes.json`). A demanda não foi alterada.
- **Piloto:** 1 checkpoint × 2 sementes (`resultados/20261116T181232_piloto/`). **Avaliação final:** 5 checkpoints × 10 sementes × (C3, C5), mais original e 2 diagnósticos, num total de 130 episódios (`resultados/avaliacao_final/avaliacao_c5.json`).
- **Diagnósticos:** "atuado com as regras do RL" nos 3 e nos 5, para separar o efeito das regras operacionais do efeito da política.

## 5. Resultados

RL: média dos 5 checkpoints ± dp entre checkpoints. Original: ± dp entre as 10 demandas. Tabela completa em `resultados/relatorio/tabela_c5.md`.

| Métrica | Original | C3 | **C3 → C5** | Atuado c/ regras RL nos 5 (diagnóstico) |
|---|---:|---:|---:|---:|
| Espera média no corredor original (s por veículo do corredor) | **15,06** | 20,34 ± 1,06 | 20,59 ± 1,17 | 21,72 |
| Espera média na rede (s por viagem) | **40,93** | 45,60 ± 1,15 | 45,95 ± 1,12 | 46,76 |
| P95 da espera no corredor (s) | **50,5** | 56,6 | 57,4 | 62,6 |
| P95 da espera na rede (s) | **120,4** | 123,4 | 123,1 | 126,5 |
| Espera nos 2 cruzamentos novos (s por veículo, ponderada) | 1,52 | 1,61 | **2,18 ± 0,37** | **1,04** |
| Fiandeiras × Clodomiro (s/veículo; 363 veículos por episódio) | 1,58 | 1,70 | 2,00 | 1,08 |
| Fiandeiras × Atílio Innocenti (s/veículo; **65 veículos por episódio**) | 1,16 | 1,15 | 3,12 ± 1,32 | 0,81 |
| Viagens concluídas (mínimo) | 1,000 | 0,551* | 0,626* | 1,000 |
| Colisões (total / nos 5 cruzamentos) | 0 / 0 | 3 / 0 | 1 / 0 | 0 / 0 |
| Teletransportes | 0 | 5 | 3 | 0 |
| Episódios travados | 0/10 | 1/50* | 1/50* | 0/10 |
| Violações de segurança | 0 | 0 | 0 | 0 |

\* O mesmo checkpoint (C s4, episódio 25) travou na mesma demanda (293) em C3 **e** em C5. Essa falha já existia nos 3 cruzamentos; não foi causada pela expansão. É o mesmo modelo que já tinha se mostrado frágil na demanda saturada.

**Comparações pareadas por demanda** (média dos 5 checkpoints em cada demanda; IC95 com t de 9 graus de liberdade):

| Δ (C5 − C3) | Média | IC95 | Demandas em que o C5 melhora |
|---|---:|---:|---:|
| Corredor original | +0,33 s | ±1,26 | 4/10 |
| Rede inteira | +0,41 s | ±1,14 | 5/10 |
| Gomes / Casa do Ator / Quatá | +0,28 / +0,06 / +0,18 s | ±0,63 / ±0,42 / ±0,91 | 4 / 4 / 6 de 10 |
| **2 cruzamentos novos** | **+0,55 s** | **±0,16** | **0/10** |
| Fiandeiras × Clodomiro | +0,29 s | ±0,17 | 1/10 |
| Fiandeiras × Atílio Innocenti | +1,96 s | ±0,59 | 0/10 |

**Por que piora nos novos:** o C5 troca de fase muito mais que o controle clássico.
- Fiandeiras × Clodomiro: 127 trocas por episódio, contra 48.
- Fiandeiras × Atílio Innocenti: 60 trocas, contra 37.
- Cada troca custa 5 s de amarelo mais vermelho geral. Em cruzamentos quase vazios (fila média de 0,02–0,20 veículo), isso aumenta a espera da via principal: a fila na Fiandeiras do `302806060` foi de 0,049, contra 0,012 no original.
- A política aprendeu com aproximações carregadas e alterna demais quando há pouco tráfego. O mesmo efeito já tinha aparecido no Modelo C na demanda moderada.

**Unidades de cada métrica:**
- corredor: por veículo que entrou nos 3 cruzamentos originais;
- rede: por viagem;
- cruzamento: por veículo que entrou naquele cruzamento;
- fila: por cruzamento, média no tempo.

O número de veículos de cada conjunto é o mesmo entre os controles (±1 veículo; tabela completa), então as médias comparam os mesmos veículos.

## 6. Respostas

1. **A política de 3 controlou 5 sem retreino?** Sim, tecnicamente: 130 episódios, decisões em todos os 5 cruzamentos, 0 erros e 0 violações.
2. **Os dois novos agentes decidiram de forma válida?** Válida, sim: a ação correta foi executada (semântica testada no SUMO) e houve 0 violações. Eficiente, não: há trocas demais.
3. **O controle permaneceu seguro?** Sim:
   - 0 violações, 0 colisões nos 5 cruzamentos, e os outros 9 semáforos ficaram no programa original;
   - a única colisão do C5 foi externa;
   - o único travamento (s4/293) ocorre igualmente no C3.
4. **Espera nos novos cruzamentos?** **Piorou**: +0,55 s por veículo, pior em 10/10 demandas. Ficou pior que o original e pior que o clássico com as mesmas regras (que, por sua vez, melhora o original nesses cruzamentos).
5. **Espera nos três originais?** Não mudou de forma significativa: diferenças de +0,06 a +0,28 s, com ICs que contêm zero.
6. **Espera na rede?** Sem mudança significativa: +0,41 ± 1,14 s.
7. **Consistência entre os 5 checkpoints?**
   - Nos novos cruzamentos, sim: **todos** os 5 pioram (de +0,07 a +1,09 s nos dois juntos; de +0,30 a +3,23 s no Atílio Innocenti).
   - No corredor, o sinal varia entre checkpoints (de −0,91 a +1,64 s).
8. **A demanda permite uma conclusão confiável?** Só em parte.
   - O `302806060` recebe só cerca de 65 veículos por episódio, com fila média de 0,02–0,06. Diferenças de 1–3 s por veículo envolvem poucos veículos.
   - O `300058973` recebe 363 veículos, mas a fila também é baixa.
   - A conclusão de que a política "troca demais em baixa demanda" é consistente. **Não há como avaliar** o comportamento desses cruzamentos sob carga sem recalibrar a demanda.
9. **Houve transferência de política?** **Transferência funcional, sim**: segura, sem degradar o corredor e operando cruzamentos não vistos. **Transferência eficiente, não**: nos cruzamentos novos ela fica abaixo do clássico com as mesmas regras e do original. Não se pode afirmar que a política "generaliza bem" para eles.
10. **Vale treinar um C5?** Só junto com uma **demanda recalibrada** que carregue Fiandeiras, Clodomiro e Atílio Innocenti. Com a demanda atual, os novos cruzamentos dão pouco sinal de aprendizado, e o clássico já é quase ótimo neles. Como próximo passo, faz mais sentido um C4 com o `300058973`.

## 7. Reprodução

```bash
python -B -X utf8 semaforo/integracao_insper/parameter_sharing/experimento_c5/testar_c5.py           # 17 verificações, ~6 min
python -B -X utf8 semaforo/integracao_insper/parameter_sharing/experimento_c5/bateria_c5.py demandas  # sementes 291-300
python -B -X utf8 semaforo/integracao_insper/parameter_sharing/experimento_c5/bateria_c5.py piloto --processos 10
python -B -X utf8 semaforo/integracao_insper/parameter_sharing/experimento_c5/bateria_c5.py avaliar --processos 12   # ~12 min, uma vez
py -B -X utf8 semaforo/integracao_insper/parameter_sharing/experimento_c5/relatorio_c5.py
```

Demonstração no SUMO-GUI: não foi adicionada ao `demo_insper.py`, para não modificar um script de demonstração que já funciona. Para ver o C5, rode um episódio de `bateria_c5.tarefa` trocando o binário por `sumo-gui`.

## 8. Gráficos

- `resultados/relatorio/c5_1_original_c3_c5.png`: corredor, rede, P95 e novos cruzamentos.
- `resultados/relatorio/c5_2_por_cruzamento.png`: espera e fila nos 5 cruzamentos, com o número de veículos de cada.
