# Rodada MARL hierarquica no cologne8

## Escopo confirmado antes de treinar

A usuaria escolheu explicitamente **cologne8: oito agentes locais e um
supervisor**, em 12/11/2026. Sao nove politicas Double DQN atuando num unico
SUMO. O cenario inclui todos os oito controladores e toda a demanda distribuida
para cologne8 no SUMO-RL 1.4.5. Nao representa a cidade inteira do TAPAS Cologne.

As redes sao novas, treinadas do zero, sem converter ou alterar os modelos
DQN13/DQN17 existentes. Trabalho mantido na branch experimental existente;
nenhum commit/push foi solicitado nesta etapa. Os arquivos anteriores e suas
alteracoes locais foram registrados por SHA-256 antes deste trabalho.

## Entradas e acoes

Vetor local base, na ordem de vias/fases registrada no manifesto de cada rodada:

```
[filas_A/25, veiculos_A/35, onehot_fase_P,
 min(tempo_verde/60,2), min(maior_espera_A/120,3), orientacao_supervisor_9]
n_entradas = 3*A + P + 1 + 9
```

A orientacao tem nove possibilidades: equilibrado e priorizar um dos oito
controladores (ordem da tabela). O one-hot e local, identifica a fase completa
G/g, que pode liberar varios movimentos ao mesmo tempo. Nao transforma as
acoes em direcoes N/L/S/O e nao cria fases/entradas ficticias.

| Controlador | A | P | Arquitetura |
|---|---:|---:|---|
| 247379907 | 4 | 4 | 26 -> 64 -> 64 -> 4 |
| 252017285 | 4 | 2 | 24 -> 64 -> 64 -> 2 |
| 256201389 | 3 | 3 | 22 -> 64 -> 64 -> 3 |
| 26110729 | 4 | 4 | 26 -> 64 -> 64 -> 4 |
| 280120513 | 3 | 3 | 22 -> 64 -> 64 -> 3 |
| 32319828 | 2 | 2 | 18 -> 64 -> 64 -> 2 |
| 62426694 | 3 | 3 | 22 -> 64 -> 64 -> 3 |
| cluster_1098574052_1098574061_247379905 | 4 | 4 | 26 -> 64 -> 64 -> 4 |
| Supervisor | rede inteira | 9 objetivos | 176 -> 64 -> 64 -> 9 |

Supervisor: 114 entradas locais base concatenadas, 27 ocupacoes a jusante
(media das faixas de saida por aproximacao, percentual/100), 24 indicadores
de estagio (verde/amarelo/vermelho por no), 9 da orientacao anterior e totais
de veiculos/350 e filas/250 em toda a rede. Durante amarelo/vermelho os
indicadores de fase verde e seu tempo ficam zero naquele no. Os estagios
explicitam essa condicao. Nao usa chegadas futuras.

Cada ator tem seus proprios pesos, replay, Adam, alvo, RNG e contadores. O
supervisor age a cada 30 s; locais, a cada 5 s elegiveis. Uma unica fotografia
gera as escolhas locais antes de aplica-las. Um unico passo SUMO avanca todos.
Todos os cruzamentos podem estar verdes simultaneamente. A transicao de um
nao obriga outro a parar.

## Recompensas e colisoes: requisito da usuaria

Custo local por segundo = veiculos parados na area + aumento de espera acima
de W=60 s. Recompensa local = -(custo local + 0,5*custo do no priorizado)/100;
segundo termo zero em equilibrado. A orientacao muda o objetivo compartilhado
e entra na observacao local. Isso permite investigar coordenacao, sem garantir
que o supervisor de fato melhore o resultado.

Supervisor recebe -(fila de toda a rede + aumento de excesso de toda a
rede)/(100*8), integrado no intervalo. Excesso conta so incremento atual,
sem atribuir ao novo cruzamento todo o historico trazido por um veiculo.
Estado usa espera acumulada, como a DQN17, com memoria SUMO de 10000 s.

**Colisao: -10000 por novo evento para cada um dos nove agentes**, alem dos
custos de fila/espera. O episodio termina imediatamente, fecha a experiencia
como terminal e nao permite que a falha desapareca da recompensa. Um evento
e um par distinto de veiculos no passo; dois veiculos colidentes nao sao
contados como duas colisoes. Campos reais de `TraCICollision` do libsumo
1.28.0 foram conferidos. Nao desativamos a deteccao de colisoes em cruzamentos.

O valor inicial de -1000 foi elevado antes do treino principal para -10000,
reduzindo o incentivo de encerrar cedo para evitar custos futuros. A forte
penalidade nao e uma garantia matematica de seguranca ou de convergencia.
Colisao em aquecimento sem acoes dos agentes interrompe a execucao como erro
do ambiente. Teleporte inesperado tambem interrompe. Os episodios encerrados
por colisao sao falhas e suas medias sao censuradas: nao representam uma hora
completa de atendimento.

Selecao de checkpoint: primeiro menos colisoes nas validacoes; depois menos
viagens previstas nao concluidas, inclusive partidas futuras nao alcancadas
por encerramento precoce; depois menor espera media das
viagens afetadas. Salva o conjunto dos nove atores do mesmo episodio, evitando
misturar politicas locais de momentos diferentes.

## Auditoria do cenario e limitacoes reais

Os arquivos originais vieram do wheel oficial SUMO-RL 1.4.5, com SHA-256 do
pacote conferido, em `referencias/cologne8_sumo_rl_1.4.5/`. Existem **2046 trips**,
com origens, destinos e horarios fixos. Diferentemente de cologne3, nao sao
4494 veiculos com rotas explicitas nem existe demanda anterior a 25200 s.
Nao copiamos o aquecimento de 1688 s do outro cenario: o inicio aqui e 25200.
O SUMO calcula as rotas das viagens na rede.

Sensores locais usam as vias/faixas realmente controladas. A ordem geografica
N/L/S/O e apenas uma ordenacao estavel das entradas, obtida da geometria das
vias; o mapeamento de acao vem exclusivamente do programa e de seus links.
O manifesto registra cada estado, link, movimento e area. Via curta pode nao
mostrar toda fila a montante. O supervisor recebe os totais globais como
informacao adicional, sem imputar a fila perdida a uma aproximacao.

Protecoes: minimo verde 10 s, amarelo 3 s, vermelho integral local 2 s,
verde maximo condicional 60 s. Apos 60 s, manter com demanda em movimentos
nao atendidos pode ser substituido por fase que os atenda. Usa `getNextTLS`
de cada veiculo e seu link real, desempata por tempo sem servico, demanda e
indice estavel. Replay guarda acao executada; logs separam pedido/intervencao.
Mantem G/g do programa. Tempos novos tornam o protocolo derivado do RESCO,
embora a rede e a demanda originais sejam preservadas.

Foi detectada uma colisao tambem **sem RL**, no programa original e seed 1001,
no instante SUMO 25389 (reportada no estado de 25390), dentro de
`cluster_1098574052_1098574061_247379905`. Portanto nem toda colisao pode ser
atribuida a uma troca aprendida. Uma copia reprocessada pelo netconvert 1.28
removeu esse primeiro caso, mas apresentou outro em cruzamento sem semaforo
(`cluster_26718385_738066527_738066531_738066575`). Reduzir o passo para 0,5/0,2 s
tambem nao eliminou os problemas. Esses diagnosticos foram preservados.

**A copia reprocessada nao sera usada no treino principal.** Ela fica como
candidata rejeitada em `referencias/cologne8_derivado_sumo128/`, com diferencas
registradas. O treino usa os arquivos originais e penaliza/encerra colisoes,
como solicitado, sem alegar que uma penalidade corrija geometria ou prioridades
da rede. Uma politica que so evita visitar trechos problematicos, acumulando
filas, tambem nao e um resultado satisfatorio; avaliar vazao/censura/espera.

## Hiperparametros e episodio

- Tres inicializacoes independentes 0,1,2; 250 episodios por inicializacao.
- Horizonte previsto: 25200--28800 s, ate 1200 s de escoamento; episodio pode
  encerrar antes por colisao. Registrar a exposicao real, sem chamar todo
  episodio curto de uma hora de treino completa.
- Treino SUMO seed 1000+episodio; validacao 201/202 a cada 25 episodios;
  teste final seed 1. As mesmas viagens OD/horarios permanecem entre sementes:
  nao e avaliacao de demanda inedita nem de outra geometria.
- Ocultas 64/64 ReLU, Double DQN, replay 50000 por ator, lote 64, Adam 5e-4,
  Huber, norma maxima de gradiente 10, alvo atualizado a cada 500 gradientes.
- Gamma 0,95^(dt/5), usando intervalo real (inclusive amarelo/vermelho).
  Fim natural, corte e colisao sao separados; horizonte finito suprime
  bootstrap no encerramento, sem experiencias entre episodios.
- **Ajuste para episodios curtos:** aquecimento local 256 experiencias;
  supervisor 64. Exploracao de 100% ate 5% em 2000 decisoes locais e 500
  decisoes do supervisor. Os limites antigos de 2000/40000 deixariam grande
  parte desta rodada sem gradientes ou quase inteiramente exploratoria.
  O CLI aceita outros valores, todos registrados no protocolo da rodada.
- Validacao/teste sem exploracao, gradientes ou mudanca de RNG/replay/
  contadores/pesos. A verificacao compara esses estados antes e depois.
- Novos arquivos em cada melhoria. Estado final completo inclui alvo, Adam,
  replay, RNG, contadores, lote, aquecimento e desconto para recarga coerente.

## Verificacao antes do treino principal

Oito testes automaticos passaram: dimensoes reais de cologne8, formatos
base/objetivos, simultaneidade, excesso sem transferir historico, tempos exatos,
protecao por link, alvo terminal/desconto, avaliacao sem aprendizado e selecao
que nao premia uma colisao precoce com media de espera baixa.

O piloto `20261113T002843Z_piloto_f82ea9c0` exercitou dois episodios curtos
encerrados por colisao, aplicou -10000 a todos os nove atores e obteve gradientes
em todos: [16,30,20,18,16,28,19,18,5]. O piloto posterior
`20261113T003221Z_piloto_d65e5c26`, com janela prevista de 3600 s, tambem passou,
mas encerrou cedo por colisao. Recarregou o checkpoint completo e conferiu
pesos/contadores/RNG, parametros e conteudo do replay; a inferencia preservou
a aprendizagem. Os oito
nos estiveram verdes simultaneamente em parte do episodio. Esses pesos sao
descartaveis e nao inicializam os treinos principais.

Tentativas anteriores registradas: conflito de DLL da copia portatil do
libsumo, erro de indentacao corrigido antes de simular, campo de colisao
inexistente corrigido apos consultar a API instalada. Nenhum modelo antigo
foi afetado. Os logs de falha permanecem preservados.

## Comandos (PowerShell, raiz do repositorio)

```powershell
$pythonMarl = '.venv-dqn-inferencia/Scripts/python.exe'
$sumoMarl = '../tools/sumo-win64-1.28.0'
& $pythonMarl -B -X utf8 semaforo/scripts/testar_marl_cologne.py
& $pythonMarl -B -X utf8 semaforo/scripts/treinar_marl_cologne.py piloto --cenario cologne8 --duracao 600 --escoamento 0 --sumo-home $sumoMarl
& $pythonMarl -B -X utf8 semaforo/scripts/treinar_marl_cologne.py treinar --cenario cologne8 --episodios 250 --sementes 0 1 2 --aquecimento-local 256 --aquecimento-supervisor 64 --decaimento-local 2000 --decaimento-supervisor 500 --sumo-home $sumoMarl
& $pythonMarl -B -X utf8 semaforo/scripts/treinar_marl_cologne.py avaliar --cenario cologne8 --checkpoint 'CAMINHO_NOVO_CHECKPOINT.pt' --sumo-home $sumoMarl --backend traci --gui
```

Caminhos relativos ao repositorio; SUMO e Python sao configuraveis. Instalar
PyTorch/NumPy e libsumo, traci, sumolib e sumo-data 1.28.0 num ambiente virtual.
Treino usa CPU/libsumo sem GUI; avaliacao pode usar TraCI+GUI no Windows.

Saidas novas em `resultados/marl_cologne8/<UTC>_<modo>_<id>/`: manifesto,
protocolo/hashes, metricas e tripinfo.gz por episodio, historicos JSONL,
validacoes, melhores politicas e ultimo checkpoint completo por inicializacao.
Piloto/avaliacoes/primeiro e ultimo episodio tambem guardam estados/Qs/acoes e
fases realmente executadas. Nao geramos uma copia de todos os Qs de cada
episodio intermediario para limitar volume.

Comparadores: Max-Pressure com fases reais e mesmas protecoes, sem calibracao
dedicada; programa fixo original com seus tempos distintos como contexto; e
orientacao zero nas mesmas politicas treinadas. Essa ultima ablacao nao e um
treino independente sem supervisor e nao prova o ganho causal da hierarquia.

## Resultado efetivo da rodada principal

Rodada concluida em `resultados/marl_cologne8/20261113T003357Z_treinar_afff873a/`.
Foram executados os tres treinamentos de 250 episodios, 60 validacoes,
3 testes finais, 3 ablacoes de orientacao e 2 comparadores (818 execucoes).
**Todos os 750 episodios de treino encerraram por colisao**. Exposicao efetiva
85,2764 horas simuladas, sem nenhum episodio de treino completar a hora prevista.
A penalidade alta nao produziu uma politica aprovada nesta configuracao.

| Modelo | Episodio escolhido | Tempo no teste seed 1 | Viagens concluidas/2046 | Eventos de colisao |
|---|---:|---:|---:|---:|
| Seed 0 | 100 | 820 s | 432 | 1 |
| Seed 1 | 100 | 965 s | 556 | 2 |
| Seed 2 | 125 | 430 s | 163 | 1 |
| Max-Pressure | - | 441 s | 168 | 1 |
| Programa original | - | 187 s | 47 | 1 |

Esses testes possuem duracoes e populacoes diferentes por causa das falhas;
espera/P95 sao parciais e nao permitem declarar superioridade. As redes com
orientacao fixa tambem falharam, sem evidencia de ganho consistente do supervisor.

- [Relatorio completo com erros, acertos, comparadores, modelos e proximo passo](resultados/marl_cologne8/20261113T003357Z_treinar_afff873a/RELATORIO.md).
- [Curvas do treinamento](resultados/marl_cologne8/20261113T003357Z_treinar_afff873a/curvas_treino.png).
- [Verificacao dos registros](resultados/marl_cologne8/20261113T003357Z_treinar_afff873a/verificacao_final.json).

A verificacao conferiu os tripinfo de 818 execucoes, 6693 decisoes registradas,
4129 eventos de fase, os checkpoints e a conservacao das viagens. Os 145
arquivos preexistentes do snapshot anterior mantiveram seus hashes. O teste
adicional de retomada confirmou que a proxima atualizacao Adam e identica
apos recarga (total final: nove testes unitarios aprovados). Foi corrigida
tambem a etiqueta de semente na recarga, sem alterar previsoes ou pesos.
`fontes_execucao/` preserva exatamente as fontes usadas na rodada principal,
com hashes em `protocolo.json`, mesmo apos essa melhoria de metadados.

Scripts adicionais `verificar_rodada_marl_cologne.py` e `relatar_marl_cologne.py`
conferem evidencias e geram relatorio/grafico, sem treinar ou alterar modelos.
Matplotlib foi instalado em `.venv-marl-relatorio`, separado do ambiente de
treino. O Python/SUMO globais nao foram alterados.

Exemplo concreto para repetir uma avaliacao (gera pasta nova; esse modelo
falhou no teste registrado):

```powershell
& '.venv-dqn-inferencia/Scripts/python.exe' -B -X utf8 semaforo/scripts/treinar_marl_cologne.py avaliar --cenario cologne8 --checkpoint 'semaforo/resultados/marl_cologne8/20261113T003357Z_treinar_afff873a/modelo_seed0/politica_ep0100.pt' --sumo-home '../tools/sumo-win64-1.28.0'
```

**Proximo passo recomendado:** diagnosticar geometria/prioridades internas e
esvaziamento de movimentos conflitantes em uma copia derivada, reproduzindo
um evento concreto. Validar o ambiente e as transicoes antes de outro treino
longo. Manter mapeamentos reais, arquitetura local/supervisor, penalidades,
separacao de sementes, replay terminal e checkpoints completos.
