"""Funcoes comuns da integracao do cenario Insper (OpenStreetMap) com TraCI.

Nao altera o Cologne8 nem os arquivos originais de semaforo/cenarios/insper:
toda saida vai para uma pasta nova em semaforo/integracao_insper/resultados/.
"""

from collections import Counter, defaultdict
import datetime
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

AQUI = Path(__file__).resolve().parent
SEMAFORO = AQUI.parent
CENARIO = SEMAFORO / "cenarios" / "insper"
REDE = CENARIO / "osm.net.xml.gz"
VIAGENS = CENARIO / "osm.passenger.trips.xml"
CONFIG = CENARIO / "osm.sumocfg"
RESULTADOS = AQUI / "resultados"
VERSAO_SUMO = "1.28.0"

# Os tres semaforos escolhidos, na ordem do trafego da Rua Ribeirao Claro
# (mao unica; a ordem e conferida pelo diagnostico, nao presumida).
CONTROLADOS = {
    "476455095": "Rua Gomes de Carvalho x Rua Ribeirao Claro",
    "40278305": "Rua Casa do Ator x Rua Ribeirao Claro",
    "40278183": "Rua Quata x Rua Ribeirao Claro",
}

# Mesmos tempos de seguranca do Cologne8 (ambiente_marl_cologne.construir_manifesto).
TEMPOS = {"verde_minimo": 10, "vermelho_geral": 2, "intervalo_decisao": 5, "verde_maximo": 60}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hashes_cenario():
    return {p.name: sha(p) for p in sorted(CENARIO.iterdir()) if p.is_file()}


def conferir_cenario(antes):
    depois = hashes_cenario()
    if depois != antes:
        mudou = sorted(k for k in set(antes) | set(depois) if antes.get(k) != depois.get(k))
        raise RuntimeError(f"Arquivos originais do cenario Insper mudaram: {mudou}")


def nova_pasta(nome):
    carimbo = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pasta = RESULTADOS / f"{carimbo}_{nome}"
    pasta.mkdir(parents=True, exist_ok=False)
    return pasta


def json_novo(path, dados):
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2, allow_nan=False)


def sumo_home():
    home = os.environ.get("SUMO_HOME")
    if not home:
        raise RuntimeError("Defina SUMO_HOME")
    ferramentas = str(Path(home) / "tools")
    if ferramentas not in sys.path:
        sys.path.append(ferramentas)
    return Path(home)


def comando_sumo(pasta, semente=None, gui=False, limite=None):
    """Usa o osm.sumocfg original, mas redireciona TODAS as saidas para `pasta`.

    output.add.xml fica de fora porque escreveria edgeData.xml na pasta do cenario.
    Colisoes tambem sao checadas dentro dos cruzamentos e apenas registradas (warn).
    """
    binario = sumo_home() / "bin" / ("sumo-gui.exe" if gui else "sumo.exe")
    pasta = Path(pasta)
    cmd = [str(binario), "-c", str(CONFIG),
           "--additional-files", str(CENARIO / "osm.poly.xml.gz"),
           "--tripinfo-output", str(pasta / "tripinfo.xml"),
           "--tripinfo-output.write-unfinished", "true",
           "--statistic-output", str(pasta / "estatisticas_sumo.xml"),
           "--log", str(pasta / "sumo.log"),
           "--verbose", "false", "--no-step-log", "true", "--duration-log.statistics", "true",
           "--collision.action", "warn", "--collision.check-junctions", "true"]
    if semente is not None:
        cmd += ["--seed", str(semente)]
    if limite is not None:
        cmd += ["--end", str(limite)]
    if gui:
        cmd += ["--start", "true", "--quit-on-end", "true"]
    return cmd


def iniciar(cmd, rotulo):
    sumo_home()
    import traci
    traci.start(cmd, label=rotulo)
    conn = traci.getConnection(rotulo)
    versao = conn.getVersion()
    if VERSAO_SUMO not in versao[1]:
        conn.close()
        raise RuntimeError(f"Exigido SUMO {VERSAO_SUMO}, encontrado {versao}")
    return conn


# ---------------------------------------------------------------- rede estatica

def ler_rede_xml():
    with gzip.open(REDE, "rb") as f:
        return ET.parse(f).getroot()


def foes_requisicao(raiz, juncao):
    """Matriz foes do <request> da juncao: foes[i] = conjunto de indices conflitantes."""
    j = next(x for x in raiz.findall("junction") if x.get("id") == juncao)
    foes = {}
    for r in j.findall("request"):
        bits = r.get("foes")[::-1]
        foes[int(r.get("index"))] = {k for k, b in enumerate(bits) if b == "1"}
    return foes


def indice_juncao(via):
    """':J_k_m' -> k + m (indice do link na juncao do SUMO)."""
    _, k, m = via.rsplit("_", 2)
    return int(k) + int(m)


def foes_traci(conn, tls):
    """Conflitos entre links do semaforo pela geometria interna do SUMO (getInternalFoes)."""
    links = conn.trafficlight.getControlledLinks(tls)
    vias = []
    for itens in links:
        if len(itens) != 1:
            raise RuntimeError(f"{tls}: link com {len(itens)} movimentos; revisar antes de controlar")
        vias.append(itens[0][2])
    entradas = [itens[0][0] for itens in links]
    internos = [set(conn.lane.getInternalFoes(v)) for v in vias]
    # getInternalFoes tambem devolve movimentos que saem da MESMA faixa (divergem, nao se cruzam);
    # eles sempre tem a mesma cor e nao sao conflitos de sinal.
    foes = {i: {j for j, vj in enumerate(vias) if j != i and entradas[j] != entradas[i]
                and (vj in internos[i] or vias[i] in internos[j])}
            for i in range(len(vias))}
    return foes, vias, internos


# ---------------------------------------------------------------- monitores dinamicos

class Travessias:
    """Detecta cada veiculo que cruza a linha de retencao de um link semaforizado.

    Um veiculo cruza quando deixa a faixa de entrada do link (fim do passo k-1) e
    aparece no interior do cruzamento ou na via de saida (fim do passo k). A luz
    registrada e a do passo k, isto e, a luz em vigor quando ele cruzou.
    """

    def __init__(self, conn, tls_ids):
        self.por_via, self.por_par = {}, {}
        self.por_saida_edge = defaultdict(list)
        self.entradas = defaultdict(set)
        for t in tls_ids:
            for link, itens in enumerate(conn.trafficlight.getControlledLinks(t)):
                for entrada, saida, via in itens:
                    alvo = (t, link)
                    self.por_via[via] = (entrada, alvo)
                    self.por_par[(entrada, saida)] = alvo
                    self.por_saida_edge[(entrada, saida.rsplit("_", 1)[0])].append(alvo)
                    self.entradas[entrada].add(t)
        self.faixa, self.pendente = {}, {}
        self.registros = []
        self.por_veiculo = defaultdict(list)
        self.problemas = Counter()
        self.nao_mapeadas = []

    def esquecer(self, vid, motivo=None):
        self.faixa.pop(vid, None)
        if self.pendente.pop(vid, None) is not None and motivo:
            self.problemas[motivo] += 1

    def atualizar(self, agora, faixas, estados):
        for vid, faixa in faixas.items():
            anterior = self.faixa.get(vid)
            self.faixa[vid] = faixa
            if anterior is None or anterior == faixa:
                continue
            if (not anterior.startswith(":") and anterior in self.entradas
                    and anterior.rsplit("_", 1)[0] != faixa.rsplit("_", 1)[0]):
                self.pendente[vid] = (anterior, agora, {t: estados[t] for t in self.entradas[anterior]})
            p = self.pendente.get(vid)
            if p is None:
                continue
            entrada, tempo, luzes = p
            alvo, aproximado = None, False
            if faixa.startswith(":"):
                achado = self.por_via.get(faixa)
                if achado is None:
                    continue  # trecho interno seguinte; aguarda a via de saida
                if achado[0] == entrada:
                    alvo = achado[1]
            else:
                alvo = self.por_par.get((entrada, faixa))
                if alvo is None:
                    opcoes = self.por_saida_edge.get((entrada, faixa.rsplit("_", 1)[0]), [])
                    alvo, aproximado = (opcoes[0], True) if opcoes else (None, False)
            del self.pendente[vid]
            if alvo is None:
                self.problemas["travessia_nao_mapeada"] += 1
                if len(self.nao_mapeadas) < 20:
                    self.nao_mapeadas.append({"tempo": agora, "veiculo": vid, "de": entrada, "para": faixa})
                continue
            tls, link = alvo
            luz = luzes[tls][link]
            registro = {"tempo": tempo, "veiculo": vid, "tls": tls, "link": link, "luz": luz,
                        "aproximado": aproximado}
            self.registros.append(registro)
            self.por_veiculo[vid].append((tempo, tls))


class MonitorPrograma:
    """Confere a cada passo que um semaforo segue o programa original carregado."""

    def __init__(self, conn, tls, agora):
        self.conn, self.id = conn, tls
        self.programa = conn.trafficlight.getProgram(tls)
        logica = next(l for l in conn.trafficlight.getAllProgramLogics(tls) if l.programID == self.programa)
        self.tipo = logica.type
        self.fases = [(p.state, p.duration, p.minDur, p.maxDur) for p in logica.phases]
        self.indice = conn.trafficlight.getPhase(tls)
        self.inicio = None  # primeira fase observada ja estava em curso: nao entra nas duracoes
        self.duracoes = defaultdict(list)
        self.trocas = 0
        self.erros = []

    def conferir(self, agora):
        tl = self.conn.trafficlight
        programa, indice, estado = tl.getProgram(self.id), tl.getPhase(self.id), tl.getRedYellowGreenState(self.id)
        if programa != self.programa:
            self.erros.append({"tempo": agora, "erro": "programa_trocado", "programa": programa})
            return
        if estado != self.fases[indice][0]:
            self.erros.append({"tempo": agora, "erro": "estado_fora_do_programa", "estado": estado})
        if indice != self.indice:
            if indice != (self.indice + 1) % len(self.fases):
                self.erros.append({"tempo": agora, "erro": "salto_de_fase", "de": self.indice, "para": indice})
            if self.inicio is not None:
                dur = agora - self.inicio
                state, padrao, minimo, maximo = self.fases[self.indice]
                self.duracoes[self.indice].append(dur)
                if any(c in "Gg" for c in state) and "y" not in state:
                    ok = minimo - 1 <= dur <= maximo + 1
                else:
                    ok = abs(dur - padrao) <= 1
                if not ok:
                    self.erros.append({"tempo": agora, "erro": "duracao_fora_dos_limites",
                                       "fase": self.indice, "duracao": dur})
            self.indice, self.inicio = indice, agora
            self.trocas += 1

    def resumo(self):
        def est(v):
            return {"n": len(v), "min": min(v), "media": round(sum(v) / len(v), 2), "max": max(v)} if v else {"n": 0}
        return {"programa": self.programa, "tipo": self.tipo, "trocas": self.trocas,
                "duracoes_por_fase": {f"{i}:{self.fases[i][0]}": est(v) for i, v in sorted(self.duracoes.items())},
                "erros": len(self.erros), "primeiros_erros": self.erros[:10]}


class VerificadorSeguranca:
    """Verificacao independente dos estados OBSERVADOS de um semaforo.

    Nao usa o estado interno do controlador: le o que o SUMO executou a cada passo.
    Regras, cobradas depois de `inicio`:
      - um link verde nunca passa direto para vermelho (G/g -> y -> r) e amarelo
        nunca volta direto para verde;
      - amarelo dura exatamente `amarelo` passos;
      - um link so abre verde se todos os seus conflitantes estao vermelhos ha
        pelo menos `vermelho_geral` passos (0 no programa original, sem vermelho geral);
      - dois links conflitantes nunca ficam ao mesmo tempo em G/y (g permissivo e aceito);
      - cada verde completo dura pelo menos `verde_minimo` passos.
    """

    def __init__(self, tls, foes, amarelo, vermelho_geral, verde_minimo, inicio):
        self.id, self.foes = tls, foes
        self.amarelo, self.vermelho_geral, self.verde_minimo = amarelo, vermelho_geral, verde_minimo
        self.inicio = inicio
        self.anterior = None
        self.desde, self.vermelho_desde = {}, {}
        self.verde_desde = self.geral_desde = self.amarelo_desde = None
        self.violacoes = []
        self.verdes, self.amarelos, self.vermelhos_gerais = [], [], []

    def _violacao(self, agora, tipo, **extra):
        if agora > self.inicio:
            self.violacoes.append({"tempo": agora, "tls": self.id, "tipo": tipo, **extra})

    def observar(self, agora, estado):
        ant = self.anterior
        mudancas = []
        for link, c in enumerate(estado):
            velho = ant[link] if ant is not None else None
            if velho == c:
                continue
            if velho in ("G", "g") and c == "r":
                self._violacao(agora, "verde_direto_para_vermelho", link=link)
            if velho == "y" and c in "Gg":
                self._violacao(agora, "amarelo_direto_para_verde", link=link)
            if velho == "y" and c == "r" and agora - self.desde[link] != self.amarelo:
                self._violacao(agora, "amarelo_com_duracao_errada", link=link, duracao=agora - self.desde[link])
            mudancas.append((link, velho, c))
            self.desde[link] = agora
            if c == "r":
                self.vermelho_desde[link] = agora
            else:
                self.vermelho_desde.pop(link, None)
        for link, velho, c in mudancas:
            if velho is not None and c in "Gg":
                for f in self.foes[link]:
                    livre = self.vermelho_desde.get(f)
                    if estado[f] != "r" or livre is None or agora - livre < self.vermelho_geral:
                        self._violacao(agora, "verde_sem_vermelho_geral_dos_conflitantes",
                                       link=link, conflitante=f)
        for i, ci in enumerate(estado):
            for j in self.foes[i]:
                if j > i and ci in "Gy" and estado[j] in "Gy":
                    self._violacao(agora, "conflitantes_ativos_juntos", links=[i, j], estado=estado)
        if ant is not None and estado != ant:
            if any(c in "Gg" for c in ant) and self.verde_desde is not None:
                if agora > self.inicio:
                    self.verdes.append(agora - self.verde_desde)
                    if agora - self.verde_desde < self.verde_minimo:
                        self._violacao(agora, "verde_menor_que_minimo", duracao=agora - self.verde_desde,
                                       estado=ant)
                self.verde_desde = None
            if all(c == "r" for c in ant) and self.geral_desde is not None:
                if agora > self.inicio:
                    self.vermelhos_gerais.append(agora - self.geral_desde)
                self.geral_desde = None
            if "y" in ant and "y" not in estado and self.amarelo_desde is not None:
                if agora > self.inicio:
                    self.amarelos.append(agora - self.amarelo_desde)
                self.amarelo_desde = None
        if ant is None or estado != ant:
            if any(c in "Gg" for c in estado):
                self.verde_desde = agora
            if all(c == "r" for c in estado):
                self.geral_desde = agora
            if "y" in estado and (ant is None or "y" not in ant):
                self.amarelo_desde = agora
        self.anterior = estado

    def resumo(self):
        def est(v):
            return {"n": len(v), "min": min(v), "max": max(v), "media": round(sum(v) / len(v), 2)} if v else {"n": 0}
        return {"violacoes": len(self.violacoes), "tipos": dict(Counter(v["tipo"] for v in self.violacoes)),
                "primeiras_violacoes": self.violacoes[:10], "verdes": est(self.verdes),
                "amarelos": est(self.amarelos), "vermelhos_gerais": est(self.vermelhos_gerais)}


class ContadorColisoes:
    """Mesmo criterio do Cologne8: um evento por novo contato de um par de veiculos."""

    def __init__(self):
        self.ativos, self.eventos = set(), []

    def atualizar(self, conn, agora):
        registros = {}
        if conn.simulation.getCollidingVehiclesNumber():
            for c in conn.simulation.getCollisions():
                registros[tuple(sorted((c.collider, c.victim)))] = {
                    "tempo": agora, "veiculos": sorted((c.collider, c.victim)), "tipo": c.type,
                    "faixa": c.lane, "posicao": round(c.pos, 2)}
        novos = [r for k, r in registros.items() if k not in self.ativos]
        self.ativos = set(registros)
        self.eventos.extend(novos)
        return novos


def juncao_da_faixa(faixa):
    return faixa[1:].rsplit("_", 2)[0] if faixa.startswith(":") else None


def ler_tripinfo(path):
    raiz = ET.parse(path).getroot()
    viagens = raiz.findall("tripinfo")
    completas = [v for v in viagens if float(v.get("arrival")) >= 0]

    def media(campo, vs):
        return round(sum(float(v.get(campo)) for v in vs) / len(vs), 3) if vs else None
    return {"registradas": len(viagens), "concluidas": len(completas),
            "nao_concluidas": len(viagens) - len(completas),
            "espera_media_s": media("waitingTime", completas),
            "perda_tempo_media_s": media("timeLoss", completas),
            "duracao_media_s": media("duration", completas),
            "atraso_insercao_medio_s": media("departDelay", viagens)}


def ler_estatisticas(path):
    raiz = ET.parse(path).getroot()
    return {filho.tag: dict(filho.attrib) for filho in raiz if filho.tag in
            ("vehicles", "teleports", "safety", "vehicleTripStatistics")}


def avisos_log(path):
    contagem = Counter()
    exemplos = defaultdict(list)
    for linha in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if linha.startswith(("Warning", "Error")):
            tipo = linha.split(":", 1)[0]
            texto = linha.split(":", 1)[1] if ":" in linha else linha
            chave = tipo + ": " + " ".join(w for w in texto.split() if not any(ch.isdigit() for ch in w))[:90]
            contagem[chave] += 1
            if len(exemplos[chave]) < 2:
                exemplos[chave].append(linha[:220])
    return {"total": sum(contagem.values()), "por_tipo": dict(contagem.most_common()),
            "exemplos": dict(exemplos)}


def distancia(a, b):
    return math.dist(a, b)
