"""Relatorio da rodada verificada; nao toca em pesos nem em fontes anteriores."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


def linha_resultado(nome, m):
    viagens = m["viagens"]["demanda_janela"]
    espera = viagens["espera_concluidos"]
    def fmt(v):
        return f"{v:.1f}" if v is not None else "n/d"
    return (f"| {nome} | {m['passos_controlados']} | {m['colisoes']} | "
            f"{viagens['concluidos']}/{m['demanda_prevista']} | {m['remanescentes']} | "
            f"{m['viagens_nao_inseridas']} | {fmt(espera['media'])} | {fmt(espera['p95'])} | "
            f"{m['intervencoes']} |")


def gerar(raiz, grafico=False):
    geral = json.loads((raiz / "resumo_geral.json").read_text(encoding="utf-8"))
    verificacao = json.loads((raiz / "verificacao_final.json").read_text(encoding="utf-8"))
    protocolo = json.loads((raiz / "protocolo.json").read_text(encoding="utf-8"))
    modelos = verificacao["modelos"]
    episodios = sum(m["episodios"] for m in modelos)
    falhas = sum(m["episodios_com_colisao"] for m in modelos)
    horas = sum(m["exposicao_horas"] for m in modelos)
    linhas = ["# Resultado da rodada MARL com supervisor - cologne8", "",
        f"Gerado em {datetime.now(timezone.utc).isoformat()}. Rodada `{raiz.name}`.", "",
        f"Foram concluidos **{len(modelos)} treinamentos de {modelos[0]['episodios']} episodios** "
        f"(total {episodios}), com oito DQNs locais e uma DQN supervisora por inicializacao.", "",
        f"**{falhas}/{episodios} episodios de treino terminaram por colisao**. "
        f"A exposicao efetiva foi {horas:.2f} horas simuladas, e nao {episodios} horas completas. "
        "Cada evento recebeu -10000 por ator e encerrou o episodio. "
        "Isso documenta uma rodada executada; nao aprova a politica para operacao.", "",
        "## Teste final com seed 1", "",
        "Mesma demanda, rede e protocolo; teste sem exploracao. As linhas interrompidas "
        "possuem duracoes e populacoes diferentes. Espera/P95 abaixo referem-se somente "
        "a quem concluiu a viagem antes da interrupcao: **nao permitem ordenar eficiencia**.", "",
        "| Controle | Controle simulado (s) | Colisoes | Concluidos/previstos | Em viagem ao encerrar | Ainda nao inseridos* | Espera parcial (s) | P95 parcial (s) | Intervencoes |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in geral["treinos"]:
        linhas.append(linha_resultado(f"MARL seed {r['semente_modelo']} (ep {r['melhor_episodio']})", r["teste_final"][0]))
    for nome, resultados in geral["comparadores"].items():
        linhas.append(linha_resultado(nome, resultados[0]))
    linhas += ["", "*Ainda nao inseridos inclui partidas futuras que nao foram alcancadas porque "
        "o episodio terminou cedo, alem de eventual atraso na entrada. "
        "`pendentes_insercao` separa os veiculos que ja deveriam entrar naquele instante.", "",
        "O programa original usa seus proprios tempos; Max-Pressure usa as mesmas protecoes "
        "do MARL e nao recebeu calibracao dedicada. Nenhum e apresentado como teto teorico.", "",
        "## Inicializacoes e checkpoints", "",
        "| Inicializacao | Melhor episodio pela validacao | Colisoes no treino | Horas efetivas | Episodios chegaram a 28800 s |",
        "|---|---:|---:|---:|---:|"]
    for m in modelos:
        linhas.append(f"| {m['semente']} | {m['melhor_episodio']} | {m['eventos_colisao_treino']} | "
                      f"{m['exposicao_horas']:.2f} | {m['episodios_completaram_hora']} |")
    linhas += ["", "Validacao: seeds 201 e 202 a cada 25 episodios. Selecao lexicografica por "
        "colisoes, demanda prevista nao concluida (incluindo partidas futuras) e espera afetada. "
        "Cada checkpoint contem os nove atores do mesmo episodio.", ""]
    for r in geral["treinos"]:
        path = Path(r["melhor_checkpoint"])
        # Nome de caminho relativo ao proprio relatorio, sem presumir onde fica o repo.
        local = f"modelo_seed{r['semente_modelo']}/{path.name}"
        linhas.append(f"- Seed {r['semente_modelo']}: [{path.name}]({local}); "
                      f"SHA-256 `{r['sha256_checkpoint']}`. Estado final para retomada: "
                      f"`modelo_seed{r['semente_modelo']}/ultimo_completo.pt`.")
    linhas += ["", "## Ablacao do canal supervisor", "",
        "Mesmas redes treinadas, mas orientacao fixada em equilibrado. Nao e um "
        "treinamento independente sem supervisor e nao isola causalmente a hierarquia.", "",
        "| Controle | Controle simulado (s) | Colisoes | Concluidos/previstos | Em viagem ao encerrar | Ainda nao inseridos* | Espera parcial (s) | P95 parcial (s) | Intervencoes |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in geral["treinos"]:
        linhas.append(linha_resultado(f"Seed {r['semente_modelo']}, orientacao zero", r["ablacao_orientacao_zero"][0]))
    linhas += ["", "## O que foi verificado", "",
        f"- {verificacao['execucoes_conferidas']} execucoes conferidas contra os tripinfo comprimidos; "
        "conservacao de viagens, espera, P95, censura, colisoes e penalidades.",
        f"- {verificacao['decisoes_conferidas']} decisoes com dimensoes/Qs finitos, "
        "acao no conjunto valido, argmax sem exploracao e mapeamento para fase real.",
        f"- {verificacao['eventos_fases_conferidos']} eventos de fase conferidos, "
        "incluindo 3 s de amarelo e 2 s de vermelho local em transicoes concluidas.",
        f"- {verificacao['arquivos_preexistentes_preservados']} arquivos preexistentes "
        "preservaram o SHA-256 anterior ao trabalho.",
        "- Nove atores com gradientes, pesos finitos, checkpoints escolhidos e ultimos "
        "estados completos; hashes das fontes de treino preservadas em `fontes_execucao/`.", "",
        "## Erros, acertos e proximo passo", "",
        "Acertos: controle simultaneo de oito nos, formatos locais derivados das fases "
        "reais, supervisor treinavel, penalidade terminal alta, replay com acao executada, "
        "fim explicito, desconto por duracao e avaliacao sem aprendizado. Esses componentes "
        "foram exercitados e possuem evidencias preservadas.", "",
        "Problema central: o programa original do cologne8 tambem colidiu sem RL. "
        "Reprocessar a rede com netconvert e reduzir o passo nao eliminaram todos os casos; "
        "a copia reprocessada nao foi usada neste treino. Fases G/g permitem movimentos "
        "com prioridade; tempos de amarelo/vermelho, por si sos, nao garantem que veiculos "
        "ja no interior tenham liberado todas as trajetorias conflitantes.", "",
        "Nao e possivel concluir que MARL ou supervisor melhoraram o transito com "
        "medias de viagens interrompidas. A penalidade alta tambem nao demonstrou "
        "garantia de seguranca. Nao comparar esses numeros diretamente ao cruzamento "
        "sintetico ou cologne1. As viagens OD/horarios sao fixas entre treino/teste.", "",
        "Menor proximo passo: reproduzir um evento de colisao com os links/fases e "
        "veiculos envolvidos, auditar prioridades/geometria interna e o esvaziamento "
        "do cruzamento nas transicoes. Corrigir e versionar uma copia derivada antes "
        "de gastar outra rodada longa. Depois exigir episodios completos, vazao e "
        "espera nao censuradas e um treino separado sem supervisor para medir seu ganho.", "",
        "Manter os nove atores, mapeamentos auditados, protecoes locais, penalidades, "
        "separacao de sementes, checkpoints completos e registros. Revisar a validacao "
        "do ambiente e a atribuicao/evitabilidade de colisoes antes de ampliar o treino.", "",
        "## Reproducao e rastreabilidade", "",
        "`protocolo.json` registra os argumentos reais. `manifesto.json` define as "
        "entradas, acoes, fontes e tempos. `historico.jsonl` registra cada episodio; "
        "`verificacao_final.json` contem os totais conferidos. O desenho completo e "
        "as tentativas anteriores estao em `semaforo/TREINO_MARL_SUPERVISOR_COLOGNE8.md`.", ""]
    if grafico:
        import os
        config = Path(__file__).resolve().parents[2] / "tmp/marl_supervisor/matplotlib"
        config.mkdir(parents=True, exist_ok=True)
        os.environ["MPLCONFIGDIR"] = str(config)
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
        for m in modelos:
            pasta = raiz / f"modelo_seed{m['semente']}"
            hist = [json.loads(l) for l in (pasta / "historico.jsonl").read_text().splitlines()]
            ys = [[h["metricas"]["passos_controlados"] for h in hist],
                  [100*(h["metricas"]["demanda_prevista"]-h["metricas"]["viagens_nao_concluidas"])
                   /h["metricas"]["demanda_prevista"] for h in hist],
                  [np.mean(h["epsilon"]) for h in hist]]
            for ax, y in zip(axes, ys):
                n = min(10, len(y))
                ax.plot(np.arange(n, len(y)+1), np.convolve(y, np.ones(n)/n, mode="valid"),
                        label=f"Inicialização {m['semente']}")
        axes[0].set_ylabel("Tempo de controle (s)")
        axes[0].axhline(3600, color="gray", linestyle="--", linewidth=1, label="1 h prevista")
        axes[0].set_title("Cologne8: treinamento hierárquico com nove Double DQNs\nMédia móvel de 10 episódios; interrupções por colisão incluídas")
        axes[1].set_ylabel("Demanda total concluída (%)")
        axes[1].set_ylim(0, 100)
        axes[2].set_ylabel("Exploração média (epsilon)")
        axes[2].set_xlabel("Episódio")
        axes[2].set_ylim(0, 1)
        for ax in axes:
            ax.grid(alpha=0.25)
        axes[0].legend(loc="upper left", fontsize=8)
        fig.tight_layout()
        destino = raiz / "curvas_treino.png"
        if destino.exists():
            raise FileExistsError(destino)
        fig.savefig(destino, dpi=150)
        plt.close(fig)
        linhas += ["![Curvas do treino, incluindo episodios encerrados por colisao](curvas_treino.png)", ""]
    destino = raiz / "RELATORIO.md"
    with destino.open("x", encoding="utf-8") as f:
        f.write("\n".join(linhas))
    return destino


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rodada", type=Path)
    ap.add_argument("--grafico", action="store_true")
    args = ap.parse_args()
    print(gerar(args.rodada, args.grafico))
