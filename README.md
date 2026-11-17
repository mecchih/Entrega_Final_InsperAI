# Semáforo Inteligente com Deep Reinforcement Learning

Projeto final do Insper AI: controle de semáforos com **Double DQN** e com uma arquitetura **Multi-Agent** (agentes locais e supervisor), avaliado em simulação no **SUMO** em três ambientes. Os ambientes têm demandas e métricas diferentes, e **seus resultados não são comparáveis entre si**.

## Entrega final

A documentação e os materiais utilizados na apresentação do projeto estão organizados na pasta [`entrega_final/`](entrega_final/README.md).

Nela, também estão disponíveis:

- **[Artigo científico (PDF)](entrega_final/artigos/)** — Localizado em `entrega_final/artigos/`. Contém a metodologia, os experimentos, os resultados e as conclusões da pesquisa.
- **[Apresentação final (PowerPoint)](entrega_final/apresentacao/)** — Localizada em `entrega_final/apresentacao/`. Contém os slides da apresentação final, incluindo a demonstração do simulador SUMO.

As demais tabelas, gráficos, análises e resumos de cada etapa do projeto também podem ser encontrados na pasta [`entrega_final/`](entrega_final/README.md).
## 1. Objetivo

Verificar se um agente que aprende por reforço consegue reduzir a espera dos veículos em relação aos controladores tradicionais (tempo fixo, Max-Pressure e o programa atuado do próprio cenário), sem violar regras de segurança. O caminho foi de um cruzamento isolado até redes reais.

## 2. Problema estudado

Um semáforo decide, a cada poucos segundos, qual movimento recebe verde. Cada troca custa tempo perdido (amarelo e vermelho geral). A melhor regra muda conforme o regime de trânsito:
- No cruzamento sintético, o verde mínimo ideal do Max-Pressure é de 10 s no trânsito normal e de 25 s na saturação.
- Uma regra fixa precisa escolher um regime e perde no outro.
- Em redes, as decisões de um cruzamento afetam os vizinhos (filas que transbordam e bloqueio da saída).

## 3. Por que Reinforcement Learning

- O agente observa o estado (filas, veículos, esperas, fase atual) e aprende por tentativa e erro qual decisão reduz a espera acumulada.
- Não é preciso dizer em que regime o trânsito está, nem calibrar parâmetros por cenário.
- A recompensa é negativa, proporcional à fila e à espera excessiva. Assim o agente aprende a minimizar o congestionamento no longo prazo, não só no próximo passo.

## 4. Como funciona a nossa Double DQN

- **Rede neural pequena:** MLP com entradas → 64 → 64 → ações (ReLU). As entradas são filas, veículos, fase, idade do verde e maior espera por aproximação. A saída é um valor Q por fase.
- **Double DQN:** a rede online escolhe a ação e a rede-alvo (atualizada a cada 500 passos) avalia. Isso reduz a superestimação dos valores Q.
- **Replay:** 50 mil transições, lote 64, Adam com taxa de aprendizado 5e-4, Huber, γ = 0,95^(dt/5). O desconto depende da duração real do intervalo (Semi-MDP).
- **Exploração:** ε de 100% → 5% (40 mil decisões).
- **Segurança fora da rede neural:** o agente só pede uma fase. Um controlador seguro impõe verde mínimo de 10 s, amarelo de 3 s, vermelho geral de 2 s e verde máximo condicional de 60 s. O replay guarda a ação **executada**.
- **Seleção do checkpoint pela validação**, nunca pelo teste.

## 5. Arquitetura Multi-Agent

- **Agentes locais:** uma Double DQN por semáforo, com pesos, replay e otimizador próprios. Cada um observa as próprias aproximações e o objetivo atual do supervisor.
- **Supervisor (modelo hierárquico):** uma Double DQN que observa a rede ou o corredor e decide a cada 30 s (ou 15 s) qual cruzamento priorizar, ou "equilibrado".
  - Ele não comanda fases.
  - Ele muda a observação dos locais e acrescenta à recompensa deles o custo do nó priorizado.
- **Modelo independente (só no Insper):** os mesmos agentes locais, sem supervisor.
- **Modelo C, Parameter Sharing (só no Insper):** os 3 agentes usam uma única Double DQN, com pesos, rede-alvo e replay compartilhados.
  - Cada agente observa o próprio cruzamento e decide sozinho.
  - A rede aprende com as experiências dos três cruzamentos, com o mesmo número de atualizações por rede que o modelo independente.

## 6. Ambientes

| Etapa | Ambiente | Controlado pela IA | Comparadores |
|---|---|---|---|
| A | Cruzamento sintético de 4 vias (`semaforo/rede/`) | 1 semáforo, 4 fases | Tempo fixo sem calibrar, Webster, Max-Pressure (ajuste único e teto por cenário) |
| (intermediária) | Cologne1 derivado (RESCO) | 1 semáforo, só inferência | — |
| B | **Cologne8** (RESCO / SUMO-RL 1.4.5; versão final v4 numa cópia derivada da rede) | 8 semáforos, mais o supervisor | Programa original, Max-Pressure; na rodada v2 também atuado calibrado, Webster, Max-Pressure por movimento, rede supervisionada, Q-learning tabular e MPC |
| C | **Insper** (OpenStreetMap, 14 semáforos) | 3 semáforos consecutivos na R. Ribeirão Claro | Programa original atuado, atuado com as regras do RL, Max-Pressure |

## 7. Origem dos dados

- **Cruzamento sintético:** rede e demanda criadas por nós (`semaforo/scripts/gerar_demanda.py`), com 4 cenários de 1570 a 2800 veículos/h e um cenário girado, nunca visto no treino.
- **Cologne8:** rede e demanda do benchmark RESCO, copiadas sem alteração do pacote SUMO-RL 1.4.5 (licença MIT; proveniência em `semaforo/referencias/`). A demanda vem do cenário TAPAS Cologne, **sintética**, derivada de dados de mobilidade: 2046 viagens das 07:00 às 08:00.
  - A versão final (v4) usa uma **cópia derivada** da rede, com `contPos=0` em 95 conexões, para que os veículos esperem a brecha antes de entrar no cruzamento (`semaforo/resultados/cologne8_corrigido/20261116_rede_sem_espera_interna_v2/`).
  - Usa também **demandas variadas** geradas a partir dos mesmos pares origem-destino: treino 100001–100500, validação 150001–150005, teste 170001–170010.
- **Insper:**
  - A rede foi exportada do **OpenStreetMap** pelo osmWebWizard (`semaforo/cenarios/insper/`).
  - **A demanda é sintética e calibrada por nós** (`semaforo/cenarios/insper_demanda/`; 2000 veículos/h no corredor no nível usado). **Não é uma medição real de trânsito.**

## 8. Estrutura do repositório

```
README.md                         este arquivo
entrega_final/                    material da apresentação: resumos, tabelas, gráficos, verificação e plano de commits
semaforo/
  LEIA-ME.md                      diário da Etapa A (histórico, dinâmica A)
  rede/  scripts/  modelos/       Etapa A: cruzamento sintético, DQN, avaliadores e modelos (.pt, ~25 kB)
  resultados/comparacao_*_C/      Etapa A: avaliações finais (dinâmica C)
  COLOGNE1.md, *COLOGNE1*.md      etapa intermediária Cologne1
  *COLOGNE8*.md                   Etapa B: protocolo, registro e análise
  TREINO_MARL_COLOGNE8_CONTINUO.md  Etapa B: histórico v2/v3 e a rodada final v4
  RESULTADOS_COMPARADORES_COLOGNE8.md, COMPARACAO_MPC_COLOGNE8.md, DEMO_VISUAL_COLOGNE8.md  comparadores e demonstração
  scripts/*marl*, *cologne8*      Etapa B: ambiente, agentes, treino, comparadores e verificação
  resultados/cologne8_corrigido/  Etapa B, versão final v4: rede derivada, auditorias, 10 modelos, teste e comparadores (políticas em Git LFS)
  resultados/piloto_supervisor_cologne8/  Etapa B: piloto pareado com e sem supervisor (v3)
  resultados/comparadores_cologne8/, mpc_cologne8/  Etapa B: comparadores calibrados e MPC (rodada v2)
  resultados/marl_cologne8/       Etapa B: rodadas v1/v2 (checkpoints e tripinfo em Git LFS)
  resultados/pacotes_registros_cologne8/  registros detalhados da v2 compactados (.tar.xz)
  referencias/                    arquivos de origem do RESCO/SUMO-RL com SHA-256
  cenarios/insper/                Etapa C: cenário OpenStreetMap original (não modificado)
  cenarios/insper_demanda/        Etapa C: demandas sintéticas calibradas (treino, validação e teste)
  integracao_insper/              Etapa C: ambiente, controle seguro, treino, avaliação e relatórios
    otimizacao_final/             experimentos finais e RELATORIO_OTIMIZACAO.md
    quarto_semaforo/              investigação do 4º semáforo (sem expansão)
    parameter_sharing/            Modelo C: DQN compartilhada, generalização e transferência (RELATORIO_PS.md)
      experimento_c5/             zero-shot C3 → C5, sem treino (RELATORIO_C5.md)
      treinamento_c5/             C5 treinado do zero com 5 agentes (RELATORIO_TREINO_C5.md)
    modelos_finais/               30 políticas do teste final e manifesto.json
    ARTEFATOS_LOCAIS.md           o que fica fora do Git (episódios, buffers) e por quê
  requirements-*.txt              versões usadas
```

## 9. Instalação

- **SUMO 1.28.0**, com a variável `SUMO_HOME` apontando para a instalação: https://sumo.dlr.de.
- **Python 3.12.** O Cologne8 foi treinado com 3.12; o Insper rodou no Anaconda 3.12 com torch 2.14.

```bash
pip install -r semaforo/requirements-marl-cologne8.txt   # torch (CPU), numpy, traci, sumolib, libsumo, matplotlib
```

Alternativa mínima: `pip install torch numpy traci sumolib libsumo matplotlib`.

Observações:
- O código do Insper usa os binários do Windows (`sumo.exe`, `sumo-gui.exe`); em Linux ou macOS veja `entrega_final/4_limitacoes_e_experimentos.md`.
- Os checkpoints do Cologne8 estão em **Git LFS** (cerca de 6.600 objetos, quase todos do histórico v1/v2 em `resultados/marl_cologne8/`).
  - Rode `git lfs install` uma vez.
  - Para não baixar o histórico pesado, clone sem LFS e busque só as políticas da versão final:

    ```bash
    GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/mecchih/Entrega_Final_InsperAI.git
    cd Entrega_Final_InsperAI
    git lfs pull --include="semaforo/resultados/cologne8_corrigido/**/*.pt"   # 45 políticas da v4 e 1 estado de ensaio, cerca de 18 MB
    ```

  - Políticas da v2: veja `entrega_final/2_cologne8.md`.
  - Os modelos do cruzamento sintético e do Insper são arquivos Git normais e já vêm no clone.
- **Ambientes:** o Cologne8 v4 e o comparador MPC usam ambientes Python próprios.
  - Cologne8 v4: `semaforo/requirements-marl-cologne8.txt`.
  - MPC: `semaforo/requirements-mpc-cologne8.txt`.
  - Os comandos dos documentos supõem `.venv-dqn-inferencia` e o SUMO em `../tools/sumo-win64-1.28.0`; ajuste `--sumo-home` à sua instalação.

## 10. Como executar as avaliações

Rode na raiz do repositório, salvo indicação contrária.

**Etapa A, cruzamento sintético.** Os scripts rodam dentro de `semaforo/scripts`.

```bash
cd semaforo/scripts
python visualizar_dqn.py --listar                                         # modelos e controladores disponíveis
python visualizar_dqn.py --modelo dqn_fila_excesso_17_C_seed0 --cenario girado   # demonstração no SUMO-GUI
python avaliar_17.py --saida ../resultados/reavaliacao_17_C                # reavalia as gerações (pasta nova; não sobrescreve)
```

**Etapa B, Cologne8.** O retreino não é necessário; os resultados ficam em JSON versionado.

```bash
python -B -X utf8 semaforo/scripts/treinar_cologne8_corrigido.py --saida semaforo/resultados/cologne8_corrigido/20261116_10sementes_500ep_v4_retomada_final --status   # situação da rodada v4
python -B -X utf8 semaforo/scripts/demo_visual_cologne8.py --sumo-home <pasta do SUMO 1.28>   # 3 janelas: tempo fixo × rede que copia × MARL (v2; requer as políticas v2 via LFS)
python -B semaforo/scripts/restaurar_registros_cologne8.py --verificar     # confere os 70 pacotes de registros (sem LFS)
python -B semaforo/scripts/testar_registros_cologne8.py                     # testes unitários dos pacotes
```

**Etapa C, Insper.**

```bash
python -B -X utf8 semaforo/integracao_insper/testar_controle_seguro_insper.py            # testes do controlador seguro (sem SUMO)
python -B -X utf8 semaforo/integracao_insper/demo_insper.py --controle A_col --modelo 1 --sem-gui --limite 900   # verificação rápida
python -B -X utf8 semaforo/integracao_insper/demo_insper.py --controle original          # SUMO-GUI, programa original
python -B -X utf8 semaforo/integracao_insper/demo_insper.py --controle A_col --modelo 1  # SUMO-GUI, MARL recomendado
python -B -X utf8 semaforo/integracao_insper/otimizacao_final/bateria_otimizacao.py comparar --bracos A_col B_col_s15   # comparação pareada na validação (só leitura)
```

A reprodução completa, que leva horas, está em `semaforo/integracao_insper/otimizacao_final/RELATORIO_OTIMIZACAO.md`, seção 10.

## 11. Principais resultados

Cada tabela usa a métrica do seu ambiente. Não compare números entre tabelas.

**Etapa A: cruzamento sintético** (dinâmica corrigida; espera média em s; 10 sementes de teste; cada geração = média de 3 redes)

| Controlador | equilibrado | assimétrico | pico | saturado | girado (nunca visto) |
|---|---:|---:|---:|---:|---:|
| Tempo fixo (Webster) | 28,7 | 33,7 | 52,1 | 93,7 | 35,4 |
| Max-Pressure teto por cenário | 24,7 | 24,7 | 26,6 | 73,6 | 33,0 |
| **DQN geração C** (17 entradas) | **22,7** | **20,7** | **22,8** | **63,7** | **22,1** |

A DQN superou os controladores tradicionais na espera média em todos os cenários, inclusive no girado, que nunca viu no treino.

**Etapa B: Cologne8, versão final v4** (rede derivada e demandas variadas reservadas; 100 testes = 10 modelos × 10 demandas; comparadores com 10 rodadas)

| Métrica | MARL v4 + supervisor | Max-Pressure | Programa original (na rede derivada) |
|---|---:|---:|---:|
| Espera média da viagem (s) | **18,44** | 22,82 | 39,03 |
| Média dos P95 (s) | **69,84** | 76,32 | 126,54 |
| Contatos (colisões) por rodada | 0,30 | 0,50 | 0,30 |
| Viagens não concluídas por rodada | 0,37 | 0 | 0 |

- Espera 19,2% menor que o Max-Pressure e 52,8% menor que o programa original.
- Na rede derivada, os contatos caíram para cerca de 0,3 por rodada (a v2, com outra rede e demanda, tinha cerca de 18). Mesmo assim, houve 30 contatos em 24 dos 100 testes, e 37 viagens ficaram pendentes em um teste.
- A v4 não tem braço sem supervisor.
  - No piloto pareado v3 (3 inicializações), o supervisor reduziu a espera em 5,7%: 14,37 contra 15,23 s.
- Fonte: `semaforo/TREINO_MARL_COLOGNE8_CONTINUO.md` e `resultados/cologne8_corrigido/20261116_10sementes_500ep_v4_retomada_final/ANALISE.json`.

*Histórico, rodada v2* (rede original e demanda única; não comparável com a v4):

| Espera média (s) | MARL v2 | atuado calibrado | Max-Pressure por movimento | Max-Pressure | rede supervisionada | Q-learning tabular | original | MPC adaptado |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| | **9,29** | 11,98 | 14,45 | 15,83 | 16,60 | 28,80 | 30,52 | 38,65 |

- Na v2, as colisões (cerca de 17 a 30 por rodada) aconteciam em todos os controladores.
- Fontes: `semaforo/RESULTADOS_COMPARADORES_COLOGNE8.md` e `semaforo/COMPARACAO_MPC_COLOGNE8.md`.

**Etapa C: Insper** (teste inédito com as sementes 241–250; espera média no corredor dos 3 cruzamentos)

| Controlador | Espera no corredor (s) |
|---|---:|
| **Programa original atuado (SUMO)** | **15,48** |
| MARL independente recomendado (A_col) | 21,49 ± 1,32 |
| MARL hierárquico (supervisor 15 s) | 21,84 ± 0,48 |
| Controle atuado com as mesmas restrições do RL | 22,25 |

**Modelo C, Parameter Sharing** (uma única Double DQN para os 3 agentes; experimento adicional):
- Na validação fez 20,36 s, contra 20,88 s do A, com 1/3 dos parâmetros.
- Nas demandas novas foi competitivo: moderada 11,1 contra 11,9 s; intensa 22,5 contra 21,8 s.
- Funcionou em um cruzamento que não participou do treino.
- Travou em 15 de 50 episódios na demanda saturada (`semaforo/integracao_insper/parameter_sharing/RELATORIO_PS.md`).
- **C5:** a mesma DQN compartilhada foi treinada do zero com 5 agentes (o corredor mais Fiandeiras × Clodomiro e × Atílio Innocenti).
  - Foi segura, mas não superou os pesos do C3 aplicados sem retreino: 9,60 contra 9,79 s nos 5 cruzamentos, diferença não significativa.
  - Piorou o cruzamento de menor volume (`.../treinamento_c5/RELATORIO_TREINO_C5.md`).

**No Insper, o programa original atuado foi superior à IA** em todas as 10 demandas de teste. A IA só empata com um controle clássico submetido às mesmas restrições de segurança. O vermelho geral de 2 s e a decisão a cada 5 s pesam mais do que a coordenação. As otimizações finais (verde de 5 s, recompensa de colisão corrigida, supervisor de 15 s) e a expansão para um 4º semáforo não mudaram esse quadro.

Detalhes, variabilidade e ressalvas: `entrega_final/`.

## 12. Limitações e trabalhos futuros

- Tudo é simulação, sem dados reais de contagem. A demanda do Insper é sintética.
- As métricas e as demandas de cada ambiente são diferentes.
- Os treinos são curtos e as amostras de sementes são pequenas (3 a 10 modelos por configuração).
- **Cologne8:**
  - a rede derivada da v4 reduziu muito os contatos, mas não os eliminou: 30 contatos em 24 dos 100 testes, e 37 viagens pendentes em um teste;
  - a v4 não tem braço independente;
  - o efeito do supervisor só foi medido no piloto v3, com 3 inicializações;
  - a espera local piorou em parte dos cruzamentos (v2 e piloto v3);
  - os XMLs brutos de treino e validação e os estados completos da v4 ficaram fora do Git (índice com SHA-256 em `resultados/cologne8_corrigido/PACOTE_GIT_20261116.json`).
- **Insper:**
  - as regras operacionais (vermelho geral de 2 s, decisão a cada 5 s) colocam a IA em desvantagem estrutural;
  - removê-las exige uma análise de segurança.
- **Trabalhos futuros:**
  - calibrar a demanda com contagens reais;
  - estudar a segurança para reduzir o vermelho geral e o intervalo de decisão;
  - criar uma recompensa com equidade (P95 por aproximação);
  - treinar um braço independente na v4 do Cologne8 e investigar os contatos residuais.

Lista completa: [`entrega_final/4_limitacoes_e_experimentos.md`](entrega_final/4_limitacoes_e_experimentos.md).
