"""Treina/avalia quatro Double DQNs em cologne3, sempre em diretorios novos."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
import uuid

sys.dont_write_bytecode = True
import torch

from agente_marl_cologne import DoubleDQN
from ambiente_marl_cologne import (FORMATO, PROJETO, construir_manifesto, json_novo, rodar, sha)


def criar_agentes(manifesto, semente, aquecimento=2000, lote=64,
                  aquecimento_supervisor=None, decaimento_local=40000, decaimento_supervisor=10000):
    agentes = [DoubleDQN(s["entradas_com_supervisor"], s["n_acoes"],
                        semente * 100 + i, aquecimento=aquecimento, lote=lote)
               for i, s in enumerate(manifesto["controladores"])]
    agentes.append(DoubleDQN(manifesto["entradas_supervisor"], len(agentes) + 1,
                            semente * 100 + 99, supervisor=True,
                            aquecimento=aquecimento if aquecimento_supervisor is None else aquecimento_supervisor, lote=lote))
    for a in agentes[:-1]:
        a.decaimento = decaimento_local
    agentes[-1].decaimento = decaimento_supervisor
    return agentes


def digest_pesos(agentes):
    h = hashlib.sha256()
    for a in agentes:
        for v in a.rede.state_dict().values():
            h.update(v.detach().numpy().tobytes())
    return h.hexdigest()


def assinatura_treino(agentes):
    return [(a.decisoes, a.gradientes, a.memoria.n, a.epsilon, a.gamma, a.lote,
             a.aquecimento, a.rng.getstate(),
             json.dumps(a.np_rng.bit_generator.state, sort_keys=True)) for a in agentes]


def checkpoint(path, agentes, manifesto, episodio, completo=False):
    dados = {"formato": FORMATO, "manifesto": manifesto, "episodio": episodio,
             "completo_para_retomada": completo,
             "agentes": [a.estado(completo) for a in agentes]}
    with Path(path).open("xb") as f:
        torch.save(dados, f)


def carregar_checkpoint(path, manifesto, completo=False):
    dados = torch.load(path, map_location="cpu", weights_only=True)
    if dados["formato"] != FORMATO or dados["manifesto"] != manifesto:
        raise ValueError("Checkpoint pertence a outro protocolo/cenario")
    if completo and not dados.get("completo_para_retomada"):
        raise ValueError("Checkpoint nao contem estado de treino")
    agentes = criar_agentes(manifesto, 0)
    for a, d in zip(agentes, dados["agentes"], strict=True):
        a.carregar(d, completo)
    return agentes, dados["episodio"]


def pontuacao(metricas):
    """Censura vem antes da media para nao premiar veiculos abandonados."""
    # Terminar cedo deixa tambem partidas futuras sem atendimento. Ignora-las
    # premiaria o episodio que colidiu antes de a maior parte da demanda chegar.
    censura = sum(m["viagens_nao_concluidas"] for m in metricas)
    esperas = [m["viagens"]["afetados_pelo_controle"]["espera_todos_inclui_censura"]["media"]
               for m in metricas]
    return [sum(m["colisoes"] for m in metricas), censura,
            statistics.mean(v if v is not None else 1e9 for v in esperas)]


def validar(agentes, manifesto, pasta, sementes, args, modo="hierarquico", detalhar=False):
    antes, pesos = assinatura_treino(agentes), digest_pesos(agentes)
    resultados = []
    for s in sementes:
        resultados.append(rodar(manifesto, agentes, pasta / f"seed{s}", s,
            treinando=False, duracao=args.duracao, escoamento=args.escoamento,
            backend=args.backend, sumo_home=args.sumo_home, gui=args.gui,
            modo=modo, detalhar=detalhar))
    if antes != assinatura_treino(agentes) or pesos != digest_pesos(agentes):
        raise AssertionError("Avaliacao alterou aprendizagem, exploracao ou pesos")
    return resultados


def executar_treino(args, manifesto, raiz):
    todos = []
    for seed in args.sementes:
        pasta = raiz / f"modelo_seed{seed}"
        pasta.mkdir()
        agentes = criar_agentes(manifesto, seed, aquecimento=args.aquecimento_local,
            aquecimento_supervisor=args.aquecimento_supervisor,
            decaimento_local=args.decaimento_local, decaimento_supervisor=args.decaimento_supervisor)
        inicio = time.perf_counter()
        melhor, melhor_arquivo, melhor_ep = [float("inf")] * 3, None, None
        historico, validacoes = [], []
        with (pasta / "historico.jsonl").open("x", encoding="utf-8") as hist:
            for ep in range(1, args.episodios + 1):
                m = rodar(manifesto, agentes, pasta / "episodios" / f"ep{ep:04d}",
                    1000 + ep, treinando=True, duracao=args.duracao,
                    escoamento=args.escoamento, backend=args.backend, sumo_home=args.sumo_home,
                    detalhar=ep in (1, args.episodios))
                registro = {"episodio": ep, "semente_modelo": seed, "semente_trafego": 1000 + ep,
                    "metricas": m, "epsilon": [a.epsilon for a in agentes],
                    "decisoes_treino": [a.decisoes for a in agentes],
                    "gradientes": [a.gradientes for a in agentes],
                    "perda_media_200": [statistics.mean(a.perdas) if a.perdas else None for a in agentes]}
                historico.append(registro)
                hist.write(json.dumps(registro, ensure_ascii=False, allow_nan=False) + "\n")
                hist.flush()
                if ep == 1 or ep % 5 == 0:
                    w = m["viagens"]["afetados_pelo_controle"]["espera_todos_inclui_censura"]["media"]
                    print(f"seed={seed} ep={ep}/{args.episodios} espera={w:.2f}s "
                          f"restam={m['remanescentes']} grad={[a.gradientes for a in agentes]} "
                          f"episodio={m['duracao_real_s']:.1f}s", flush=True)
                if ep % args.validar_cada == 0 or ep == args.episodios:
                    val = validar(agentes, manifesto, pasta / "validacao" / f"ep{ep:04d}",
                                  [201, 202], args)
                    score = pontuacao(val)
                    salvou = score < melhor
                    if salvou:
                        melhor, melhor_ep = score, ep
                        melhor_arquivo = pasta / f"politica_ep{ep:04d}.pt"
                        checkpoint(melhor_arquivo, agentes, manifesto, ep)
                    validacoes.append({"episodio": ep, "pontuacao": score, "melhorou": salvou,
                                       "resultados": val})
                    json_novo(pasta / "validacao" / f"ep{ep:04d}" / "resumo.json", validacoes[-1])
                    print(f"VALIDACAO seed={seed} ep={ep} colisoes={score[0]} censurados={score[1]} "
                          f"espera={score[2]:.2f}s salvou={salvou}", flush=True)
        checkpoint(pasta / "ultimo_completo.pt", agentes, manifesto, args.episodios, completo=True)
        if any(a.gradientes == 0 for a in agentes):
            raise RuntimeError("Rodada terminou sem gradientes em algum agente; nao pode ser declarada treinamento dos nove")
        avaliadores, _ = carregar_checkpoint(melhor_arquivo, manifesto)
        testes = validar(avaliadores, manifesto, pasta / "teste_final", [1], args, detalhar=True)
        sem_supervisor = validar(avaliadores, manifesto, pasta / "ablacao_orientacao_zero", [1], args,
                                 modo="sem_supervisor", detalhar=True)
        resumo = {"semente_modelo": seed, "episodios": args.episodios,
            "melhor_episodio": melhor_ep, "melhor_validacao": melhor,
            "melhor_checkpoint": str(melhor_arquivo.relative_to(PROJETO)),
            "sha256_checkpoint": sha(melhor_arquivo), "duracao_s": time.perf_counter() - inicio,
            "validacoes": validacoes, "teste_final": testes,
            "ablacao_orientacao_zero": sem_supervisor,
            "nota_ablacao": "mesmas redes condicionadas, objetivo fixado em zero; nao equivale a treinar IQL sem supervisor"}
        json_novo(pasta / "resumo.json", resumo)
        todos.append(resumo)
    # Referencias da mesma demanda e semente; original usa tempos diferentes.
    agentes = criar_agentes(manifesto, 9876)
    comparadores = {}
    for modo in ("max_pressure", "original_fixo"):
        comparadores[modo] = validar(agentes, manifesto, raiz / "comparadores" / modo, [1], args,
                                    modo=modo, detalhar=True)
    final = {"status": "CONCLUIDO", "treinos": todos, "comparadores": comparadores}
    json_novo(raiz / "resumo_geral.json", final)
    return final


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("modo", choices=["treinar", "avaliar", "piloto"])
    ap.add_argument("--episodios", type=int, default=250)
    ap.add_argument("--sementes", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--validar-cada", type=int, default=25)
    ap.add_argument("--duracao", type=int, default=3600)
    ap.add_argument("--escoamento", type=int, default=1200)
    ap.add_argument("--backend", choices=["libsumo", "traci"], default="libsumo")
    ap.add_argument("--sumo-home", type=Path)
    ap.add_argument("--gui", action="store_true")
    ap.add_argument("--checkpoint", type=Path)
    ap.add_argument("--saida", type=Path, help="diretorio que ainda nao existe")
    ap.add_argument("--cenario", choices=["cologne3", "cologne8"], default="cologne8")
    ap.add_argument("--aquecimento-local", type=int, default=2000)
    ap.add_argument("--aquecimento-supervisor", type=int, default=256)
    ap.add_argument("--decaimento-local", type=int, default=40000)
    ap.add_argument("--decaimento-supervisor", type=int, default=10000)
    args = ap.parse_args()
    if args.episodios < 1 or args.validar_cada < 1 or len(set(args.sementes)) != len(args.sementes):
        ap.error("Numero de episodios/intervalo/sementes invalido")
    if args.gui and (args.backend != "traci" or args.modo != "avaliar"):
        ap.error("GUI disponivel somente para avaliar com backend traci")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    manifesto = construir_manifesto(args.cenario)
    nome = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + args.modo + "_" + uuid.uuid4().hex[:8]
    raiz = args.saida or PROJETO / f"resultados/marl_{args.cenario}" / nome
    raiz = raiz.resolve()
    raiz.mkdir(parents=True, exist_ok=False)
    json_novo(raiz / "manifesto.json", manifesto)
    scripts = [Path(__file__), Path(__file__).with_name("agente_marl_cologne.py"),
               Path(__file__).with_name("ambiente_marl_cologne.py")]
    json_novo(raiz / "protocolo.json", {"argumentos": {k: str(v) if isinstance(v, Path) else v
        for k, v in vars(args).items()}, "torch": str(torch.__version__), "python": sys.version,
        "scripts_sha256": {str(p.relative_to(PROJETO)): sha(p) for p in scripts},
        "treino": "1000+episodio", "validacao": [201, 202], "teste": [1],
        "nota": "mesmas rotas fixas em todas as sementes; nao e demanda inedita"})
    print(f"RESULTADOS {raiz}", flush=True)
    print("ARQUITETURAS", [(s["entradas_com_supervisor"], 64, 64, s["n_acoes"])
          for s in manifesto["controladores"]], "SUPERVISOR", manifesto["entradas_supervisor"],
          "->", len(manifesto["acoes_supervisor"]), flush=True)
    try:
        if args.modo == "treinar":
            executar_treino(args, manifesto, raiz)
        elif args.modo == "avaliar":
            if not args.checkpoint:
                ap.error("Informe --checkpoint")
            agentes, ep = carregar_checkpoint(args.checkpoint, manifesto)
            ms = validar(agentes, manifesto, raiz / "avaliacao", [1], args, detalhar=True)
            json_novo(raiz / "resumo_geral.json", {"status": "CONCLUIDO", "episodio": ep, "resultados": ms})
        else:
            agentes = criar_agentes(manifesto, 9876, aquecimento=8, lote=8)
            iniciais = digest_pesos(agentes)
            ms = []
            # Uma colisao pode terminar cedo: usar episodios novos ate que
            # todos os atores exercitem replay/gradiente, sem mudar o lote real.
            for piloto_ep in range(1, 6):
                m = rodar(manifesto, agentes, raiz / f"piloto_ep{piloto_ep}", 1000 + piloto_ep,
                          treinando=True, duracao=args.duracao, escoamento=args.escoamento,
                          backend=args.backend, sumo_home=args.sumo_home, detalhar=True)
                ms.append(m)
                if m["colisoes"]:
                    for a in agentes:
                        ultimo = (a.memoria.posicao - 1) % a.memoria.capacidade
                        if a.memoria.r[ultimo] > -10000 or a.memoria.fim[ultimo] != 1:
                            raise AssertionError("Colisao nao entrou como penalidade terminal no replay")
                if all(a.gradientes > 0 for a in agentes):
                    break
            if any(a.gradientes == 0 for a in agentes) or digest_pesos(agentes) == iniciais:
                raise AssertionError("Piloto nao exercitou gradientes dos quatro agentes")
            checkpoint(raiz / "piloto.pt", agentes, manifesto, 1, completo=True)
            recarregados, _ = carregar_checkpoint(raiz / "piloto.pt", manifesto, completo=True)
            if digest_pesos(agentes) != digest_pesos(recarregados) or assinatura_treino(agentes) != assinatura_treino(recarregados):
                raise AssertionError("Retomada de checkpoint inconsistente")
            import numpy as np
            for a, b in zip(agentes, recarregados):
                for campo in ("s", "s2", "a", "r", "dt", "fim"):
                    if not np.array_equal(getattr(a.memoria, campo)[:a.memoria.n],
                                          getattr(b.memoria, campo)[:b.memoria.n]):
                        raise AssertionError("Replay recarregado diverge")
            validacao = validar(agentes, manifesto, raiz / "avaliacao", [201], args, detalhar=True)
            json_novo(raiz / "resumo_geral.json", {"status": "CONCLUIDO", "metricas_piloto": ms,
                "gradientes": [a.gradientes for a in agentes], "avaliacao": validacao,
                "pesos_atualizados": True, "inferencia_preservou_treino": True,
                "checkpoint_completo_recarregado": True, "piloto_descartado_do_treino_principal": True})
        print(f"CONCLUIDO {raiz}", flush=True)
    except BaseException as e:
        json_novo(raiz / "falha.json", {"tipo": type(e).__name__, "mensagem": str(e)})
        raise


if __name__ == "__main__":
    main()
