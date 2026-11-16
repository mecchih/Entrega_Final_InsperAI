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

## Piloto pareado com e sem supervisor

Executado entre 15 e 16/11/2026, com saída separada em
`resultados/piloto_supervisor_cologne8/20261115_pareado_3x100_reinicio/`.
Essa é a rodada concluída: a primeira tentativa parou em 50 episódios somados,
antes dos checkpoints previstos a cada 25. Os dados parciais foram preservados
em `20261115_pareado_3x100/INTERRUPCAO_OBSERVADA.json`. O reinício usa processo
externo oculto, checkpoint completo no episódio 1 e depois a cada cinco.
O carregamento completo foi conferido, e um teste reproduziu a próxima ação e
atualização após restaurar replay, alvo, Adam e RNG. Para uma futura interrupção,
`--retomar-raiz PASTA_ANTERIOR` permite ao executor continuar dos checkpoints
completos em uma saída nova, preservando os históricos e fontes anteriores.
São três inicializações por configuração e 100 episódios cada (600 no total),
com pesos novos e capacidade/inicialização idênticas nas oito redes locais.
Sem supervisor, o one-hot de orientação permanece neutro desde o treino;
não existe uma nona rede nesse braço. As dimensões locais são preservadas.

Os dois braços usam a mesma recompensa local base, sem o adicional do objetivo,
as mesmas demandas variadas e −10.000 por contato, sem término por colisão.
Rede, fases e modelo veicular originais foram mantidos. A auditoria reproduziu
29 contatos no programa original e 22 no Max-Pressure (seed 301); aumentar a
margem de parada reduziu contatos, mas não eliminou o problema e não foi adotado
no piloto. Os resultados continuam condicionais a um ambiente com contatos.

`protocolo.json`, `manifesto.json` e `demandas/indice.json` registram o contrato;
`fontes_execucao/` contém o código realmente executado. Treino, três demandas de
validação e quatro de teste reservado estão separados. `CONCLUIDO.json` indica
o fim dos treinos; a análise posterior terá `VERIFICADO.json` e `ANALISE.json`.
`TUDO_CONCLUIDO.json` só será criado após análise e conferência de preservação.
Não comparar diretamente as médias com a rodada anterior, pois demanda e
recompensa mudaram. Acompanhar sem alterar a execução:

```powershell
& '.venv-dqn-inferencia/Scripts/python.exe' -B semaforo/scripts/monitorar_piloto_supervisor.py semaforo/resultados/piloto_supervisor_cologne8/20261115_pareado_3x100_reinicio
```

### Resultado do piloto — 16/11/2026

Concluído às **00:15 de 16/11, horário de São Paulo**. Foram 600 episódios
de treino, 72 avaliações de validação, 24 testes reservados dos modelos e oito
simulações dos comparadores: **704 simulações na rodada válida**. Os 50 episódios
da tentativa interrompida ficaram separados e não entram nesta comparação.
Todas as redes apresentaram atualizações por gradiente. A auditoria recalculou
os arquivos de viagens das 696 simulações de treino/validação/teste e confirmou
as inicializações locais idênticas em cada par. Os **133 arquivos anteriores
protegidos por SHA-256 permaneceram intactos**. Não foi feito commit/push.

Médias no teste reservado: três inicializações por braço RL, cada uma avaliada
nas mesmas quatro demandas (1534, 2558, 2046 e 2251 viagens; sementes SUMO
9301–9304). Cada comparador foi executado uma vez por demanda, pois não tem
semente de inicialização de rede. As médias dão o mesmo peso a cada rodada;
P95 significa a média dos P95 de cada rodada, sem juntar todas as viagens.

| Controlador | Espera (s/viagem) | P95 (s) | Fila média (veículos) | Contatos/rodada | Atraso de inserção (s) |
|---|---:|---:|---:|---:|---:|
| Oito DQNs + supervisor | 14,37 | 58,20 | 8,39 | 28,08 | 4,18 |
| Oito DQNs independentes | 15,23 | 61,32 | 8,75 | 31,92 | 4,60 |
| Max-Pressure | 20,78 | 68,75 | 12,15 | 25,75 | 8,17 |
| Programa original | 37,44 | 119,88 | 21,57 | 43,50 | 9,95 |

Todos os testes reservados e comparadores concluíram todas as viagens, sem
teleportes. A espera exclui o atraso de inserção, mostrado separadamente;
a duração média de viagem foi 98,26 / 99,19 / 110,18 / 125,34 s na ordem da
tabela. Intervenções das proteções foram 59,50 / 105,00 / 42,25 por rodada;
o programa original não foi instrumentado para essa métrica. Durante o
**treinamento**, 18 dos 600 episódios tiveram viagens pendentes no limite
do escoamento; isso não ocorreu nas avaliações reservadas.

O supervisor reduziu a espera em **5,67%**, P95 em 5,09%, fila em 4,14% e
contatos em 12,01% frente ao treino independente. Frente ao Max-Pressure,
a espera foi 30,86% menor, mas houve **9,06% mais contatos**. Frente ao
programa original, a espera caiu 61,63%. Os resultados por par foram:

| Inicialização | Espera com / sem supervisor (s) | Contatos com / sem | Episódio escolhido com / sem |
|---|---:|---:|---:|
| 0 | 15,17 / 16,38 | 29,00 / 37,00 | 25 / 25 |
| 1 | 13,63 / 14,71 | 24,25 / 27,00 | 25 / 25 |
| 2 | 14,29 / 14,60 | 31,00 / 31,75 | 100 / 50 |

Os checkpoints foram escolhidos apenas pela validação, priorizando contatos,
depois viagens pendentes e depois espera. Os três pares atenderam ao critério
prévio de pelo menos 5% de melhora de espera na validação sem piorar contatos
ou deixar viagens pendentes. Isso justifica considerar uma confirmação maior;
não representa significância estatística com apenas três inicializações.
Quatro dos seis checkpoints escolhidos foram do episódio 25: prolongar o treino
não produziu melhora uniforme segundo esse critério.

O ganho não se distribuiu igualmente: no pico central de 2558 viagens, a
espera com supervisor foi 21,93 s contra 21,70 s, e P95 97,05 contra 90,33 s.
Na agregação local ponderada pelos veículos observados, 14 de 25 entradas
com observações em ambos os braços tiveram espera maior com supervisor;
a maior piora média foi +2,07 s na entrada `133081985#1`, TLS `252017285`.
Essa é espera parada na área do cruzamento, não a espera total de viagem;
as amostras locais podem diferir porque a passagem pelos cruzamentos muda.
A melhora global não demonstra equidade entre entradas.

**Manter:** comparação pareada, demandas separadas, oito agentes independentes
treinados desde o início, seleção sem consultar teste, transições protegidas,
penalidade alta sem término por colisão e checkpoints completos frequentes.
**Rever antes de uma confirmação longa:** os contatos nas interseções permissivas
e a escala/atribuição do custo. A penalidade respondeu por cerca de **99,93% do
retorno negativo acumulado dos oito locais** nos dois braços. A queda da espera
não resolve essa limitação nem demonstra segurança.

A auditoria anterior ao piloto encontrou contatos também nos controladores
sem RL. Seguir a cadeia das faixas internas corrigiu a classificação dos
movimentos: 46 dos 48 eventos classificáveis envolviam movimentos G/g e o
veículo com prioridade menor quase parado. Não foram encontrados pares de
verdes protegidos conflitantes nas 141 verificações estáticas. Esses indícios
sugerem investigar posição de espera/geometria/comportamento veicular; não
provam uma causa única. Alterar `jmStoplineGapMinor` para 1 m reduziu os
contatos original/Max-Pressure de 29/22 para 12/9; 2 m junto de `jmAdvance=0`
produziu 10/8. Essas sensibilidades usam uma semente e não foram incorporadas
ao piloto, evitando mudar a física durante a comparação do supervisor.

Não comparar os 14,37 s diretamente aos 9,29 s da rodada anterior: mudaram
as demandas e a recompensa local. Os pesos são novos. As demandas variadas
reutilizam os pares origem/destino disponíveis em Cologne8; não testam outra
cidade ou novos pares fora desse conjunto. O próximo experimento deve manter
a penalidade alta e validar as condições de colisão antes de ampliar sementes,
com novas demandas reservadas para a confirmação.

Evidências na pasta da rodada:

- [Análise numérica, pares, validação e esperas locais](resultados/piloto_supervisor_cologne8/20261115_pareado_3x100_reinicio/ANALISE.json).
- [Curvas de validação e comparação reservada](resultados/piloto_supervisor_cologne8/20261115_pareado_3x100_reinicio/comparacao_piloto.png).
- [Agregação por entrada](resultados/piloto_supervisor_cologne8/20261115_pareado_3x100_reinicio/ESPERAS_ENTRADAS_AGREGADAS.json).
- [Conferência dos resultados](resultados/piloto_supervisor_cologne8/20261115_pareado_3x100_reinicio/VERIFICADO.json), [preservação](resultados/piloto_supervisor_cologne8/20261115_pareado_3x100_reinicio/PRESERVACAO.json) e [conclusão final](resultados/piloto_supervisor_cologne8/20261115_pareado_3x100_reinicio/TUDO_CONCLUIDO.json).

Para repetir o piloto, na raiz do repositório, usar **uma saída que ainda não
exista**, ajustando o caminho de SUMO à instalação local:

```powershell
& '.venv-dqn-inferencia/Scripts/python.exe' -B -X utf8 semaforo/scripts/executar_piloto_supervisor.py --saida 'semaforo/resultados/piloto_supervisor_cologne8/NOVA_RODADA' --sumo-home '../tools/sumo-win64-1.28.0'
```

## Nova rodada após auditoria — v4, 16/11/2026

A usuária autorizou corrigir os problemas necessários e iniciar o treino.
Processo externo oculto lançado às **00:51 de 16/11, horário de São Paulo**,
com saída nova em `resultados/cologne8_corrigido/20261116_10sementes_500ep_v4/`.
Esta seção registra o lançamento, não a conclusão. São **10 inicializações
(0–9), 500 episódios cada, oito DQNs locais e um supervisor**, três processos
em paralelo e uma thread PyTorch por processo. Todos os pesos começam novos;
pesos do piloto e dos ensaios não são reutilizados.
As sementes 0/1/2 iniciaram às **01:01**, após gerar as demandas e registrar
por hash os 30.624 arquivos de pesos/resultados anteriores (14,7 GiB).
Às **01:08**, havia 57 episódios concluídos: 19 em cada semente ativa, com
atualizações por gradiente nos nove atores e perdas finitas. Os três primeiros
checkpoints completos foram carregados e conferidos; os 133 hashes da auditoria
anterior também corresponderam. Isso confirma o arranque, sem antecipar o
resultado do treino ou dos testes reservados.

### Auditoria e mudanças adotadas

Ajustes apenas no comportamento veicular não resolveram: o conjunto de margens
e aceitação de brechas teve 16 contatos em cada comparador na seed 301. Os
registros mostraram carros parados na espera interna invadindo a trajetória
prioritária. Foi criada uma **rede derivada** pelo netconvert 1.28, com
`contPos=0` em 95 conexões: o veículo deve esperar uma brecha antes de entrar,
em vez de estacionar dentro da interseção. A cópia mantém os oito TLS, a
topologia externa e os 103 movimentos controlados. Cada cor de cada fase foi
remapeada pela identidade real do movimento; índices não foram presumidos.
Todos os pares G/G conferidos pela matriz de conflitos passaram no teste.

O reprocessamento também alterou a geometria/comprimento de três faixas
externas: `-309744810#1_0` (99,89→89,64 m), `133081987#3_0` (99,94→88,58 m)
e `23656410#0_0` (25,48→25,50 m). As formas completas constam na auditoria.
As categorias ferroviárias adicionais em `disallow` não mudam a permissão
dos automóveis usados. O modelo veicular adotado continua original, com
`minGap=1,5 m` e `tau` efetivo de 1 s. Sensibilidades com `minGap=2,5` e
`tau=2` foram preservadas, mas não adotadas: não eliminaram todos os contatos.

Na configuração escolhida, oito rodadas nativas cobriram demanda original
(seeds 301/1001), pico de 2455 viagens (3002) e duplo pico de 2251 (3003),
sempre com programa original e Max-Pressure. Todas concluíram todas as viagens.
Houve **quatro contatos residuais, todos no cruzamento sem semáforo
`cluster_26718385_738066527_738066531_738066575`**. Não houve contato observado
nas áreas dos oito TLS nessas rodadas. Isso é uma correção parcial observada,
sem garantia de ausência de colisões no treino.

A punição bruta permanece **−10.000 por evento ao supervisor**. Cada local
recebe a mesma punição quando as faixas registradas pertencem à sua área;
locais sem área envolvida não recebem esse custo. O vínculo vem das faixas
controladas e suas conexões internas, sem afirmar culpa causal. Eventos fora
dessas áreas continuam registrados e punem o supervisor. A detecção permanece
ativa, com `collision.action=warn`, sem teleportes e sem terminar por colisão.
Logs incluem o vetor real de penalidades e os eventos sem jurisdição local.

Toda recompensa é dividida por 1000 antes do replay, mantendo custos brutos
nos resultados. Isso melhora a escala numérica, preservando a proporção entre
punições e custos de trânsito; não elimina por si a dominância relativa de
colisões. A arquitetura 64/64, Adam, replay e tempos permanecem iguais.

Entradas locais, na ordem: filas/25, carros/35, one-hot da fase verde,
idade do verde/60 (teto 2), maior espera por entrada/120 (teto 3), orientação
one-hot de nove valores. As dimensões são **26/24/22/26/22/18/22/26**, com
4/2/3/4/3/2/3/4 ações reais. O supervisor continua **176→64→64→9**.
Cruzamentos não relacionados continuam podendo ficar verdes ao mesmo tempo.

### Validação antes do lançamento e acompanhamento

Passaram cinco testes novos e cinco de regressão. O ensaio realizou dois
episódios completos com atualizações nos nove atores, restauração de checkpoint
completo e avaliação sem alterar pesos/replay/RNG. Usou aquecimento 64 apenas
para testar o código; a rodada principal mantém **2000**. O ensaio também
revelou uma política ainda pouco treinada que deixou 559 viagens pendentes.
O seletor foi corrigido **antes da rodada**: prioriza menos viagens pendentes,
depois menos contatos e depois espera média mais atraso de inserção. Não
premiar zero colisões obtido por travar a demanda. Relatório, recálculo de
viagens, comparadores e gráfico também passaram por ensaio separado; seus
números reutilizam calibração e não são resultados reservados do treino.

Demandas novas usam geração 100001–100500; cinco validações, 150001–150005;
dez testes reservados, 170001–170010. Validação a cada 25 episódios; testes
somente do checkpoint escolhido ao final. Os comparadores serão executados
novamente nas mesmas condições reservadas. Estão planejadas **6120 simulações**:
5000 de treino, 1000 de validação, 100 testes dos modelos e 20 comparadores.
Esta rodada não tem braço independente v4: avalia o conjunto corrigido,
sem isolar o efeito causal do supervisor. Também não permite comparar médias
diretamente ao piloto v3, pois ambiente, atribuição do custo e seleção mudaram.

Fontes executadas ficam congeladas em `fontes_execucao/`. Checkpoints completos
nos episódios 1/10/25/50, múltiplos de 100 e último, com nomes exclusivos;
histórico e métricas a cada episódio. A frequência limita o consumo de disco,
sem remover checkpoints anteriores. Há reserva de 8 GiB e salvamento do estado
antes de bloquear novo episódio por disco insuficiente. Retomada usa
`--retomar-raiz PASTA_ANTERIOR` e uma saída nova. Monitoramento é gravado a cada
60 s em `monitoramento.jsonl`, com alertas de estagnação e ausência de gradientes.

Ao final, o executor produzirá `ANALISE.json`, `curvas_comparacao.png`,
`PRESERVACAO.json` e só então `TUDO_CONCLUIDO.json`. `FALHA*.json` indica
problemas; ausência de conclusão não significa sucesso. Nenhum commit/push
é feito automaticamente. Acompanhar, na raiz do repositório:

```powershell
& '.venv-dqn-inferencia/Scripts/python.exe' -B -X utf8 semaforo/scripts/treinar_cologne8_corrigido.py --saida semaforo/resultados/cologne8_corrigido/20261116_10sementes_500ep_v4 --status
```

Para repetir, ajustar SUMO à instalação local e escolher uma saída inexistente:

```powershell
& '.venv-dqn-inferencia/Scripts/python.exe' -B -X utf8 semaforo/scripts/treinar_cologne8_corrigido.py --saida semaforo/resultados/cologne8_corrigido/NOVA_RODADA --rede semaforo/resultados/cologne8_corrigido/20261116_rede_sem_espera_interna_v2/cologne8.net.xml --sumo-home '../tools/sumo-win64-1.28.0' --auditoria semaforo/resultados/cologne8_corrigido/AUDITORIA_FINAL_20261116.json
```

- [Auditoria final e limitações](resultados/cologne8_corrigido/AUDITORIA_FINAL_20261116.json).
- [Protocolo da rodada](resultados/cologne8_corrigido/20261116_10sementes_500ep_v4/protocolo.json), [checkpoints iniciais conferidos](resultados/cologne8_corrigido/20261116_10sementes_500ep_v4/ARRANQUE_VERIFICADO.json), [aprendizado inicial](resultados/cologne8_corrigido/20261116_10sementes_500ep_v4/APRENDIZADO_INICIAL.json) e [monitoramento](resultados/cologne8_corrigido/20261116_10sementes_500ep_v4/monitoramento.jsonl).
- [Proveniência da rede derivada](resultados/cologne8_corrigido/20261116_rede_sem_espera_interna_v2/PROVENIENCIA.json).
- [Ensaio de integração](resultados/cologne8_corrigido/20261116_integracao_v4/VERIFICADO.json) e [ensaio do relatório](resultados/cologne8_corrigido/20261116_ensaio_relatorio/VERIFICADO.json).
- [Erros de preparação e erratas preservadas](resultados/cologne8_corrigido/ERRATA_PREPARACAO.json).
- Referências: [SUMO — `contPos`](https://eclipse.dev/sumo/docs/Networks/PlainXML.html#connection_descriptions), [espera interna](https://eclipse.dev/sumo/docs/Simulation/Intersections.html#waiting_within_the_intersection) e [detecção/segurança](https://eclipse.dev/sumo/docs/Simulation/Safety.html).

### Interrupção por reserva de disco — 16/11, 08:01

A rodada parou em **4046/5000 episódios (80,92%)**. Os três processos ativos
registraram `Disco abaixo de 8 GiB: estado preservado; nao iniciar outro episodio`.
O espaço livre caiu de 13,9 GiB às 07:30 para menos de 8 GiB às 07:58; os
processos salvaram os estados completos e encerraram às 08:01. O diagnóstico
confirma o gatilho de espaço, sem atribuir a queda a outro programa ou à tampa.

Sementes 0–5 concluíram os 500 episódios e seus testes. Os checkpoints de
emergência das sementes **6/7/8 correspondem exatamente aos episódios
359/350/337** dos históricos. Foram carregados em CPU, com nove atores,
pesos finitos, redes-alvo, Adam, replay e RNG presentes. A semente 9 não iniciou.
Assim, os 4046 episódios registrados estão recuperáveis; faltam 954 de treino,
além das avaliações restantes, comparadores e análise final. Nenhum peso foi
alterado nessa conferência e nenhum resultado anterior foi apagado.

Às 12:42, a medida de espaço era 7,72 GiB. Uma estimativa conservadora para
os checkpoints/saídas restantes é 2,61 GiB adicionais: manter a reserva de
8 GiB exige cerca de **11 GiB livres antes da retomada**, mais margem para
consumo externo. A rodada permanece parada; baixar a reserva não foi adotado.
O monitor registrou a falha, mas não existe retomada automática dessa condição.
Retomar em saída nova com `--retomar-raiz`, mantendo contrato e pesos salvos;
preservar a pasta interrompida e seus arquivos de falha.

- [Diagnóstico, hashes e checkpoints recuperáveis](resultados/cologne8_corrigido/20261116_10sementes_500ep_v4/DIAGNOSTICO_PARADA_20261116.json).

### Limpeza de caches e retomada — 16/11, 13:08

Foram removidas somente as pastas de cache de instalação `tmp/uv-cache-dqn`
e `tmp/uv-cache-mpc`: 23.786 arquivos, somando 1,78 GiB lógicos. Os ambientes
Python instalados, modelos, checkpoints, demandas e resultados foram
preservados. Os hashes dos três checkpoints de emergência permaneceram iguais
antes e depois da exclusão. Os sete fontes de execução, a rede e a auditoria
também conferiram com o protocolo; Torch, NumPy e libsumo carregaram normalmente.

O tamanho lógico dos caches não equivale a espaço físico recuperado. O espaço
disponível variou durante a inspeção e já havia aumentado antes da exclusão;
não se atribui toda essa variação à limpeza. Na retomada havia **14,75 GiB
livres**, mantendo a reserva de 8 GiB e margem sobre os 10,61 GiB estimados.
Não foi necessário limpar caches dos navegadores ou remover outros arquivos.

A execução foi retomada em
`resultados/cologne8_corrigido/20261116_130813_10sementes_500ep_v4_retomada/`,
com `--retomar-raiz` apontando para a rodada interrompida. A saída anterior
permanece intacta. O executor primeiro refaz as avaliações das sementes 0–5
a partir de seus estados completos, sem repetir seus treinos. Depois continua
as sementes 6/7/8 após os episódios 359/350/337 e inicia a semente 9; restavam
954 episódios de treino ao lançar a retomada. Arquivos de falha da saída
anterior continuam como registro histórico, sem representar a nova execução.

```powershell
& '.venv-dqn-inferencia/Scripts/python.exe' -B -X utf8 semaforo/scripts/treinar_cologne8_corrigido.py --saida semaforo/resultados/cologne8_corrigido/20261116_130813_10sementes_500ep_v4_retomada --status
```

- [Registro da limpeza, preservação e processo de retomada](resultados/cologne8_corrigido/LIMPEZA_E_RETOMADA_20261116.json).

### Nova parada por espaço — 16/11, 15:09

A retomada chegou a **4701/5000 episódios (94,02%)**. As sementes 0–8
concluíram os treinos e seus testes; a semente 9 terminou o episódio 201.
Antes de iniciar o 202, a reserva de 8 GiB bloqueou a execução novamente.
O checkpoint `seed9/estado_ep0201.pt` foi salvo e carregado em CPU: nove
agentes, estado completo, tensores finitos e episódio correspondente ao
histórico. Pesos, redes-alvo, otimizadores, replay e RNG estão presentes.
Restam **299 episódios**, as avaliações restantes e a análise final.

Às 15:43 havia cerca de 5,1 GiB livres e nenhum processo do treinador ativo.
O espaço continuou variando mesmo após o encerramento do treino. A inspeção
encontrou um `git add --sparse --pathspec-from-file=- --pathspec-file-nul`
iniciado às 14:47, com `git-lfs filter-process` ativo; uma amostra de I/O
registrou aproximadamente 6,5 MB/s de gravação por esses processos. Os
objetos locais do LFS somavam 21.823.842.744 bytes e os objetos do Git
6.872.037.984 bytes, cerca de 26,7 GiB juntos. As datas de modificação
apontavam cerca de 8,2 GiB nesses dois locais nas três horas anteriores;
isso identifica consumo relevante do Git, sem provar que toda a variação
de espaço tenha uma única causa. Não foram apagados objetos do Git/LFS nem
interrompidos processos de origem ainda não confirmada.

A execução está parada e a previsão de horário anterior deixa de valer.
Antes de nova tentativa, resolver o consumo de disco e a cadeia de retomada:
a segunda raiz não contém estados completos das sementes 0–5, pois elas
foram restauradas da primeira. Usar somente essa raiz com o coordenador
atual faria essas sementes iniciarem novamente. Preservar ambas as raízes
e reutilizar seus estados e resultados ao preparar a próxima retomada.
Os fontes congelados do experimento permanecem inalterados.

- [Diagnóstico da segunda parada e verificação do checkpoint](resultados/cologne8_corrigido/20261116_130813_10sementes_500ep_v4_retomada/DIAGNOSTICO_PARADA_20261116_1509.json).

### Retomada somente da última semente — 16/11, 15:52

O `git add`/LFS encerrou e o espaço disponível voltou a 11,5 GiB, sem
exclusão de objetos do Git, pesos ou resultados. Para limitar novas indexações
volumosas, o `.gitignore` passou a excluir somente `estado_ep*.pt` nas pastas
`cologne8_corrigido` e `piloto_supervisor_cologne8`. Esses estados completos
continuam no disco para retomada; políticas selecionadas, métricas, históricos
e demais evidências continuam elegíveis para versionamento. Arquivos já
versionados não foram removidos do índice.

O novo `scripts/retomar_cologne8_corrigido.py` atende especificamente ao estado
auditado dessa interrupção: nove sementes concluídas e semente 9 salva no
episódio 201. Ele prepara uma saída nova, reutiliza os históricos, resumos e
testes concluídos e executa apenas o trabalhador da semente 9. Os 218 arquivos
copiados foram conferidos por SHA-256; nenhuma das nove sementes concluídas
foi treinada ou avaliada novamente. O manifesto, os sete fontes congelados,
os parâmetros de aprendizado, demandas, seleção e avaliações permanecem
iguais. Os caminhos originais dos episódios, validações e políticas continuam
apontando para as duas raízes anteriores, que precisam ser preservadas.

Saída ativa:
`resultados/cologne8_corrigido/20261116_10sementes_500ep_v4_retomada_final/`.
A retomada iniciou às 15:52 com 11,45 GiB livres, exigindo ao menos 11 GiB
antes do lançamento e mantendo a reserva original de 8 GiB durante o treino.
Às 15:52:50, a semente 9 já havia concluído o episódio 204. A conferência
confirmou próximo episódio restaurado 202, prefixo de 201 episódios idêntico
e aumento dos contadores de gradientes de todos os nove agentes. O pipeline
final continua usando o relatório congelado para conferir 6100 simulações
MARL, rodar os 20 comparadores, gerar o gráfico e conferir a preservação.

```powershell
& '.venv-dqn-inferencia/Scripts/python.exe' -B -X utf8 semaforo/scripts/treinar_cologne8_corrigido.py --saida semaforo/resultados/cologne8_corrigido/20261116_10sementes_500ep_v4_retomada_final --status
```

- [Preparação e origem das cópias](resultados/cologne8_corrigido/20261116_10sementes_500ep_v4_retomada_final/RETOMADA_SELETIVA.json), [verificação do protocolo](resultados/cologne8_corrigido/20261116_10sementes_500ep_v4_retomada_final/PREPARACAO_VERIFICADA.json) e [continuidade efetiva dos gradientes e histórico](resultados/cologne8_corrigido/20261116_10sementes_500ep_v4_retomada_final/RETOMADA_VERIFICADA.json).

### Conclusão da rodada v4 — 16/11, 17:29

**Os dez modelos concluíram 500 episódios cada: 5000 episódios de treino.**
O último episódio terminou às 16:58 e os testes da última semente terminaram
antes das 17:00. Às **17:29:55**, `TUDO_CONCLUIDO.json` confirmou treino,
análise e preservação completos. O relatório conferiu **6100 simulações MARL**
(5000 treinos, 1000 validações e 100 testes reservados), executou os **20
comparadores** e produziu o gráfico. Não houve erro de execução na retomada
final. A conferência confirmou os **30.624 arquivos protegidos**, as 218
cópias reutilizadas e o checkpoint de emergência anterior preservados.

Resultados médios no teste reservado, na mesma rede derivada e nas mesmas
dez demandas/sementes SUMO. MARL reúne dez inicializações por demanda (100
rodadas); cada comparador executa as dez demandas (10 rodadas).

| Controlador | Espera média (s) | Média dos P95 (s) | Contatos por rodada | Viagens não concluídas por rodada |
|---|---:|---:|---:|---:|
| MARL v4 com supervisor | 18,44 | 69,84 | 0,30 | 0,37 |
| Max-Pressure | 22,82 | 76,32 | 0,50 | 0 |
| Programa original na rede derivada | 39,03 | 126,54 | 0,30 | 0 |

A espera média do MARL foi **19,2% menor que Max-Pressure** e **52,8% menor
que o programa original** nesse teste. Isso não elimina as limitações:
houve **30 contatos em 24 dos 100 testes MARL**, e **37 viagens ficaram
pendentes em um desses testes**. Os comparadores concluíram todas as viagens.
O cenário continua permitindo contatos residuais; menor espera média não
estabelece segurança nem robustez em todas as demandas. A média dos P95 não
é o P95 de todos os veículos reunidos. A v4 não tem braço sem supervisor,
portanto não isola seu efeito causal, e suas médias não devem ser comparadas
diretamente às v2/v3, que usam outros protocolos/cenários.

Próxima análise: localizar a rodada com pendências e distinguir os contatos
das áreas controladas daqueles em cruzamentos sem controle, antes de definir
novas correções ou outro treinamento. Os checkpoints completos continuam
salvos localmente; nenhum deles foi removido ao encerrar a rodada.

- [Análise e dados das 120 rodadas de teste/comparação](resultados/cologne8_corrigido/20261116_10sementes_500ep_v4_retomada_final/ANALISE.json), [gráfico](resultados/cologne8_corrigido/20261116_10sementes_500ep_v4_retomada_final/curvas_comparacao.png), [preservação](resultados/cologne8_corrigido/20261116_10sementes_500ep_v4_retomada_final/PRESERVACAO.json) e [conclusão integral](resultados/cologne8_corrigido/20261116_10sementes_500ep_v4_retomada_final/TUDO_CONCLUIDO.json).

### Pacote publicado no Git

O pacote inclui os fontes do piloto v3 e da rodada corrigida v4, demandas,
redes derivadas, auditorias, históricos, métricas de todas as simulações,
políticas em Git LFS, resultados reservados/comparadores com seus XMLs e
gráficos. Alterações locais de DQN17/Cologne1/Cologne3 ficam fora desse commit.

Os estados completos `estado_ep*.pt` e os XMLs brutos dos diretórios de treino
e validação dessas duas rodadas permanecem **no arquivo local**, sem exclusão
ou alteração. O [índice de publicação](resultados/cologne8_corrigido/PACOTE_GIT_20261116.json)
registra os XMLs omitidos por caminho/tamanho/SHA-256, os estados locais e
os hashes dos dez estados finais de retomada e das políticas selecionadas.
Isso reduz o envio sem descartar os dados originais. Um clone contém as
métricas e evidências do teste, mas precisa desses XMLs locais para repetir
o recálculo integral das 6100 simulações e dos estados completos para retomar
o aprendizado. Não foi criado arquivo remoto externo desses dados locais.

Os JSONs preservam os caminhos absolutos da máquina que executou o experimento
como proveniência. Para repetir o treino, usar os comandos relativos acima e
ajustar `--sumo-home` à instalação disponível. Para reler resultados em outra
máquina, os caminhos originais precisam ser resolvidos na cópia de trabalho;
não se deve editar os registros de origem esperando manter seus hashes.
