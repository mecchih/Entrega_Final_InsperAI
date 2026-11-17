# Integração Insper: o que está no Git e o que fica só local

O `.gitignore` da raiz (bloco "Integracao Insper") separa o que vai para o GitHub do que fica só na máquina local. Nada foi apagado: os artefatos locais continuam nas pastas originais.

## Vai para o Git (cerca de 48 MB no total)

| O quê | Onde |
|---|---|
| Código | `*.py` desta pasta, de `otimizacao_final/` e de `quarto_semaforo/` |
| Documentação | `LEIA-ME.md`, `MARL_INSPER.md`, `otimizacao_final/RELATORIO_OTIMIZACAO.md`, `quarto_semaforo/RELATORIO_QUARTO_SEMAFORO.md`, `resultados/bateria_principal_20261116/RESULTADOS.md` |
| Cenário OSM original | `semaforo/cenarios/insper/` (cerca de 0,6 MB) |
| Demandas sintéticas | `semaforo/cenarios/insper_demanda/` (cerca de 39 MB; todas as sementes de treino, validação e teste) |
| Modelos finais | `modelos_finais/`: 30 políticas do teste final (cerca de 2,5 MB) e `manifesto.json` |
| Resumos agregados | `**/resultados/*.json(l)`, `**/resultados/*/*.json`, relatórios (`*.md`, `*.png`, `relatorio/*.json`) e, para cada treino, `configuracao.json`, `historico.jsonl` e `resumo_treino.json` |

## Fica só local (cerca de 1 GB)

| O quê | Tamanho aproximado | Para que serve | Como recuperar |
|---|---|---|---|
| `**/retomada.pt`, `final_completo.pt` | 27–35 MB cada, cerca de 700 MB no total | Retomar um treino interrompido (contém o replay) | Retreinar com `otimizacao_final/bateria_otimizacao.py treinar` |
| Checkpoints intermediários `politica_ep*.pt` | cerca de 70–110 kB cada | Seleção na validação | Os selecionados estão copiados em `modelos_finais/`; os demais vêm de um retreino |
| `**/episodios/` (`metricas.json` e `sumo.log` por episódio) | centenas de MB | Auditoria por episódio | Os números agregados estão nos resumos versionados; reavaliar com `bateria_otimizacao.py` |
| `**/logs/`, subpastas por semente de calibração e testes de integração, `tripinfo*.xml` | dezenas de MB | Depuração | Rodar novamente os scripts correspondentes |

## Observações

- Vários resumos (`teste_final.json`, `braco_*.json`, `gerado.json` das demandas) guardam **caminhos absolutos desta máquina** (`C:\Users\...`). São registros históricos e não foram editados.
  - Os scripts não dependem desses caminhos.
  - Para localizar um checkpoint, use `modelos_finais/manifesto.json`, que tem caminhos relativos.
- `resultados/_interrompidos_bug_amarelo_assumir/` e `quarto_semaforo/resultados/_falhou_*` guardam execuções interrompidas por defeitos já corrigidos. Ficam só como registro.
