"""Rodada longa de cologne8: colisao penalizada, episodio continua, fontes congeladas.

Coordenador usa somente biblioteca padrao; cada processo SUMO tem relogio e
memoria proprios. Paralelismo e entre inicializacoes, nao entre nos da cidade.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode = True
PROJETO = Path(os.environ.get("SMARTFLOW_PROJETO", Path(__file__).resolve().parents[1])).resolve()


def agora():
    return datetime.now(timezone.utc).isoformat()


def novo(path, dados):
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False, allow_nan=False)


def evento(path, dados):
    with Path(path).open("a", encoding="utf-8") as f:
        f.write(json.dumps({"utc": agora(), **dados}, ensure_ascii=False, allow_nan=False) + "\n")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bibliotecas():
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    from ambiente_marl_cologne import construir_manifesto, rodar
    from treinar_marl_cologne import criar_agentes, assinatura_treino, digest_pesos, pontuacao
    return torch, construir_manifesto, rodar, criar_agentes, assinatura_treino, digest_pesos, pontuacao


def salvar(path, agentes, manifesto, ep, seed, completo=False, retomada=None):
    import torch
    with Path(path).open("xb") as f:
        torch.save({"formato": manifesto["formato"], "manifesto": manifesto, "episodio": ep,
            "semente_modelo": seed, "completo_para_retomada": completo,
            "agentes": [a.estado(completo) for a in agentes], "retomada": retomada}, f)


def carregar(path, manifesto, criar_agentes, completo=False):
    import torch
    d = torch.load(path, map_location="cpu", weights_only=True)
    if d["formato"] != manifesto["formato"] or d["manifesto"] != manifesto:
        raise ValueError("Checkpoint tem outro protocolo, cenario ou fontes")
    if completo and not d["completo_para_retomada"]:
        raise ValueError("Retomada exige replay, alvos, Adam e RNG")
    ag = criar_agentes(manifesto, d["semente_modelo"])
    for a, dados in zip(ag, d["agentes"], strict=True):
        a.carregar(dados, completo)
    return ag, d


def avaliar(agentes, manifesto, pasta, sementes, cfg, funcoes, modo="hierarquico", detalhar=False):
    _, _, rodar, _, assinatura, digest, _ = funcoes
    antes, pesos = assinatura(agentes), digest(agentes)
    resultados = []
    for seed in sementes:
        resultados.append(rodar(manifesto, agentes, pasta / f"seed{seed}", seed,
            treinando=False, duracao=cfg["duracao"], escoamento=cfg["escoamento"],
            backend="libsumo", sumo_home=Path(cfg["sumo_home"]), modo=modo, detalhar=detalhar))
    if antes != assinatura(agentes) or pesos != digest(agentes):
        raise AssertionError("Avaliacao alterou aprendizagem ou pesos")
    return resultados


def trabalhar(raiz, seed, retomar=None):
    funcoes = bibliotecas()
    torch, construir, rodar, criar_agentes, _, _, pontuacao = funcoes
    cfg = json.loads((raiz / "protocolo.json").read_text(encoding="utf-8"))
    manifesto = construir("cologne8", continuar_apos_colisao=True)
    if manifesto != json.loads((raiz / "manifesto.json").read_text(encoding="utf-8")):
        raise ValueError("Arquivos do cenario mudaram apos a preparacao")
    pasta = raiz / f"modelo_seed{seed}"
    pasta.mkdir(exist_ok=False)
    inicio = time.perf_counter()
    ep_inicial, historicos_anteriores, validacoes = 0, [], []
    melhor, melhor_ep, melhor_arq = [float("inf")] * 3, None, None
    if retomar:
        agentes, d = carregar(retomar, manifesto, criar_agentes, completo=True)
        if d["semente_modelo"] != seed:
            raise ValueError("Semente solicitada difere da semente do checkpoint")
        ep_inicial = d["episodio"]
        estado = d["retomada"]
        historicos_anteriores = estado["historicos"]
        validacoes = estado["validacoes"]
        melhor, melhor_ep, melhor_arq = estado["melhor"], estado["melhor_ep"], Path(estado["melhor_arq"])
        if any(a.aquecimento != max(64, cfg["aquecimento_local"]) for a in agentes[:-1]) or agentes[-1].aquecimento != max(64, cfg["aquecimento_supervisor"]):
            raise ValueError("Aquecimento do checkpoint difere da configuracao solicitada")
    else:
        agentes = criar_agentes(manifesto, seed, aquecimento=cfg["aquecimento_local"],
            aquecimento_supervisor=cfg["aquecimento_supervisor"],
            decaimento_local=cfg["decaimento_local"], decaimento_supervisor=cfg["decaimento_supervisor"])
    historico_path = pasta / "historico.jsonl"
    with historico_path.open("x", encoding="utf-8") as hist:
        for ep in range(ep_inicial + 1, cfg["episodios"] + 1):
            m = rodar(manifesto, agentes, pasta / "episodios" / f"ep{ep:04d}",
                1000 + ep, treinando=True, duracao=cfg["duracao"], escoamento=cfg["escoamento"],
                backend="libsumo", sumo_home=Path(cfg["sumo_home"]),
                detalhar=ep in (ep_inicial + 1, cfg["episodios"]))
            if m["terminado_por_colisao"] or m["fim_sumo"] < 25200 + cfg["duracao"]:
                raise AssertionError("Protocolo continuo encerrou episodio antes da hora prevista")
            registro = {"episodio": ep, "semente_modelo": seed, "semente_trafego": 1000 + ep,
                "metricas": m, "epsilon": [a.epsilon for a in agentes],
                "decisoes_treino": [a.decisoes for a in agentes], "gradientes": [a.gradientes for a in agentes],
                "perda_media_200": [statistics.mean(a.perdas) if a.perdas else None for a in agentes]}
            hist.write(json.dumps(registro, ensure_ascii=False, allow_nan=False) + "\n")
            hist.flush()
            evento(raiz / f"progresso_seed{seed}.jsonl", {"tipo": "episodio", "episodio": ep,
                "colisoes": m["colisoes"], "espera": m["viagens"]["demanda_janela"]["espera_todos_inclui_censura"]["media"],
                "nao_concluidas": m["viagens_nao_concluidas"], "segundos_sumo": m["passos_controlados"],
                "segundos_reais": m["duracao_real_s"], "gradientes": registro["gradientes"]})
            print(f"seed={seed} ep={ep}/{cfg['episodios']} colisoes={m['colisoes']} "
                  f"nao_concluidas={m['viagens_nao_concluidas']} tempo={m['duracao_real_s']:.2f}s", flush=True)
            if ep % cfg["validar_cada"] == 0 or ep == cfg["episodios"]:
                val = avaliar(agentes, manifesto, pasta / "validacao" / f"ep{ep:04d}",
                              cfg["sementes_validacao"], cfg, funcoes)
                score = pontuacao(val)
                melhorou = score < melhor
                if melhorou:
                    melhor, melhor_ep = score, ep
                    melhor_arq = pasta / f"politica_ep{ep:04d}.pt"
                    salvar(melhor_arq, agentes, manifesto, ep, seed)
                v = {"episodio": ep, "pontuacao": score, "melhorou": melhorou, "resultados": val}
                validacoes.append(v)
                novo(pasta / "validacao" / f"ep{ep:04d}" / "resumo.json", v)
                evento(raiz / f"progresso_seed{seed}.jsonl", {"tipo": "validacao", "episodio": ep,
                    "pontuacao": score, "melhorou": melhorou})
            if ep % cfg["salvar_cada"] == 0 or ep == cfg["episodios"]:
                salvar(pasta / f"estado_ep{ep:04d}.pt", agentes, manifesto, ep, seed, completo=True,
                    retomada={"historicos": historicos_anteriores + [{"caminho": str(historico_path), "ate_episodio": ep}],
                        "validacoes": validacoes, "melhor": melhor, "melhor_ep": melhor_ep,
                        "melhor_arq": str(melhor_arq)})
    if any(a.gradientes == 0 for a in agentes):
        raise RuntimeError("Algum dos nove atores terminou sem aprender")
    escolhidos, _ = carregar(melhor_arq, manifesto, criar_agentes)
    testes = avaliar(escolhidos, manifesto, pasta / "teste_final", cfg["sementes_teste"], cfg,
                      funcoes, detalhar=True)
    ablacao = avaliar(escolhidos, manifesto, pasta / "ablacao_orientacao_zero", cfg["sementes_teste"], cfg,
                       funcoes, modo="sem_supervisor")
    resumo = {"semente_modelo": seed, "episodios": cfg["episodios"], "episodio_inicial": ep_inicial,
        "historicos": historicos_anteriores + [{"caminho": str(historico_path), "ate_episodio": cfg["episodios"]}], "pasta_modelo": str(pasta),
        "melhor_episodio": melhor_ep, "melhor_validacao": melhor,
        "melhor_checkpoint": str(melhor_arq.relative_to(PROJETO)), "sha256_checkpoint": sha(melhor_arq),
        "ultimo_completo": str(pasta / f"estado_ep{cfg['episodios']:04d}.pt"),
        "duracao_s": time.perf_counter() - inicio, "validacoes": validacoes,
        "teste_final": testes, "ablacao_orientacao_zero": ablacao,
        "gradientes_finais": [a.gradientes for a in agentes]}
    novo(pasta / "resumo.json", resumo)
    evento(raiz / f"progresso_seed{seed}.jsonl", {"tipo": "CONCLUIDO", "episodio": cfg["episodios"]})


def comparadores(raiz):
    funcoes = bibliotecas()
    _, construir, _, criar_agentes, _, _, _ = funcoes
    cfg = json.loads((raiz / "protocolo.json").read_text(encoding="utf-8"))
    m = construir("cologne8", continuar_apos_colisao=True)
    a = criar_agentes(m, 9876)
    saida = {modo: avaliar(a, m, raiz / "comparadores" / modo, cfg["sementes_teste"], cfg,
                          funcoes, modo=modo) for modo in ("max_pressure", "original_fixo")}
    novo(raiz / "comparadores.json", saida)


def coordenar(raiz, cfg, retomar=None):
    fila, ativos, falhas = list(cfg["sementes_modelo"]), {}, []
    ambiente = os.environ.copy()
    ambiente.update(SMARTFLOW_PROJETO=str(PROJETO), PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1",
                    OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    fonte = raiz / "fontes_execucao" / Path(__file__).name
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    while fila or ativos:
        while fila and len(ativos) < cfg["trabalhadores"]:
            seed = fila.pop(0)
            args = [sys.executable, "-B", "-X", "utf8", str(fonte), "--worker", str(seed), "--raiz", str(raiz)]
            if retomar:
                args += ["--retomar-checkpoint", str(retomar)]
            log = (raiz / f"worker_seed{seed}.log").open("x", encoding="utf-8")
            p = subprocess.Popen(args, cwd=PROJETO.parent, env=ambiente,
                                 stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
            ativos[seed] = (p, log)
            evento(raiz / "eventos_execucao.jsonl", {"tipo": "INICIADO", "semente": seed, "pid": p.pid})
            print(f"INICIADO seed={seed} pid={p.pid}", flush=True)
        for seed, (p, log) in list(ativos.items()):
            codigo = p.poll()
            if codigo is None:
                continue
            log.close()
            evento(raiz / "eventos_execucao.jsonl", {"tipo": "FIM_PROCESSO", "semente": seed, "codigo": codigo})
            if codigo:
                falhas.append({"semente": seed, "codigo": codigo})
            del ativos[seed]
            print(f"FIM seed={seed} codigo={codigo}", flush=True)
        if ativos:
            time.sleep(2)
    if falhas:
        novo(raiz / "falhas.json", falhas)
        raise RuntimeError(f"Falha em {len(falhas)} inicializacoes; demais resultados preservados")
    # Comparadores em processo separado para nao reservar torch/replay no coordenador.
    log = (raiz / "comparadores.log").open("x", encoding="utf-8")
    try:
        resultado = subprocess.run([sys.executable, "-B", "-X", "utf8", str(fonte),
            "--comparadores", "--raiz", str(raiz)], cwd=PROJETO.parent, env=ambiente,
            stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
    finally:
        log.close()
    if resultado.returncode:
        raise RuntimeError("Comparadores falharam; consultar comparadores.log")
    todos = [json.loads((raiz / f"modelo_seed{s}/resumo.json").read_text(encoding="utf-8"))
             for s in cfg["sementes_modelo"]]
    refs = json.loads((raiz / "comparadores.json").read_text(encoding="utf-8"))
    novo(raiz / "resumo_geral.json", {"status": "CONCLUIDO", "protocolo": "continuo_v2",
                                    "treinos": todos, "comparadores": refs})
    evento(raiz / "eventos_execucao.jsonl", {"tipo": "TREINOS_E_TESTES_CONCLUIDOS"})
    # Conferencia e relatorio ocorrem mesmo que a interface do agente seja fechada.
    etapas = [(sys.executable, "verificar_marl_continuo.py", []),
              (cfg["python_relatorio"], "relatar_marl_continuo.py", ["--grafico"])]
    for python, script, extras in etapas:
        with (raiz / (script + ".log")).open("x", encoding="utf-8") as log:
            result = subprocess.run([python, "-B", "-X", "utf8", str(raiz / "fontes_execucao" / script),
                str(raiz), *extras], cwd=PROJETO.parent, env=ambiente, stdout=log,
                stderr=subprocess.STDOUT, creationflags=flags)
        if result.returncode:
            raise RuntimeError(f"Falha em {script}; consultar seu log")
    novo(raiz / "CONCLUIDO.json", {"status": "CONCLUIDO_E_VERIFICADO", "utc": agora()})
    print(f"CONCLUIDO {raiz}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--episodios", type=int, default=500)
    ap.add_argument("--sementes", type=int, nargs="+", default=list(range(10)))
    ap.add_argument("--sementes-teste", type=int, nargs="+", default=list(range(1, 11)))
    ap.add_argument("--trabalhadores", type=int, default=3)
    ap.add_argument("--aquecimento-local", type=int, default=2000)
    ap.add_argument("--aquecimento-supervisor", type=int, default=2000)
    ap.add_argument("--sumo-home", type=Path)
    ap.add_argument("--saida", type=Path)
    ap.add_argument("--snapshot", type=Path)
    ap.add_argument("--python-relatorio", type=Path,
                    default=PROJETO.parent / ".venv-marl-relatorio/Scripts/python.exe")
    ap.add_argument("--worker", type=int)
    ap.add_argument("--raiz", type=Path)
    ap.add_argument("--comparadores", action="store_true")
    ap.add_argument("--retomar-checkpoint", type=Path)
    args = ap.parse_args()
    if args.worker is not None:
        trabalhar(args.raiz, args.worker, args.retomar_checkpoint)
        return
    if args.comparadores:
        comparadores(args.raiz)
        return
    if args.episodios < 1 or args.trabalhadores < 1 or len(args.sementes) != len(set(args.sementes)):
        ap.error("Episodios, trabalhadores ou sementes invalidos")
    if not args.sumo_home:
        ap.error("Informe --sumo-home")
    if args.retomar_checkpoint and len(args.sementes) != 1:
        ap.error("Retomada requer exatamente uma semente de modelo")
    # Importar ambiente nao carrega PyTorch; apenas NumPy e biblioteca padrao.
    from ambiente_marl_cologne import construir_manifesto
    m = construir_manifesto("cologne8", continuar_apos_colisao=True)
    nome = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_continuo_" + uuid.uuid4().hex[:8]
    raiz = (args.saida or PROJETO / "resultados/marl_cologne8" / nome).resolve()
    raiz.mkdir(parents=True, exist_ok=False)
    fontes = raiz / "fontes_execucao"
    fontes.mkdir()
    nomes = ["treinar_marl_continuo.py", "agente_marl_cologne.py", "ambiente_marl_cologne.py",
             "treinar_marl_cologne.py", "esquema_dqn_cologne3.py", "verificar_marl_continuo.py",
             "verificar_rodada_marl_cologne.py", "relatar_marl_continuo.py"]
    hashes = {}
    for nome in nomes:
        src = Path(__file__).parent / nome
        raw = src.read_bytes()
        with (fontes / nome).open("xb") as f:
            f.write(raw)
        hashes[nome] = hashlib.sha256(raw).hexdigest()
    cfg = {"episodios": args.episodios, "sementes_modelo": args.sementes,
        "sementes_treino_sumo": "1000+episodio", "sementes_validacao": [201, 202],
        "sementes_teste": args.sementes_teste, "trabalhadores": min(args.trabalhadores, len(args.sementes)),
        "duracao": 3600, "escoamento": 1200, "validar_cada": 25, "salvar_cada": 100,
        "aquecimento_local": args.aquecimento_local, "aquecimento_supervisor": args.aquecimento_supervisor,
        "decaimento_local": 40000, "decaimento_supervisor": 10000,
        "sumo_home": str(args.sumo_home.resolve()), "python": sys.version,
        "fontes_sha256": hashes, "iniciado_utc": agora(),
        "snapshot": str(args.snapshot.resolve()) if args.snapshot else None,
        "python_relatorio": str(args.python_relatorio.resolve()),
        "retomar_checkpoint": str(args.retomar_checkpoint.resolve()) if args.retomar_checkpoint else None,
        "nota": "Mesmo OD/horarios entre sementes. Colisoes continuam com -10000 por contato novo/ator."}
    novo(raiz / "protocolo.json", cfg)
    novo(raiz / "manifesto.json", m)
    print(f"RESULTADOS {raiz}", flush=True)
    try:
        coordenar(raiz, cfg, args.retomar_checkpoint.resolve() if args.retomar_checkpoint else None)
    except BaseException as e:
        novo(raiz / "falha_coordenador.json", {"tipo": type(e).__name__, "mensagem": str(e)})
        raise


if __name__ == "__main__":
    main()
