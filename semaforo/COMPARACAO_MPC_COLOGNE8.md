# Comparação do MPC sem RL no Cologne8

Em 14/11/2026 testamos um MPC centralizado como comparador sem RL. **Esta
configuração ficou pior em espera que MARL, Max-Pressure e programa original.**
É uma comparação exploratória entre controladores; não demonstra superioridade
geral sobre MPC nem reproduz exatamente o experimento dos autores.

## Resultados

Médias nas sementes de tráfego 1 a 10; MARL reúne dez inicializações por semente.

| Controlador | Espera (s) | Média dos P95 (s) | Fila média | Colisões |
|---|---:|---:|---:|---:|
| Nosso MARL | 9,29 | 35,43 | 4,94 | 18,46 |
| Max-Pressure | 15,83 | 50,85 | 8,42 | 18,20 |
| Programa original | 30,52 | 87,55 | 16,01 | 23,60 |
| MPC adaptado | 38,65 | 109,12 | 20,21 | 29,50 |

Todas as rodadas MPC concluíram as 2.046 viagens, sem teleporte ou viagem
interrompida. O MARL teve espera 75,96% menor que este MPC; o MPC ficou 26,66%
acima do programa original. Nenhum controlador demonstrou operação sem colisões.
P95 é a média dos percentis por rodada, não um percentil agrupado.

[Relatório detalhado e próximos testes](resultados/mpc_cologne8/20261114_comparacao_10sementes/analise_20261114T180227118654Z/RELATORIO.md) ·
[Estatísticas e esperas por entrada](resultados/mpc_cologne8/20261114_comparacao_10sementes/analise_20261114T180227118654Z/estatisticas.json) ·
[Índice das execuções](resultados/mpc_cologne8/indice_execucoes.json).

## Modelo e adaptações

Código de Hu, Yang, Wang e Tan:
[Information-Region MPC](https://github.com/Tarard/Information-Region-MPC),
commit `fdbdf4a8888755859232c11efbdf8f443e0813b1`, de 08/11/2026.
É um manuscrito submetido ao ECC 2027, sem aceitação confirmada. Reutilizamos
**somente o modelo central store-and-forward e o solver**, não o IR-MPC
distribuído. Fontes externas, licença MIT e hashes estão em
[referencias/mpc_externo_fdbdf4a](referencias/mpc_externo_fdbdf4a/proveniencia.json).
MPC é otimização matemática; não é outra rede neural pré-treinada.

- SUMO 1.28.0, mesmas ruas e demanda do Cologne8 e oito TLS com fases reais.
  O motor MARL original foi preservado; a cópia isolada está em
  `scripts/ambiente_comparacao_mpc.py`.
- QP global a cada 120s, horizonte de 480s, saturação assumida de
  0,5 veículo/s/faixa e verdes quantizados em blocos de 5s. Mantidos mínimo
  de 10s, máximo alvo de 60s, amarelo de 3s e vermelho geral local de 2s.
  Os locais podem estar verdes simultaneamente.
- Giros e destinos calibrados com programa original, seed 1001. Nas avaliações,
  taxas de chegada usam apenas os 120s passados. Sumidouros matemáticos permitem
  destinos internos; não alteram ruas ou rotas do SUMO.
- O adaptador segue a ordem cíclica das fases; o MARL pode selecionar outras
  fases. O MPC observa as 149 vias, enquanto o MARL usa seus sensores e totais.
  Os ciclos executados coincidiram com os planos de 120s nesta rodada;
  novos offsets ou inicializações exigem nova auditoria.
- O modelo aproxima G/g com a mesma capacidade e não prevê conflitos
  microscópicos. A função objetivo é de eficiência, sem aprendizado da
  penalidade de colisão. Mantido `collision.action=warn` e o contador histórico;
  os episódios continuam após contatos.

## Validação e limitações

Passaram dez testes automatizados e o piloto independente de 300s (seed 201):
146 viagens concluídas, três colisões, cinco QPs, 592 decisões e 100 transições.
A rodada principal, incluindo outro piloto, teve **336 QPs válidos, 46.993
decisões e 8.213 transições**; uma auditoria conferiu exatamente **24.717 estados
e instantes** contra os planos calculados. As métricas de viagem foram
recalculadas a partir de `tripinfo.xml.gz`.

A regressão de Max-Pressure e programa original (hora completa, seed 1)
reproduziu as métricas históricas. Foram preservados por SHA-256 133 arquivos
protegidos, incluindo pesos, fontes, rede e demanda:
[verificação](resultados/mpc_cologne8/20261114_comparacao_10sementes/VERIFICACAO.json) ·
[agenda executada](resultados/mpc_cologne8/20261114_comparacao_10sementes/VERIFICACAO_CICLOS_20261114T180140524466Z.json) ·
[preservação](resultados/mpc_cologne8/20261114_comparacao_10sementes/PRESERVACAO.json).

O preparo encontrou problemas de cache e restrição de rede, resolvidos em
ambiente separado. Avisos de colisão permaneceram nos logs; o PowerShell os
rotulou como `NativeCommandError` ao redirecionar stderr, sem falha do executor.
A primeira análise foi preservada com uma nota corrigindo a descrição dos ciclos;
os valores numéricos e as simulações não mudaram.

**Manter:** observação causal, fases auditadas, fontes externas intactas, rastros
do solver, resultados desfavoráveis e separação das sementes. **Próximo passo:**
auditar colisões e previsões, calibrar capacidade/ciclos apenas em treino e
validação e reservar nova demanda de teste. Não ajustar olhando estas sementes
e reapresentá-las como um teste independente. Nenhuma DQN foi retreinada.

## Execução

Na raiz do repositório, com Python 3.12 e SUMO 1.28.0 instalado separadamente:

```powershell
python -m venv .venv-mpc-cologne8
& '.venv-mpc-cologne8/Scripts/python.exe' -m pip install -r semaforo/requirements-mpc-cologne8.txt
& '.venv-mpc-cologne8/Scripts/python.exe' -B semaforo/scripts/testar_controlador_mpc.py
& '.venv-mpc-cologne8/Scripts/python.exe' -B semaforo/scripts/comparar_mpc_cologne8.py --modo curto --sumo-home 'C:/caminho/para/SUMO-1.28.0'
```

O modo curto inclui calibração de uma hora e piloto de 300s. Para dez sementes
completas, usar `--modo completo --sementes 1 2 3 4 5 6 7 8 9 10`.
GUI opcional: `--backend traci --gui`; a rodada registrada usou libsumo.
Aceita `SUMO_HOME` e `--saida`, recusando sobrescrever uma pasta existente.

Os scripts `verificar_comparacao_mpc.py`, `verificar_ciclos_mpc.py` e
`relatar_comparacao_mpc.py` recebem o caminho da rodada e conferem/analisam os
dados sem refazer simulações. Cada nova análise gera outra saída. Decisões
registram estado, fases pedida/executada, intervenções e alocação do MPC;
`q` fica vazio porque MPC não produz valores Q. Fontes, piloto, logs e dados
brutos estão preservados em `resultados/mpc_cologne8/`.
