# Registro consolidado do experimento MARL no Cologne8

Este e o ponto de entrada para continuar o experimento sem depender da
conversa. Trabalho organizado na branch **experimento/marl-cologne8-supervisor**,
derivada de `2e5713a`, sem alterar `main` nem os pesos dos experimentos
anteriores. As datas das pastas usam UTC; os horarios descritos usam Sao Paulo.

**Resultado principal:** o MARL atendeu todas as 2.046 viagens em cada um dos
cem testes finais e reduziu a espera media em 41,31% frente ao Max-Pressure
implementado. **As colisoes nao foram resolvidas:** todos os testes tiveram
contatos detectados, com media proxima a do Max-Pressure. O beneficio do
supervisor e misto e depende de uma inicializacao com falha forte na ablacao.

## Leitura dos resultados

- [Analise completa](ANALISE_MARL_COLOGNE8_CONTINUO.md): resultados por modelo,
  cruzamento e aproximacao, comparacoes pareadas, colisoes e supervisor.
- [Protocolo da rodada longa](TREINO_MARL_COLOGNE8_CONTINUO.md): parametros,
  sementes, pausa, retomada, monitoramento e verificacoes anteriores ao treino.
- [Rodada terminal anterior](TREINO_MARL_SUPERVISOR_COLOGNE8.md): explica por
  que as primeiras medias eram parciais e nao comparaveis as da rodada longa.
- [Indice das execucoes](resultados/indice_execucoes_cologne8.json): classifica
  pilotos, auditorias, tentativas rejeitadas e rodadas de treinamento.
- [Inventario com hashes](resultados/indice_artefatos_cologne8.jsonl): tamanho,
  SHA-256 e forma de armazenamento de cada artefato do pacote.

## Escopo e arquitetura

O ambiente e o recorte **cologne8**, distribuido no SUMO-RL 1.4.5, com oito
semaforos e 2.046 viagens OD. Nao e toda a cidade de Colonia nem transito ao
vivo. Rede e demanda originais foram preservadas. O controle usa tempos e
transicoes proprios e, portanto, e um protocolo derivado do benchmark.

Cada experimento possui oito Double DQNs locais e uma Double DQN supervisora.
Os locais podem manter verde ao mesmo tempo. Suas entradas preservam a
familia da DQN17: filas, contagens, fase ativa, idade do verde e maior espera
por entrada; acrescentam o objetivo do supervisor. Dimensoes seguem as
aproximacoes e fases reais, sem completar acoes ficticias.

| Componente | Definicao |
|---|---|
| Entradas locais | 26, 24, 22, 26, 22, 18, 22, 26 |
| Acoes locais | 4, 2, 3, 4, 3, 2, 3, 4 fases reais |
| Supervisor | 176 entradas, 9 objetivos: equilibrado ou priorizar um dos oito locais |
| Ocultas | 64 e 64 neuronios, ReLU |
| Tempo de decisao | Locais elegiveis a cada 5 s; supervisor a cada 30 s |
| Transicoes | Verde minimo 10 s, amarelo 3 s, vermelho integral local 2 s |
| Atendimento externo | Maximo condicional de verde de 60 s, com movimento real demandado |
| Treino longo | Dez inicializacoes 0 a 9, 500 episodios cada, pesos novos |
| Avaliacao | Validacao 201/202; teste final 1 a 10, sem exploracao ou atualizacao |
| Colisao na rodada longa | -10.000 por novo contato para cada ator; episodio continua |

O esquema comum ainda se chama `esquema_dqn_cologne3.py` por origem historica.
A referencia `cologne3_sumo_rl_1.4.5` integra este pacote somente porque os
testes de regressao desse modulo tambem exercitam o formato de tres locais.
Isso nao transforma a rodada principal em um treino de Cologne3.

## Etapas e tentativas preservadas

| Pasta em resultados/marl_cologne8 | Papel no experimento |
|---|---|
| 20261113T002405Z_piloto_a486d158 | Piloto inicial com falha registrada; nao usar como resultado principal |
| 20261113T002517Z_auditoria_original | Colisao reproduzida com programa original sem RL |
| 20261113T002613Z_auditoria_reprocessada | Diagnostico da copia reprocessada da rede |
| 20261113T002705Z_auditoria_original_passo02 | Diagnostico com passo reduzido no original |
| 20261113T002705Z_auditoria_reprocessado_passo05 | Diagnostico com passo de 0,5 s na copia |
| 20261113T002706Z_auditoria_reprocessado_passo02 | Diagnostico com passo de 0,2 s na copia |
| 20261113T002843Z_piloto_f82ea9c0 | Piloto de aprendizagem e instrumentacao |
| 20261113T003221Z_piloto_d65e5c26 | Piloto antes da rodada terminal principal |
| 20261113T003357Z_treinar_afff873a | Rodada historica: 3 x 250 episodios, todos encerrados por colisao |
| 20261113T003821Z_conferencia_sensores | Conferencia dos sensores e movimentos usados na protecao |
| 20261113T010530Z_piloto_continuo | Colisao nao terminal, aprendizagem nos nove atores |
| 20261113T011248Z_continuo_bf6c3fff | Ensaio completo do executor, semente descartavel 777 |
| 20261113T011843Z_continuo_10seeds_9f8d757b | Rodada principal: 10 x 500, testes, comparadores, monitor e analises |

A copia `referencias/cologne8_derivado_sumo128` foi rejeitada para o treino
principal. Reprocessar o XML e reduzir o passo nao eliminaram todos os
contatos, e a conversao tambem alterou fases. Sua proveniencia e seus logs
permanecem arquivados como diagnostico, sem substituir a referencia original.

## Resultados que deram certo

A rodada longa terminou em **13/11/2026 as 06h39**, apos aproximadamente 8h21.
Foram 5.000 episodios, 400 simulacoes de validacao, cem testes finais,
cem ablacoes e vinte comparadores: **5.620 simulacoes**.

| Media por simulacao de teste | MARL | Max-Pressure | Programa original |
|---|---:|---:|---:|
| Espera da viagem | 9,29 s | 15,83 s | 30,52 s |
| Media dos P95 | 35,43 s | 50,85 s | 87,55 s |
| Fila media na rede | 4,94 | 8,42 | 16,01 |
| Viagens concluidas | 2.046 | 2.046 | 2.046 |
| Colisoes | 18,46 | 18,20 | 23,60 |

O ganho de espera frente ao Max-Pressure apareceu nos cem pares modelo x
semente. O P95 melhorou em 99 pares e empatou em um. Os nove atores de cada
modelo tiveram gradientes e pesos finitos. O executor paralelo, checkpoints,
avaliacoes sem aprendizagem, verificacao e relatorio automaticos concluiram.

Os checkpoints sao conjuntos de nove politicas escolhidos pela validacao;
nao selecionamos um novo vencedor pelas sementes finais. A menor espera no
teste foi do modelo 0, e a menor media de colisoes, do modelo 6. Todos os
pesos e estados de retomada, inclusive os intermediarios, foram preservados.

## O que ainda nao deu certo

**Colisoes:** 1.846 contatos nos cem testes MARL, nenhum teste sem colisao.
Os tres cruzamentos principais concentram 89,11% dos contatos; 179 ocorreram
fora dos oito TLS controlados. A penalidade ja domina mais de 99,96% da
magnitude do custo de treino. Ela nao substitui uma verificacao das fases,
prioridades, geometria e possibilidade de evitar cada contato.

**Equidade:** a espera local media piorou em tres dos oito cruzamentos e
em onze das 25 entradas observadas. Menor media global nao significa ganho
para toda via. Duas entradas nao tiveram veiculos observados no teste.

**Supervisor:** melhorou a espera de sete modelos e piorou a de tres. Na
ablacao modelo 6 / trafego 8, houve 145 viagens nao concluidas e espera media
de 297,97 s. O ganho agregado do supervisor cai de 36,78% para 2,16% quando
esse modelo e retirado dos dois lados apenas como analise de sensibilidade.
A ablacao nao equivale a treinar agentes independentes sem supervisor.

**Ambiente e interpretacao:** o programa original tambem colide. Com
`collision.action=warn`, o SUMO mantem os veiculos em simulacao apos contatos.
As esperas medidas sao condicionais a esse protocolo. Nao demonstram uma
operacao fisicamente segura. Os OD e horarios permanecem iguais entre
sementes; nao ha teste de nova demanda ou de outro mapa nesta rodada.

**Historico:** a primeira rodada encerrava por colisao e teve apenas 85,28
horas simuladas nos 750 episodios. Comparar suas esperas parciais diretamente
as da rodada longa seria incorreto. Na primeira geracao da analise detalhada,
foi corrigido um agrupamento que confundia junctions internas do SUMO com
cruzamentos fisicos; a saida inicial permanece marcada para nao usar esse
agrupamento. Nenhuma simulacao ou contagem total foi alterada por essa correcao.

## O que manter e os proximos testes

Manter os mapeamentos auditados, o controle local simultaneo, a protecao
temporal, o registro de intervencoes e da acao executada, a punicao alta e
a continuidade apos colisao, as sementes separadas, os checkpoints completos
e os registros de tentativas com erro. Nao reutilizar medias parciais como
se fossem resultados de uma hora completa.

Os proximos testes estao registrados como plano, nao como ja executados:

1. Reproduzir contatos nos TLS 247379907, 26110729 e no cruzamento agrupado,
   e na juncao 252016274. Comparar o mesmo evento no programa original,
   inspecionar movimentos G/g, prioridade e liberacao fisica do interior.
2. Investigar o bloqueio da ablacao modelo 6 / trafego 8 e as entradas que
   pioraram. Acrescentar carro isolado e demanda rara, como na analise da DQN C.
3. Apos estabilizar o ambiente, treinar uma referencia independente com oito
   agentes e sem supervisor, com mesmo orcamento e mesmas sementes.
4. Ampliar variedade de demanda e validacao, reservar um novo teste final e
   recalibrar uma referencia Max-Pressure forte. Rever a atribuicao do custo
   de colisao preservando punicao alta; aumentar apenas sua escala nao e o
   primeiro experimento indicado.

## Organizacao dos arquivos e Git LFS

Os cerca de 10,5 GB do experimento foram mantidos, incluindo pilotos,
diagnosticos, logs, viagens e checkpoints intermediarios/finais. Os arquivos
`.pt` e `tripinfo.xml.gz` usam **Git LFS**; os demais arquivos cientificos
permanecem no Git normal, com seus bytes preservados por `.gitattributes`.
Caches de fonte do Matplotlib ficam locais e fora do commit.

Git LFS armazena no commit ponteiros SHA-256 para o conteudo dos arquivos;
o conteudo permanece disponivel nos objetos LFS locais. O push deve enviar
esses objetos ao servidor. Ver
[a documentacao do GitHub](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage).
**Este commit local nao equivale a um upload dos cerca de 10 GB de objetos LFS.**

Depois de obter a branch e instalar Git LFS, `git lfs pull` baixa os objetos
necessarios para conferir o pacote inteiro. Em uma copia somente com os
ponteiros, o verificador informa o objeto faltante em vez de declarar sucesso.

O pacote tambem inclui rede original, rotas, licenca e proveniencia do
SUMO-RL; a copia rejeitada; fontes congeladas; backup da versao terminal;
e evidencias do lancamento em `referencias/cologne8_execucao_20261113/`.
O snapshot anterior ao treino registra o contexto local original e inclui
arquivos de outras etapas; ele e historico, nao uma lista de exigencias para
um checkout exclusivo deste experimento.

Os scripts novos do Cologne8, seus documentos e dependencias de teste foram
incluidos. Alteracoes locais independentes do teste DQN17/Cologne1 e suas
propostas/resultados separados ficaram fora deste commit, preservadas no disco.

## Conferir e reproduzir

O verificador de pacote usa somente a biblioteca padrao do Python e deriva
os caminhos da posicao do repositorio, sem exigir a pasta original da autora:

```powershell
python -B semaforo/scripts/verificar_pacote_cologne8.py
python -B semaforo/scripts/verificar_pacote_cologne8.py --rapido
```

O primeiro comando calcula todos os hashes, incluindo os objetos LFS; pode
demorar por ler cerca de 10,5 GB. O segundo verifica todos os tamanhos e os
hashes dos arquivos de ate 1 MB, identificando explicitamente o escopo parcial.
Ambos conferem a conclusao da rodada e os numeros principais publicados.

Para preparar um ambiente novo com Python 3.12 e os pacotes principais
registrados nos ambientes originais:

```powershell
python -m venv .venv-marl-cologne8
& '.venv-marl-cologne8/Scripts/python.exe' -m pip install -r semaforo/requirements-marl-cologne8.txt
& '.venv-marl-cologne8/Scripts/python.exe' -B semaforo/scripts/testar_marl_cologne.py
& '.venv-marl-cologne8/Scripts/python.exe' -B semaforo/scripts/testar_monitoramento_marl.py
```

O arquivo de requisitos reune os pacotes principais do ambiente de treino e
do ambiente separado de graficos. As versoes efetivamente capturadas tambem
estao nos JSON de dependencias da rodada. O SUMO 1.28.0 com `bin` e `tools`
deve estar instalado separadamente para executar novas simulacoes.

Um **novo** treino, somente quando autorizado, pode usar:

```powershell
& '.venv-marl-cologne8/Scripts/python.exe' -B -X utf8 `
  semaforo/scripts/treinar_marl_continuo.py `
  --episodios 500 --sementes 0 1 2 3 4 5 6 7 8 9 `
  --sementes-teste 1 2 3 4 5 6 7 8 9 10 --trabalhadores 3 `
  --sumo-home 'C:/caminho/para/sumo-1.28.0' `
  --python-relatorio '.venv-marl-cologne8/Scripts/python.exe'
```

A saida padrao e sempre uma pasta nova. Nao apontar `--saida` para uma rodada
ja existente. O codigo congelado e os JSON originais conservam seus caminhos
absolutos historicos: os verificadores originais e a reanalise completa podem
exigir esse contexto local. **Para conferir este commit em outra pasta, usar
o verificador de pacote relativo acima**, sem reescrever os registros antigos.

A analise de integridade da rodada e a verificacao do pacote nao garantem
ausencia de colisoes, superioridade sobre todo controlador ou generalizacao
para transito novo. Essas questoes permanecem nas proximas etapas descritas.
