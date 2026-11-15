# Referências do experimento Colônia

`sumo_rl_1.4.5/` contém um recorte do wheel oficial SUMO-RL 1.4.5, obtido do PyPI:
rede, rotas e configuração de cologne1; fontes usados na auditoria; licença e
metadados originais do pacote. Isso não é uma instalação funcional de SUMO-RL.

`proveniencia.json` registra a URL, o SHA-256 do wheel e a relação de arquivos
extraídos. Os bytes foram mantidos na cópia de `tmp/` para esta pasta; a
configuração `.gitattributes` impede conversão de finais de linha nesses arquivos.
As fontes externas não foram editadas. A instalação do simulador SUMO é separada.

O runner cria outra cópia da rede em cada pasta de resultado e altera somente
o programa semafórico dessa cópia. A referência original e as rotas não mudam.
Veja [o registro completo](../REGISTRO_COLOGNE1.md) para decisões, comandos,
resultados e limitações.

## Comparador MPC no Cologne8

`mpc_externo_fdbdf4a/` preserva o modelo central e o solver externos (MIT),
com commit e hashes registrados. É código de um manuscrito submetido ao ECC
2027, sem aceitação confirmada. A adaptação, os resultados e os comandos estão
em [COMPARACAO_MPC_COLOGNE8.md](../COMPARACAO_MPC_COLOGNE8.md).
