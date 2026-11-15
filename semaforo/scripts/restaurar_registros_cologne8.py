"""Restaura os registros detalhados do MARL Cologne8 a partir dos pacotes .tar.xz.

Usa apenas a biblioteca padrao. Nao importa torch, nao inicia SUMO e nao altera
pacotes, inventario ou arquivos ja existentes.

Garantias:
- confere o inventario pelo hash em indice_execucoes_cologne8.json;
- confere o SHA-256 de cada pacote (.tar.xz) e do .tar descomprimido contra o manifesto;
- cada arquivo restaurado precisa constar do inventario, com mesmo tamanho e SHA-256;
- recusa caminhos absolutos, '..', barras invertidas, links e qualquer destino fora de --destino;
- nunca sobrescreve: arquivo existente identico e mantido; diferente interrompe tudo;
- verifica tudo antes de escrever o primeiro arquivo (duas passagens).

Uso, na raiz do repositorio:
  python semaforo/scripts/restaurar_registros_cologne8.py                 # restaura no proprio repositorio
  python semaforo/scripts/restaurar_registros_cologne8.py --verificar     # so confere, nao escreve
  python semaforo/scripts/restaurar_registros_cologne8.py --destino DIR   # restaura em outra pasta
"""

import argparse
import hashlib
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile

INDICE = "semaforo/resultados/indice_execucoes_cologne8.json"
PASTA_PACOTES = "semaforo/resultados/pacotes_registros_cologne8"
MANIFESTO = PASTA_PACOTES + "/manifesto_pacotes.json"
FORMATO = "pacotes_registros_cologne8_v1"
PREFIXO_MARL = "semaforo/resultados/marl_cologne8/"
REPO = Path(__file__).resolve().parents[2]


class ErroRestauracao(Exception):
    pass


def sha_arquivo(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def ler_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ler_inventario(repo):
    """Inventario do pacote Cologne8, conferido pelo hash registrado no indice."""
    meta = ler_json(repo / INDICE)["inventario"]
    caminho = repo / meta["caminho"]
    if sha_arquivo(caminho) != meta["sha256"]:
        raise ErroRestauracao(f"Inventario divergente do indice: {meta['caminho']}")
    inv = {}
    with caminho.open(encoding="utf-8") as f:
        for linha in f:
            a = json.loads(linha)
            inv[a["caminho"]] = a
    return meta, inv


class LeitorComHash:
    """Arquivo somente leitura que calcula o SHA-256 do que passa por ele."""

    def __init__(self, f):
        self.f, self.h, self.n = f, hashlib.sha256(), 0

    def read(self, n=-1):
        b = self.f.read(n)
        self.h.update(b)
        self.n += len(b)
        return b

    def esgotar(self):
        while self.read(1024 * 1024):
            pass
        return self.h.hexdigest(), self.n


def nome_seguro(nome, prefixo):
    """Rejeita qualquer nome que possa sair da arvore prevista."""
    if not isinstance(nome, str) or not nome or "\\" in nome or "\x00" in nome:
        raise ErroRestauracao(f"Nome invalido no pacote: {nome!r}")
    if nome.startswith("/") or re.match(r"^[A-Za-z]:", nome) or ":" in nome:
        raise ErroRestauracao(f"Caminho absoluto ou com unidade no pacote: {nome!r}")
    partes = PurePosixPath(nome).parts
    if any(p in ("", ".", "..") for p in partes) or "/".join(partes) != nome:
        raise ErroRestauracao(f"Caminho nao normalizado no pacote: {nome!r}")
    if not nome.startswith(prefixo):
        raise ErroRestauracao(f"Arquivo fora do prefixo do pacote: {nome!r}")
    return nome


def alvo_dentro(destino, nome):
    alvo = (destino / nome).resolve()
    if not alvo.is_relative_to(destino):
        raise ErroRestauracao(f"Destino fora da pasta prevista: {nome}")
    return alvo


def percorrer(repo, pacote, inv, destino, escrever, estados):
    """Le um pacote membro a membro. Sem escrever, classifica cada destino;
    escrevendo, cria somente os marcados como ausentes na primeira passagem."""
    rel = pacote["caminho"]
    if not rel.startswith(PASTA_PACOTES + "/") or not rel.endswith(".tar.xz"):
        raise ErroRestauracao(f"Pacote fora da pasta de pacotes: {rel}")
    if not pacote["prefixo"].startswith(PREFIXO_MARL) or not pacote["prefixo"].endswith("/"):
        raise ErroRestauracao(f"Prefixo de pacote invalido: {pacote['prefixo']}")
    arq = (repo / rel).resolve()
    if not arq.is_relative_to((repo / PASTA_PACOTES).resolve()) or not arq.is_file():
        raise ErroRestauracao(f"Pacote ausente: {rel}")
    if arq.stat().st_size != pacote["bytes"] or sha_arquivo(arq) != pacote["sha256"]:
        raise ErroRestauracao(f"Pacote divergente do manifesto: {rel}")
    vistos = set()
    total = 0
    with lzma.open(arq, "rb") as xz:
        leitor = LeitorComHash(xz)
        with tarfile.open(fileobj=leitor, mode="r|") as tar:
            for m in tar:
                nome = nome_seguro(m.name, pacote["prefixo"])
                if not m.isreg():
                    raise ErroRestauracao(f"Membro nao e arquivo comum (link/pasta/dispositivo): {nome}")
                if nome in vistos:
                    raise ErroRestauracao(f"Membro repetido: {nome}")
                vistos.add(nome)
                a = inv.get(nome)
                if a is None or a["git_lfs"]:
                    raise ErroRestauracao(f"Membro fora do inventario (ou Git LFS): {nome}")
                if m.size != a["bytes"]:
                    raise ErroRestauracao(f"Tamanho divergente do inventario: {nome}")
                dados = tar.extractfile(m).read()
                if len(dados) != a["bytes"] or hashlib.sha256(dados).hexdigest() != a["sha256"]:
                    raise ErroRestauracao(f"SHA-256 divergente do inventario: {nome}")
                total += len(dados)
                alvo = alvo_dentro(destino, nome)
                if not escrever:
                    if alvo.is_symlink() or (alvo.exists() and not alvo.is_file()):
                        raise ErroRestauracao(f"Destino existe e nao e arquivo comum: {alvo}")
                    if alvo.exists():
                        if sha_arquivo(alvo) != a["sha256"]:
                            raise ErroRestauracao(f"Arquivo existente difere do original; nada foi sobrescrito: {alvo}")
                        estados[nome] = "identico"
                    else:
                        estados[nome] = "ausente"
                elif estados.get(nome) == "ausente":
                    alvo.parent.mkdir(parents=True, exist_ok=True)
                    if not alvo.parent.resolve().is_relative_to(destino):
                        raise ErroRestauracao(f"Pasta de destino fora da pasta prevista: {alvo.parent}")
                    criado = False
                    try:
                        with alvo.open("xb") as f:  # 'x': falha se o arquivo ja existir
                            criado = True
                            f.write(dados)
                    except BaseException:
                        if criado:
                            alvo.unlink(missing_ok=True)
                        raise
                    estados[nome] = "restaurado"
        sha_tar, bytes_tar = leitor.esgotar()
    if sha_tar != pacote["sha256_tar"] or bytes_tar != pacote["bytes_tar"]:
        raise ErroRestauracao(f"Conteudo descomprimido divergente do manifesto: {rel}")
    if len(vistos) != pacote["membros"] or total != pacote["bytes_membros"]:
        raise ErroRestauracao(f"Quantidade de membros divergente do manifesto: {rel}")
    return vistos


def restaurar(repo=REPO, destino=None, verificar=False, filtro=None, saida=sys.stderr):
    repo = Path(repo).resolve()
    destino = Path(destino).resolve() if destino else repo
    meta, inv = ler_inventario(repo)
    man = ler_json(repo / MANIFESTO)
    if man.get("formato") != FORMATO:
        raise ErroRestauracao(f"Formato de manifesto desconhecido: {man.get('formato')}")
    if man["inventario"]["sha256"] != meta["sha256"]:
        raise ErroRestauracao("Manifesto gerado para outro inventario")
    pacotes = [p for p in man["pacotes"] if not filtro or filtro in p["caminho"]]
    if not pacotes:
        raise ErroRestauracao("Nenhum pacote selecionado")
    estados, todos = {}, set()
    for i, p in enumerate(pacotes, 1):  # 1a passagem: confere tudo, nao escreve
        membros = percorrer(repo, p, inv, destino, False, estados)
        if membros & todos:
            raise ErroRestauracao(f"Membros repetidos entre pacotes: {p['caminho']}")
        todos |= membros
        print(f"[conferido {i}/{len(pacotes)}] {p['caminho']} ({len(membros)} arquivos)", file=saida, flush=True)
    if not filtro and len(todos) != man["total_membros"]:
        raise ErroRestauracao("Total de arquivos diferente do manifesto")
    ausentes = sum(v == "ausente" for v in estados.values())
    if not verificar and ausentes:
        for i, p in enumerate(pacotes, 1):  # 2a passagem: escreve so o que falta
            percorrer(repo, p, inv, destino, True, estados)
            print(f"[restaurado {i}/{len(pacotes)}] {p['caminho']}", file=saida, flush=True)
    contagem = {k: sum(v == k for v in estados.values()) for k in ("restaurado", "identico", "ausente")}
    return {"pacotes": len(pacotes), "arquivos": len(todos), "destino": str(destino),
            "verificar_apenas": verificar, "restaurados": contagem["restaurado"],
            "ja_presentes_identicos": contagem["identico"],
            "ausentes_nao_escritos": contagem["ausente"] if verificar else 0}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", type=Path, default=REPO, help="raiz do repositorio (pacotes, manifesto e inventario)")
    ap.add_argument("--destino", type=Path, help="pasta onde restaurar (padrao: a raiz do repositorio)")
    ap.add_argument("--verificar", action="store_true", help="so confere pacotes e destino; nao escreve")
    ap.add_argument("--pacote", help="restaura so pacotes cujo caminho contem este texto")
    args = ap.parse_args(argv)
    try:
        r = restaurar(args.repo, args.destino, args.verificar, args.pacote)
    except (ErroRestauracao, OSError, tarfile.TarError, lzma.LZMAError) as e:
        print(f"FALHA: {e}", file=sys.stderr)
        return 1
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
