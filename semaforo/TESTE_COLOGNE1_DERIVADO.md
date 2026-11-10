# Teste da DQN pronta em Colonia com fases adaptadas

Executado em 10 de novembro de 2026, apos a escolha explicita da usuaria por
uma versao derivada de cologne1 com uma aproximacao verde por vez.

O registro consolidado, os erros e as prioridades de continuidade estao em
[REGISTRO_COLOGNE1.md](REGISTRO_COLOGNE1.md).

## Resultado da rodada completa

Pasta: `resultados/cologne1_derivado/20261110T204551Z_seed1_e699817c/`.

| Indicador | Resultado |
|---|---:|
| Semente SUMO | 1 |
| Periodo de chegada | 25200 a 28800 s, uma hora |
| Escoamento adicional executado | 44 s |
| Viagens programadas / inseridas / concluidas | 2015 / 2015 / 2015 |
| Viagens interrompidas | 0 |
| Demanda vencida nao inserida ao final | 0 |
| Veiculos remanescentes | 0 |
| Espera media dentro da rede | 37,40 s |
| P95 da espera dentro da rede | 191 s |
| Espera maxima dentro da rede | 383 s |
| Atraso medio antes da insercao | 4,36 s |
| Fila media nas oito faixas de entrada, incluindo escoamento | 17,32 veiculos |
| Fila media no periodo de chegada | 17,46 veiculos |
| Fila maxima nas oito faixas de entrada | 42 veiculos |
| Decisoes da DQN | 339 |
| Intervencoes externas na escolha da DQN | 0 |
| Colisoes / teletransportes | 0 / 0 |
| Parametros da rede e arquivos preexistentes preservados | Sim |

A rodada completa usou SUMO-GUI 1.28.0; a janela foi observada no desktop durante
a simulacao. O relogio final foi 28844 s. Nao foi executada uma bateria de sementes.

### Espera da viagem por aproximacao

A aproximacao e a primeira entrada controlada presente na rota efetivamente
atribuida ao veiculo. A espera e a da viagem inteira dentro da rede, inclusive
em trechos anteriores ao semaforo. Nao e apenas a espera na faixa junto a linha
de parada e nao inclui o atraso antes da insercao.

| Aproximacao | Viagens | Media | P95 | Maximo |
|---|---:|---:|---:|---:|
| N | 313 | 100,49 s | 271 s | 304 s |
| L | 572 | 25,96 s | 96 s | 383 s |
| S | 688 | 19,42 s | 62 s | 209 s |
| O | 438 | 35,52 s | 123 s | 309 s |
| Sem passagem por uma entrada controlada | 4 | 35,00 s | 140 s | 140 s |

O P95 e as diferencas entre aproximacoes mostram esperas altas para parte dos
veiculos nesta rodada. A origem dessa desigualdade exige analise adicional;
nao foi isolado o efeito de geometria, demanda, observacao ou politica.

## Experimento implementado

- Checkpoint: `modelos/dqn_fila.pt`, SHA-256
  `4df5afec39207e621f9e1e83a7917153283cce053db1cdb2fd0dac8113596a41`.
- Carregamento `torch.load(..., map_location="cpu", weights_only=True)` com
  `load_state_dict(..., strict=True)` na classe `Rede` original do projeto.
- `eval()`, `requires_grad_(False)` e `torch.inference_mode()`. Nao ha exploracao,
  otimizador, replay, aprendizagem ou escrita de checkpoint no runner.
- Observacao criada com filas e contagens nas duas faixas da entrada de cada
  aproximacao, em N/L/S/O. Usa a funcao original `estado_para_vetor`:
  filas/25, contagens/35, one-hot da aproximacao verde, `min(tempo_verde/60, 2)`.
- Acoes 0/1/2/3 correspondem a N/L/S/O. A escolha e sempre `argmax(Q)`.
- Decisao na grade de 5 s, somente em verde apos cumprir 10 s de verde real.
  Trocas executam 3 s de amarelo e 2 s de vermelho geral.
- A contagem temporal e corrigida: difere do erro de 1 s de vermelho geral e
  do segundo excedente de verde da implementacao local usada no treino antigo.
  Essa diferenca e registrada como parte da transferencia, sem retreinamento.
- Nao foi adicionado verde maximo nem mecanismo extra de atendimento. As
  transicoes e o minimo de verde limitam quando a rede pode decidir; nenhuma
  escolha feita numa decisao foi substituida por regra externa.
- O teletransporte foi desabilitado e a deteccao de colisoes no cruzamento foi
  ativada. Colisao ou teletransporte fazem o teste encerrar para revisao.

### Rede e demanda

Referencia: arquivos oficiais de SUMO-RL 1.4.5 ja auditados em
`semaforo/referencias/sumo_rl_1.4.5/sumo_rl/nets/RESCO/cologne1/`, relativamente
a raiz do repositorio. A origem e o hash do pacote estao em `proveniencia.json`
na pasta `sumo_rl_1.4.5`.

As execucoes historicas usaram uma copia identica em `tmp/cologne1_auditoria/`.
Na organizacao da branch, os arquivos foram copiados byte a byte para o caminho
versionado acima; os logs antigos mantem seus caminhos originais. A copia em
`tmp/` permanece local, sem fazer parte do commit.

O arquivo de rotas e usado diretamente, sem reescrever seus 2015 trips nem seus
parametros veiculares. Uma copia de `cologne1.net.xml` e criada em cada execucao,
substituindo somente `tlLogic`. O runner verifica por XML que todo o restante da
rede permanece igual, e compara hashes das fontes antes/depois.

| Acao | Aproximacao | Edge | Fase verde XML da copia |
|---|---|---|---:|
| 0 | N | `27115123#3` | 0 |
| 1 | L | `-32038056#3` | 3 |
| 2 | S | `23429231#1` | 6 |
| 3 | O | `28198821#3` | 9 |

Cada verde e seguido de amarelo e vermelho geral no programa copiado. Os links
sao extraidos das conexoes da rede. A geometria confirma a rotulacao geografica,
a matriz `foes` nao indica conflitos entre movimentos da mesma fase criada, e
o mapeamento e novamente conferido pelo TraCI antes da primeira inferencia.

Durante o controle, `setRedYellowGreenState` usa o programa `online` do SUMO.
Por isso, o indice interno retornado por `getPhase()` nao deve ser confundido
com o indice XML da copia nem com o indice da acao. Ambos sao registrados,
assim como o estado real das luzes. O log de fases liga a aplicacao de cada verde
a decisao correspondente, incluindo os estagios intermediarios.

## Arquivos do teste

- `scripts/testar_dqn_cologne1.py`: runner independente; os scripts anteriores
  de treino/avaliacao nao foram alterados.
- `requirements-inferencia.txt`: versoes do ambiente CPU usado.
- Em cada pasta nova de execucao: `configuracao.json`, copia de rede derivada,
  `decisoes.jsonl`, `fases.jsonl`, `serie.csv`, `tripinfo.xml`,
  `estatisticas_sumo.xml`, `colisoes.xml`, `avisos_sumo.log` e `resultado.json`.
- Na rodada completa citada acima: `verificacao_final.json` registra as
  verificacoes adicionais das 339 decisoes e dos 585 eventos de fase.

`decisoes.jsonl` contem semente, filas/contagens brutas, vetor de 13 valores,
quatro valores Q, argmax, aproximacao solicitada e estado realmente executado
naquele momento. Ao trocar, esse estado inicialmente e amarelo; o verde alvo
aparece depois em `fases.jsonl`. `serie.csv` registra filas e contagens a cada
segundo. Valores invalidos, dimensoes diferentes ou divergencia de fases fazem
a execucao falhar, sem adaptar silenciosamente a entrada/acao.

## Executar novamente

Com o ambiente `.venv-dqn-inferencia` preparado, na raiz do repositorio:

```powershell
# Verificacao curta, sem GUI e sem escoamento
& '.venv-dqn-inferencia/Scripts/python.exe' -B -X utf8 `
  semaforo/scripts/testar_dqn_cologne1.py `
  --sumo-home '../tools/sumo-win64-1.28.0' `
  --duracao 300 --escoamento 0 --sementes 1

# Rodada completa com GUI
& '.venv-dqn-inferencia/Scripts/python.exe' -B -X utf8 `
  semaforo/scripts/testar_dqn_cologne1.py `
  --sumo-home '../tools/sumo-win64-1.28.0' `
  --duracao 3600 --escoamento 1200 --sementes 1 --gui --delay-ms 10
```

Os caminhos acima sao relativos a raiz; o repositorio pode estar em outra
pasta. Ajuste `--sumo-home` para uma instalacao real contendo `bin` e `tools`.
`--sumo-rl-source`, `--checkpoint` e `--output-root` permitem informar outros
caminhos. O default das fontes deriva da posicao do proprio script no repo.
Para testes posteriores o script aceita, por exemplo, `--sementes 1 2 3`, mas
essa bateria nao foi executada. Para rodar sem janela, omita `--gui`.

Em uma copia nova, e preciso preservar os arquivos de referencia do cenario e
criar um novo ambiente Python 3.12. Depois de criar esse ambiente com `venv` ou
`uv venv`, instale `semaforo/requirements-inferencia.txt` nele. O teste usou
Python 3.12.14, PyTorch 2.15.0+cpu, NumPy 2.5.4 e o TraCI distribuido no SUMO 1.28.0.
Nenhuma dependencia global foi substituida.

## Verificacoes e tentativas preservadas

1. `20261110T204050Z_seed1_56fff472`: verificacao de 300 s aprovada, 33 decisoes,
   143 viagens concluidas e 49 ainda na rede no corte curto. Zero colisoes.
2. `20261110T204121Z_seed1_7d0f4b46`: tentativa GUI interrompida depois de 1800 s,
   apos solicitar captura de imagem por TraCI em execucao isolada do desktop.
   O XML parcial nao representa uma rodada completa; a tentativa foi preservada
   com `falha_gui.json`. O bloqueio nao foi usado como resultado de desempenho.
3. Foi removida a captura automatica por TraCI do runner. Foi acrescentado
   tratamento de XML parcial para preservar diagnostico quando houver falha.
4. `20261110T204534Z_seed1_6369d66d`: verificacao GUI de 60 s aprovada no desktop.
5. `20261110T204551Z_seed1_e699817c`: rodada completa aprovada, sem a captura
   automatica, com GUI acessivel e observada pelo controle do computador.

Na rodada final foram conferidos: ordem/escala das 13 entradas, quatro Qs
finitos, argmax, amarelos de 3 s, vermelhos gerais de 2 s e verdes de pelo menos
10 s (excluindo segmento terminal incompleto). As contagens de chegadas do
TraCI e do tripinfo concordam em 2015. Os parametros em memoria e o checkpoint
em disco permaneceram iguais. `git diff` nao mostrou alteracao de arquivos
versionados preexistentes.

## O que este teste permite concluir

A DQN pronta foi executada sem retreinamento e conseguiu atender toda a demanda
desta rodada do cenario derivado, respeitando as transicoes implementadas. A
espera apresentou cauda alta e distribuicao desigual entre aproximacoes.

Nao e uma avaliacao no cologne1/RESCO original: o programa de fases foi alterado.
Uma unica semente, sem controladores comparadores nesta mesma configuracao, nao
demonstra superioridade, robustez ou generalizacao ampla. Comprimentos das faixas
observadas variam muito entre aproximacoes; isso difere do treino original. A
fila medida cobre somente as oito faixas imediatas, nao todos os trechos a
montante. Os 37,40 s de espera nao incluem os 4,36 s medios antes da insercao.
O P95 e calculado por selecao do elemento `round(0.95 * (n - 1))` da lista
ordenada, como no projeto original. Nao foram comparados diretamente estes
numeros com os resultados do cruzamento original.
