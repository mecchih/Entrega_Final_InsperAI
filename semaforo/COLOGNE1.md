# Auditoria da DQN pronta no cologne1

Este documento registra a etapa inicial, anterior à autorização do cenário
derivado. A continuação, os resultados completos e a organização da branch
estão em [REGISTRO_COLOGNE1.md](REGISTRO_COLOGNE1.md).

Auditoria realizada em 10 de novembro de 2026. Resultado: **teste de inferência
bloqueado por incompatibilidade semântica das ações**. Nenhuma rede foi treinada,
nenhum peso foi alterado e nenhuma inferência foi executada.

## Arquivos e versões verificados

- Git inicial: `main`, commit `652e773`, sem alterações locais. Não foram
  encontrados `AGENTS.md` no repositório ou nos diretórios ancestrais acessíveis.
  Foram lidos o README e `semaforo/LEIA-ME.md`.
- Modelo escolhido para auditoria: `semaforo/modelos/dqn_fila.pt`.
- Definição e treinamento: `scripts/dqn.py`, `scripts/treinar_dqn.py` e
  `scripts/simulacao.py`. Esta cópia ainda contém a dinâmica original, sem modos A/B/C.
- SUMO encontrado e executado: **1.28.0**, instalação portátil em
  `../tools/sumo-win64-1.28.0`, relativamente à raiz deste repositório nesta máquina.
  O executável GUI existe, mas não foi aberto porque a inferência foi bloqueada.
- Interpretador utilizado: Python 3.12.14 do runtime local. Nele não foram
  encontradas distribuições instaladas de PyTorch, SUMO-RL, TraCI ou libsumo.
  Isso não afirma a ausência de outras instalações Python no computador.
- Foi usado o **TraCI incluído em tools/ da instalação SUMO 1.28.0**, sem instalar
  pacotes ou alterar o PATH/SUMO_HOME do sistema.
- Foi baixado o wheel oficial **SUMO-RL 1.4.5 do PyPI**, sem instalar suas dependências.
  Foram extraídos somente cenário, fontes necessários, metadados e licença em
  `tmp/cologne1_auditoria/sumo_rl_1.4.5/`, relativamente à raiz do repositório.
  Essa pasta é uma referência de código, não uma instalação funcional do SUMO-RL.
  `proveniencia.json` registra URL, versão e SHA-256 conferido contra o PyPI.

O SHA-256 do checkpoint é
`4df5afec39207e621f9e1e83a7917153283cce053db1cdb2fd0dac8113596a41`.
O checkpoint contém somente o state_dict, sem metadados completos do ambiente de
treinamento. Sua correspondência histórica com esse código não é certificada
pelo próprio arquivo; arquitetura e dimensões são consistentes com o projeto.

## Contrato real da DQN

Rede: `13 -> 64 -> 64 -> 4`, ReLU após cada camada oculta. Os tensores do checkpoint
têm dimensões `[64,13]`, `[64]`, `[64,64]`, `[64]`, `[4,64]`, `[4]`.
Todos os valores armazenados são finitos. A inspeção foi estrutural, sem
`torch.load`, sem instanciar a rede e sem calcular valores Q.

| Índices | Conteúdo, exatamente nessa ordem | Transformação |
|---|---|---|
| 0–3 | Filas N, L, S, O | Soma de `getLastStepHaltingNumber` nas duas faixas de cada aproximação, dividida por 25 |
| 4–7 | Veículos presentes N, L, S, O | Soma de `getLastStepVehicleNumber` nas duas faixas, dividida por 35 |
| 8–11 | Aproximação verde N, L, S, O | One-hot da única aproximação selecionada |
| 12 | Contador de tempo no verde | `min(tempo_no_verde / 60, 2)` |

Filas e contagens não recebem clipping em 1. A entrada é float32.
O tempo usado é o contador do motor, que possui a diferença descrita abaixo.

O vetor não inclui espera acumulada, densidade por capacidade, nome do cenário
ou tempo absoluto da simulação. Não basta produzir quaisquer 13 números.

| Saída Q | Significado no treinamento | Fase verde no XML original | Entrada liberada |
|---|---|---|---|
| 0 | N | 0 | `top0A0`, faixas 0 e 1 |
| 1 | L | 2 | `right0A0`, faixas 0 e 1 |
| 2 | S | 4 | `bottom0A0`, faixas 0 e 1 |
| 3 | O | 6 | `left0A0`, faixas 0 e 1 |

O motor coleta as fases verdes na ordem do programa do semáforo `A0`.
Conferindo `connection/@linkIndex`, cada uma abre todos os movimentos daquela
única entrada, com `G`; as outras três permanecem vermelhas. O XML também contém
retornos, embora o gerador de demanda do projeto use reto/direita/esquerda.

### Tempos e treinamento

- Decisões na grade de 5 s, condicionadas ao contador de verde mínimo de 10 s;
  durante transições o controlador não é consultado.
- Constantes: amarelo 3 s e vermelho geral 2 s.
- A rotina original tem um erro de contagem: o novo verde é aplicado antes do
  último `simulationStep` do vermelho geral. O vermelho integral executado é 1 s.
- O agendamento também mantém o verde antigo no passo em que a troca é solicitada.
  Executando o laço original com uma API falsa, sem DQN, e pedindo troca assim que
  permitido, a sequência registrada é **11 s verde, 3 s amarelo, 1 s vermelho**.
  Esse teste de lógica não é uma simulação de trânsito nem uma nova avaliação.
- A DQN não possui limite máximo de verde nesta cópia. O limite de 60 s do
  Max-Pressure não se aplica automaticamente à DQN. A entrada de tempo satura em 120 s.
- Os históricos locais possuem 250 episódios; o checkpoint de fila foi escolhido
  na validação do episódio 250. Treino usa quatro cenários e seeds `1000 + episódio`;
  validação usa 201/202. O cenário girado não participa dessa seleção.
- O checkpoint não contém otimizador, replay ou estado de exploração. Nada foi retomado.

## Contrato real do cologne1

Arquivos extraídos do wheel oficial:

```text
tmp/cologne1_auditoria/sumo_rl_1.4.5/
  sumo_rl/nets/RESCO/cologne1/cologne1.net.xml
  sumo_rl/nets/RESCO/cologne1/cologne1.rou.xml
  sumo_rl/nets/RESCO/cologne1/cologne1.sumocfg
  sumo_rl/environment/{env,traffic_signal,observations,resco_envs}.py
```

Há um semáforo: **`GS_cluster_357187_359543`**, programa `0`, 20 links controlados,
oito faixas de entrada e quatro fases verdes. A configuração RESCO define
`begin_time=25200` e duração de 3600 s, até 28800. O arquivo de demanda contém
2015 elementos `trip`; isso não é uma contagem de viagens concluídas.

As entradas, identificadas pelos movimentos e pela geometria das faixas, são:

| Referência geográfica aproximada | Edge de entrada |
|---|---|
| N | `27115123#3` |
| L | `-32038056#3` |
| S | `23429231#1` |
| O | `28198821#3` |

Esses rótulos descrevem a geometria. Não foram usados como remapeamento de ações.

| Ação SUMO-RL | Fase no XML | Movimentos efetivamente liberados |
|---|---|---|
| 0 | 0 | N e S: reto/direita com `G`; esquerda/retorno permissivos com `g` |
| 1 | 2 | N e S: somente esquerda/retorno com `G` |
| 2 | 4 | L e O: reto/direita com `G`; esquerda/retorno permissivos com `g` |
| 3 | 6 | L e O: somente esquerda/retorno com `G` |

O mapeamento acima vem de `phase/@state` cruzado com `connection/@linkIndex`,
`from`, `to`, `fromLane`, `toLane` e `dir`. Não foi deduzido apenas pelo índice.
Os 20 links, os estados de todas as fases e o ID também foram conferidos no
SUMO 1.28.0 por TraCI, sem avançar a simulação.

### Observação e transições do SUMO-RL 1.4.5

A observação padrão é `one_hot_fase + flag_min_green + densidades_por_faixa +
filas_por_faixa`: **4 + 1 + 8 + 8 = 21 valores**. Densidades/filas são divididas
pela capacidade estimada da faixa e limitadas a 1. A ordem de faixas é determinada
pelos links controlados, não pela ordem N/L/S/O do projeto.

Seria possível agregar contagens por entrada usando TraCI e aplicar os divisores
25/35. Entretanto, não há uma única aproximação verde para montar os quatro
indicadores esperados pelo modelo: cada fase atende duas entradas e pode atender
somente parte de seus movimentos. Uma observação personalizada, sozinha, não
resolve a incompatibilidade.

No XML, os verdes têm durações 29/6/29/6 s e os amarelos 5 s; não há fase de
vermelho integral. Os atributos dos verdes são `minDur=5`, `maxDur=50`.
Isso é diferente do programa reconstruído pelo SUMO-RL:

- A versão 1.4.5 cria quatro verdes e transições amarelas entre pares de fases.
- Os defaults de `SumoEnvironment` são `delta_time=5`, `yellow_time=2`,
  `min_green=5` e `max_green=50`.
- `max_green` é armazenado, mas não é aplicado nessa versão. O código atual da
  branch main na internet pode ter comportamento diferente; não foi usado em
  substituição ao código 1.4.5 auditado.
- Não há vermelho geral no controle dessa versão. Links que permanecem abertos
  na nova fase podem permanecer verdes durante a transição.
- As restrições podem manter a fase atual apesar da ação solicitada. O relógio
  de mudança inclui amarelo e não equivale diretamente ao contador da DQN.

## Resultado e limite da verificação

Relatório final desta auditoria:
`resultados/cologne1_auditoria/20261110T200239Z_2e552059/auditoria.json`.
O log de carregamento do SUMO está na mesma pasta. As tentativas anteriores
também foram preservadas; a tentativa intermediária `20261110T200229Z_e53784e6`
registrou um erro no instrumento de auditoria, corrigido antes da execução final.

- Dimensões e valores finitos do checkpoint: conferidos, sem inferência.
- Carregamento de rede e rotas no SUMO: passou, seed 1, relógio em 25200.
- Estados de fases e links XML versus SUMO: conferem.
- Compatibilidade das ações: **reprovada**. Quatro saídas não significam quatro ações equivalentes.
- Teste curto com DQN, valores Q, métricas de desempenho e rodada completa:
  **não executados**, conforme a condição de parada solicitada.
- Nenhuma observação foi enviada à rede. Não houve exploração, atualização,
  seleção de ação ou intervenção de controlador. Métricas de espera, P95, fila,
  chegadas e viagens interrompidas não foram produzidas.
- Hashes SHA-256 de todos os pesos e JSONs de resultados preexistentes: iguais
  antes/depois. Nenhum arquivo preexistente foi editado ou movido.

O script novo é deliberadamente de **auditoria, não de inferência**. Não existe
comando legítimo de rodada completa com a DQN pronta no cologne1 original neste
estado. Não foi criado um runner que fingisse compatibilidade.

## Reproduzir a auditoria

Na raiz de qualquer cópia deste repositório, com os arquivos de referência
preservados e um Python 3.10 ou posterior:

```powershell
python -B semaforo/scripts/auditar_cologne1.py `
  --sumo-rl-source semaforo/referencias/sumo_rl_1.4.5
```

Nesta máquina, `python` não estava no PATH. O interpretador efetivamente usado foi:

```powershell
$pythonExe = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $pythonExe -B -X utf8 semaforo/scripts/auditar_cologne1.py `
  --sumo-rl-source semaforo/referencias/sumo_rl_1.4.5 `
  --sumo-home '../tools/sumo-win64-1.28.0'
```

Em outro computador, informe `--sumo-home` com uma instalação real que contenha
`bin/sumo` e `tools/traci`. A opção é facultativa e somente carrega/confronta os
arquivos com o simulador, sem executar passos. O checkpoint pode ser selecionado
com `--checkpoint`. Todas as saídas vão para subpastas novas com timestamp/UUID;
nenhum resultado existente é sobrescrito. O retorno **2** significa a recusa
esperada por incompatibilidade; **1** indica erro ou revisão manual necessária.

## Menor próximo passo necessário

Decidir explicitamente qual experimento se deseja:

1. **Manter o cologne1/RESCO original:** é necessário um checkpoint cuja
   observação e ações correspondam às fases do cenário. A DQN atual não satisfaz
   esse contrato. Criar/treinar outro modelo está fora desta solicitação.
2. **Preservar os pesos atuais:** estudar e autorizar uma cópia derivada do cenário
   com quatro fases de uma aproximação por vez, validar movimentos, conflitos e
   transições e definir a observação personalizada. Isso altera o programa
   semafórico do benchmark e deve ser apresentado como um cenário derivado de
   cologne1, não como o cologne1/RESCO original. Não foi feito nesta auditoria.

Trocar a ordem das saídas, duplicar fases, somar valores Q ou reinterpretar um
one-hot seriam adaptações de política, não meras conversões de formato. Não
foram feitas silenciosamente. A auditoria demonstra incompatibilidade de
interface; não demonstra bom ou mau desempenho da DQN em Colônia.

Fontes oficiais: [SUMO-RL no PyPI](https://pypi.org/project/sumo-rl/1.4.5/),
[repositório SUMO-RL](https://github.com/LucasAlegre/sumo-rl),
com versão e hashes locais documentados em `proveniencia.json` e no JSON final.
