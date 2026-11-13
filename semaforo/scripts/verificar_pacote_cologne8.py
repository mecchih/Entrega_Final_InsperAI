"""Confere o pacote Cologne8 por caminhos relativos, sem SUMO, treino ou escrita.

Por padrao calcula o SHA-256 de todos os artefatos, inclusive objetos LFS.
--rapido confere tamanhos e hashes de arquivos ate 1 MB, sem alegar hash total.
Logs originais com caminhos absolutos permanecem intactos e nao sao executados.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def ler(path):
    return json.loads(path.read_text(encoding="utf-8"))


def conferir(repo, rapido=False):
    repo = repo.resolve()
    indice = repo / "semaforo/resultados/indice_execucoes_cologne8.json"
    meta = ler(indice)
    inventario = repo / meta["inventario"]["caminho"]
    assert sha(inventario) == meta["inventario"]["sha256"], "Indice de artefatos divergente"
    n = hashes = tamanho = lfs = 0
    registros = {}
    with inventario.open(encoding="utf-8") as f:
        for linha in f:
            a = json.loads(linha)
            rel = a["caminho"]
            p = (repo / rel).resolve()
            assert p.is_relative_to(repo), f"Caminho fora do repositorio: {rel}"
            assert rel not in registros, f"Registro duplicado: {rel}"
            assert p.is_file(), f"Arquivo ausente: {rel}"
            if a["git_lfs"]:
                with p.open("rb") as dado:
                    ponteiro = dado.read(64).startswith(b"version https://git-lfs.github.com/spec/v1\n")
                assert not ponteiro, f"Objeto LFS nao baixado: {rel}. Execute git lfs pull."
                lfs += 1
            assert p.stat().st_size == a["bytes"], f"Tamanho divergente: {rel}"
            if not rapido or a["bytes"] <= 1_000_000:
                assert sha(p) == a["sha256"], f"SHA-256 divergente: {rel}"
                hashes += 1
            registros[rel] = a
            n += 1
            tamanho += a["bytes"]
            if n % 2000 == 0:
                print(f"Conferidos {n} artefatos...", file=sys.stderr, flush=True)
    assert n == meta["inventario"]["arquivos"]
    assert tamanho == meta["inventario"]["bytes"]
    assert lfs == meta["inventario"]["arquivos_lfs"]
    principal = repo / meta["principal"]["pasta"]
    g = ler(principal / "resumo_geral.json")
    cfg = ler(principal / "protocolo.json")
    ver = ler(principal / "verificacao_final.json")
    assert ler(principal / "CONCLUIDO.json")["status"] == "CONCLUIDO_E_VERIFICADO"
    assert ver["status"] == "VERIFICADO" and ver["execucoes_conferidas"] == 5620
    assert cfg["episodios"] == 500 and len(g["treinos"]) == 10
    assert {t["semente_modelo"] for t in g["treinos"]} == set(range(10))
    rs = []
    for t in g["treinos"]:
        assert t["episodios"] == 500
        assert {m["semente"] for m in t["teste_final"]} == set(range(1, 11))
        checkpoint = "semaforo/" + t["melhor_checkpoint"].replace("\\", "/")
        assert registros[checkpoint]["sha256"] == t["sha256_checkpoint"]
        for m in t["teste_final"]:
            assert not m["treinando"] and not m["terminado_por_colisao"]
            assert m["teleportes"] == m["viagens_nao_concluidas"] == 0
            assert m["viagens"]["demanda_janela"]["concluidos"] == 2046
            rs.append(m)
    espera = sum(m["viagens"]["demanda_janela"]["espera_todos_inclui_censura"]["media"] for m in rs) / len(rs)
    assert math.isclose(espera, 9.290913978494624, abs_tol=1e-12)
    assert sum(m["colisoes"] for m in rs) == 1846
    return {"status": "CONFERIDO_RAPIDO" if rapido else "CONFERIDO_COMPLETO",
        "utc": datetime.now(timezone.utc).isoformat(), "arquivos": n, "bytes": tamanho,
        "arquivos_lfs": lfs, "arquivos_sha256_conferidos": hashes,
        "testes_finais": len(rs), "episodios_treino": 5000,
        "espera_media_marl_s": espera, "eventos_colisao_teste": 1846,
        "nota": "Confere integridade e numeros publicados; nao aprova seguranca ou generalizacao"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repositorio", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--rapido", action="store_true")
    a = ap.parse_args()
    print(json.dumps(conferir(a.repositorio, a.rapido), ensure_ascii=False, indent=2))
