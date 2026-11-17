# Publicação no GitHub — registro (17/11/2026)

O plano de commits de 16/11 foi executado na branch `integracao/entrega-final`, criada a partir de `origin/main` em `180e403f` (merge do PR #6, Cologne8 v4). A integração na `main` foi feita por Pull Request, sem force push e sem reescrever histórico.

## O que já estava na `main`

- PRs #1 a #6: Etapa A (DQN do cruzamento sintético e geração C de 17 entradas), Cologne1 derivado, MARL Cologne8 v1/v2, limpeza com os pacotes de registros, e o **Cologne8 v4 corrigido**, com o piloto do supervisor e o comparador MPC.

## Commits da integração

| # | Commit | Conteúdo | Arquivos |
|---|---|---|---:|
| 1 | `c2d502dc` chore(gitignore) | Restaura o bloco dos registros compactados do Cologne8 (havia saído no merge da v4), mantém as regras da v4 (`estado_ep*.pt`, XMLs brutos) e acrescenta o bloco do Insper | 1 |
| 2 | `ed16bee1` merge | Branch `experimento/comparadores-cologne8` (Julia Lico): comparadores calibrados, rede supervisionada, Q-learning tabular e demonstração visual. Só arquivos novos | 295 |
| 3 | `76786878` chore(gitattributes) | `-text` para o cenário, as demandas e as evidências do Insper (bytes originais, inclusive CRLF) | 1 |
| 4 | `cc728ae5` feat(insper) | Cenário OpenStreetMap original | 15 |
| 5 | `845451e4` feat(insper) | Demandas sintéticas calibradas | 378 |
| 6 | `6ac5dcb3` feat(insper) | Integração TraCI, controle seguro e MARL do corredor (código, documentação e resumos da bateria principal) | 79 |
| 7 | `68978c2b` feat(insper) | Otimização final | 89 |
| 8 | `0e584290` feat(insper) | Investigação do 4º semáforo | 6 |
| 9 | `e45ce35c` feat(insper) | 30 políticas do teste final (independentes e hierárquicas) com manifesto | 31 |
| 10 | `b1025535` feat(insper) | Modelo C3 (parameter sharing), generalização, transferência e viabilidade C6 | 61 |
| 11 | `b1fe85ad` feat(insper) | Zero-shot C3 → C5 | 13 |
| 12 | `c8401059` feat(insper) | C5 treinado do zero e os 5 checkpoints selecionados | 38 |
| 13 | `d1fd80d8` docs(etapa-a) | Diagnóstico de equilíbrio citado por `dqn.py` | 7 |
| 14 | docs | README principal e `entrega_final/` (inclui este arquivo), atualizados com a v4 do Cologne8 | — |

## Tamanho e armazenamento

- Os blobs novos do Insper têm no máximo 0,73 MB, e as demandas somam 73 MB.
- Os 45 `.pt` do Insper (de 25 a 110 kB) vão como Git normal, como os `.pt` de `semaforo/modelos/`.
- **Git LFS:** só os `.pt` e `.xml.gz` do Cologne8 (`marl_cologne8/`, `cologne8_corrigido/`, `piloto_supervisor_cologne8/`).
  - Em 17/11, a API do LFS confirmou que os 6.616 objetos referenciados estão no servidor.

## Fica fora do Git (de propósito)

- **Insper:** episódios, logs, `retomada.pt`, checkpoints intermediários e saídas brutas por semente (ver `semaforo/integracao_insper/ARTEFATOS_LOCAIS.md`).
- **Cologne8 v2:** as cópias restauradas dos registros detalhados. Elas estão versionadas como pacotes `.tar.xz`.
- **Cologne8 v4:** os estados completos `estado_ep*.pt` e os XMLs brutos de treino e validação, indexados com SHA-256 em `semaforo/resultados/cologne8_corrigido/PACOTE_GIT_20261116.json`.

## Caminhos absolutos

- Código, README e `entrega_final/`: sem caminhos absolutos.
- Registros de proveniência foram preservados sem edição, como na política já usada no Cologne1 e no Cologne8:
  - os `gerado.json` das demandas;
  - os 5 arquivos do osmWebWizard;
  - alguns resumos de validação e teste do Insper.
- Eles contêm o caminho da pasta de trabalho no Windows. Não há outros dados pessoais (e-mail, token ou senha).
- Os resultados do C5 já foram gravados com caminhos relativos.

## Pendência fora do Git

A pasta `C:\c\Users\...\gen_teste` foi criada por engano fora do repositório numa etapa anterior (3 arquivos de teste). Pode ser apagada manualmente; não afeta o Git.
