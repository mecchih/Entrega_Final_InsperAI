"""Empacota os registros detalhados da rodada principal do MARL Cologne8 em .tar.xz.

Sem perda: cada pacote e um .tar deterministico (ordem fixa, mtime 0, dono 0)
comprimido com xz. Antes de empacotar, cada arquivo e conferido contra o
inventario (tamanho e SHA-256). Nao remove nem altera os originais, nao toca em
arquivos Git LFS e nunca sobrescreve pacotes ou manifesto existentes.

Entram, por semente de modelo, somente registros cujo conteudo tambem e
resumido em arquivos que permanecem abertos (historico.jsonl, resumo.json,
resumo_geral.json e analises):
  episodios/epNNNN/{metricas.json, sumo.log, execucao.json, decisoes.jsonl, fases.jsonl}
  validacao/epNNNN/{resumo.json, seedNNN/{metricas.json, sumo.log, execucao.json}}
  teste_final/seedNN/{decisoes.jsonl, fases.jsonl}

Uso, na raiz do repositorio:
  python semaforo/scripts/empacotar_registros_cologne8.py              # cria pacotes e manifesto
  python semaforo/scripts/empacotar_registros_cologne8.py --conferir   # refaz os .tar dos originais e compara
"""

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import lzma
from multiprocessing import Pool
from pathlib import Path
import re
import sys
import tarfile

from restaurar_registros_cologne8 import (FORMATO, MANIFESTO, PASTA_PACOTES, PREFIXO_MARL, REPO,
                                          ler_inventario, ler_json, sha_arquivo)

RODADA = PREFIXO_MARL + "20261113T011843Z_continuo_10seeds_9f8d757b"
REGRAS = {  # expressao (relativa a rodada) -> funcao que da o tipo do pacote
    r"modelo_seed(\d+)/episodios/ep\d{4}/(metricas\.json|sumo\.log|execucao\.json|decisoes\.jsonl|fases\.jsonl)":
        lambda nome: {"metricas.json": "episodios_metricas", "sumo.log": "episodios_sumo_log",
                      "execucao.json": "episodios_execucao"}.get(nome, "episodios_decisoes_fases"),
    r"modelo_seed(\d+)/validacao/ep\d{4}/(resumo\.json|seed\d+/(?:metricas\.json|sumo\.log|execucao\.json))":
        lambda nome: "validacao",
    r"modelo_seed(\d+)/teste_final/seed\d+/(decisoes\.jsonl|fases\.jsonl)":
        lambda nome: "teste_final_" + nome.split(".")[0],
}
PRESET_XZ = 9 | lzma.PRESET_EXTREME


def selecionar(inv):
    """Agrupa os arquivos candidatos do inventario em (semente, tipo) -> caminhos."""
    grupos = {}
    for caminho, a in inv.items():
        if a["git_lfs"] or not caminho.startswith(RODADA + "/"):
            continue
        rel = caminho[len(RODADA) + 1:]
        for regra, tipo in REGRAS.items():
            m = re.fullmatch(regra, rel)
            if m:
                chave = (int(m.group(1)), tipo(m.group(2).rsplit("/", 1)[-1]))
                grupos.setdefault(chave, []).append(caminho)
                break
    return {k: sorted(v) for k, v in sorted(grupos.items())}


def tar_deterministico(repo, caminhos, inv):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for c in caminhos:
            dados = (repo / c).read_bytes()
            a = inv[c]
            if len(dados) != a["bytes"] or hashlib.sha256(dados).hexdigest() != a["sha256"]:
                raise SystemExit(f"Original divergente do inventario, nada empacotado: {c}")
            ti = tarfile.TarInfo(c)
            ti.size, ti.mtime, ti.mode, ti.uid, ti.gid, ti.uname, ti.gname = len(dados), 0, 0o644, 0, 0, "", ""
            tar.addfile(ti, io.BytesIO(dados))
    return buf.getvalue(), sum(inv[c]["bytes"] for c in caminhos)


def caminho_pacote(semente, tipo):
    return f"{PASTA_PACOTES}/{RODADA.rsplit('/', 1)[1]}/modelo_seed{semente}/{tipo}.tar.xz"


def _criar(args):
    repo, (semente, tipo), caminhos, inv = args
    tar, bytes_membros = tar_deterministico(repo, caminhos, inv)
    xz = lzma.compress(tar, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, preset=PRESET_XZ)
    rel = caminho_pacote(semente, tipo)
    destino = repo / rel
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("xb") as f:  # nunca sobrescreve
        f.write(xz)
    return {"caminho": rel, "semente_modelo": semente, "tipo": tipo,
            "prefixo": f"{RODADA}/modelo_seed{semente}/", "membros": len(caminhos),
            "bytes_membros": bytes_membros, "bytes_tar": len(tar),
            "sha256_tar": hashlib.sha256(tar).hexdigest(), "bytes": len(xz),
            "sha256": hashlib.sha256(xz).hexdigest()}


def _refazer(args):
    repo, (semente, tipo), caminhos, inv = args
    tar, _ = tar_deterministico(repo, caminhos, inv)
    return caminho_pacote(semente, tipo), hashlib.sha256(tar).hexdigest(), len(caminhos)


def empacotar(repo=REPO, processos=4):
    repo = Path(repo).resolve()
    if (repo / MANIFESTO).exists():
        raise SystemExit(f"Manifesto ja existe; nada foi alterado: {MANIFESTO}")
    meta, inv = ler_inventario(repo)
    grupos = selecionar(inv)
    tarefas = [(repo, k, v, {c: inv[c] for c in v}) for k, v in grupos.items()]
    with Pool(processos) as pool:
        pacotes = pool.map(_criar, tarefas)
    man = {
        "formato": FORMATO,
        "criado_utc": datetime.now(timezone.utc).isoformat(),
        "descricao": "Registros detalhados da rodada principal MARL Cologne8, sem perda; "
                     "restaurar com semaforo/scripts/restaurar_registros_cologne8.py",
        "rodada": RODADA,
        "inventario": {"caminho": meta["caminho"], "sha256": meta["sha256"]},
        "regras_relativas_a_rodada": list(REGRAS),
        "tar": "PAX, ordem alfabetica, mtime 0, modo 0644, dono 0",
        "compressao": "xz, preset 9e, CRC64",
        "total_pacotes": len(pacotes),
        "total_membros": sum(p["membros"] for p in pacotes),
        "total_bytes_membros": sum(p["bytes_membros"] for p in pacotes),
        "total_bytes_pacotes": sum(p["bytes"] for p in pacotes),
        "pacotes": pacotes,
    }
    with (repo / MANIFESTO).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return man


def conferir(repo=REPO, processos=4):
    """Refaz cada .tar a partir dos originais e compara com o manifesto (reprodutibilidade)."""
    repo = Path(repo).resolve()
    meta, inv = ler_inventario(repo)
    man = ler_json(repo / MANIFESTO)
    assert man["inventario"]["sha256"] == meta["sha256"], "Manifesto de outro inventario"
    esperado = {p["caminho"]: p for p in man["pacotes"]}
    grupos = selecionar(inv)
    with Pool(processos) as pool:
        refeitos = pool.map(_refazer, [(repo, k, v, {c: inv[c] for c in v}) for k, v in grupos.items()])
    assert sorted(c for c, _, _ in refeitos) == sorted(esperado), "Conjunto de pacotes mudou"
    for c, h, n in refeitos:
        p = esperado[c]
        assert h == p["sha256_tar"] and n == p["membros"], f"Pacote nao reproduz os originais: {c}"
        assert sha_arquivo(repo / c) == p["sha256"], f"Pacote alterado: {c}"
    return {"pacotes": len(refeitos), "arquivos": sum(n for _, _, n in refeitos), "reproduzidos": True}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", type=Path, default=REPO)
    ap.add_argument("--conferir", action="store_true",
                    help="refaz os .tar a partir dos originais e compara com o manifesto")
    ap.add_argument("--processos", type=int, default=4)
    args = ap.parse_args(argv)
    if args.conferir:
        r = conferir(args.repo, args.processos)
    else:
        man = empacotar(args.repo, args.processos)
        r = {k: man[k] for k in ("total_pacotes", "total_membros", "total_bytes_membros",
                                 "total_bytes_pacotes")}
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
