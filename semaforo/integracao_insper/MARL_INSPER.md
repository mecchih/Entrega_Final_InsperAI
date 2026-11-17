# Multi-Agent no corredor Insper: ambiente e primeiros treinos

Esta é a etapa 2, de 15/11/2026, no cenário `intenso` (cerca de 2.190 viagens; 2.000 viagens/h passam pelo corredor).

## Arquivos

| Arquivo | Função |
|---|---|
| `ambiente_marl_insper.py` | Episódio TraCI com os modos `original`, `independente` e `hierarquico`, a recompensa, a validade do episódio e as métricas resumidas. |
| `treinar_marl_insper.py` | Treino. Gera as 30 demandas de treino em `cenarios/insper_demanda/intenso_treino/` (sementes 1001–1030) e salva os checkpoints. |
| `avaliar_marl_insper.py` | Avaliação gulosa, sem exploração, nas sementes de teste 211–215, que não foram usadas no treino. |
| `testar_ambiente_marl_insper.py` | Testes curtos de 900 a 1.500 s simulados. |

O ambiente reaproveita, sem alterar:
- de `scripts/agente_marl_cologne.py`: `DoubleDQN` e `Replay`, com os mesmos hiperparâmetros;
- de `scripts/ambiente_marl_cologne.py`: `incremento_excesso` e `ContadorColisoes`;
- o controlador seguro do Insper;
- o observador `SensoresInsper` (local com 13 entradas e 2 ações; supervisor com 48 entradas e 4 ações).

Correções em arquivos da etapa anterior:
1. `controle_seguro_insper.py`: quando o controle assumia o semáforo com o amarelo já completo, o amarelo ganhava 1 s a mais. O verificador independente detectou isso na demanda 1014, e há um teste novo para o caso.
2. `observacao_insper.py`: as escalas agora podem ser passadas como parâmetro.

## Regras do episódio

- **Tempos:**
  - de 0 a 300 s, os programas originais funcionam como aquecimento;
  - de 300 s até a rede esvaziar, os agentes controlam, com limite de 5.400 s;
  - decisão local a cada 5 s depois do verde mínimo e decisão do supervisor a cada 30 s.
- **Segurança:** verde mínimo de 10 s, amarelo de 3 s, vermelho geral de 2 s e verde máximo condicional de 60 s.
  - O replay guarda a ação **executada**, depois da proteção de verde máximo.
  - Violação de transição ou escrita em semáforo não controlado gera erro e interrompe o treino.
- **Recompensa:** tem a forma do Cologne8.
  - Local: −(fila + excesso de espera acima de 60 s + 0,5 × custo do semáforo priorizado)/100 por segundo.
  - Supervisor: −(fila + excesso de espera do **corredor**)/300 por segundo. No Cologne8 era a rede inteira, mas aqui os outros 11 semáforos não são controlados.
  - Colisão: −10.000 por ator.
  - Teletransporte: −10 por ator. Isso substitui o encerramento do episódio usado no Cologne8; sem essa penalidade, o teletransporte "resolveria" a fila.
  - `--waiting-time-memory 10000`, como no Cologne8. O padrão do SUMO esquece a espera depois de 100 s.
- **Validade:**
  - travamento (mais de 80% dos veículos da rede parados por 300 s, ou mais de 22 teletransportes): o episódio é encerrado e marcado inválido;
  - menos de 95% das viagens concluídas: inválido;
  - até 1 teletransporte, o máximo do programa original: `ocasional`;
  - de 2 a 22: `elevado`, válido mas marcado.
- **Comparabilidade dos modelos:**
  - mesmas sementes locais (1000·s + k), mesma sequência de demandas, mesmo número de episódios e mesmos hiperparâmetros locais;
  - o independente usa a orientação fixa "equilibrado";
  - o supervisor usa os hiperparâmetros de supervisor do Cologne8 (épsilon decai em 10 mil decisões).

## Resultados

- **Testes curtos:** todos passaram.
- **Treinos de verificação:** 2 modelos × 2 sementes × 20 episódios. Todos concluíram e geraram checkpoints a cada 5 episódios, mais o `final_completo.pt`.
- **Avaliação preliminar:** está em `resultados/20261115T224520Z_avaliacao_marl/avaliacao.json`.

Comandos:

```powershell
python -B -X utf8 semaforo/integracao_insper/testar_ambiente_marl_insper.py
python -B -X utf8 semaforo/integracao_insper/treinar_marl_insper.py --modelo hierarquico --episodios 150 --semente 3
python -B -X utf8 semaforo/integracao_insper/avaliar_marl_insper.py --original --checkpoint hier_s3=<pasta>/politica_ep0150.pt
```

## Bateria principal (150 episódios × 5 sementes × 2 modelos)

Resultados, critério de seleção, gráficos e problemas em
`resultados/bateria_principal_20261116/RESULTADOS.md`. Para reproduzir:
`bateria_marl_insper.py demandas | paralelismo | treinar | validar | testar` e depois
`py -B semaforo/integracao_insper/relatorio_marl_insper.py`. O `py` é usado porque o
matplotlib do Anaconda está quebrado com o NumPy 2.

A métrica de espera no corredor mudou antes da bateria: agora inclui os veículos
que não pararam. Os números da avaliação preliminar acima não são comparáveis
com os da bateria.
