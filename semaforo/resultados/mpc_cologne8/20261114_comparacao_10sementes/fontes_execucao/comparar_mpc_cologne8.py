"""Calibra e testa MPC sem RL no Cologne8; sempre cria uma pasta nova."""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import statistics
import sys
import uuid

# Antes de importar NumPy/SciPy/SUMO, limitar threads do processo desta tarefa.
for variavel in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variavel] = "1"
sys.dont_write_bytecode = True

from ambiente_comparacao_mpc import construir_manifesto, rodar, json_novo
from controlador_mpc_cologne8 import CONFIG, EXTERNO, MPC, Observador

PROJETO = Path(__file__).resolve().parents[1]
HISTORICO = PROJETO / "resultados/marl_cologne8/20261113T011843Z_continuo_10seeds_9f8d757b"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for pedaco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(pedaco)
    return h.hexdigest()


def ambiente():
    return {"python": sys.version, "executavel": sys.executable,
            "pacotes": {nome: importlib.metadata.version(nome) for nome in
                        ("numpy", "scipy", "clarabel", "osqp", "libsumo", "traci", "sumolib")}}


def checar_fontes():
    p = json.loads((EXTERNO / "proveniencia.json").read_text(encoding="utf-8"))
    for dado in p["arquivos"]:
        if sha(EXTERNO / dado["arquivo"]) != dado["sha256"]:
            raise ValueError("Fonte externa alterada: " + dado["arquivo"])
    m = json.loads((EXTERNO / "motor_proveniencia.json").read_text(encoding="utf-8"))
    for chave in ("original", "copia"):
        if sha(PROJETO.parent / m[chave]) != m["sha256_" + chave]:
            raise ValueError("Motor diverge da proveniencia: " + chave)


def medidas(m):
    d = m["viagens"]["demanda_janela"]
    return {"espera_s": d["espera_todos_inclui_censura"]["media"],
            "p95_s": d["espera_todos_inclui_censura"]["p95"],
            "duracao_viagem_s": d["duracao_concluidos"]["media"],
            "fila": m["fila_media_rede"], "colisoes": m["colisoes"],
            "concluidas": d["concluidos"], "nao_concluidas": m["viagens_nao_concluidas"],
            "teleportes": m["teleportes"], "intervencoes": m["intervencoes"]}


def comparar_historico(raiz, resultados, sementes):
    """Le resultados congelados; nunca escolhe checkpoint por resultado final."""
    if not HISTORICO.exists():
        return {"status": "historico_nao_disponivel"}
    protocolo = json.loads((HISTORICO / "protocolo.json").read_text(encoding="utf-8"))
    if not set(sementes).issubset(protocolo["sementes_teste"]):
        return {"status": "sementes_fora_do_teste_historico"}
    grupos = {"MPC": [medidas(m) for m in resultados]}
    fontes = []
    for chave, modo in (("Max-Pressure", "max_pressure"), ("Original", "original_fixo")):
        caminhos = [HISTORICO / "comparadores" / modo / f"seed{s}" / "metricas.json" for s in sementes]
        grupos[chave] = [medidas(json.loads(p.read_text(encoding="utf-8"))) for p in caminhos]
        fontes += caminhos
    modelos = sorted(HISTORICO.glob("modelo_seed*"))
    caminhos = [p / "teste_final" / f"seed{s}" / "metricas.json" for p in modelos for s in sementes]
    grupos["MARL"] = [medidas(json.loads(p.read_text(encoding="utf-8"))) for p in caminhos]
    fontes += caminhos
    medias = {g: {k: statistics.mean(r[k] for r in rows) for k in rows[0]} for g, rows in grupos.items()}
    deltas = {g: {k: medias["MPC"][k] - medias[g][k] for k in medias[g]} for g in grupos if g != "MPC"}
    pareados = []
    for seed, mpc in zip(sementes, grupos["MPC"], strict=True):
        referencias = [r for r in caminhos if r.parent.name == f"seed{seed}"]
        # Dez inicializacoes do MARL para a mesma semente de trafego.
        marl = [medidas(json.loads(p.read_text(encoding="utf-8"))) for p in referencias]
        pareados.append({"semente": seed, "mpc": mpc,
                         "marl_media_modelos": {k: statistics.mean(r[k] for r in marl) for k in mpc}})
    return {"status": "comparacao_descritiva_mesmo_protocolo_sumo",
            "medias": medias, "delta_mpc_menos_referencia": deltas, "pareados": pareados,
            "n_execucoes": {g: len(r) for g, r in grupos.items()},
            "nota": "MPC e controlador adaptado. Relogios, transicoes e metricas comuns; sensoriamento, modelo e politica diferentes. Dez modelos MARL reutilizam as mesmas sementes de trafego. P95 e media dos percentis por execucao.",
            "fontes_historicas": [{"arquivo": p.relative_to(PROJETO).as_posix(), "sha256": sha(p)} for p in fontes]}


def executar(args):
    checar_fontes()
    manifesto = construir_manifesto("cologne8", continuar_apos_colisao=True)
    tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:6]
    raiz = Path(args.saida).resolve() if args.saida else PROJETO / "resultados/mpc_cologne8" / tag
    raiz.mkdir(parents=True, exist_ok=False)
    print("SAIDA", raiz, flush=True)
    fontesp = [Path(__file__), Path(__file__).with_name("controlador_mpc_cologne8.py"),
               Path(__file__).with_name("ambiente_comparacao_mpc.py"),
               Path(__file__).with_name("verificar_comparacao_mpc.py")]
    json_novo(raiz / "protocolo.json", {"utc": datetime.now(timezone.utc).isoformat(),
        "modo": args.modo, "config_mpc": CONFIG, "ciclo_nominal_s": 120,
        "calibracao_seed": 1001, "teste_seeds": args.sementes, "piloto_seed": 201,
        "duracao_calibracao": 3600, "duracao_piloto": 300,
        "duracao_completa": 3600, "escoamento": 1200, "backend": args.backend,
        "sumo_home": str(args.sumo_home), "ambiente": ambiente(),
        "fontes": {p.name: sha(p) for p in fontesp},
        "parametros_congelados_antes_teste": True,
        "nao_e_reproducao_exata_do_artigo": True,
        "calibracao": "Giros/destinos observados com programa original em seed 1001, sem treinar redes; taxas futuras estimadas exclusivamente pela janela passada de 120s.",
        "execucao_verdes": "QP aloca tempos num ciclo NOMINAL; executor local mantem fase ate idade atingir alvo e segue ordem ciclica real, com atualizacao 120s, decisao 5s e protecoes historicas. Ciclos fisicos nao sao sincronizados nem obrigados a durar exatamente 120s."})
    json_novo(raiz / "manifesto.json", manifesto)
    net = PROJETO / "referencias/cologne8_sumo_rl_1.4.5/sumo_rl/nets/RESCO/cologne8/cologne8.net.xml"
    observador = Observador(net)
    calibracao = rodar(manifesto, [], raiz / "calibracao_seed1001", 1001,
                      sumo_home=args.sumo_home, modo="original_fixo", controlador_externo=observador,
                      backend="libsumo", detalhar=False)
    perfil = observador.perfil()
    json_novo(raiz / "perfil_calibracao.json", perfil)
    print("CALIBRACAO", json.dumps(medidas(calibracao)), flush=True)
    resultados = []
    etapas = [("piloto_seed201", 201, 300)]
    if args.modo == "completo":
        etapas += [(f"teste_seed{seed}", seed, 3600) for seed in args.sementes]
    for nome, seed, duracao in etapas:
        controlador = MPC(net, manifesto, perfil, raiz / (nome + "_mpc"))
        try:
            resultado = rodar(manifesto, [], raiz / nome, seed, modo="mpc_externo",
                              duracao=duracao, sumo_home=args.sumo_home, gui=args.gui,
                              backend=args.backend, detalhar=True, controlador_externo=controlador)
        finally:
            controlador.fechar()
        if resultado["terminado_por_colisao"] or resultado["fim_sumo"] < 25200 + duracao:
            raise AssertionError("Verificacao encerrou antes da janela prevista")
        if resultado["versao_sumo"][1] != "SUMO 1.28.0":
            raise ValueError("Versao do SUMO difere do experimento historico")
        print(nome, json.dumps(medidas(resultado)), flush=True)
        if duracao == 3600:
            resultados.append(resultado)
    comparacao = comparar_historico(raiz, resultados, args.sementes) if resultados else None
    json_novo(raiz / "resumo.json", {"resultados_completos": resultados, "comparacao": comparacao})
    if "torch" in sys.modules:
        raise AssertionError("Comparador sem RL importou torch")
    from verificar_comparacao_mpc import verificar
    json_novo(raiz / "VERIFICACAO.json", verificar(raiz))
    json_novo(raiz / "CONCLUIDO.json", {"status": "CONCLUIDO", "utc": datetime.now(timezone.utc).isoformat(),
               "calibracao": 1, "piloto": 1, "rodadas_completas": len(resultados),
               "pesos_carregados": 0, "redes_treinadas": 0})
    print("CONCLUIDO", raiz, flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--modo", choices=("curto", "completo"), default="curto")
    ap.add_argument("--sementes", nargs="+", type=int, default=list(range(1, 11)))
    ap.add_argument("--saida", type=Path)
    ap.add_argument("--sumo-home", type=Path, default=Path(os.environ["SUMO_HOME"]) if "SUMO_HOME" in os.environ else None)
    ap.add_argument("--backend", choices=("libsumo", "traci"), default="libsumo")
    ap.add_argument("--gui", action="store_true")
    args = ap.parse_args()
    if len(set(args.sementes)) != len(args.sementes):
        ap.error("Sementes repetidas")
    if args.gui and args.backend != "traci":
        ap.error("--gui exige --backend traci")
    executar(args)


if __name__ == "__main__":
    main()
