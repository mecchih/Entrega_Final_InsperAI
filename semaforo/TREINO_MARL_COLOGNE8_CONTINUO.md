# Colônia ampliada: treino longo com colisão não terminal

Protocolo definido em 12/11/2026, após a usuária pedir treinos mais longos,
dez sementes e continuidade após colisões. Esta rodada é separada da anterior.
Nenhum peso/histórico/resultado anterior será sobrescrito. Código anterior
preservado em `referencias/marl_terminal_20261113T010040Z/` e na rodada antiga.

## O que muda e o que permanece

- **10 inicializações de treino: 0 a 9; 500 episódios cada**, total 5000.
  Dobra os 250 episódios anteriores. No histórico da DQN C havia três
  inicializações de treino, e dez sementes de avaliação; aqui ampliamos ambos.
- Cada episódio percorre 25200--28800 s de demanda e até 1200 s de escoamento.
  **Colisão não encerra episódio nem treinamento.** Apenas fim natural ou
  limite do escoamento fecha a última experiência. Erro de software/valor
  inválido ou teleporte inesperado continua sendo tratado como erro.
- Mantém **−10.000 por novo evento para cada um dos nove atores**. O mesmo par
  reportado em passos consecutivos é cobrado uma vez; se deixa de ser reportado
  e volta a colidir, constitui um novo contato. Não remove/teleporta carros por
  colisão: `collision.action=warn`; detecção em cruzamentos continua habilitada.
- Punir colisão não transforma a transição em terminal. O replay inclui a
  punição, o próximo estado, o intervalo real e o bootstrap normal. Uma colisão
  exatamente no fim previsto pode coincidir com uma experiência terminal,
  mas não é a causa do término.
- Mesma rede/demanda originais `cologne8` do SUMO-RL 1.4.5: oito controladores,
  2046 viagens OD/horários fixos, rotas calculadas pelo SUMO. A cópia reprocessada
  da rede continua fora do treino. Não é a cidade inteira do TAPAS Cologne.
- Mesmas entradas, fases e proteções auditadas. Redes locais têm
  `[26,24,22,26,22,18,22,26]` entradas e `[4,2,3,4,3,2,3,4]` saídas; supervisor
  `176 -> 64 -> 64 -> 9`. Ocultas locais 64/64 ReLU. Um único relógio SUMO
  por episódio; oito cruzamentos podem estar verdes simultaneamente.

Novo formato explícito: `smartflow_marl_supervisor_cologne_continuo_v2`.
Pesos anteriores não inicializam esta rodada: a dinâmica terminal e os replays
anteriores não correspondem ao novo protocolo. O script histórico continua
disponível para reproduzir a rodada terminal; a entrada da rodada nova é
`scripts/treinar_marl_continuo.py`.

## Aprendizado e avaliação

Os nove atores têm seus próprios pesos, alvo, replay, Adam, RNG e contadores.
Fila/espera e objetivo do supervisor mantêm a definição da rodada anterior.

Restauramos parâmetros adequados a episódios completos, conforme a DQN C:
replay 50000 por ator, lote 64, aquecimento **2000 experiências por ator**,
Adam 5e-4, Huber, norma de gradiente máxima 10, alvo a cada 500 atualizações,
desconto `0,95^(dt/5)`. Exploração local 100% até 5% em **40000 decisões**;
supervisor, mais lento, em **10000**. Os limites reduzidos da rodada terminal
(256/64 e 2000/500) não são reutilizados aqui.

- Tráfego de treino: seed `1000 + episódio`, pareado entre inicializações.
- Validação a cada 25 episódios, sem exploração/gradientes, seeds 201 e 202.
- Seleção conjunta dos nove atores do mesmo episódio: menos colisões, depois
  menos viagens previstas não concluídas, depois menor espera afetada.
- Avaliação final: **seeds de tráfego 1 a 10 por modelo**. Não escolhe pesos
  com essas sementes. Compara Max-Pressure sob as mesmas proteções e programa
  original com seus tempos, nas mesmas dez sementes.
- Ablação adicional: mesmas redes, orientação fixada em equilibrado, nas dez
  sementes. Não substitui treinar uma referência independente sem supervisor.

As viagens OD e os horários continuam iguais entre sementes. A variabilidade
do SUMO e da inicialização não demonstra generalização para demanda inédita.
As colisões também observadas no controlador original permanecem uma limitação
do ambiente. A punição alta não garante que os agentes aprendam a evitá-las.

## Verificações antes da rodada principal

Dez testes unitários passaram, incluindo deduplicação de contato, dimensões,
transições, desconto/terminal e retomada reproduzindo a próxima atualização.
O piloto `20261113T010530Z_piloto_continuo` percorreu a hora e o escoamento:
33 eventos, 2046 viagens concluídas e punições **não terminais** no replay dos
nove atores. Os pesos do piloto são descartáveis.

Um ensaio completo do novo executor com uma inicialização descartável (777),
um episódio e aquecimento reduzido exclusivamente para teste terminou em
`20261113T011248Z_continuo_bf6c3fff/`. Foram conferidas sete simulações, incluindo
validação, teste, ablação e comparadores; checkpoint, verificação e relatório
automáticos concluíram. O treino do ensaio percorreu 4186 s SUMO, com 40 eventos,
sem término por colisão. Conferidos 3603 arquivos anteriores intactos e três
scripts alterados com backup. A rodada principal começa do zero e usa o
aquecimento de 2000, não o reduzido desses ensaios.

## Execução longa e acompanhamento

Três processos de treino em paralelo, cada um com uma thread PyTorch e um SUMO
próprio. As demais sementes aguardam na fila. O paralelismo é entre inicializações;
os oito agentes locais de um episódio continuam no mesmo SUMO. Foi escolhido
considerando oito CPUs lógicas e a memória disponível. Esta carga leva horas.

Código é copiado para `fontes_execucao/` e **executado dessa cópia congelada**.
Alterar os scripts do repositório depois não muda os processos da rodada.
Checkpoints novos a cada melhora; estado completo a cada 100 episódios e no
último: redes/alvos/Adam/replay/RNG/contadores. Cada arquivo tem nome novo.
O executor grava progresso por episódio e dispara verificação, relatório e
curvas automaticamente depois de todos os treinos/testes. Só cria
`CONCLUIDO.json` após concluir essas etapas. Falhas ficam em logs e JSON.

PowerShell, na raiz do repositório:

```powershell
& '.venv-dqn-inferencia/Scripts/python.exe' -B -X utf8 semaforo/scripts/treinar_marl_continuo.py --episodios 500 --sementes 0 1 2 3 4 5 6 7 8 9 --sementes-teste 1 2 3 4 5 6 7 8 9 10 --trabalhadores 3 --sumo-home '../tools/sumo-win64-1.28.0' --snapshot 'tmp/marl_continuo/antes_20261113T010040Z.json'
& '.venv-dqn-inferencia/Scripts/python.exe' -B -X utf8 semaforo/scripts/acompanhar_marl_continuo.py 'CAMINHO_DA_RODADA' --intervalo 30
```

Para retomar uma semente de um estado completo, usar **saída nova**, a mesma
semente de modelo e `--retomar-checkpoint CAMINHO/estado_ep0100.pt`. O histórico
anterior é referenciado com limite de episódio para evitar contagem duplicada.
Não converter um checkpoint da rodada terminal para esse fim.

Se a usuária pedir pausa, o marcador `PAUSAR_APOS_EPISODIO` na pasta da rodada
faz cada processo ativo terminar o episódio atual e gravar estado completo;
sementes da fila não iniciam. Isso é separado do comportamento de colisão.

O protocolo completo e os hashes estarão na pasta da execução. Pesos antigos,
históricos e resultados anteriores permanecem preservados. Nenhum commit/push
é feito automaticamente nesta etapa.

Referência do comportamento `warn` e da detecção:
[SUMO — Safety](https://sumo.dlr.de/docs/Simulation/Safety.html).

## Rodada principal lançada

Pasta: `resultados/marl_cologne8/20261113T011843Z_continuo_10seeds_9f8d757b/`.
Protocolo: 500 episódios, sementes de modelo 0--9, teste 1--10, três processos.
As sementes 0/1/2 iniciaram juntas; as demais entram conforme os processos
terminam. Primeiros episódios completaram a hora e o escoamento, sem término
por colisão e com todas as viagens concluídas nesses primeiros registros.

- [Configuração e hashes da rodada](resultados/marl_cologne8/20261113T011843Z_continuo_10seeds_9f8d757b/protocolo.json).
- [Eventos de execução](resultados/marl_cologne8/20261113T011843Z_continuo_10seeds_9f8d757b/eventos_execucao.jsonl).
- `CONCLUIDO.json` será criado somente após treino, testes, conferência e relatório.
- `falha_coordenador.json` registra erro; não confundir ausência de conclusão
  com conclusão bem-sucedida. Resultados intermediários permanecem disponíveis.

```powershell
& '.venv-dqn-inferencia/Scripts/python.exe' -B -X utf8 semaforo/scripts/acompanhar_marl_continuo.py 'semaforo/resultados/marl_cologne8/20261113T011843Z_continuo_10seeds_9f8d757b' --intervalo 30
```

Os 3527 arquivos de pesos/resultados anteriores conferidos no lançamento
mantiveram seus hashes. Não foi feito commit/push nem iniciada atualização
dos pesos anteriores. Esta seção registra o lançamento; o andamento real
está nos arquivos da execução, não em uma afirmação antecipada de conclusão.

## Monitoramento contínuo adicionado

A pedido da usuária, foi ativado `scripts/monitorar_marl_continuo.py`, com
checagens a cada 60 segundos, em processo separado. O monitor não altera
pesos, fases, exploração ou o código congelado, e não pausa por colisão.

Conferências: avanço dos episódios, processos ativos, perdas/gradientes
finitos, aprendizado após aquecimento, protocolo sem término por colisão,
penalidades, integridade ZIP dos checkpoints estabilizados, fontes/rede/rotas
por hash, memória/disco e tendências dos últimos 20 episódios. Quatro testes
do monitor passaram, incluindo leitura de arquivo ainda em gravação e
distinção entre aquecimento e ausência de aprendizado.

- [Acompanhamento atualizado pelo monitor](resultados/marl_cologne8/20261113T011843Z_continuo_10seeds_9f8d757b/monitoramento/20261113T013904Z_d4b004/MONITORAMENTO.md).
- [Estado atual em JSON](resultados/marl_cologne8/20261113T011843Z_continuo_10seeds_9f8d757b/monitoramento/20261113T013904Z_d4b004/estado_atual.json).
- O histórico completo é `historico_monitoramento.jsonl` nessa pasta; novos
  alertas e resoluções ficam em `alertas.jsonl`, se ocorrerem. Falhas do
  próprio monitor são registradas em `erros_monitor.jsonl`.
- O monitor encerra quando houver conclusão verificada, pausa solicitada
  ou falha registrada pelo coordenador. Não envia mensagens automáticas no
  chat e não substitui a interpretação dos resultados pelo assistente.

Também foram auditados diretamente os checkpoints escolhidos nas três
sementes ativas (episódios 50/75/75 no momento da auditoria): nove redes
por checkpoint, dimensões corretas, pesos finitos e todos os atores com
gradientes. Os hashes permaneceram iguais antes/depois da leitura. Evidência
em `auditoria_checkpoints_inicial.json` dentro da pasta do monitor.
