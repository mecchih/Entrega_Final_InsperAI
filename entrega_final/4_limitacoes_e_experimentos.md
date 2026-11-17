# Experimentos realizados e limitações

## Como os experimentos foram conduzidos

Os três ambientes seguem o mesmo protocolo.

1. **As mesmas regras de segurança para todos os controladores.** Amarelo de 3 s, vermelho geral de 2 s, verde mínimo de 10 s e decisão a cada 5 s. Os programas originais do SUMO mantêm as próprias regras.
2. **Treino, validação e teste separados por sementes de tráfego.** As sobreposições foram conferidas por programa no Insper.
3. **O checkpoint é escolhido pela validação**, nunca pelo teste e nunca pelo último episódio.
4. **Várias inicializações:** 3 redes por geração no cruzamento, 10 modelos no Cologne8 e 5 por configuração no Insper. A variabilidade é reportada entre modelos e entre demandas.
5. **Teste final uma única vez**, com as mesmas demandas para todos os controladores.
6. **Episódios inválidos** (travamento, teletransportes em excesso, viagens não concluídas) são registrados e não entram nas médias.

## Limitações gerais

- **Tudo é simulação no SUMO**, sem dados de contagem reais. Nada foi testado em campo.
- **Demanda:**
  - cruzamento: sintética, gerada por nós;
  - Cologne8: TAPAS, sintética derivada de dados de mobilidade;
  - Insper: sintética calibrada sobre a rede do OpenStreetMap.
- **Métricas por ambiente:** cada ambiente tem métricas próprias (espera da viagem no cruzamento e no Cologne8; espera no corredor no Insper). **Os números de ambientes diferentes não são comparáveis entre si.**
- **Treinos curtos:** 150 a 500 episódios. A amostra de sementes é pequena (5 a 10 modelos).
- **Sem pedestres e sem ônibus prioritários.** Bicicletas aparecem só como links da rede do Insper.

## Limitações por etapa

### Cruzamento sintético
- Os números históricos da dinâmica A têm um defeito de transição. Os resultados finais usam a dinâmica C.
- A DQN otimiza a fila total. A cauda (P95) da rua secundária melhorou na geração C, mas ainda fica acima do Webster no cenário girado.

### Cologne8
- **Na v4 (rede derivada com `contPos=0`)**, os contatos caíram para cerca de 0,3 por rodada em todos os controladores, mas não zeraram.
  - O MARL teve 30 contatos em 24 dos 100 testes, e 37 viagens pendentes em um teste.
  - A v4 não tem braço sem supervisor.
  - Os estados completos e os XMLs brutos de treino e validação ficaram fora do Git.
- Na v2 (rede original), as colisões existiam em todos os controladores (o SUMO só avisa, `collision.action=warn`). O MARL não as reduziu em relação ao Max-Pressure.
- O ganho do supervisor depende de um modelo que falhou na ablação. Não houve baseline independente treinado.
- A espera local piorou em 3 dos 8 cruzamentos.
- Os checkpoints estão em Git LFS. Alguns verificadores precisam de caminhos absolutos do computador onde o treino rodou.

### Insper
- **O programa original atuado venceu a IA** (15,48 contra cerca de 21 s). A IA só empata com um controle clássico submetido às mesmas restrições.
- O vermelho geral de 2 s e a decisão a cada 5 s não foram alterados. Seria preciso uma análise de segurança antes.
- O baseline "atuado com as regras do RL" é uma **aproximação** do atuado do SUMO, não uma reprodução.
- O Max-Pressure observa só a fila da faixa imediata. Não é o Max-Pressure clássico com pressão a jusante.
- A demanda sintética carrega pouco a Av. Hélio Pellegrino. Isso afeta especialmente a análise do quarto semáforo.
- O código do Insper chama `sumo.exe` e `sumo-gui.exe`, nomes de binário do Windows. Em Linux ou macOS é preciso trocar por `sumo` em `ambiente_marl_insper*.py`, `ambiente_quarto.py`, `avaliar_demanda_insper.py` e `insper_comum.py`.

## Trabalhos futuros

1. **Insper:**
   - Analisar a segurança das áreas de conflito para reduzir ou eliminar o vermelho geral.
   - Testar decisões a cada 1–2 s, que é a principal desvantagem estrutural.
2. **Calibrar a demanda com contagens reais**, da CET-SP ou de câmeras, principalmente na Hélio Pellegrino.
3. **Equidade:** uma recompensa que penalize a cauda (P95) e a espera local por cruzamento.
4. **Cologne8:**
   - Treinar um baseline de agentes independentes sem supervisor.
   - Investigar as colisões nas 3 junções que concentram 89% delas.
5. **Mais sementes e treinos mais longos**, só quando a validação ainda estiver melhorando.
6. **C5-B, antes de expandir para mais cruzamentos:**
   - Os mesmos 5 cruzamentos, com custo de troca de fase ou recompensa normalizada por cruzamento.
   - Opcionalmente, com a demanda recalibrada nos 2 novos.
   - O C5-A mostrou que o volume baixo e a recompensa sem custo de troca fazem a rede compartilhada trocar de fase à toa (`semaforo/integracao_insper/parameter_sharing/treinamento_c5/RELATORIO_TREINO_C5.md`).
