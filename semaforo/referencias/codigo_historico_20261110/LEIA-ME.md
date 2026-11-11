# Código anterior à organização da branch

Os arquivos `.py.txt` preservam exatamente os bytes dos scripts existentes antes
da organização deste trabalho em branch. A reconstrução desfez somente a mudança
do caminho padrão das referências e foi aceita apenas após conferir o SHA-256
contra o snapshot anterior à organização.

| Arquivo | SHA-256 |
|---|---|
| `testar_dqn_cologne1.py.txt` | `f4350810a0f3f4c41c166f6aac5b403494909fefe9fc1fa552e299d56a51e43e` |
| `auditar_cologne1.py.txt` | `2d3cdb21f0ecc9cdb7378a98bb26148a82bff31944d1576d69d449b13d427996` |

Esses hashes correspondem às fontes registradas na rodada completa válida e na
auditoria final. São referências históricas para consulta; execute os pontos
de entrada atuais de `semaforo/scripts/`, cujo caminho padrão dos dados foi
tornado portátil. Não foi reconstruída a versão exata de todas as tentativas
anteriores que falharam.
