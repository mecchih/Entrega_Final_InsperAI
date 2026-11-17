# Material da entrega final

Esta pasta reúne o que vai para os slides. Os números foram conferidos contra os JSON brutos de cada experimento; as fontes estão citadas em cada arquivo. **As três etapas usam ambientes, demandas e métricas diferentes: não compare números entre elas.**

| Arquivo | Conteúdo |
|---|---|
| [`1_cruzamento_sintetico.md`](1_cruzamento_sintetico.md) | Etapa A: gerações A, B e C da Double DQN contra os tradicionais, mais a etapa intermediária Cologne1 |
| [`2_cologne8.md`](2_cologne8.md) | Etapa B: 8 agentes e supervisor no Cologne8; versão final v4, histórico v2 e comparadores |
| [`3_insper.md`](3_insper.md) | Etapa C: corredor do Insper, otimização final e 4º semáforo |
| [`4_limitacoes_e_experimentos.md`](4_limitacoes_e_experimentos.md) | Protocolo dos experimentos, limitações e trabalhos futuros |
| [`VERIFICACAO.md`](VERIFICACAO.md) | Testes curtos executados em 16 e 17/11 (antes da publicação) e o resultado de cada um |
| [`PLANO_COMMITS.md`](PLANO_COMMITS.md) | Registro da publicação no GitHub: commits por componente, verificações e o que ficou fora do Git |
| `graficos/` | 19 gráficos: cópias dos originais, mais um gráfico novo da Etapa A |
| `gerar_grafico_cruzamento.py` | Gera `graficos/A1_...png` a partir de `semaforo/resultados/comparacao_17_C/resumo.json` |

## Gráficos para a apresentação

| Slide | Gráfico | Mensagem |
|---|---|---|
| Etapa A | `A1_cruzamento_geracoes_dqn.png` | A DQN supera o Webster e o teto Max-Pressure na espera média em todos os cenários, inclusive no nunca visto. A geração C reduz a cauda (P95). |
| Etapa B | `B4_cologne8_v4_teste.png` | **Versão final v4:** MARL 18,44 s contra 22,82 s (Max-Pressure) e 39,03 s (original), com 0,30 contato por rodada depois da correção da rede. |
| Etapa B (histórico v2) | `B1_cologne8_marl_vs_controles.png` | v2, na rede original: MARL 9,29 s contra 15,83 s (Max-Pressure) e 30,52 s (original). As colisões existiam em todos. |
| Etapa B (histórico v2) | `B5_cologne8_v2_comparadores.png` | Na v2, o MARL vence também o atuado calibrado (11,98 s), a rede supervisionada e o Q-learning. |
| Etapa B | `B2_cologne8_curvas_treino.png` | O aprendizado converge nas 10 inicializações. |
| Etapa B (opcional) | `B3_cologne8_modelos_e_supervisor.png` | Variação entre modelos e escolhas do supervisor. |
| Etapa C | `C1_insper_teste_espera_media.png` | O original atuado (15,5 s) vence todas as versões do MARL (cerca de 21–23 s); o MARL empata com o clássico sob as mesmas regras. |
| Etapa C | `C2_insper_teste_p95.png` | A mesma conclusão na cauda. |
| Etapa C | `C3_insper_validacao.png` | Seleção feita só pela validação; o desempenho estabiliza a partir do episódio 50. |
| Etapa C (opcional) | `C4_insper_supervisor_30_vs_15.png` | Supervisor a 15 s ≈ 30 s (pareado por semente). |
| Etapa C, Modelo C | `D2_insper_parameter_sharing_generalizacao.png` | A política compartilhada é competitiva com o A na demanda moderada e na intensa, mas trava mais na saturada (15/50 episódios). |
| Etapa C, Modelo C | `D3_insper_parameter_sharing_transferencia.png` | A política funciona em um cruzamento que nunca viu, com perda pequena. |
| Etapa C, zero-shot C3 → C5 | `E1_insper_zero_shot_c3_c5.png` | Os mesmos pesos controlam 5 cruzamentos com segurança, sem mudar o corredor nem a rede. |
| Etapa C, zero-shot C3 → C5 | `E2_insper_zero_shot_por_cruzamento.png` | Nos 2 cruzamentos novos, quase vazios, a espera piora: transferência funcional, não eficiente. |
| Etapa C, C5 treinado | `F2_insper_c5_comparacao.png` | Treinar os 5 agentes do zero não supera o C3 → C5 sem retreino (−0,19 ± 0,24 s nos 5 cruzamentos, n.s.), e o original segue na frente. |
| Etapa C, C5 treinado | `F4_insper_c5_trocas_novos.png` | Nos 2 cruzamentos novos, quase vazios, o C5 continua trocando de fase 2 a 3 vezes mais que o atuado. |
| Etapa C, C5 (opcional) | `F1_insper_c5_treino.png` | O treino com 5 agentes converge no mesmo ritmo do C3. |
| Etapa C, C5 (opcional) | `F3_insper_c5_por_cruzamento.png` | Espera em cada um dos 5 cruzamentos: Atílio Innocenti piora com o RL. |
| Etapa C, Modelo C (opcional) | `D1_insper_parameter_sharing_aprendizado.png` | Com o mesmo número de atualizações por rede, C e A aprendem no mesmo ritmo. |

## Demonstração no SUMO-GUI

Rode na raiz do repositório, com SUMO 1.28 e `SUMO_HOME` definido.

**Etapa A** (abre o SUMO-GUI e mostra as decisões e os valores Q):

```bash
cd semaforo/scripts
python visualizar_dqn.py --modelo dqn_fila_excesso_17_C_seed0 --cenario girado
python visualizar_dqn.py --controlador webster --cenario pico
python visualizar_dqn.py --modelo dqn_fila_C_seed0 --comparar-com dqn_fila_excesso_17_C_seed0
```

**Etapa C, Insper** (um episódio do teste final; demanda sintética da semente 241):

```bash
python -B -X utf8 semaforo/integracao_insper/demo_insper.py --controle original
python -B -X utf8 semaforo/integracao_insper/demo_insper.py --controle A_col --modelo 1
python -B -X utf8 semaforo/integracao_insper/demo_insper.py --controle B_col_s15 --modelo 1 --atraso 20
```

Também é possível abrir só o cenário no programa original, sem Python:

```bash
sumo-gui -c semaforo/cenarios/insper_demanda/intenso_teste_final/semente_241/cenario.sumocfg
```

**Etapa B, Cologne8:**
- Demonstração da v2 com 3 janelas (tempo fixo × rede que copia × MARL): `python -B -X utf8 semaforo/scripts/demo_visual_cologne8.py --sumo-home <pasta do SUMO 1.28>`.
  - Requer a política v2 do modelo 0 via LFS (`semaforo/DEMO_VISUAL_COLOGNE8.md`).
- Não há um comando pronto de demonstração com as políticas da v4.
- Para mostrar a rede: `sumo-gui -c semaforo/referencias/cologne8_sumo_rl_1.4.5/sumo_rl/nets/RESCO/cologne8/cologne8.sumocfg`.
- Para os resultados, use os gráficos.
