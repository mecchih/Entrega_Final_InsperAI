# Verificação antes da publicação (17/11/2026)

Feita na branch `integracao/entrega-final`, sobre a `main` atualizada (Cologne8 v4 incluído), sem treino e sem alterar resultados. Ambiente: Windows 11, SUMO 1.28.0 e Python 3.12 (Anaconda, torch 2.14).

| # | O que foi verificado | Resultado |
|---|---|---|
| 1 | Sintaxe dos 194 `.py` versionados (`ast.parse`) | OK, 0 erros |
| 2 | Etapa A: `testar_dinamica.py` e `testar_analise.py` | **TUDO OK** nos dois; modelos `.pt` e `avaliacao_final.json` inalterados |
| 3 | Etapa B: `restaurar_registros_cologne8.py --verificar` e `testar_registros_cologne8.py` | OK: 16.640 registros idênticos, 0 ausentes; 15 testes OK |
| 4 | Etapa B: `testar_marl_cologne.py`, `testar_monitoramento_marl.py`, `testar_cologne8_corrigido.py` (v4) e `testar_piloto_supervisor.py` | OK: 10 + 4 + 5 + 5 testes |
| 5 | Etapa B: `testar_controlador_mpc.py` | **Não executável aqui**: o ambiente MPC (`requirements-mpc-cologne8.txt`: clarabel, osqp e scipy compatível) não está instalado. Erro de importação do SciPy/NumPy, não do código |
| 6 | Etapa C: `testar_controle_seguro_insper.py` e `testar_integracao_traci_insper.py` | OK: 19 testes; 15/15 rodadas no SUMO aprovadas |
| 7 | Etapa C: `testar_c5.py` (zero-shot C3 → C5, sem treino) | OK: 17/17 verificações; arquivos do cenário inalterados (SHA-256) |
| 8 | Checkpoints finais por SHA-256 | OK: 30 do Insper, 10 do Modelo C, 5 do C5 e as 10 políticas selecionadas da v4 do Cologne8 (estas baixadas via LFS e conferidas contra `PACOTE_GIT_20261116.json`); 13 modelos da Etapa A presentes |
| 9 | Git LFS no servidor (API batch, sem baixar) | OK: os 6.616 objetos LFS referenciados estão disponíveis |
| 10 | Bytes do Insper versionados = bytes em disco | OK em 717 de 718 arquivos. A exceção é um `.py` com CRLF no disco, normalizado para LF como os demais códigos |
| 11 | Arquivos grandes | Nenhum blob novo acima de 1 MB. O maior blob do repositório (12,7 MB, Cologne8 v2) já estava publicado |
| 12 | Exclusões e conflitos em relação a `origin/main` | 0 arquivos apagados; só `.gitignore` e `.gitattributes` modificados (apenas acréscimos); 0 conflitos |
| 13 | `git diff --check` | Os avisos aparecem só em evidências preservadas byte a byte (`-text`): CRLF nos JSON gerados no Windows e linha em branco final em duas tabelas geradas. Não foram editados para não alterar resultados |
| 14 | Caminhos absolutos | Nenhum em código, README ou `entrega_final/`. Registros de proveniência mantidos (ver `PLANO_COMMITS.md`) |

Não executados de propósito:
- `testar_ps.py`, `testar_otimizacao.py`, `testar_treino_c5.py`, `testar_treino_C.py` e `testar_recompensa_excesso.py`: fazem passos de treino.
- `testar_visualizacao.py`: abre janelas do SUMO-GUI.
- `testar_obs17.py`: leva mais de 15 min (ver a verificação de 16/11).
- `verificar_pacote_cologne8.py`: exige baixar cerca de 10 GB de LFS do histórico v2.

O teste 6 gravou a saída em `semaforo/integracao_insper/resultados/20261117T034409Z_teste_integracao/` (local, não versionada).

---

# Verificação executada em 16/11/2026

Foram só testes curtos: nenhum treino e nenhuma bateria nova. Ambiente: Windows 11, SUMO 1.28.0 e Python 3.12 (Anaconda, torch 2.14).

| # | O que foi verificado | Comando | Resultado |
|---|---|---|---|
| 1 | Etapa A: dinâmica do simulador, modelos e arquivos preservados | `cd semaforo/scripts && python testar_dinamica.py` | **TUDO OK**; 13 arquivos conferidos por hash, nenhum alterado |
| 2 | Etapa A: observação de 17 entradas, carga dos 10 modelos de 13 entradas e da rede de 17, treino curto e inferência | `cd semaforo/scripts && python testar_obs17.py` | **8 grupos OK** (3/5, 6, 9, 10, 11, 12, 14a, 1-5/7/8/13). Interrompido pelo limite de 15 min que impusemos no último grupo (mini-avaliação de 15 rodadas, 14b), sem falha de código |
| 3 | Etapa A: listagem dos modelos e controladores | `python visualizar_dqn.py --listar` | OK: 13 modelos, 6 controladores e 5 cenários |
| 4 | Etapa A: carga direta dos checkpoints | `torch.load` de `dqn_fila_excesso_17_C_seed0`, `dqn_fila_C_seed0` e `dqn_fila` | OK (formato `dqn_v2` com 17 entradas; `state_dict` com 13) |
| 5 | Etapa B: 70 pacotes de registros do Cologne8 | `python -B semaforo/scripts/restaurar_registros_cologne8.py --verificar` | OK: 16.640 arquivos idênticos, 0 ausentes |
| 6 | Etapa B: testes unitários dos pacotes | `python -B semaforo/scripts/testar_registros_cologne8.py` | OK (15 testes) |
| 7 | Etapa B: checkpoint final disponível no servidor LFS | `git -c lfs.fetchexclude= lfs fetch origin --include=".../modelo_seed0/politica_ep0375.pt"` e `torch.load` | OK: 308.161 bytes, SHA-256 confere, formato `..._continuo_v2`, episódio 375, 9 atores. Só este modelo foi baixado (para o cache LFS); a cópia de trabalho continua com ponteiros |
| 8 | Etapa C: controlador seguro | `python -B -X utf8 semaforo/integracao_insper/testar_controle_seguro_insper.py` | OK (19 testes) |
| 9 | Etapa C: os modelos finais carregam e rodam | `demo_insper.py --sem-gui --limite 900` com `A_col` (modelo 1), `B_col_s15` (modelo 2) e `original` | OK: válidos, 0 violações, 0 colisões, 0 teletransportes |
| 10 | Etapa C: comandos de leitura dos resultados | `bateria_otimizacao.py comparar --bracos A_col B_col_s15` | OK: reproduz a validação (20,88 contra 21,75 s) |
| 11 | Etapa C: exportação dos modelos finais | `exportar_modelos_finais.py` | OK: 30 cópias com SHA-256 iguais às originais; caminhos relativos no manifesto |
| 12 | Configurações do SUMO acessíveis, sem escrever nas pastas | `sumo -c` no Cologne8 (`referencias/.../cologne8.sumocfg`) e no Insper (`insper_demanda/intenso_teste_final/semente_241/cenario.sumocfg`) | OK: exit 0; pastas inalteradas por hash |
| 13 | Gráfico novo da Etapa A | `py -B entrega_final/gerar_grafico_cruzamento.py` | OK: valores conferidos com `comparacao_17_C/resumo.json` |
| 14 | Caminhos absolutos no código | `grep` por `C:\Users` e pelo usuário em `*.py` e nos `.md` novos | Nenhum caminho absoluto obrigatório no código. Os dois relatórios do Insper tinham o caminho do Python local nos comandos de reprodução; trocado por `python`. Os registros históricos com caminhos absolutos estão listados em `PLANO_COMMITS.md` |

Observações:
- O teste 2 deixou o arquivo temporário `semaforo/resultados/_tmp_tripinfo_28012.xml`, que é ignorado pelo Git e pode ser apagado.
- `semaforo/scripts/verificar_pacote_cologne8.py` não foi executado: exige todo o conteúdo LFS (cerca de 6.500 objetos), mesmo com `--rapido`.
- O código do Insper usa nomes de binário do Windows (`sumo.exe`); não foi testado em Linux.
