# Pacotes dos registros detalhados do MARL Cologne8

Os registros detalhados da rodada principal
`resultados/marl_cologne8/20261113T011843Z_continuo_10seeds_9f8d757b/`
estao guardados, sem perda, em 70 pacotes `.tar.xz` no Git normal:
`resultados/pacotes_registros_cologne8/`. O objetivo e reduzir o ZIP baixado
do GitHub (um arquivo por episodio pesa muito no ZIP: 89,0 MB -> 51,9 MB)
sem tirar nenhum dado do repositorio.

Desde a manutencao de 15/11/2026, esses 16.640 arquivos nao sao mais
versionados soltos: num clone ou ZIP novo eles **nao existem nos caminhos
originais ate a restauracao** abaixo. O `.gitignore` mantem as copias
restauradas fora dos commits. As versoes soltas continuam no historico Git
(tag local `antes-limpeza-repositorio`, commit `ac9552d9`).

## O que esta nos pacotes

Por semente de modelo (0 a 9), 16.640 arquivos, 387,0 MB -> 19,8 MB:

| Pacote | Arquivos de origem |
|---|---|
| `episodios_metricas` | `episodios/epNNNN/metricas.json` (inclui `eventos_colisao`) |
| `episodios_sumo_log` | `episodios/epNNNN/sumo.log` (avisos de colisao do SUMO) |
| `episodios_execucao` | `episodios/epNNNN/execucao.json` |
| `episodios_decisoes_fases` | `episodios/epNNNN/decisoes.jsonl` e `fases.jsonl` (ep 1 e 500) |
| `validacao` | `validacao/epNNNN/resumo.json` e `seedNNN/{metricas.json,sumo.log,execucao.json}` |
| `teste_final_decisoes` / `teste_final_fases` | `teste_final/seedNN/decisoes.jsonl` / `fases.jsonl` |

Ficam sempre abertos: `historico.jsonl` (cada linha traz o mesmo `metricas`
do episodio, inclusive os eventos de colisao), `resumo.json`,
`resumo_geral.json`, metricas do teste final e da ablacao, comparadores,
analises (`analise_detalhada_*`, incluindo `eventos_colisao.csv`), protocolo,
verificacao, logs dos processos, politicas e estados. **Nenhum arquivo Git LFS
(`.pt`, `tripinfo.xml.gz`) entra nos pacotes.**

## Garantias

- Cada pacote e um `.tar` deterministico (ordem alfabetica, mtime 0, dono 0)
  comprimido com xz 9e. O manifesto `manifesto_pacotes.json` guarda, por
  pacote, SHA-256 do `.tar.xz`, SHA-256 do `.tar`, quantidade e bytes.
- Os hashes de cada arquivo vem do inventario oficial
  `resultados/indice_artefatos_cologne8.jsonl`, que **nao foi alterado** e e
  conferido pelo hash registrado em `resultados/indice_execucoes_cologne8.json`.
- A restauracao confere tudo antes de escrever o primeiro arquivo, nunca
  sobrescreve (arquivo identico e mantido; diferente interrompe), e recusa
  caminhos absolutos, `..`, links, membros fora do inventario ou de Git LFS e
  destinos fora da pasta escolhida.
- A tag `antes-limpeza-repositorio` preserva a referencia ao historico Git,
  mas nao substitui backup dos objetos Git LFS.

## Restaurar e conferir

Na raiz do repositorio, com qualquer Python 3.9+ (somente biblioteca padrao):

```powershell
python -B semaforo/scripts/restaurar_registros_cologne8.py --verificar   # so confere
python -B semaforo/scripts/restaurar_registros_cologne8.py               # restaura nos caminhos originais
python -B semaforo/scripts/restaurar_registros_cologne8.py --destino C:\tmp\c8   # restaura em outra pasta
python -B semaforo/scripts/empacotar_registros_cologne8.py --conferir    # refaz os .tar dos originais e compara
python -B semaforo/scripts/testar_registros_cologne8.py                  # testes de seguranca
```

Depois de restaurar, `analisar_marl_continuo.py`, `verificar_marl_continuo.py`
e `verificar_pacote_cologne8.py` leem os mesmos arquivos de antes, sem
alteracao. Os dois verificadores tambem exigem os objetos Git LFS
(`git lfs pull`), como ja era o caso.

No Windows, o caminho completo de cada arquivo restaurado precisa caber em
260 caracteres: use `--destino` curto (por exemplo `C:\tmp\c8`) ou habilite
caminhos longos no sistema.

Treinos novos nao usam os pacotes: continuam gravando arquivos individuais em
uma pasta de rodada nova. Os pacotes cobrem somente a rodada acima.
