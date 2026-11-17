# Integração do cenário Insper (OSM) com TraCI

Esta pasta guarda o diagnóstico e o primeiro teste de controle dos semáforos do
cenário `semaforo/cenarios/insper/` (ruas próximas ao Insper, em São Paulo).
**Nenhum modelo foi treinado ou carregado.** Os scripts não alteram:
- os arquivos do cenário (todos os scripts conferem o SHA-256 de cada arquivo no início e no fim);
- os códigos do Cologne8, os modelos e os resultados históricos.

Toda saída vai para `resultados/<data>_<nome>/`, numa pasta nova a cada execução.

## Como rodar

Precisa do SUMO 1.28.0 com `SUMO_HOME` definido. O teste `dqn_inicial` também
precisa de `torch`. Rode na raiz do repositório:

```powershell
python -B -X utf8 semaforo/integracao_insper/diagnosticar_cenario_insper.py                 # ~1 min
python -B -X utf8 semaforo/integracao_insper/testar_controle_seguro_insper.py               # sem SUMO, 18 testes
python -B -X utf8 semaforo/integracao_insper/testar_integracao_traci_insper.py              # ~4 min, 15 rodadas
python -B -X utf8 semaforo/integracao_insper/testar_integracao_traci_insper.py --politicas ciclo_fixo --sementes 1 --gui
```

A simulação usa o `osm.sumocfg` original. Só muda as saídas, que vão para a
pasta de resultados, e deixa de carregar o `output.add.xml`, porque ele
escreveria `edgeData.xml` dentro da pasta do cenário. As colisões são checadas
também dentro dos cruzamentos (`--collision.check-junctions true`) e apenas
registradas (`--collision.action warn`).

## Arquivos

| Arquivo | Função |
|---|---|
| `insper_comum.py` | Caminhos, comando do SUMO e conferência dos hashes do cenário. Também tem os monitores, todos lendo o que o SUMO executou: travessias da linha de retenção, programa original, verificação de segurança e colisões. |
| `controle_seguro_insper.py` | `ControladorFasesSeguro`, a máquina de estados verde → amarelo → vermelho geral → verde, com verde mínimo e verde máximo condicional. `SemaforosProtegidos` bloqueia escrita TraCI nos semáforos não controlados. |
| `observacao_insper.py` | Vetores de observação local e do supervisor, no mesmo formato do Cologne8. |
| `diagnosticar_cenario_insper.py` | Análise da rede, rotas, demanda e fases, rodando só com os programas originais. |
| `testar_controle_seguro_insper.py` | Testes unitários sem SUMO: programa, transições, assumir o controle em amarelo, verde máximo, proteção de escrita e verificador. |
| `testar_integracao_traci_insper.py` | Teste de integração TraCI com políticas de teste. |

## Diagnóstico

Resultados em `resultados/20261115T211910Z_diagnostico/diagnostico.json`: seed
padrão do SUMO e seeds 1, 2 e 3.

### 1. Conectividade e relação espacial

Os três cruzamentos estão em sequência na **Rua Ribeirão Claro, que é mão
única**. Entre eles não há outra junção:

```
(borda da rede) 234368025#0, 214,8 m
   → 476455095  Gomes de Carvalho
   → 760437731, 96,0 m, 2 faixas
   → 40278305   Casa do Ator
   → 234368026#0, 97,3 m, 2 faixas
   → 40278183   Quatá
   → 234368026#1, 27,5 m
   → cluster_13529541823_… (semáforo não controlado, 25 links)
```

- As rotas de carro (`passenger`) foram confirmadas com o sumolib: 476455095 → 40278305 tem 96 m e 476455095 → 40278183 tem 193 m.
- **Não existe rota no sentido inverso dentro da rede.** O trânsito entre os três é sempre o mesmo encadeamento.
- A distância em linha reta é de cerca de 112 m entre cruzamentos vizinhos.
- O tempo observado entre uma travessia e a seguinte é de 7 a 21 s, com mediana de 12 a 13 s.

Cada cruzamento tem duas aproximações: a Ribeirão Claro e a transversal.

### 2. Demanda gerada e veículos observados

O `osm.passenger.trips.xml` tem **278 viagens em 1 hora em toda a rede**. O
`randomTrips` gerou essas viagens com 12 veículos por hora por km de faixa.
Elas não têm rota fixa: o SUMO calcula a rota na inserção e não há reroteamento.

| Semáforo | Planejados na inserção | Cruzaram de fato | Aproximação Ribeirão Claro | Transversal |
|---|---:|---:|---:|---:|
| 476455095 Gomes de Carvalho | 44 | 43–44 | 11–12 | 32 (Gomes de Carvalho) |
| 40278305 Casa do Ator | 59 | 59 | 48 | 11 (Casa do Ator) |
| 40278183 Quatá | 77 | 76–77 | 43 | 33–34 (Quatá) |

- A rota planejada e a observada coincidem em 277 ou 278 dos 278 veículos.
- A seed padrão reproduz exatamente o `stats.xml` e o `tripinfos.xml` da execução no GUI: 278 viagens concluídas e duração média de 134,27 s.
- Fila máxima nas aproximações: 1 ou 2 veículos parados.
- Média de veículos parados por aproximação: 0,001 a 0,014.

### 3. Tráfego compartilhado

Dos 95 veículos que cruzam pelo menos um dos três semáforos, **56 (59%) cruzam
dois ou três**, e 29 cruzam os três. Cerca de 43 veículos por hora vão de
476455095 para 40278305, e 42 de 40278305 para 40278183.

A estrutura justifica coordenação: é um corredor de mão única, curto, e a
maior parte do fluxo é compartilhada. **O volume atual não justifica.** Com
cerca de 1 veículo por minuto por aproximação, não há fila a reduzir, e um
treino nessa demanda não diferenciaria políticas.

### 4. Fases e controle pelo TraCI

- **Os programas são `actuated`**, com `minDur=5` e `maxDur=50`. Os 42 s são apenas a duração nominal. Na demanda atual, os verdes observados duram de 5 a 10 s, com média de 5,1 s.
- O amarelo é de 3 s e não há vermelho geral.
- Cada semáforo tem duas fases verdes que não compartilham links. Os conflitos do `<request>` da rede coincidem com a geometria interna do TraCI (`getInternalFoes`). Na geometria do TraCI foram descontados os pares que saem da mesma faixa, porque eles divergem e sempre têm a mesma cor.
- Nenhuma fase tem dois verdes `G` conflitantes.
- `setRedYellowGreenState` troca o semáforo para o programa `online` e exibe exatamente o estado enviado. **O SUMO não insere amarelo nem vermelho**, então o controlador faz toda a transição.

### 5. Estados e ações para a Double DQN

O formato é o mesmo de `ambiente_marl_cologne.vetor_base`/`estados`:

| | Cálculo | Dimensão |
|---|---|---:|
| Observação local | 2 aproximações × (fila, carros, espera) + 2 fases + idade do verde (9), mais a orientação (4) | **13** |
| Ação local | fase verde 0 ou 1 | **2** |
| Supervisor | 27 + 6 de ocupação a jusante + 9 de estágio + 4 de orientação + 2 da rede | **48** |
| Ação do supervisor | equilibrado ou priorizar cada um dos três | **4** |

Adaptações necessárias:
- **Área de observação:** a via de chegada da Quatá tem 7,1 m e a da Gomes de Carvalho tem 37,7 m. Por isso cada aproximação passa a incluir as vias a montante até 100 m, parando em outro semáforo. No Cologne8 era só a via controlada.
- **Escalas:** as escalas da rede (350 veículos e 250 parados) vieram do Cologne8 e precisam ser recalibradas.
- **Ambiente:** `ambiente_marl_cologne.py` não serve diretamente. Ele exige que todos os semáforos da rede sejam controlados, usa os caminhos do RESCO e a janela fixa 25200–28800 s. Será preciso um ambiente novo, derivado dele, sem alterar o original.

### 6. Amarelo, vermelho geral e colisões

O controlador:
- só troca de fase depois de 10 s de verde;
- passa pelo amarelo do programa (3 s, conferido link a link);
- faz 2 s de vermelho geral, como no Cologne8, antes de abrir o verde pedido;
- recusa assumir um programa com verdes conflitantes, link verde em fases seguidas, amarelo diferente do verde ou cor desconhecida;
- ao assumir no meio de um amarelo, completa os 3 s;
- tem o verde máximo condicional de 60 s do Cologne8.

Um verificador independente lê o estado executado pelo SUMO a cada segundo e
procura:
- verde direto para vermelho;
- amarelo com duração diferente de 3 s;
- verde aberto sem 2 s de vermelho dos links conflitantes;
- links conflitantes em G ou y ao mesmo tempo;
- verde abaixo do mínimo.

Ao abrir cada verde, ele também conta os veículos ainda dentro de movimentos
conflitantes.

**Colisão já existente na rede:** nas seeds 1 e 2, inclusive com o programa
original, há um contato entre os mesmos dois veículos (`veh109` e `veh116`) na
junção 1550389898, perto de 1513 s. Essa junção faz parte do semáforo não
controlado `joinedS_1389167582_…`, a cerca de 400 m. É um problema do cenário,
como no Cologne8. Ele só aparece com a checagem de colisão dentro dos
cruzamentos, que o GUI não usou.

### 7. Os outros 11 semáforos

Continuam no programa original `0` (actuated):
- o acesso de escrita TraCI a eles é bloqueado;
- a cada segundo é conferido que o programa é o `0`, que o estado é o da fase atual, que as fases avançam em ordem e que cada duração está dentro de `minDur`/`maxDur`;
- não houve nenhum erro em nenhuma rodada.

O tempo de cada fase muda quando o controle muda o tráfego, porque eles são
atuados.

**Atenção:** o `cluster_13529541823_…`, com 25 links, fica só 27,5 m depois de
40278183. Com mais demanda, a fila dele pode bloquear a saída do corredor.

## Teste de integração

Resultados em `resultados/20261115T212446Z_teste_integracao/resumo.json`: 5
políticas × 3 seeds, controle assumido em 300 s. Cada rodada tem `fases.jsonl`,
`linha_do_tempo_semaforos.csv`, `travessias.csv`, `metricas.json`,
`tripinfo.xml` e `sumo.log`.

Políticas testadas:
- `original`: sem controle, como referência;
- `ciclo_fixo`: troca aos 30 s de verde;
- `aleatoria`: escolhe uma fase ao acaso a cada 5 s;
- `adversaria`: pede troca a todo segundo, inclusive durante amarelo e vermelho;
- `dqn_inicial`: Double DQN do Cologne8 com pesos aleatórios, sem treino e sem replay.

**15/15 rodadas aprovadas.** Em todas:
- 0 violações de segurança, 0 travessias no vermelho e 0 colisões nos três cruzamentos ou em suas faixas de chegada;
- 0 teletransportes e 278/278 viagens concluídas;
- 0 erros e 0 alterações nos outros 11 semáforos;
- 0 verdes abertos com veículo em movimento conflitante.

Tempos observados:
- amarelos sempre de 3 s e vermelhos gerais sempre de 2 s;
- verdes de pelo menos 10 s;
- na política adversária, todas as trocas aconteceram exatamente aos 10 s, e cerca de 3.285 pedidos inválidos por semáforo foram recusados;
- no programa original, os verdes duram de 5 a 10 s.

Espera média na rede inteira:

| Política | Espera média |
|---|---|
| `original` | 33,8–34,2 s |
| `ciclo_fixo` | 36,5–42,1 s |
| `aleatoria` | 36,2–37,4 s |
| `adversaria` | 34,0–37,4 s |
| `dqn_inicial` | 38,0–41,5 s |

Isso não é uma avaliação de desempenho. Com essa demanda, o programa atuado
original é difícil de superar, e o vermelho geral acrescenta 2 s por troca.

Testes complementares:
- **Assumir o controle em amarelo:** em `20261115T212829Z_teste_integracao/`, com `--assumir 295`, os três semáforos foram assumidos no meio do amarelo. O amarelo foi completado até 3 s, seguido de 2 s de vermelho geral e do verde seguinte do programa. 3/3 rodadas aprovadas. Nas seeds 2 e 3 da bateria principal, o 476455095 também foi assumido em amarelo.
- **Sem o verde máximo:** em `20261115T212920Z_teste_integracao_sem_verde_maximo/`, a `dqn_inicial` sem a proteção de 60 s mantém um verde indefinidamente. O resultado é de 57 a 94 teletransportes, de 6 a 16 viagens não concluídas e espera média de 209 a 315 s. Na seed 1 houve também uma colisão na junção sem semáforo 5087305044, na fila da Quatá. **A proteção de verde máximo é obrigatória enquanto a política não estiver treinada.** Com ela, a mesma rede passa nas 3 seeds.

## Próximos passos para o Multi-Agent

1. **Demanda:** criar, como cópia derivada e versionada, uma demanda mais alta e com perfil de pico para o corredor da Ribeirão Claro. Por exemplo, um novo `randomTrips` com densidade maior e várias seeds, ou fluxos calibrados com contagens reais. Conferir com o diagnóstico que haja fila e saturação parcial, sem bloqueio total. O cenário original continua intacto.
2. **Ambiente:** escrever `ambiente_marl_insper.py`, derivado de `ambiente_marl_cologne.py` e sem alterá-lo. Ele deve:
   - controlar só os 3 semáforos, usando `ControladorFasesSeguro`, `SemaforosProtegidos` e `SensoresInsper`;
   - deixar os outros 11 no programa original;
   - ter um manifesto próprio com hashes da rede e da demanda;
   - definir a janela de aquecimento, controle e escoamento para a demanda nova.
3. **Recompensas e escalas:** manter a forma do Cologne8 (fila + excesso de espera, penalidade de colisão, supervisor sobre a rede ou sobre o corredor). Recalibrar as escalas de observação para a nova demanda.
4. **Referências de comparação:** o programa atuado original (`original`), um tempo fixo e um Max-Pressure, todos com o mesmo verificador e as mesmas seeds.
5. **Colisão na junção 1550389898:** investigar a colisão do programa original, fora do corredor, antes de comparar colisões entre políticas. Separar sempre as colisões nos controlados das que acontecem fora deles.
6. **Treino curto de verificação:** só depois disso, e com autorização, rodar um treino curto antes de qualquer rodada longa.
