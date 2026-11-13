"""Relatorio da rodada longa completa, com sementes de treino/teste separadas."""

import argparse
import json
import os
from pathlib import Path
import statistics


def media_dp(valores):
    return f"{statistics.mean(valores):.2f} ± {statistics.stdev(valores) if len(valores)>1 else 0:.2f}"


def linha(nome, resultados):
    w = [r["viagens"]["demanda_janela"]["espera_todos_inclui_censura"]["media"] for r in resultados]
    p95 = [r["viagens"]["demanda_janela"]["espera_todos_inclui_censura"]["p95"] for r in resultados]
    return (f"| {nome} | {len(resultados)} | {media_dp(w)} | {media_dp(p95)} | "
            f"{media_dp([r['colisoes'] for r in resultados])} | "
            f"{sum(r['viagens_nao_concluidas'] for r in resultados)} | "
            f"{media_dp([r['viagens']['demanda_janela']['concluidos'] for r in resultados])} |")


def gerar(raiz, grafico):
    cfg = json.loads((raiz / "protocolo.json").read_text(encoding="utf-8"))
    g = json.loads((raiz / "resumo_geral.json").read_text(encoding="utf-8"))
    ver = json.loads((raiz / "verificacao_final.json").read_text(encoding="utf-8"))
    total = sum(x["episodios"] for x in ver["modelos"])
    eventos = sum(x["eventos_colisao_treino"] for x in ver["modelos"])
    fim_col = sum(x["episodios_terminados_por_colisao"] for x in ver["modelos"])
    h = sum(x["exposicao_horas"] for x in ver["modelos"])
    L = ["# MARL cologne8: rodada longa sem encerrar por colisao", "",
        f"Rodada `{raiz.name}`. {len(g['treinos'])} inicializacoes × {cfg['episodios']} episodios "
        f"= **{total} episodios**, com oito DQNs locais e uma supervisora por inicializacao.", "",
        f"Exposicao efetiva: **{h:.2f} horas simuladas**. Eventos de colisao no treino: "
        f"**{eventos}**. Episodios encerrados por colisao: **{fim_col}**.", "",
        "Colisao recebe -10000 por novo contato para cada ator, sem terminar o episodio. "
        "Contato persistente do mesmo par em passos consecutivos conta uma vez; apos "
        "separacao um novo contato conta novamente. SUMO collision.action=warn: nao remove "
        "nem teleporta os veiculos por causa da colisao. Isso e um experimento simulado "
        "com contatos detectados, nao uma validacao fisica de acidentes reais.", "",
        "## Teste final", "",
        "Media ± desvio padrao entre sementes de trafego. Espera inclui viagens em "
        "andamento como limite inferior; a coluna nao concluidas indica censura. "
        "P95 e a media dos P95 de cada rodada, nao um percentil agrupado. "
        "Mesmas origens/destinos/horarios entre sementes, com estocasticidade do SUMO.", "",
        "| Controle | Rodadas | Espera (s) | P95 (s) | Colisoes/rodada | Nao concluidas (soma) | Viagens concluidas/rodada |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for r in g["treinos"]:
        L.append(linha(f"MARL modelo seed {r['semente_modelo']} (ep {r['melhor_episodio']})", r["teste_final"]))
    for nome, rs in g["comparadores"].items():
        L.append(linha(nome, rs))
    L += ["", "Nao selecionar o melhor modelo pelas sementes finais: cada conjunto acima "
        "foi escolhido pelas seeds de validacao 201/202. Colisoes, nao atendimento, "
        "espera e filas devem ser considerados juntos; reduzir espera com muitas colisoes "
        "nao e um resultado satisfatorio.", "", "## Checkpoints e aprendizagem", ""]
    for r in g["treinos"]:
        L.append(f"- Seed {r['semente_modelo']}: episodio escolhido {r['melhor_episodio']}; "
                 f"checkpoint `{r['melhor_checkpoint']}`; SHA-256 `{r['sha256_checkpoint']}`; "
                 f"estado completo `{r['ultimo_completo']}`.")
    L += ["", "## Ablacao da orientacao do supervisor", "",
        "Mesmas redes condicionadas, orientacao fixada em equilibrado. Nao equivale a "
        "um treino independente sem supervisor e nao estabelece ganho causal da hierarquia.", "",
        "| Controle | Rodadas | Espera (s) | P95 (s) | Colisoes/rodada | Nao concluidas (soma) | Viagens concluidas/rodada |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for r in g["treinos"]:
        L.append(linha(f"Seed {r['semente_modelo']}, orientacao zero", r["ablacao_orientacao_zero"]))
    L += ["", "## Protocolo e verificacao", "",
        f"Treino SUMO: 1000+episodio; validacao: {cfg['sementes_validacao']}; "
        f"teste: {cfg['sementes_teste']}. Rede/demanda originais cologne8 do SUMO-RL 1.4.5, "
        "SUMO 1.28.0; intervalo local 5 s, supervisor 30 s; verde minimo 10, amarelo 3, "
        "vermelho integral local 2, maximo condicional 60 s. Locais podem estar verdes simultaneamente.", "",
        "Replay 50000 por ator, lote 64, aquecimento 2000, Adam 5e-4, Huber, alvo a cada "
        "500 gradientes; gamma=0,95^(dt/5), epsilon local de 100% a 5% em 40000 decisoes "
        "e supervisor em 10000. Final natural/corte de escoamento fecha a experiencia; "
        "colisao mantem bootstrap e as proximas decisoes. Nenhum peso da rodada anterior "
        "foi convertido ou atualizado nesta rodada.", "",
        f"Conferidas {ver['execucoes_conferidas']} execucoes, {ver['decisoes_conferidas']} "
        f"decisoes e {ver['eventos_fases_conferidos']} eventos de fase. "
        f"{ver['arquivos_anteriores_preservados']} arquivos anteriores preservaram seus hashes; "
        "scripts alterados tiveram backup anterior. Fontes executadas estao congeladas em "
        "`fontes_execucao/`, parametros em `protocolo.json`, progresso em JSONL.", "",
        "## Limites e comparacao com a rodada anterior", "",
        "A rodada anterior parava no primeiro evento e teve exposicao curta; comparar "
        "diretamente suas esperas ou seus totais de colisoes com os daqui seria inadequado. "
        "Agora a demanda inteira pode ser atendida mesmo depois de uma colisao, como "
        "solicitado. Isso permite estudar consequencias e aprendizagem ao longo da hora, "
        "mas nao elimina os conflitos observados tambem no programa original. "
        "Nao ha conclusao de generalizacao para outras cidades, horarios ou demandas.", ""]
    if grafico:
        config = raiz / "cache_matplotlib"
        config.mkdir(exist_ok=True)
        os.environ["MPLCONFIGDIR"] = str(config)
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        fig, axs = plt.subplots(3, 1, figsize=(11, 10), sharex=True)
        for r in g["treinos"]:
            hist = []
            for ref in r["historicos"]:
                hist += [v for line in Path(ref["caminho"]).read_text().splitlines()
                         if (v := json.loads(line))["episodio"] <= ref["ate_episodio"]]
            ys = [[x["metricas"]["colisoes"] for x in hist],
                  [x["metricas"]["viagens"]["demanda_janela"]["espera_todos_inclui_censura"]["media"] for x in hist],
                  [x["metricas"]["viagens_nao_concluidas"] for x in hist]]
            n = min(20, len(hist))
            for ax, y in zip(axs, ys):
                ax.plot(np.arange(n, len(y)+1), np.convolve(y, np.ones(n)/n, mode="valid"),
                        label=f"Seed {r['semente_modelo']}", linewidth=1)
        axs[0].set_title("Cologne8: MARL contínuo com supervisor\nMédia móvel de 20 episódios; colisões não encerram o episódio")
        for ax, label in zip(axs, ("Eventos de colisão", "Espera média (s)", "Viagens não concluídas")):
            ax.set_ylabel(label)
            ax.grid(alpha=.25)
        axs[0].legend(ncol=5, fontsize=8)
        axs[-1].set_xlabel("Episódio")
        fig.tight_layout()
        path = raiz / "curvas_treino_continuo.png"
        if path.exists():
            raise FileExistsError(path)
        fig.savefig(path, dpi=150)
        plt.close(fig)
        L += ["![Curvas da rodada contínua](curvas_treino_continuo.png)", ""]
    with (raiz / "RELATORIO.md").open("x", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rodada", type=Path)
    ap.add_argument("--grafico", action="store_true")
    args = ap.parse_args()
    gerar(args.rodada, args.grafico)
