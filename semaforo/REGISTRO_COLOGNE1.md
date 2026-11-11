# Registro consolidado — transferência da DQN para Colônia

Data: **10 de novembro de 2026**, fuso `America/Sao_Paulo`.
Branch: **`experimento/dqn-cologne1-derivado`**, criada a partir de `main` no
commit `652e773`. Não foi feito merge, reset, rebase, treinamento ou push.

Este é o ponto de entrada para quem continuar o trabalho sem ler a conversa.
Os documentos anteriores permanecem disponíveis:

- [Auditoria inicial do cologne1](COLOGNE1.md): contrato do modelo e incompatibilidade original.
- [Relatório da simulação derivada](TESTE_COLOGNE1_DERIVADO.md): implementação, resultados e comandos.
- [Índice das nove execuções](resultados/indice_execucoes_cologne1.json): classificação, arquivos e hashes SHA-256.

## 1. Objetivo e estado final

O objetivo autorizado foi testar **a DQN já treinada**, sem alterar os pesos,
inicialmente no cenário cologne1 de SUMO-RL/RESCO. A auditoria demonstrou que a
interface de ações não era equivalente. A inferência foi interrompida nessa
etapa, antes de reinterpretar saídas silenciosamente.

A usuária então escolheu explicitamente **manter ruas e demanda de Colônia e
adaptar o programa para uma aproximação verde por vez**. Essa versão derivada
foi implementada e testada, inclusive com SUMO-GUI. A rodada principal terminou
com 2015 viagens concluídas, sem carros remanescentes, colisões ou teletransportes.

**Não é uma avaliação no benchmark cologne1/RESCO original.** A alteração das
fases e da contagem temporal faz parte do experimento. Ainda não existe uma
comparação com baselines nessa mesma versão, nem uma bateria de sementes.

## 2. O que havia no repositório

A cópia local tinha um modelo de fila (`dqn_fila.pt`), um modelo de espera
(`dqn_espera.pt`), históricos de 250 episódios e avaliações do cruzamento
original. Os arquivos de definição da rede, geração de demanda, controle,
treinamento e avaliação já existiam e foram lidos; a DQN não foi criada aqui.

O resumo externo de 9/11 descrevia três modelos de fila, instrumentação e modos
A/B/C. Esses arquivos não estavam nesta cópia. Não foram reconstruídos nem
declarados como implementados nesta branch. Se estiverem com outro integrante,
precisam ser reconciliados separadamente antes de continuar o treinamento.

O README do projeto original e os resultados históricos continuam intactos.
Afirmações antigas de superioridade/generalização não devem ser transferidas
automaticamente para este experimento.

## 3. Contrato confirmado da DQN

Checkpoint testado: `modelos/dqn_fila.pt`.
SHA-256: `4df5afec39207e621f9e1e83a7917153283cce053db1cdb2fd0dac8113596a41`.

| Componente | Contrato encontrado |
|---|---|
| Rede | Double DQN no treinamento; MLP 13 → 64 → 64 → 4, ReLU nas camadas ocultas |
| Entradas 0–3 | Filas N/L/S/O, somadas nas duas faixas de cada entrada, divididas por 25 |
| Entradas 4–7 | Veículos presentes N/L/S/O, divididos por 35 |
| Entradas 8–11 | One-hot da única aproximação verde: N/L/S/O |
| Entrada 12 | `min(tempo_no_verde / 60, 2)` |
| Saídas 0/1/2/3 | Dar verde a N/L/S/O, respectivamente |
| Exploração no teste | Zero; escolha `argmax(Q)` |
| Aprendizagem no teste | Nenhuma; sem otimizador ou replay no runner |

O teste instancia somente `Rede`, carrega o state_dict com `strict=True`, usa
`eval()`, congela os parâmetros e calcula Q dentro de `torch.inference_mode()`.
Não instancia um novo agente para treinar. Confere valores finitos, dimensões,
igualdade dos parâmetros em memória e hashes dos arquivos protegidos.

## 4. Por que o cenário original foi recusado

As quatro ações do cologne1 não são as quatro aproximações do nosso modelo:

| Ação SUMO-RL | Fase no XML original | Significado |
|---|---:|---|
| 0 | 0 | Movimentos de N e S; inclui conversões permissivas |
| 1 | 2 | Esquerda/retorno de N e S |
| 2 | 4 | Movimentos de L e O; inclui conversões permissivas |
| 3 | 6 | Esquerda/retorno de L e O |

Os links, movimentos, faixas e estados de luz foram lidos do XML e conferidos
via TraCI no SUMO 1.28.0. O semáforo é `GS_cluster_357187_359543`.
Não foi assumido que índices numericamente iguais tivessem o mesmo significado.

A observação padrão do SUMO-RL 1.4.5 tem **21 valores**, com fase, indicador de
verde mínimo, densidades e filas normalizadas por faixa. A DQN requer 13 valores
com outra ordem e escala. Uma observação personalizada resolveria as contagens,
mas não transformaria fases de duas entradas em uma única aproximação verde.

## 5. O que foi adaptado e o que foi preservado

### Adaptações executadas

- Em cada execução, uma cópia da rede recebe quatro verdes, um por aproximação.
  O programa original de referência não é reescrito.
- O estado é montado com medições TraCI e transformado pela função original
  `estado_para_vetor`; a observação padrão do SUMO-RL não é enviada à DQN.
- Verde mínimo real de 10 s, amarelo de 3 s e vermelho geral de 2 s. Decisões
  na grade de 5 s, somente fora das transições e após o mínimo.
- A contagem temporal do runner é corrigida. A rotina original de treino
  executava 3 s de amarelo, 1 s de vermelho geral e um segundo excedente de
  verde quando a troca era solicitada. Essa diferença foi registrada, não
  escondida, e a rotina antiga não foi alterada.
- Não foi adicionado verde máximo nem regra extra para substituir ações da rede.

### Preservações verificadas

- Pesos, históricos e resultados anteriores: sem sobrescrita, exclusão ou movimentação.
- Arquitetura, significado das saídas e normalização: mantidos.
- Ruas, conexões e demais elementos da rede: iguais após remover `tlLogic`
  das duas árvores XML para comparação.
- Rotas, os 2015 trips e parâmetros dos veículos: arquivo original usado diretamente.
- Referências externas: copiadas byte a byte de `tmp/` para `referencias/`.
- Tentativas com erro e XMLs parciais: mantidos, identificados como tal.

O mapeamento N/L/S/O foi conferido pela geometria. A matriz `foes` não aponta
conflitos entre os movimentos abertos em cada fase criada, e os links são
conferidos novamente no simulador antes de inferir. Isso é uma verificação do
cenário simulado; não é validação de segurança para uso em via real.

## 6. Resultados da rodada principal

Execução **`20261110T204551Z_seed1_e699817c`**, em
`resultados/cologne1_derivado/`. Os identificadores de pasta usam timestamps UTC.

| Indicador | Valor |
|---|---:|
| Semente SUMO | 1 |
| Demanda | 25200–28800 s, uma hora |
| Tempo total executado | 3644 s |
| Escoamento após a demanda | 44 s |
| Viagens programadas / inseridas / concluídas | 2015 / 2015 / 2015 |
| Interrompidas / não inseridas vencidas / remanescentes | 0 / 0 / 0 |
| Espera média dentro da rede | 37,4015 s |
| P95 / máximo da espera | 191 / 383 s |
| Atraso médio antes da inserção | 4,3648 s |
| Fila média nas oito faixas imediatas, com escoamento | 17,3159 veículos |
| Fila média no período de demanda / fila máxima | 17,4594 / 42 veículos |
| Decisões / eventos de fase | 339 / 585 |
| Intervenções externas / colisões / teletransportes | 0 / 0 / 0 |

### Distribuição por aproximação

| Grupo | Viagens | Espera média | P95 | Máximo |
|---|---:|---:|---:|---:|
| N | 313 | 100,4856 s | 271 s | 304 s |
| L | 572 | 25,9633 s | 96 s | 383 s |
| S | 688 | 19,4215 s | 62 s | 209 s |
| O | 438 | 35,5228 s | 123 s | 309 s |
| Rota sem entrada controlada | 4 | 35,0000 s | 140 s | 140 s |

O grupo é a primeira aproximação controlada da rota efetiva. A métrica atribui
a espera da viagem inteira dentro da rede, inclusive em trechos anteriores ao
semáforo; não mede somente a espera na linha de parada. Quatro viagens não
passaram por uma entrada controlada e continuam incluídas no total de 2015.

O P95 usa o elemento de índice `round(0.95 * (n - 1))` da lista ordenada.
O atraso de inserção é separado e não está nos 37,4015 s de espera. Os quantis
dessas duas variáveis não podem ser somados para formar um P95 total.

### Interpretação sustentada

A política pronta foi executável nesse contrato adaptado e atendeu toda a
demanda dessa rodada. Ao mesmo tempo, houve cauda alta e desigualdade entre
aproximações. Isso não demonstra superioridade sobre regras clássicas nem
generalização para outra geometria em sentido amplo. Não houve comparação
direta com os números do cruzamento de treino.

## 7. Tentativas, erros, correções e acertos

| Etapa | Registro | Ocorrência e encaminhamento |
|---|---|---|
| Auditoria inicial | `200115Z_4761eba3` | Recusa correta das ações incompatíveis; sem inferência |
| Instrumento de auditoria | `200229Z_e53784e6` | `NameError: REDE` no ambiente falso usado para conferir tempos; corrigido apenas no instrumento |
| Auditoria corrigida | `200239Z_2e552059` | Conferiu XML/TraCI e contagem temporal; manteve a recusa do cenário original |
| Preparação do checkpoint | `88daf1ff4102` | Carregamento estrito, modo avaliação, parâmetros congelados; ainda sem inferência |
| Teste curto headless | `204050Z_seed1_56fff472` | 300 s, 33 decisões, 143 chegadas; 49 viagens ainda na rede no corte curto |
| Primeira tentativa GUI | `204121Z_seed1_7d0f4b46` | Parou de avançar após a captura TraCI aos 1800 s; processo exclusivo encerrado; XML ficou parcial |
| Recuperação da GUI | código do runner | Removida captura automática; acrescentado tratamento de XML parcial para registrar falhas |
| Teste GUI no desktop | `204534Z_seed1_6369d66d` | 60 s, 5 decisões, 7 chegadas; 15 interrompidas e 1 não inserida no corte curto, não um fracasso de escoamento completo |
| Rodada principal GUI | `204551Z_seed1_e699817c` | Hora completa + 44 s; 2015 chegadas e nenhuma interrupção; janela observada no desktop |
| Organização da branch | `verificacao_organizacao/20261110T210016Z_seed1_f377b74b` | Teste de 60 s aprovado usando o novo caminho padrão versionado das referências |

Os prefixos acima abreviam os nomes completos; o índice JSON contém os caminhos
exatos. A primeira tentativa GUI não tem `resultado.json` completo. Seu
`falha_gui.json` identifica o encerramento e os arquivos parciais não entram
nas métricas da rodada principal. A causa exata do bloqueio gráfico não foi
isolada; a sequência temporal aponta a captura como ponto de parada.

Outras dificuldades operacionais resolvidas:

- `python` não estava no PATH; foi localizado o Python do runtime e criado
  `.venv-dqn-inferencia`, separado das dependências globais.
- PyTorch não estava instalado no interpretador inicialmente inspecionado.
  Foi instalado o build CPU oficial no ambiente isolado. Um aviso transitório
  de renomeação do cache durante a instalação foi seguido por conclusão normal.
- Acesso à rede e escrita em `.git` precisaram da autorização da ferramenta;
  as operações autorizadas foram concluídas. Nenhuma configuração de segurança
  ou de identidade Git foi alterada.
- O primeiro acesso à janela por caminho de executável não correspondia à API
  Windows disponível; a seleção foi refeita por inventário e ID da janela.
- Ao preparar o arquivo histórico de código, as chaves do snapshot usavam
  separadores Windows. A primeira consulta por caminho POSIX falhou antes de
  gravar o índice. Os separadores foram normalizados e os hashes conferidos.

### Uma pendência de repetibilidade já observada

As duas tentativas GUI usaram seed 1, mas seus registros em instantes comuns
não foram idênticos. A primeira diferença de observação encontrada está em
25730 s, ou 530 s decorridos: ambas tinham as mesmas filas, mas a contagem de
veículos em O era 8 na tentativa interrompida e 6 na rodada válida. As versões
do runner e o contexto de execução gráfica eram diferentes; não foi realizado
um experimento controlado para identificar a causa. Portanto, não se promete
reprodução bit a bit apenas por repetir a semente. A rodada válida tem seus
próprios dados brutos completos e foi conferida internamente.

## 8. O que manter

1. **Pesos congelados para esta pergunta de transferência.** Separar qualquer
   treinamento futuro em outro experimento, sem substituir estes checkpoints.
2. **Contrato explícito.** Ordem N/L/S/O, escala original, ações por aproximação
   e estados reais das luzes nos logs.
3. **Fontes e resultados imutáveis.** Uma pasta nova por execução; hashes e
   proveniência; preservar tentativas que falharam.
4. **Transições verificadas.** Não copiar de volta a contagem incorreta do motor
   antigo para ocultar a diferença entre ambientes.
5. **Avaliação além da média.** P95, máximo, inserção, atendimento e resultados
   por aproximação precisam continuar no relatório.
6. **Verificação curta antes da longa.** Valida dimensões, Q, fases e operação
   do ambiente antes de gastar tempo em uma rodada integral.
7. **Separação de branch e escopo.** Não alterar os scripts centrais do colega
   como efeito colateral da organização deste experimento.

## 9. O que mudar ou investigar a seguir

| Prioridade | Trabalho proposto | Critério para concluir |
|---|---|---|
| Alta | Investigar repetibilidade no mesmo build, modo e comando, sem captura automática | Explicar ou quantificar divergências com seed fixa; registrar diferenças de execução |
| Alta | Comparar a DQN com regras calibradas nesta mesma versão derivada | Mesmas ruas, demanda, fases, transições, métricas e sementes; calibração separada do teste |
| Alta | Investigar atendimento de N e a cauda da espera | Relacionar tempo sem verde, filas a montante e verde executado; separar medição de hipótese |
| Alta | Reconciliar a versão A/B/C descrita no resumo externo | Localizar código/modelos/resultados reais com o colega; auditar antes de continuar o treino |
| Média | Repetir avaliações em poucas sementes após estabilizar o ambiente | Medidas de dispersão e diferenças pareadas; sem escolher só a melhor rodada |
| Média | Estudar limite de tempo sem atendimento ou recompensa de equidade | Novo experimento controlado, com intervenções e ações efetivas registradas |
| Média | Tornar metadados portáveis em execuções futuras | Guardar caminhos relativos + hashes; manter os caminhos antigos como histórico |
| Média | Salvar automaticamente o código/configuração exatos de cada execução futura | Associar evidência ao commit e ao conteúdo executado, inclusive falhas |
| Baixa | Retirar `.pyc` já versionados na base, em mudança combinada com o colega | Remover apenas artefatos gerados, sem misturar com a evidência científica |

O estado observa apenas as duas faixas imediatas de cada aproximação, cujos
comprimentos são muito diferentes. O impacto de fila fora dessa área é uma
hipótese relevante para N, ainda não uma explicação causal demonstrada.
Mais episódios, uma CNN, múltiplos cruzamentos ou outra DQN não foram executados
nem são requisito para registrar corretamente este teste.

## 10. Organização entregue na branch

```text
.gitignore / .gitattributes               ambientes fora do Git; evidências sem conversão de bytes
semaforo/
  REGISTRO_COLOGNE1.md                    este registro e roteiro de continuidade
  COLOGNE1.md                            auditoria inicial, identificada como histórica
  TESTE_COLOGNE1_DERIVADO.md               relatório específico da rodada válida
  requirements-inferencia.txt            versões do ambiente CPU
  referencias/
    sumo_rl_1.4.5/                       dados, fontes auditados, licença e proveniência
    codigo_historico_20261110/            bytes dos scripts anteriores à reorganização
  scripts/
    auditar_cologne1.py                   auditoria sem inferência no cenário original
    testar_dqn_cologne1.py                teste com pesos congelados no derivado
    verificar_resultados_cologne1.py      conferência independente dos registros gravados
  resultados/
    indice_execucoes_cologne1.json        índice das nove execuções e hashes de seus arquivos
    cologne1_auditoria/                   inclusive erro do instrumento
    preparacao_inferencia/               carregamento do checkpoint
    cologne1_derivado/                   testes curtos, tentativa parcial e rodada completa
    verificacao_organizacao/              teste do caminho portátil das referências
```

Os scripts históricos em `.py.txt` foram reconstruídos apenas desfazendo a
mudança de caminho padrão e conferidos contra o snapshot anterior à organização.
Seus hashes correspondem às fontes registradas na auditoria final e na rodada
principal. São arquivos para consulta, não pontos de entrada executáveis nesta
pasta. Os scripts atuais só mudaram o caminho padrão das referências nessa etapa;
o cálculo da DQN e a dinâmica do runner permanecem iguais aos da rodada válida.

`tmp/` e o ambiente Python permanecem locais e ignorados, sem exclusão. Os
arquivos de dados necessários estão agora em `referencias/` e serão incluídos
no commit. Nenhum peso, histórico ou resultado anterior foi movido. Os caminhos
absolutos presentes nos JSONs/XMLs antigos representam a máquina da execução;
os comandos recomendados abaixo usam caminhos relativos/configuráveis.

## 11. Reproduzir e conferir

Na raiz de uma cópia do repositório, a conferência dos resultados exige apenas
Python padrão; não inicia SUMO nem importa PyTorch:

```powershell
python -B semaforo/scripts/verificar_resultados_cologne1.py
```

Ela recalcula média/P95/máximo do tripinfo e filas do CSV, confere os 13 valores
de entrada, argmax dos quatro Qs registrados, sequência real de fases e hashes
do modelo e referências. Não recalcula Q a partir da rede nem prova, sozinha,
qual código foi executado historicamente.

Para uma nova instalação, crie um ambiente Python 3.12 separado e instale as
dependências nele. O simulador SUMO 1.28.0, com `bin` e `tools`, é externo ao Git:

```powershell
python -m venv .venv-dqn-inferencia
& '.venv-dqn-inferencia/Scripts/python.exe' -m pip install `
  -r semaforo/requirements-inferencia.txt
```

Use um ambiente novo; não recrie um ambiente local existente para seguir a
receita. No computador original ele já está preparado. `python` precisa ser
substituído pelo caminho real do interpretador caso não esteja no PATH.

```powershell
# Auditoria do cologne1 ORIGINAL: retorno 2 e a recusa esperada, sem inferência.
& '.venv-dqn-inferencia/Scripts/python.exe' -B -X utf8 `
  semaforo/scripts/auditar_cologne1.py --sumo-home '../tools/sumo-win64-1.28.0'

# Verificação curta do DERIVADO.
& '.venv-dqn-inferencia/Scripts/python.exe' -B -X utf8 `
  semaforo/scripts/testar_dqn_cologne1.py --sumo-home '../tools/sumo-win64-1.28.0' `
  --duracao 300 --escoamento 0 --sementes 1

# Rodada completa do DERIVADO.
& '.venv-dqn-inferencia/Scripts/python.exe' -B -X utf8 `
  semaforo/scripts/testar_dqn_cologne1.py --sumo-home '../tools/sumo-win64-1.28.0' `
  --duracao 3600 --escoamento 1200 --sementes 1 --gui --delay-ms 10
```

Adapte `--sumo-home` à instalação real. `--sumo-rl-source`, `--checkpoint` e
`--output-root` são configuráveis. O padrão das referências agora aponta para
`semaforo/referencias/sumo_rl_1.4.5/`, derivado da posição do próprio script.
O runner admite várias sementes, mas só seed 1 foi usada neste trabalho.

## 12. Validação desta organização e entrega Git

- Conferência independente da rodada principal: passou, 339 decisões,
  585 eventos de fase e 3644 amostras; 2015 chegadas fecham com o tripinfo.
- Teste curto de 60 s com o caminho padrão versionado: passou, 5 decisões,
  zero colisões e pesos preservados. Não foi repetida a rodada longa nesta etapa.
- Fontes SUMO-RL copiadas sem modificação; metadados e licença preservados.
- Hashes dos pesos, históricos e resultados já existentes conferidos antes
  do commit; os arquivos brutos não foram normalizados nem reescritos.
- Arquivos de ambiente, cache e `tmp/` fora do commit. `.pyc` antigos da base
  não foram removidos nesta mudança.
- O commit fica na nova branch local. `main` continua apontando para `652e773`.
  O hash da entrega pode ser consultado com `git log -1 --oneline` nessa branch.

Antes de integrar com o trabalho do colega, revisar o diff dessa branch contra
a base. Esta entrega não resolve automaticamente divergências de uma versão
mais nova do projeto que esteja em outra máquina ou em outro ramo.
