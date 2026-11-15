"""Testes do empacotamento/restauracao dos registros MARL Cologne8.

Os testes de seguranca montam um repositorio falso numa pasta temporaria, com
pacotes forjados; nao leem nem escrevem nada do repositorio real. O ultimo
teste confere o manifesto real, se existir, sem escrever.

Uso (de dentro de scripts/):  python testar_registros_cologne8.py
"""

import hashlib
import io
import json
import lzma
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest

import restaurar_registros_cologne8 as rr

PREF = rr.PREFIXO_MARL + "rodada_teste/modelo_seed0/"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def tar_xz(membros):
    """membros: (nome, dados) ou (nome, TarInfo pronto)."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as t:
        for nome, x in membros:
            if isinstance(x, tarfile.TarInfo):
                t.addfile(x)
            else:
                ti = tarfile.TarInfo(nome)
                ti.size = len(x)
                t.addfile(ti, io.BytesIO(x))
    tar = buf.getvalue()
    return tar, lzma.compress(tar)


class RepoFalso:
    def __init__(self, raiz, arquivos, pacotes, lfs=()):
        """arquivos: nome -> bytes (inventario); pacotes: nome do pacote -> membros."""
        self.raiz = Path(raiz)
        inv = "".join(json.dumps({"caminho": n, "bytes": len(d), "sha256": sha(d), "git_lfs": n in lfs}) + "\n"
                      for n, d in arquivos.items()).encode()
        self.escrever("semaforo/resultados/indice_artefatos_cologne8.jsonl", inv)
        self.escrever(rr.INDICE, json.dumps({"inventario": {
            "caminho": "semaforo/resultados/indice_artefatos_cologne8.jsonl", "sha256": sha(inv)}}).encode())
        lista = []
        for nome, membros in pacotes.items():
            tar, xz = tar_xz(membros)
            rel = f"{rr.PASTA_PACOTES}/{nome}.tar.xz"
            self.escrever(rel, xz)
            regulares = [d for _, d in membros if isinstance(d, bytes)]
            lista.append({"caminho": rel, "prefixo": PREF, "membros": len(membros),
                          "bytes_membros": sum(map(len, regulares)), "bytes_tar": len(tar),
                          "sha256_tar": sha(tar), "bytes": len(xz), "sha256": sha(xz)})
        self.manifesto = {"formato": rr.FORMATO, "inventario": {"sha256": sha(inv)},
                          "total_membros": sum(p["membros"] for p in lista), "pacotes": lista}
        self.salvar_manifesto()

    def escrever(self, rel, dados):
        p = self.raiz / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(dados)

    def salvar_manifesto(self):
        (self.raiz / rr.MANIFESTO).write_text(json.dumps(self.manifesto), encoding="utf-8")


class Restauracao(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="rc8t_"))
        self.repo = self.tmp / "repo"
        self.dest = self.tmp / "destino"
        self.dest.mkdir()
        self.a, self.b = PREF + "episodios/ep0001/metricas.json", PREF + "episodios/ep0001/sumo.log"
        self.arqs = {self.a: b'{"eventos_colisao": [1, 2]}', self.b: b"Warning: collision\n"}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def restaurar(self, **kw):
        return rr.restaurar(self.repo, self.dest, saida=io.StringIO(), **kw)

    def arquivos_no_destino(self):
        return [p for p in self.tmp.rglob("*") if p.is_file() and self.repo not in p.parents]

    def recusa(self, pacotes, arquivos=None, trecho=None, **kw):
        RepoFalso(self.repo, arquivos or self.arqs, pacotes, **kw)
        with self.assertRaises(rr.ErroRestauracao) as e:
            self.restaurar()
        if trecho:
            self.assertIn(trecho, str(e.exception))
        self.assertEqual(self.arquivos_no_destino(), [], "nada pode ser escrito quando ha falha")

    def test_restaura_identico_e_segunda_vez_nao_escreve(self):
        RepoFalso(self.repo, self.arqs, {"p": [(self.a, self.arqs[self.a]), (self.b, self.arqs[self.b])]})
        r = self.restaurar()
        self.assertEqual((r["restaurados"], r["ja_presentes_identicos"]), (2, 0))
        for n, d in self.arqs.items():
            self.assertEqual((self.dest / n).read_bytes(), d)
        r = self.restaurar()
        self.assertEqual((r["restaurados"], r["ja_presentes_identicos"]), (0, 2))

    def test_verificar_nao_escreve(self):
        RepoFalso(self.repo, self.arqs, {"p": [(self.a, self.arqs[self.a])]})
        r = self.restaurar(verificar=True)
        self.assertEqual(r["ausentes_nao_escritos"], 1)
        self.assertEqual(self.arquivos_no_destino(), [])

    def test_nao_sobrescreve_arquivo_diferente(self):
        RepoFalso(self.repo, self.arqs, {"p": [(self.b, self.arqs[self.b]), (self.a, self.arqs[self.a])]})
        alvo = self.dest / self.a
        alvo.parent.mkdir(parents=True)
        alvo.write_bytes(b"editado pela usuaria")
        with self.assertRaises(rr.ErroRestauracao):
            self.restaurar()
        self.assertEqual(alvo.read_bytes(), b"editado pela usuaria")
        self.assertFalse((self.dest / self.b).exists(), "conferencia previa: nada escrito antes da falha")

    def test_caminhos_perigosos(self):
        d = self.arqs[self.a]
        for nome in ("../fora.txt", PREF + "../../../../fora.txt", "/etc/fora.txt", "C:/fora.txt",
                     "C:fora.txt", PREF + "a\\..\\..\\fora.txt", PREF + "./x", PREF + "a//b", ""):
            with self.subTest(nome=nome):
                shutil.rmtree(self.repo, ignore_errors=True)
                self.recusa({"p": [(nome, d)]}, arquivos={nome: d, **self.arqs})

    def test_fora_do_prefixo_do_pacote(self):
        outro = rr.PREFIXO_MARL + "outra_rodada/x.json"
        self.recusa({"p": [(outro, b"x")]}, arquivos={outro: b"x"}, trecho="prefixo")

    def test_links_e_pastas(self):
        for tipo in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.DIRTYPE):
            with self.subTest(tipo=tipo):
                shutil.rmtree(self.repo, ignore_errors=True)
                ti = tarfile.TarInfo(self.a)
                ti.type, ti.linkname = tipo, "../../../../../../fora.txt"
                self.recusa({"p": [(self.a, ti)]}, trecho="arquivo comum")

    def test_membro_fora_do_inventario(self):
        self.recusa({"p": [(PREF + "novo.json", b"x")]}, trecho="inventario")

    def test_membro_lfs(self):
        self.recusa({"p": [(self.a, self.arqs[self.a])]}, lfs={self.a}, trecho="inventario")

    def test_conteudo_diferente_do_inventario(self):
        self.recusa({"p": [(self.a, b'{"eventos_colisao": []}')]}, trecho="divergente")

    def test_membro_repetido(self):
        self.recusa({"p": [(self.a, self.arqs[self.a]), (self.a, self.arqs[self.a])]}, trecho="repetido")
        shutil.rmtree(self.repo)
        self.recusa({"p": [(self.a, self.arqs[self.a])], "q": [(self.a, self.arqs[self.a])]}, trecho="repetido")

    def test_pacote_alterado(self):
        rf = RepoFalso(self.repo, self.arqs, {"p": [(self.a, self.arqs[self.a])]})
        p = self.repo / rf.manifesto["pacotes"][0]["caminho"]
        b = bytearray(p.read_bytes()); b[-20] ^= 1
        p.write_bytes(bytes(b))
        with self.assertRaises(rr.ErroRestauracao):
            self.restaurar()
        self.assertEqual(self.arquivos_no_destino(), [])

    def test_pacote_fora_da_pasta(self):
        rf = RepoFalso(self.repo, self.arqs, {"p": [(self.a, self.arqs[self.a])]})
        rf.manifesto["pacotes"][0]["caminho"] = rr.PASTA_PACOTES + "/../../fora.tar.xz"
        rf.salvar_manifesto()
        with self.assertRaises(rr.ErroRestauracao):
            self.restaurar()

    def test_inventario_alterado(self):
        RepoFalso(self.repo, self.arqs, {"p": [(self.a, self.arqs[self.a])]})
        inv = self.repo / "semaforo/resultados/indice_artefatos_cologne8.jsonl"
        inv.write_bytes(inv.read_bytes() + b"\n")
        with self.assertRaises(rr.ErroRestauracao):
            self.restaurar()

    def test_destino_com_link_para_fora(self):
        RepoFalso(self.repo, self.arqs, {"p": [(self.a, self.arqs[self.a])]})
        fora = self.tmp / "fora"
        fora.mkdir()
        try:
            os.symlink(fora, self.dest / "semaforo", target_is_directory=True)
        except OSError:
            if os.name != "nt":
                self.skipTest("sem permissao para criar links simbolicos neste sistema")
            import _winapi  # juncao de pasta: no Windows nao exige administrador
            _winapi.CreateJunction(str(fora), str(self.dest / "semaforo"))
        with self.assertRaises(rr.ErroRestauracao):
            self.restaurar()
        self.assertEqual(list(fora.rglob("*")), [])


class ManifestoReal(unittest.TestCase):
    def test_manifesto_real_confere_sem_escrever(self):
        if not (rr.REPO / rr.MANIFESTO).exists():
            self.skipTest("pacotes ainda nao gerados")
        import empacotar_registros_cologne8 as er
        _, inv = rr.ler_inventario(rr.REPO)
        grupos = er.selecionar(inv)
        man = rr.ler_json(rr.REPO / rr.MANIFESTO)
        self.assertEqual(len(grupos), man["total_pacotes"])
        self.assertEqual(sum(map(len, grupos.values())), man["total_membros"])
        self.assertTrue(all(not inv[c]["git_lfs"] for v in grupos.values() for c in v))


if __name__ == "__main__":
    unittest.main(verbosity=2)
