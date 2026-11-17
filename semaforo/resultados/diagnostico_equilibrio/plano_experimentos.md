# Plano: uma DQN mais equilibrada com as ruas secundarias

Base: diagnostico em `resumo.md` (mesma pasta). Nada aqui foi implementado nem treinado.

## O problema, em uma frase

A recompensa atual (`-Δ fila acumulada / 100`) soma "carros x segundos parados": um carro
esperando 300 s custa exatamente o mesmo que 10 carros esperando 30 s. Para minimizar a
media, a rede aprende a atender a rua secundaria raramente e em lotes. Dois agravantes:

* a rede **nao ve ha quanto tempo** cada carro (ou cada direcao) esta esperando -- o estado
  so tem filas, carros, fase e tempo de verde. Um carro parado ha 10 s e ha 1000 s geram o
  mesmo estado;
* com γ = 0,95 por decisao de 5 s o horizonte efetivo e ~100 s: o custo de deixar alguem
  esperando 5 minutos mal aparece no valor Q.

## Alternativas

| alternativa | o que muda | ataca a causa? | risco / custo | mantem experimento controlado? |
|---|---|---|---|---|
| **R1. Fila + excesso de espera** `r = -(Δfila + β·Δexcesso)/100`, excesso = Σ por segundo dos carros parados com espera acumulada > W | so a recompensa | sim: torna o custo **convexo** (carro acima de W custa 1+β por segundo) e o custo aparece na hora, sem depender do horizonte | 2 parametros (W, β); a parte nova da recompensa depende de algo que a rede nao ve (parcialmente observavel) | **sim** |
| R2. Penalidade fixa por carro que cruza W (evento) | so a recompensa | parcialmente: pune a passagem do limiar, nao a duracao (1183 s custa igual a 61 s) | sinal esparso, pouco informativo | sim |
| R3. Espera ao quadrado (Σ w²) | so a recompensa | sim, convexo | escala explode no saturado; treino instavel; dificil de calibrar | sim |
| O1. Acrescentar espera a observacao (ex.: maior espera acumulada por aproximacao, 4 entradas) | entrada da rede 13 → 17 | sim: torna "quem esta esperando ha muito" visivel e quebra os ciclos (o estado deixa de se repetir) | muda a arquitetura de entrada; nao da para atribuir o ganho a recompensa se feito junto | so como 2º experimento |
| M1. Replay balanceado tipo "Memory Palace" (memorias separadas por fase atual x acao, amostragem igual) | so o aprendizado | indireto: melhora estados raros (carro sozinho), mas nao muda **o que** a recompensa valoriza | muda a dinamica do treino; efeito dificil de isolar | so como 3º experimento |
| S1. Regra de seguranca de "tempo maximo sem verde" no simulador | dinamica (C → D) | resolve o ciclo por forca, nao ensina a rede | muda a dinamica e invalida a comparacao com tudo que ja foi medido em C | nao (decisao de projeto, nao de aprendizado) |

Sobre M1: a ideia de "Memory Palace" (memorias separadas por combinacao fase/acao, amostradas
em proporcao igual) aparece em IntelliLight (Wei et al., KDD 2018). Nao conferi o paper de
Taoyu Pan citado; vale checar se a variante dele e a mesma antes de implementar.

## Recomendacao

**Experimento 1 (so recompensa): R1**, com tudo o mais congelado: Double DQN, 13 entradas,
2x64, 4 acoes, γ, lr, lote, memoria, aquecimento, alvo, ε, 250 episodios, 4 cenarios de treino,
sementes 0/1/2, dinamica C, mesma validacao (201-202) e mesmo criterio de checkpoint.

Parametros fixados ANTES de treinar (para nao "escolher o que deu certo"):

* **W = 60 s** (aprox. um ciclo do Webster; abaixo do P95 atual das secundarias, ~130-200 s);
* **β = 1** (um carro acima de W passa a custar o dobro por segundo);
* espera = `vehicle.getAccumulatedWaitingTime` (a mesma que o tripinfo usa; `getWaitingTime`
  zera quando o carro anda alguns metros na fila);
* contado nas vias de entrada, a cada segundo, na hora **e** no escoamento (como a fila em C).

Se o Experimento 1 nao eliminar o ciclo do "carro sozinho" ou nao reduzir o P95 das
secundarias, a explicacao provavel e a observacao: entao **Experimento 2 = R1 + O1**
(17 entradas: + maior espera acumulada entre os carros de cada aproximacao / 120 s, limitada
a 2), comparado contra o Experimento 1. M1 so se ainda sobrarem falhas em estados raros.

## Como saber se funcionou (criterios definidos antes)

Comparacao pareada por semente de teste (1-10), dinamica C, 5 cenarios, contra as 3 DQN C
atuais (mesmas sementes de treino 0/1/2), Webster e Max-Pressure teto recalibrado.

Sucesso se, na media das 3 redes novas:

1. **0 veiculos nao atendidos** em 50/50 rodadas por rede, e 0/36 ciclos no teste do carro
   sozinho (`diagnosticar_equilibrio.py --automato`, que roda sem simulador);
2. **P95 das secundarias** (girado: L/O; assimetrico: N/S) cai pelo menos 20% e a espera
   maxima (incluindo nao concluidos) cai;
3. **espera media** piora no maximo 5% em relacao as DQN C atuais e continua abaixo de
   Webster e Max-Pressure teto (recal. C) em todos os cenarios;
4. o girado continua fora do treino e do checkpoint.

Relatar tambem: tempo sem verde (medio e maximo) por direcao, % de verde x % de demanda,
intervencoes da regra de seguranca, e o resultado por semente (quantas das 10 melhoram),
nao so medias.

## Arquivos que precisariam mudar (Experimento 1)

* `scripts/simulacao.py`: novo acumulador `excesso_acumulado` na `Observacao` (somado a cada
  segundo, como `fila_acumulada`), ligado por uma opcao (ex.: `Dinamica(espera_limite=60)` ou
  parametro de `rodar`) para nao mudar nada nas rodadas atuais -- as metricas oficiais e os
  controladores tradicionais ficam identicos.
* `scripts/dqn.py`: nova funcao `recompensa_fila_excesso` e entrada `"fila_excesso"` em
  `RECOMPENSAS` (a `recompensa_fila` atual fica intacta).
* `scripts/treinar_dqn.py`: aceitar o tipo `fila_excesso`; validacao registrando tambem P95,
  espera maxima e nao atendidos (o criterio de checkpoint continua o mesmo).
* `scripts/avaliar_C.py` e `scripts/analisar_comportamento.py`: rotulos dos novos modelos
  (`dqn_fila_excesso_C_seed{0,1,2}.pt`); saida em pasta nova.
* novo teste (ex.: `scripts/testar_recompensa_excesso.py`): excesso calculado bate com uma
  conta independente segundo a segundo; com β = 0 a recompensa e identica a atual; rodadas
  antigas continuam identicas.

Experimento 2 mexeria tambem em `dqn.py` (`estado_para_vetor`, `TAMANHO_ESTADO`) e em
`simulacao.py` (a observacao passaria a trazer a maior espera por aproximacao).
