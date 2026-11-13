"""Vigilancia do treino em andamento. Nao escreve nos treinos ou nos pesos.

Registra sinais de vida, integridade, recursos e tendencias; nunca pausa por
colisao, muda hiperparametros ou reinicia treinamento automaticamente.
"""

import argparse
from collections import deque
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import time
import uuid
import zipfile


def utc():
    return datetime.now(timezone.utc).isoformat()


def local():
    try:
        from zoneinfo import ZoneInfo
        zona = ZoneInfo("America/Sao_Paulo")
    except (ImportError, KeyError):
        zona = timezone(timedelta(hours=-3))
    return datetime.now(zona).strftime("%d/%m/%Y %H:%M:%S %z")


def ler(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def append(path, value):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")


def substituir_proprio(path, value):
    """Somente o arquivo de estado desta instancia; historico e append-only."""
    temp = path.with_name(path.name + ".novo")
    with temp.open("w", encoding="utf-8") as f:
        if isinstance(value, str):
            f.write(value)
        else:
            json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
    os.replace(temp, path)


def processo_vivo(pid):
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return None
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, int(pid))
    if not handle:
        return False if ctypes.get_last_error() == 87 else None
    try:
        code = wintypes.DWORD()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
            return None
        return code.value == 259
    finally:
        kernel.CloseHandle(handle)


def ram_livre():
    if os.name != "nt":
        return None
    class Memoria(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (x, ctypes.c_ulonglong) for x in ("total_phys", "avail_phys", "total_page",
                "avail_page", "total_virtual", "avail_virtual", "avail_ext")]
    m = Memoria()
    m.length = ctypes.sizeof(m)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
        return None
    return m.avail_phys / 2**30


class ArquivoIncremental:
    def __init__(self, path):
        self.path, self.offset = path, 0

    def novos(self):
        if not self.path.exists():
            return []
        with self.path.open("rb") as f:
            if f.seek(0, 2) < self.offset:
                raise RuntimeError(f"Arquivo de treino foi truncado: {self.path}")
            f.seek(self.offset)
            raw = f.read()
        fim = raw.rfind(b"\n") + 1
        if not fim:
            return []
        self.offset += fim
        return [json.loads(line) for line in raw[:fim].decode("utf-8").splitlines() if line]


def validar_registro(x, cfg):
    problemas = []
    m = x["metricas"]
    if m["terminado_por_colisao"] or m["fim_sumo"] < 25200 + cfg["duracao"]:
        problemas.append("episodio_fora_do_protocolo")
    valores = x["epsilon"] + x["gradientes"] + x["decisoes_treino"] + m["recompensas"]
    valores += [v for v in x["perda_media_200"] if v is not None]
    if not all(math.isfinite(v) for v in valores):
        problemas.append("valor_nao_finito")
    if len(x["gradientes"]) != 9:
        problemas.append("quantidade_de_atores_incorreta")
    penalidade = -10000 * m["colisoes"]
    if m["penalidade_colisao_por_agente"] != penalidade:
        problemas.append("penalidade_divergente")
    if m["teleportes"]:
        problemas.append("teleporte_inesperado")
    for i, (dec, grad) in enumerate(zip(x["decisoes_treino"], x["gradientes"])):
        aquecimento = cfg["aquecimento_supervisor"] if i == 8 else cfg["aquecimento_local"]
        if dec > aquecimento + 2 and grad == 0:
            problemas.append(f"ator_{i}_sem_gradientes_apos_aquecimento")
    return problemas


def compacto(x):
    m = x["metricas"]
    return {"episodio": x["episodio"], "colisoes": m["colisoes"],
        "espera": m["viagens"]["demanda_janela"]["espera_todos_inclui_censura"]["media"],
        "p95": m["viagens"]["demanda_janela"]["espera_todos_inclui_censura"]["p95"],
        "nao_concluidas": m["viagens_nao_concluidas"], "segundos_reais": m["duracao_real_s"],
        "gradientes": x["gradientes"], "epsilon": x["epsilon"], "perdas": x["perda_media_200"]}


class Monitor:
    def __init__(self, raiz, saida, intervalo=60):
        self.raiz, self.saida, self.intervalo = raiz, saida, intervalo
        self.cfg = ler(raiz / "protocolo.json")
        self.manifesto = ler(raiz / "manifesto.json")
        self.launch = ler(raiz / "processo_coordenador.json")
        self.projeto = Path(self.launch["argumentos"][4]).resolve().parents[1]
        self.eventos = ArquivoIncremental(raiz / "eventos_execucao.jsonl")
        self.historicos = {s: ArquivoIncremental(raiz / f"modelo_seed{s}/historico.jsonl")
                          for s in self.cfg["sementes_modelo"]}
        self.inicios, self.fins, self.ultimos = {}, {}, {}
        self.janelas = {s: deque(maxlen=20) for s in self.historicos}
        self.primeiros = {s: [] for s in self.historicos}
        self.problemas_registros, self.alertas_anteriores = {}, set()
        self.ckpt_conferidos = {}
        self.ckpt_observados = {}
        self.ultima_integridade, self.integridade = 0.0, {}

    def coletar(self):
        for e in self.eventos.novos():
            if e["tipo"] == "INICIADO":
                self.inicios[e["semente"]] = e
            elif e["tipo"] == "FIM_PROCESSO":
                self.fins[e["semente"]] = e
        for seed, arquivo in self.historicos.items():
            for x in arquivo.novos():
                problemas = validar_registro(x, self.cfg)
                if problemas:
                    self.problemas_registros[seed] = problemas
                c = compacto(x)
                anterior = self.ultimos.get(seed)
                if anterior and any(n < a for n, a in zip(c["gradientes"], anterior["gradientes"])):
                    self.problemas_registros[seed] = ["contador_gradiente_retrocedeu"]
                self.ultimos[seed] = c
                self.janelas[seed].append(c)
                if len(self.primeiros[seed]) < 20:
                    self.primeiros[seed].append(c)

    def inspecionar(self):
        self.coletar()
        agora = time.time()
        alertas = []
        def alerta(codigo, texto, seed=None, nivel="critico"):
            alertas.append({"codigo": codigo, "semente": seed, "nivel": nivel, "texto": texto})
        fim = "em_execucao"
        if (self.raiz / "CONCLUIDO.json").exists():
            fim = "concluido_e_verificado"
        elif (self.raiz / "PAUSADO.json").exists():
            fim = "pausado"
        elif (self.raiz / "falha_coordenador.json").exists():
            fim = "erro"
            alerta("falha_coordenador", str(ler(self.raiz / "falha_coordenador.json")))
        vivo = processo_vivo(self.launch["pid_coordenador"])
        if vivo is False and fim == "em_execucao":
            alerta("coordenador_parado", "Processo encerrou sem marcador de conclusao")
        gb = shutil.disk_usage(self.raiz).free / 2**30
        ram = ram_livre()
        if gb < 5:
            alerta("disco_baixo", f"Disco livre: {gb:.2f} GB", nivel="critico" if gb < 1 else "aviso")
        if ram is not None and ram < 1:
            alerta("ram_baixa", f"RAM livre: {ram:.2f} GB", nivel="aviso")
        if agora - self.ultima_integridade >= 1800:
            self.integridade = {p: hashlib.sha256((self.raiz / "fontes_execucao" / p).read_bytes()).hexdigest() == h
                                for p, h in self.cfg["fontes_sha256"].items()}
            self.integridade.update({p: hashlib.sha256((self.projeto / p).read_bytes()).hexdigest() == h
                                     for p, h in self.manifesto["fontes"].items()})
            self.ultima_integridade = agora
        if not all(self.integridade.values()):
            alerta("fonte_alterada", "Copia congelada nao confere com hashes do protocolo")
        modelos = []
        for seed in self.cfg["sementes_modelo"]:
            pasta = self.raiz / f"modelo_seed{seed}"
            x = self.ultimos.get(seed)
            estado = "fila" if seed not in self.inicios else "iniciando"
            if seed in self.fins:
                estado = "concluido" if self.fins[seed]["codigo"] == 0 else "erro"
                if estado == "erro":
                    alerta("worker_falhou", f"Codigo de saida {self.fins[seed]['codigo']}", seed)
            elif seed in self.inicios:
                if processo_vivo(self.inicios[seed]["pid"]) is False:
                    alerta("worker_parado", "Processo ativo da fila nao esta mais em execucao", seed)
                idade = agora - (self.historicos[seed].path.stat().st_mtime if self.historicos[seed].path.exists()
                                 else datetime.fromisoformat(self.inicios[seed]["utc"]).timestamp())
                tempos = [r["segundos_reais"] for r in self.janelas[seed]]
                limite = max(180, 12 * statistics.median(tempos)) if tempos else 300
                if x:
                    estado = "treino" if x["episodio"] < self.cfg["episodios"] else "avaliacao_final"
                if idade > limite:
                    alerta("sem_avanco", f"Sem episodio novo ha {idade:.0f}s (limite de observacao {limite:.0f}s)", seed, "aviso")
            if seed in self.problemas_registros:
                alerta("registro_invalido", ", ".join(self.problemas_registros[seed]), seed)
            for p in pasta.glob("*.pt"):
                s = p.stat()
                assinatura = (s.st_size, s.st_mtime_ns)
                estavel = self.ckpt_observados.get(str(p)) == assinatura
                self.ckpt_observados[str(p)] = assinatura
                if estavel and agora - s.st_mtime > 30 and self.ckpt_conferidos.get(str(p)) != assinatura:
                    try:
                        with zipfile.ZipFile(p) as z:
                            if z.testzip() is not None:
                                raise ValueError("CRC invalido")
                        self.ckpt_conferidos[str(p)] = assinatura
                    except (zipfile.BadZipFile, ValueError, OSError) as e:
                        alerta("checkpoint_invalido", str(p) + ": " + str(e), seed)
            info = {"semente": seed, "estado": estado, "episodio": x["episodio"] if x else 0,
                    "ultimo": x}
            if self.janelas[seed]:
                recentes, iniciais = self.janelas[seed], self.primeiros[seed]
                info["media_colisoes_20_recentes"] = statistics.mean(y["colisoes"] for y in recentes)
                info["media_colisoes_20_iniciais"] = statistics.mean(y["colisoes"] for y in iniciais)
                info["media_espera_20_recentes"] = statistics.mean(y["espera"] for y in recentes)
                info["viagens_nao_concluidas_20_recentes"] = sum(y["nao_concluidas"] for y in recentes)
            modelos.append(info)
        estado = {"utc": utc(), "horario_sao_paulo": local(), "status": fim,
            "episodios_registrados": sum(x["episodio"] for x in modelos),
            "episodios_previstos": len(modelos) * self.cfg["episodios"],
            "coordenador_vivo": vivo, "disco_livre_gb": gb, "ram_livre_gb": ram,
            "fontes_conferem": all(self.integridade.values()), "checkpoints_zip_conferidos": len(self.ckpt_conferidos),
            "alertas": alertas, "modelos": modelos}
        return estado

    def registrar(self, estado):
        append(self.saida / "historico_monitoramento.jsonl", estado)
        atuais = {(x["codigo"], x["semente"]) for x in estado["alertas"]}
        for a in estado["alertas"]:
            if (a["codigo"], a["semente"]) not in self.alertas_anteriores:
                append(self.saida / "alertas.jsonl", {"utc": utc(), **a})
        for codigo, seed in self.alertas_anteriores - atuais:
            append(self.saida / "alertas.jsonl", {"utc": utc(), "codigo": codigo, "semente": seed,
                "nivel": "resolvido", "texto": "Condicao nao observada nesta checagem"})
        self.alertas_anteriores = atuais
        substituir_proprio(self.saida / "estado_atual.json", estado)
        L = ["# Monitoramento do treino MARL", "",
            f"Atualizado: **{estado['horario_sao_paulo']}**. Status: **{estado['status']}**.", "",
            f"Episodios: **{estado['episodios_registrados']}/{estado['episodios_previstos']}**. "
            f"Disco livre: {estado['disco_livre_gb']:.1f} GB. "
            f"RAM livre: {estado['ram_livre_gb']:.1f} GB." if estado['ram_livre_gb'] is not None else "RAM indisponivel.", "",
            "| Semente | Estado | Episodio | Colisoes recentes (media, ate 20) | Espera recente (s) | Nao concluidas recentes (soma) |",
            "|---|---|---:|---:|---:|---:|"]
        for x in estado["modelos"]:
            col = f"{x['media_colisoes_20_recentes']:.2f}" if x["ultimo"] else "-"
            esp = f"{x['media_espera_20_recentes']:.2f}" if x["ultimo"] else "-"
            L.append(f"| {x['semente']} | {x['estado']} | {x['episodio']} | {col} | {esp} | "
                     f"{x.get('viagens_nao_concluidas_20_recentes','-')} |")
        L += ["", "Alertas ativos:", ""]
        L += [f"- {a['nivel']}: seed {a['semente']}: {a['texto']}" for a in estado["alertas"]] or ["- Nenhum."]
        L += ["", "Tendencias de treino sao descritivas; nao substituem validacao/teste. "
              "Monitor checa a execucao automaticamente, sem presenca continua do assistente. "
              "Nao muda pesos, exploracao ou fases e nao encerra por colisao. "
              "Alertas ficam em arquivo; nao sao mensagens automaticas no chat.", ""]
        substituir_proprio(self.saida / "MONITORAMENTO.md", "\n".join(L))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rodada", type=Path)
    ap.add_argument("--intervalo", type=int, default=60)
    ap.add_argument("--uma-vez", action="store_true")
    args = ap.parse_args()
    if args.intervalo < 5:
        ap.error("Intervalo minimo 5 segundos")
    raiz = args.rodada.resolve()
    pasta = raiz / "monitoramento" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:6])
    pasta.mkdir(parents=True, exist_ok=False)
    raw = Path(__file__).read_bytes()
    (pasta / Path(__file__).name).write_bytes(raw)
    with (pasta / "configuracao.json").open("x", encoding="utf-8") as f:
        json.dump({"pid": os.getpid(), "intervalo_s": args.intervalo, "rodada": str(raiz),
            "script_sha256": hashlib.sha256(raw).hexdigest(), "iniciado_utc": utc()}, f, indent=2)
    monitor = Monitor(raiz, pasta, args.intervalo)
    print(f"MONITOR {pasta}", flush=True)
    while True:
        try:
            estado = monitor.inspecionar()
            monitor.registrar(estado)
            print(f"{estado['horario_sao_paulo']} {estado['episodios_registrados']}/{estado['episodios_previstos']} "
                  f"status={estado['status']} alertas={len(estado['alertas'])}", flush=True)
            if estado["status"] != "em_execucao" or args.uma_vez:
                break
        except Exception as e:
            append(pasta / "erros_monitor.jsonl", {"utc": utc(), "tipo": type(e).__name__, "erro": str(e)})
            print(f"ERRO MONITOR: {type(e).__name__}: {e}", flush=True)
            if args.uma_vez:
                raise
        time.sleep(args.intervalo)


if __name__ == "__main__":
    main()
