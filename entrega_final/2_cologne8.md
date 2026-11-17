# Etapa B — Multi-Agent no Cologne8

## Versão final: v4 (16/11/2026)

Fonte principal: `semaforo/TREINO_MARL_COLOGNE8_CONTINUO.md`, seções "Nova rodada após auditoria — v4" a "Limpeza autorizada".

### Por que houve uma v4

- Na v2, todos os controladores colidiam, inclusive o programa original: cerca de 18 a 30 contatos por rodada.
- A auditoria mostrou carros parados na espera interna do cruzamento invadindo a trajetória prioritária.
- **Correção:** uma **cópia derivada** da rede, gerada pelo netconvert 1.28 com `contPos=0` em 95 conexões. O veículo espera a brecha antes de entrar.
  - A rede mantém os 8 TLS, a topologia externa e os 103 movimentos controlados.
  - As fases foram remapeadas pela identidade real de cada movimento.
  - Pasta: `semaforo/resultados/cologne8_corrigido/20261116_rede_sem_espera_interna_v2/`.
- **Demandas variadas** com os mesmos pares origem-destino: treino 100001–100500, validação 150001–150005, teste reservado 170001–170010.

### Desenho

- **Agentes:** 8 Double DQN locais (entradas 26/24/22/26/22/18/22/26; 2 a 4 ações reais) e 1 supervisor 176 → 64 → 64 → 9.
- **Colisão:** punição de −10.000 por contato.
  - O supervisor recebe sempre.
  - Cada local recebe só quando o contato acontece na sua área.
  - Todas as recompensas são divididas por 1000 antes do replay.
- **Treino:** 10 inicializações × 500 episódios, com validação a cada 25 episódios.
- **Seleção, só pela validação:** primeiro menos viagens pendentes, depois menos contatos, depois menor espera mais atraso de inserção.
- **Segurança:** a mesma (verde mínimo de 10 s, amarelo de 3 s, vermelho geral de 2 s, verde máximo condicional de 60 s, `collision.action=warn`).

### Resultado no teste reservado

100 rodadas MARL = 10 modelos × 10 demandas. Comparadores: 10 rodadas cada.

| Métrica | MARL v4 + supervisor | Max-Pressure | Programa original (rede derivada) |
|---|---:|---:|---:|
| Espera média da viagem (s) | **18,44** | 22,82 | 39,03 |
| Média dos P95 (s) | **69,84** | 76,32 | 126,54 |
| Fila média (veículos) | **10,02** | 12,70 | 21,11 |
| Atraso de inserção (s) | **2,53** | 6,32 | 4,64 |
| Contatos por rodada | 0,30 | 0,50 | 0,30 |
| Viagens não concluídas por rodada | 0,37 | 0 | 0 |

Fonte: `semaforo/resultados/cologne8_corrigido/20261116_10sementes_500ep_v4_retomada_final/ANALISE.json` (6100 simulações MARL e 20 comparadores conferidos).

- **Espera:** 19,2% menor que o Max-Pressure e 52,8% menor que o programa original.
- **Contatos e pendências:** houve 30 contatos em 24 dos 100 testes MARL, e 37 viagens ficaram pendentes em um teste (modelo 0, demanda 2). Os comparadores concluíram todas as viagens.
- **Supervisor:** a v4 não tem braço sem supervisor.
  - O piloto pareado v3 (3 inicializações × 100 episódios, `resultados/piloto_supervisor_cologne8/20261115_pareado_3x100_reinicio/`) mediu 14,37 s com supervisor contra 15,23 s sem ele (−5,7%).
  - A amostra é pequena, e a espera local piorou em 14 de 25 entradas.
- **Comparabilidade:** os números da v4 não são comparáveis com a v2. Rede, demanda, punição e seleção mudaram.

### Modelos da v4

- **Políticas selecionadas (episódio por modelo 0–9):** 300, 150, 425, 275, 400, 450, 200, 500, 450 e 175.
  - Lista com SHA-256: `semaforo/resultados/cologne8_corrigido/PACOTE_GIT_20261116.json` (`politicas_v4_selecionadas`).
  - Os arquivos `seedN/politica_epXXXX.pt` ficam nas raízes `20261116_10sementes_500ep_v4/` (modelos 0–6) e `20261116_130813_10sementes_500ep_v4_retomada/` (modelos 7–9).
- **Git LFS:** as 45 políticas da v4 estão em Git LFS (cerca de 15 MB) e disponíveis no servidor:
  ```bash
  git lfs pull --include="semaforo/resultados/cologne8_corrigido/**/*.pt"
  ```
- **Fora do Git:** os estados completos de retomada (`estado_ep*.pt`) e os XMLs brutos de treino e validação ficaram no computador onde a rodada foi executada, com caminho, tamanho e SHA-256 no mesmo índice.
- **Proveniência:** os JSON da v4 preservam os caminhos absolutos da máquina de origem. Não os edite, para não quebrar os hashes.
- **Situação e reprodução:** `semaforo/scripts/treinar_cologne8_corrigido.py --status` e os comandos em `TREINO_MARL_COLOGNE8_CONTINUO.md`.

### Comparadores extras (rodada v2, mesmo executor)

Branch `experimento/comparadores-cologne8`; detalhes em `semaforo/RESULTADOS_COMPARADORES_COLOGNE8.md`.

| Espera média (s), sementes 1–10 | MARL v2 | atuado calibrado | MP por movimento | MP por faixa | rede supervisionada | Q-learning tabular | original | Webster |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| | **9,29** | 11,98 | 14,45 | 15,83 | 16,60 | 28,80 | 30,52 | 43,32 |

- O **MPC adaptado** (Information-Region MPC, só o modelo central) fez 38,65 s (`semaforo/COMPARACAO_MPC_COLOGNE8.md`).
- **Demonstração visual** com 3 janelas do SUMO-GUI (tempo fixo × rede que copia × MARL): `semaforo/DEMO_VISUAL_COLOGNE8.md`.

---

## Histórico: rodada v2 (13/11/2026)

As seções abaixo descrevem a rodada anterior, na rede original do RESCO. Ela continua versionada e documentada.

## O ambiente

- **Cologne8**, do benchmark RESCO, com os arquivos do pacote oficial SUMO-RL 1.4.5 (licença MIT).
- Proveniência e SHA-256 em `semaforo/referencias/cologne8_sumo_rl_1.4.5/proveniencia.json`.
- São 8 semáforos de uma região de Colônia (Alemanha), com 2046 viagens de carro entre 07:00 e 08:00 e mais até 1200 s de escoamento.
- A demanda vem do cenário TAPAS Cologne: é **sintética** (modelo de atividades construído a partir de dados de mobilidade), não uma contagem ao vivo.
- A rede e a demanda não foram alteradas. As regras de tempo seguem o nosso protocolo.

## Arquitetura

- **8 agentes locais Double DQN**, um por semáforo, com pesos, replay e otimizador próprios.
  - Observação local: filas, veículos, fase atual, tempo de verde, maior espera por aproximação e o objetivo do supervisor (one-hot de 9).
  - Ação: escolher uma das fases verdes reais do semáforo.
- **1 supervisor Double DQN**, que decide a cada 30 s.
  - Observação de 176 dimensões: a rede inteira, as ocupações a jusante e o objetivo anterior.
  - 9 ações: "equilibrado" ou "priorizar o agente k".
  - O supervisor não comanda fases. Ele muda a observação e a recompensa dos locais.
- **Recompensas:**
  - local: −(fila + incremento de espera acima de 60 s + 0,5 × custo do nó priorizado)/100 por segundo;
  - supervisor: o mesmo custo somado na rede.
  - Colisão: −10.000 para cada ator.
- **Segurança:** verde mínimo de 10 s, amarelo de 3 s, vermelho geral de 2 s, decisão a cada 5 s e verde máximo condicional de 60 s.
- **Treino:**
  - 10 inicializações × 500 episódios (5000 episódios);
  - validação a cada 25 episódios (sementes 201–202);
  - **teste final:** 10 modelos × sementes 1–10, ou seja 100 rodadas. Comparadores com 10 sementes cada.
- **Rodada final:** `semaforo/resultados/marl_cologne8/20261113T011843Z_continuo_10seeds_9f8d757b/`. Análise em `analise_detalhada_20261113T132621Z_902ba2/` e `semaforo/ANALISE_MARL_COLOGNE8_CONTINUO.md`.

## Resultado final

Fontes: `modelo_seed*/resumo.json`, `comparadores.json` e `analise_detalhada_20261113T132621Z_902ba2/estatisticas.json`.

| Métrica | MARL + supervisor (n = 100) | Max-Pressure (n = 10) | Programa original de tempo fixo (n = 10) |
|---|---:|---:|---:|
| Espera média da viagem (s) | **9,29 ± 0,68** | 15,83 ± 1,74 | 30,52 ± 0,58 |
| Média dos P95 por simulação (s) | **35,43 ± 2,77** | 50,85 ± 9,14 | 87,55 ± 2,69 |
| Fila média na rede (veículos) | **4,94** | 8,42 | 16,01 |
| Viagens com espera > 60 s | **0,96%** | 2,54% | 14,35% |
| Viagens concluídas | 2046/2046 | 2046/2046 | 2046/2046 |
| Eventos de colisão por simulação | 18,46 | 18,20 | 23,60 |

**Contra o Max-Pressure, pareado:**
- espera −41,3% (IC95 bootstrap −7,74 a −5,56 s);
- P95 −30,3%;
- melhor em 100/100 pares modelo × semente;
- colisões sem diferença (+1,4%, IC inclui zero).

**Variação entre os 10 modelos:** desvio-padrão de 0,60 s na espera, que vai de 8,55 a 10,54 s.

## Ressalvas

- **O supervisor tem efeito misto.**
  - Na ablação com o objetivo fixo em "equilibrado", a espera foi 14,70 s, mas esse número é dominado por um modelo que falhou: o modelo 6 fez 62 s na ablação.
  - Sem o modelo 6, o ganho do supervisor cai para 2,2%, e as colisões sobem 4,3%.
  - Não foi treinado um baseline de agentes independentes sem supervisor.
- **As colisões não foram resolvidas.** Todos os controladores colidem, inclusive o programa original (`collision.action=warn`).
- **Equidade local:** a espera local piorou em 3 dos 8 cruzamentos.
- **O P95 é a média dos P95 de cada simulação**, não um P95 conjunto.
- **As 100 rodadas não são demandas independentes:** os pares origem-destino e os horários são os mesmos; só a estocasticidade do SUMO muda.

## Modelos e reprodução

- **Checkpoints selecionados (um conjunto de 9 atores por modelo):** `modelo_seedN/politica_epXXXX.pt`, nos episódios 375, 375, 150, 375, 450, 300, 500, 475, 50 e 375 (modelos 0 a 9). A seleção está registrada em `resumo.json` (`melhor_checkpoint`, `sha256_checkpoint`).
- Os `.pt` e os `tripinfo.xml.gz` estão em **Git LFS**. Neste computador eles são ponteiros, porque `lfs.fetchexclude` está configurado para não baixar o histórico pesado.
- Em 16/11 baixamos do servidor o checkpoint do modelo 0. O SHA-256 confere, e ele carrega no torch: formato `..._continuo_v2`, episódio 375, 9 atores.
- Para baixar os 10:
  ```bash
  git -c lfs.fetchexclude= lfs pull --include="semaforo/resultados/marl_cologne8/20261113T011843Z_continuo_10seeds_9f8d757b/modelo_seed*/politica_ep*.pt"
  ```
  Isso baixa as políticas de todos os episódios, não só as 10 selecionadas (cerca de 300 kB cada).
- **Verificação sem LFS:**
  - `python -B semaforo/scripts/restaurar_registros_cologne8.py --verificar` confere os 70 pacotes `.tar.xz` dos registros;
  - os números da tabela saem direto de `modelo_seed*/resumo.json` e `comparadores.json`.
- **Limitações de reprodução:**
  - `verificar_pacote_cologne8.py` exige o conteúdo LFS completo, mesmo com `--rapido`.
  - `verificar_marl_continuo.py` e `analisar_marl_continuo.py` leem caminhos absolutos gravados no computador onde o treino rodou.
  - Não há um comando pronto para reavaliar os checkpoints contínuos: `treinar_marl_cologne.py avaliar` aceita só o formato v1.

## Gráficos

- `graficos/B1_cologne8_marl_vs_controles.png`: espera, P95, fila e colisões.
- `graficos/B2_cologne8_curvas_treino.png`: curvas de treino das 10 inicializações.
- `graficos/B3_cologne8_modelos_e_supervisor.png`: espera × colisões por modelo e escolhas do supervisor.
- `graficos/B4_cologne8_v4_teste.png`: v4, com o treino, a validação e o teste (espera e contatos). Cópia de `cologne8_corrigido/.../curvas_comparacao.png`.
- `graficos/B5_cologne8_v2_comparadores.png`: v2 contra os comparadores calibrados. Cópia de `resultados/comparadores_cologne8/comparacao_cologne8.png`.
