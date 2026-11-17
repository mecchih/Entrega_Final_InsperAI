# Viabilidade da expansão do Modelo C de 3 para 6 semáforos

Esta é só uma análise. Não houve treino, nenhum modelo foi alterado, e o cenário foi conferido por SHA-256 antes e depois.

- Script: `viabilidade_c6.py`. Ele lê a rede, os conflitos internos via TraCI (1 passo) e as rotas da validação 221–225.
- Dados: `resultados/viabilidade_c6_20261116T173604.json`.

## Conclusão

**Recomendação: expandir depois; manter 3 semáforos na entrega de hoje.**

- Só **um** dos 11 semáforos (`300058973`) entra na política compartilhada sem adaptação, além da permutação já usada.
- Os outros dois candidatos com estrutura compatível têm problemas que exigem trabalho novo:
  - `302806060`: tráfego insuficiente na demanda atual e mapeamento fase ↔ aproximação invertido.
  - `299169962`: a área de observação se sobrepõe a uma ciclovia e a um conector de 0,2 m.
- Os seis não formam um corredor contínuo: todos os novos se ligam ao corredor através do cluster da Hélio Pellegrino, que é incompatível e continuaria sem controle.
- A estimativa realista é de 8 a 10 h de trabalho de ponta a ponta. Não cabe no prazo de hoje com margem de segurança.

## 1. Os 11 semáforos não controlados

Veículos por semente: rotas que passam pelo semáforo na demanda intensa de validação, que é sintética e estratificada no corredor.

| Semáforo | Local | Verdes | Links (bici) | Conflitos na mesma fase | Aproximações de veículos | Veículos/semente (do corredor) | Compatível? |
|---|---|---:|---:|---:|---|---:|---|
| `2577302612` | travessia isolada (via sem nome) | 1 | 1 | 0 | 1, sem tráfego | 0 | **Não**: 1 fase |
| `2577302625` | travessia isolada (via sem nome) | 1 | 1 | 0 | 1, sem tráfego | 0 | **Não**: 1 fase |
| **`300058973`** | **R. Fiandeiras × R. Clodomiro Amazonas** | 2 | 6 (0) | **0** | Fiandeiras (2 faixas, 336) · Clodomiro (2 faixas, 44) | 380 (330) | **Sim** |
| **`302806060`** | **R. Fiandeiras × R. Prof. Atílio Innocenti** | 2 | 6 (0) | **0** | Fiandeiras (2, 50) · Atílio Innocenti (2, 27) | **77** (51) | **Estrutura sim**; tráfego insuficiente; mapeamento invertido |
| **`299169962`** | **Av. Hélio Pellegrino × R. Baluarte** (acesso) | 2 | 7 (0) | **0** | Hélio Pellegrino (3 faixas, 611) · conector de 0,2 m alimentado por ciclovia e via de 3,5 m (135) | 746 (679) | **Estrutura sim**; observação precisa ser redesenhada |
| `cluster_13529541823_…` (4º) | Ribeirão Claro × Hélio Pellegrino | 2 | 25 (8) | **45** | 3 + 2 ciclovias | 1327 (1256) | **Não**: conflitos permissivos (já investigado) |
| `cluster_1389167570_…` | Hélio Pellegrino × Prof. Atílio Innocenti | 2 | 20 (6) | **23** | 3 + ciclovias | 203 (153) | **Não**: conflitos permissivos |
| `cluster_1389167593_…` | Hélio Pellegrino × R. Uberabinha | 2 | 19 (6) | **23** | 3 + ciclovias | 772 (680) | **Não**: conflitos permissivos |
| `cluster_2577302635_302805867` | Av. Santo Amaro × R. Casa do Ator | **3** | 7 (0) | 2 | 3 | 505 (449) | **Não**: 3 verdes, não cabe em 2 ações |
| `joinedS_1389167582_…_1550389898` | Av. Santo Amaro × Hélio Pellegrino | **5** | 80 (14) | 16 | 21 | 1050 (917) | **Não**: interseção complexa |
| `joinedS_2577302624_…` | Av. Santo Amaro × R. Graúna | **6** | 22 (0) | 3 | 9 | 673 (581) | **Não**: 6 verdes |

**Leitura:**
- Ter 4 fases no programa não garante compatibilidade. Todos os 2-verdes têm 4 fases (verde, amarelo, verde, amarelo), mas três deles são clusters com conflitos permissivos.
- Os três controlados hoje têm 0 conflitos dentro da mesma fase, 2 aproximações e 2 verdes de 42 s (min 5, max 50) com amarelo de 3 s. Os três candidatos `300058973`, `302806060` e `299169962` têm **exatamente** o mesmo programa, o que é compatível com o `ControladorFasesSeguro` e com o verificador.

## 2. Candidatos e mapa das conexões

Distância mais curta pela rede dirigida:

```
            Ribeirão Claro (mão única)                         Hélio Pellegrino
476455095 ──96 m──▶ 40278305 ──97 m──▶ 40278183 ──27 m──▶ [cluster 4º, NÃO controlável]
 Gomes de C.          Casa do Ator         Quatá                │       │        │
                                                       150 m via Ribeirão   227 m via Hélio
                                                       Claro → Fiandeiras   Pellegrino
                                                                ▼              ▼
              302806060 ──180 m (Fiandeiras)──▶ 300058973      299169962
              Fiandeiras × Atílio Innocenti      Fiandeiras ×    Hélio P. ×
              (121 m até o cluster 4º)            Clodomiro       Baluarte
```

- O caminho mais curto de **Quatá → `300058973`** tem 177 m, de **Quatá → `299169962`** tem 254 m e de **`302806060` → Quatá** tem 216 m.
- **Todos passam pelo cluster da Hélio Pellegrino ou pela Av. Brigadeiro**, que continuariam sem controle.
- Não existe ligação direta entre os novos e o corredor sem atravessar uma interseção que não podemos controlar.
- `302806060` alimenta `300058973` pela Fiandeiras, a 180 m. É o único par novo diretamente encadeado.

## 3. Compatibilidade com a rede de 13 entradas e 2 ações

| Item | `300058973` | `302806060` | `299169962` |
|---|---|---|---|
| 2 aproximações e 2 verdes | sim | sim | sim |
| Slot *j* servido pela fase *1 − j* (relação dos 3 atuais) | **sim** | **não**: slot *j* → fase *j* | sim |
| Aproximação principal no slot 0 (convenção canônica do Modelo C) | sim (Fiandeiras, que recebe o fluxo vindo da Ribeirão Claro) | sim (Fiandeiras) | **não**: Hélio Pellegrino está no slot 1 |
| Transformação necessária | nenhuma | permutar só a fase one-hot e a ação (as aproximações ficam) | permutar aproximações, fase e ação, como em Casa do Ator |
| Áreas de observação de 100 m | sem sobreposição | sem sobreposição | **sobreposição**: a área do conector inclui 944842829#0 (Hélio) e ciclovias. `SensoresInsper` recusa ("via atribuída a duas aproximações") |
| Normalização (fila/25, carros/35, espera/120) | compatível | compatível | 3 faixas na Hélio Pellegrino: filas maiores, mas dentro da escala |
| Escala da recompensa | baixa (fila na Clodomiro ≈ 0) | **muito baixa** (77 veículos/h ao todo) | alta na Hélio, quase nula no conector |
| Segurança (verde 10, amarelo 3, vermelho geral 2, verde máximo 60) | aplicável | aplicável | aplicável |

**Problema transversal: a demanda.** A demanda calibrada é estratificada no corredor: cerca de 2000 veículos/h no corredor e só cerca de 190 veículos/h no resto da rede. Por isso:
- as transversais dos candidatos recebem quase nada (Clodomiro 44, Atílio Innocenti 27, conector 135 por hora);
- nesses cruzamentos a política aprenderia, na prática, "verde sempre para a via principal".

Uma comparação séria de C6 exigiria uma **nova calibração de demanda** que carregue os seis. Isso muda as demandas de referência e obriga a rodar de novo os baselines e o próprio C3 nessas demandas.

## 4. Os três experimentos

| | A: C3 → C6 sem retreino | B: C3 → C6 com ajuste fino | C: C6 do zero |
|---|---|---|---|
| Alterações | Ambiente v3 com lista de semáforos parametrizada (hoje TLS, TRECHOS, bloqueio, sensores, verificação de dimensões, "11 outros" e métricas assumem 3). Tabela de orientação para 6. Área de observação do `299169962`. Métrica nova "espera nas 6 áreas", mantendo a do corredor | A de A, mais o treino retomado do checkpoint C3, com replay novo (n_aprendizes = 6 e orçamento escalado) | A de A, mais o treino do zero com 6 aprendizes |
| Custo de execução (tempos reais × cerca de 1,3 pelo dobro de agentes) | Avaliação: 5 modelos × 10 demandas mais baselines, cerca de 15 min | 75 episódios × 5 sementes, cerca de 1 h, mais validação de cerca de 20 min | 150 episódios × 5 sementes, cerca de 2–2,5 h, mais validação de cerca de 25 min |
| Riscos | Política fora da distribuição (transversais quase vazias, 3 faixas, mapeamento novo). **Baixo risco de segurança**, porque o controlador seguro e o verificador valem para os 6 | Esquecimento da política do corredor; comparação justa exige orçamento definido com cuidado | Pouco sinal nas transversais novas; recompensas com escalas muito diferentes entre os 6 (de cerca de 0 a −265 por episódio) |
| Pré-requisito comum | Demanda recalibrada para os 6 e baselines (original e atuado com as regras do RL) refeitos nela | idem | idem |

## 5. Estimativa de duração

Base: os tempos reais de 15 e 16/11 em 16 threads e 16 GB.
- 150 episódios: cerca de 1,6 h com 10 processos, a cerca de 38 s por episódio com 3 controlados.
- Validação de 2 braços: cerca de 20 min.
- Teste de 460 episódios: cerca de 28 min.
- Calibração de demanda: cerca de 1 h.

| Etapa | Estimativa |
|---|---:|
| Ambiente v3 parametrizado, observação do `299169962`, orientação para 6 e métrica nova | 2–3 h |
| Testes automatizados e de segurança (6 verificadores, 8 "outros" intactos, permutações, replay) | 0,5–1 h |
| Calibração de demanda para os 6 e validação dos níveis | 1–1,5 h |
| Experimento A (avaliação) | 0,3 h |
| Experimentos B e C em paralelo (10 processos) | 2–2,5 h |
| Validação de B e C e teste final (A, B, C, C3 e baselines nas demandas novas) | 1–1,5 h |
| Relatório e gráficos | 1 h |
| **Total** | **cerca de 8–10 h** |

São 17:40 de 16/11. **A implementação é arriscada para o prazo:**
- terminaria de madrugada, sem margem para corrigir defeitos de segurança, que no Modelo C apareceram e foram corrigidos antes do treino;
- não sobraria tempo para revisar resultados;
- dos três semáforos, dois exigem trabalho de representação ou de demanda.

## 6. Riscos de segurança

- **Baixo para os 3 candidatos estruturalmente compatíveis.** Têm 0 conflitos dentro da fase e o mesmo programa dos atuais. O controlador seguro e o verificador independente se aplicam sem mudança.
- **Médio na implementação:**
  - um erro na permutação do `302806060` (só fase e ação) ou do `299169962` pode fazer a rede pedir o verde da aproximação errada. Isso é seguro, porque o controlador continua impedindo conflitos, mas a política fica errada;
  - o "dono" das áreas de observação precisa ser redefinido sem misturar ciclovias.
- **Fora de alcance:** os clusters da Hélio Pellegrino (`cluster_1352…`, `cluster_1389167570…`, `cluster_1389167593…`) e os da Santo Amaro (3, 5 e 6 verdes) **não** devem ser incluídos sem um novo modelo de segurança para conflitos permissivos.

## 7. Recomendação

**Expandir posteriormente.** Hoje, manter os 3 semáforos e apresentar a expansão como trabalho futuro, com estes passos:
1. Ambiente parametrizado por uma lista de semáforos.
2. Começar por **C4 = C3 + `300058973`**, o único candidato limpo.
3. Recalibrar a demanda para carregar Fiandeiras e Clodomiro.
4. Só depois incluir `302806060` (com permutação de fase e ação) e `299169962` (com a área de observação redesenhada).
