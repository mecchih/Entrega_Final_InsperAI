"""
Testes da dinamica configuravel do simulador (transicao corrigida e regra
de verde maximo).

Confere que:
  1. com as opcoes desligadas (dinamica=None OU Dinamica() explicita), a
     rodada reproduz EXATAMENTE resultados/avaliacao_final.json;
  2. na transicao corrigida, o SUMO executa, segundo a segundo, 3 s de
     amarelo + 2 s de vermelho geral, e cada verde dura exatamente o
     tempo_no_verde que o controlador viu ao pedir a troca;
  3. na dinamica original o defeito e reproduzido (1 s de vermelho, verde +1 s);
  4. so existem estados permitidos (4 verdes protegidos, seus amarelos e
     tudo vermelho) e as fases verdes nao compartilham nenhum movimento;
  5. a regra de verde maximo: com um controlador que NUNCA troca, ela
     intervem, o verde nunca passa do limite quando ha demanda, cada
     intervencao e registrada, e sem demanda ela nao intervem;
  6. as contagens de veiculos fecham (concluidos + interrompidos = tripinfo;
     sem atendimento <= na rede + aguardando entrada);
  7. modelos .pt, avaliacao_final.json e resultados anteriores intactos.

Uso (de dentro de scripts/):  python testar_dinamica.py [--sementes 1 10]
"""

import argparse
import hashlib
import json
import os
from multiprocessing import Pool

import analisar_comportamento as ac
import gerar_demanda
import simulacao
from controladores import webster
from simulacao import (AMARELO, APROXIMACOES, DINAMICAS, Controlador, Dinamica,
                       VERDE_MINIMO, VERMELHO_GERAL)
from testar_analise import ROTULOS_AVALIACAO

AVALIACAO = os.path.join(simulacao.PASTA, "resultados", "avaliacao_final.json")
PROTEGIDOS = [
    os.path.join(simulacao.PASTA, "modelos", f"{m}.pt")
    for m in ["dqn_fila", "dqn_fila_seed1", "dqn_fila_seed2", "dqn_espera"]
] + [AVALIACAO] + [
    os.path.join(simulacao.PASTA, "resultados", "analise_comportamento", f)
    for f in ["rodadas.json", "resumo.json", "resumo.md"]
] + [
    os.path.join(simulacao.PASTA, "resultados", f)
    for f in ["treino_fila_original.json", "treino_fila_seed1.json",
              "treino_fila_seed2.json", "treino_espera.json", "baselines.json"]
]


def sha(caminho):
    with open(caminho, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class Teimoso(Controlador):
    """Nunca pede troca: o pior caso para a regra de verde maximo."""
    nome = "teimoso"

    def decidir(self, obs):
        return APROXIMACOES.index(obs.aprox_verde)


class Alternador(Controlador):
    """Troca para a proxima aproximacao em toda decisao: maximo de transicoes."""
    nome = "alternador"

    def decidir(self, obs):
        return (APROXIMACOES.index(obs.aprox_verde) + 1) % 4


def rodar_registrado(ctrl, cenario, seed, dinamica, duracao=3600):
    reg = ac.Registro()
    m = simulacao.rodar(ctrl, cenario, gerar_demanda.gerar(cenario), seed=seed,
                        duracao=duracao, instrumentacao=reg, dinamica=dinamica)
    segs = reg.segmentos()
    ac.checar_consistencia(reg, segs, m, dinamica)  # erro se algo nao fecha
    return m, reg, segs


# -------------------------------------------------------------------------
def _reproducao(args):
    cenario, rotulo, seed, rotas = args
    oficial = simulacao.rodar(ac.fabricar(rotulo), cenario, rotas, seed=seed)
    explicito = simulacao.rodar(ac.fabricar(rotulo), cenario, rotas, seed=seed,
                                dinamica=Dinamica())
    return cenario, rotulo, seed, oficial, explicito


def teste_reproducao(sementes, processos):
    print("1. dinamica original reproduz avaliacao_final.json")
    with open(AVALIACAO) as f:
        ref = json.load(f)
    cenarios = list(gerar_demanda.CENARIOS)
    rotas = {c: gerar_demanda.gerar(c) for c in cenarios}
    tarefas = [(c, r, s, rotas[c]) for c in cenarios for r in ROTULOS_AVALIACAO
               for s in sementes]
    falhas = 0
    with Pool(processos) as pool:
        for cen, rot, seed, oficial, explicito in pool.imap_unordered(_reproducao, tarefas):
            esperado = ref[f"{cen}|{ROTULOS_AVALIACAO[rot]}"][seed - 1]
            ok = oficial == esperado and {k: explicito[k] for k in esperado} == esperado
            falhas += not ok
            if not ok:
                print(f"  FALHOU: {cen} {rot} seed {seed}")
    print(f"  {len(tarefas) - falhas}/{len(tarefas)} rodadas identicas "
          f"(dinamica=None e Dinamica() explicita)")
    return falhas


def teste_transicao():
    print("2/3. estados executados pelo SUMO, segundo a segundo")
    falhas = 0
    for nome, din in [("original", DINAMICAS["A"]), ("corrigida", Dinamica(transicao_corrigida=True))]:
        for ctrl, cen in [(Alternador(), "equilibrado"), (ac.fabricar("DQN original"), "saturado")]:
            m, reg, segs = rodar_registrado(ctrl, cen, 3, din, duracao=900)
            internos = segs[:-1]  # o ultimo trecho pode ter sido cortado
            amarelos = {s["dur"] for s in internos if s["tipo"] == "amarelo"}
            vermelhos = {s["dur"] for s in internos if s["tipo"] == "vermelho"}
            trocas = {d["t"]: d for d in reg.decisoes if d["escolha"] != d["verde"]}
            atraso = 0 if din.transicao_corrigida else 1
            # verde executado - tempo_no_verde visto pelo controlador ao trocar
            sobra = set()
            for s in internos:
                if s["tipo"] == "verde" and s["completo"] and not s["inicial"]:
                    d = trocas[s["inicio"] + s["dur"] - atraso]
                    sobra.add(s["dur"] - d["tempo_no_verde"])
            # o amarelo comeca no segundo do pedido (corrigida) ou no seguinte
            inicio_amarelo = {s["inicio"] - t for t in trocas for s in segs
                              if s["tipo"] == "amarelo" and 0 <= s["inicio"] - t <= 1}
            esperado = ({AMARELO}, {VERMELHO_GERAL}, {0}, {0}) if din.transicao_corrigida \
                else ({AMARELO}, {VERMELHO_GERAL - 1}, {1}, {1})
            obtido = (amarelos, vermelhos, sobra, inicio_amarelo)
            ok = obtido == esperado
            falhas += not ok
            print(f"  {nome:9s} {ctrl.nome:12s}: amarelo={sorted(amarelos)} s, "
                  f"vermelho={sorted(vermelhos)} s, verde - contado={sorted(sobra)} s, "
                  f"amarelo comeca +{sorted(inicio_amarelo)} s -> {'ok' if ok else 'FALHOU'}")
    # Webster corrigido: verde executado = exatamente o tempo da formula
    m, reg, segs = rodar_registrado(ac.fabricar("Webster"), "assimetrico", 1,
                                    Dinamica(transicao_corrigida=True), duracao=900)
    tempos = webster("assimetrico")
    verdes = {(APROXIMACOES[s["aprox"]], s["dur"]) for s in segs[:-1]
              if s["tipo"] == "verde" and s["completo"] and not s["inicial"]}
    ok = verdes == {(a, tempos[a]) for a in APROXIMACOES}
    falhas += not ok
    print(f"  Webster corrigido: verdes executados {sorted(verdes)} vs formula {tempos} "
          f"-> {'ok' if ok else 'FALHOU'}")
    return falhas


def teste_estados_permitidos():
    print("4. fases protegidas")
    m, reg, segs = rodar_registrado(Alternador(), "equilibrado", 1,
                                    DINAMICAS["C"], duracao=300)
    verdes = [{i for i, c in enumerate(e) if c in "Gg"} for e in reg.estados_verdes]
    disjuntas = all(not (verdes[i] & verdes[j]) for i in range(4) for j in range(i + 1, 4))
    # cada fase verde libera exatamente as faixas da sua aproximacao
    simulacao.trafego.start(["sumo", "-n", simulacao.REDE, "--no-step-log", "true"])
    links = simulacao.trafego.trafficlight.getControlledLinks(simulacao.SEMAFORO)
    simulacao.trafego.close()
    origem = [{l[0] for l in links[i]} for i in range(len(links))]
    por_fase = [set().union(*(origem[i] for i in v)) for v in verdes]
    certo = all(por_fase[k] == set(simulacao.FAIXAS_ENTRADA[a])
                for k, a in enumerate(APROXIMACOES))
    # todo estado executado e permitido (classificar levanta erro se nao for)
    estados = {ac.Registro.classificar(reg, e)[0] for _, e in reg.estados}
    # nunca verde -> verde direto
    direto = any(a["tipo"] == "verde" and b["tipo"] == "verde" for a, b in zip(segs, segs[1:]))
    ok = disjuntas and certo and not direto and estados <= {"verde", "amarelo", "vermelho"}
    print(f"  fases disjuntas={disjuntas}, cada fase = 1 aproximacao={certo}, "
          f"troca verde->verde direta={direto} -> {'ok' if ok else 'FALHOU'}")
    return 0 if ok else 1


def teste_verde_maximo():
    print("5. regra de verde maximo")
    falhas = 0
    for chave in ["A", "B", "C"]:
        din = DINAMICAS[chave]
        m, reg, segs = rodar_registrado(Teimoso(), "equilibrado", 2, din, duracao=600)
        maior = max(s["dur"] for s in segs if s["tipo"] == "verde")
        n = m["intervencoes_seguranca_hora"] + m["intervencoes_seguranca_escoamento"]
        if din.verde_maximo is None:
            ok = n == 0 and len(reg.intervencoes) == 0 and maior >= 600
        else:
            limite = din.verde_maximo + (0 if din.transicao_corrigida else 1)
            ok = (n > 0 and n == len(reg.intervencoes)
                  and m["verde_max_executado_total"] == limite
                  and maior <= limite
                  and all(i["pedido_controlador"] == i["verde"]
                          and i["escolha_executada"] != i["verde"]
                          and i["tempo_no_verde"] >= din.verde_maximo
                          and i["carros"][i["escolha_executada"]] > 0
                          for i in reg.intervencoes))
        falhas += not ok
        print(f"  {din.nome:40s} teimoso: maior verde {maior} s, intervencoes {n}, "
              f"sem atendimento {m['veiculos_sem_atendimento']} -> {'ok' if ok else 'FALHOU'}")
    # sem demanda em outro lado, a regra nao intervem: rede vazia (rota so ate t=0)
    vazio = os.path.join(simulacao.PASTA, "resultados", f"_tmp_vazio_{os.getpid()}.rou.xml")
    with open(vazio, "w") as f:
        f.write('<routes><vType id="carro"/><route id="r" edges="top0A0 A0bottom0"/>'
                '<vehicle id="v0" type="carro" route="r" depart="0"/></routes>\n')
    try:
        m = simulacao.rodar(Teimoso(), "equilibrado", vazio, seed=1, duracao=300,
                            dinamica=DINAMICAS["C"])
    finally:
        os.remove(vazio)
    ok = m["intervencoes_seguranca_hora"] == 0 and m["verde_max_executado_hora"] == 300
    falhas += not ok
    print(f"  sem demanda em outra aproximacao: intervencoes "
          f"{m['intervencoes_seguranca_hora']}, verde {m['verde_max_executado_hora']} s "
          f"-> {'ok' if ok else 'FALHOU'}")
    return falhas


def teste_contagens():
    print("6. contagem de veiculos")
    falhas = 0
    for chave in ["A", "C"]:
        # teimoso + saturado: muita gente presa, inclusive sem conseguir entrar
        m, reg, segs = rodar_registrado(Teimoso(), "saturado", 1, DINAMICAS[chave], duracao=900)
        ok = (m["veiculos_concluidos"] + m["veiculos_interrompidos"] == m["n_carros"]
              and m["veiculos_interrompidos"] == m["veiculos_na_rede_no_fim"]
              and m["veiculos_sem_atendimento"]
              <= m["veiculos_na_rede_no_fim"] + m["veiculos_aguardando_entrada_no_fim"]
              and sum(1 for v in reg.veiculos if not v["chegou"]) == m["veiculos_interrompidos"])
        falhas += not ok
        print(f"  {DINAMICAS[chave].nome:40s} concluidos {m['veiculos_concluidos']}, "
              f"interrompidos {m['veiculos_interrompidos']}, aguardando entrada "
              f"{m['veiculos_aguardando_entrada_no_fim']} (fora do tripinfo), sem atendimento "
              f"{m['veiculos_sem_atendimento']} -> {'ok' if ok else 'FALHOU'}")
    return falhas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sementes", type=int, nargs="*", default=[1, 10])
    ap.add_argument("--processos", type=int, default=6)
    args = ap.parse_args()

    hashes = {p: sha(p) for p in PROTEGIDOS if os.path.exists(p)}
    falhas = 0
    falhas += teste_transicao()
    falhas += teste_estados_permitidos()
    falhas += teste_verde_maximo()
    falhas += teste_contagens()
    falhas += teste_reproducao(args.sementes, args.processos)

    print("7. arquivos preservados")
    mudou = [os.path.basename(p) for p, h in hashes.items() if sha(p) != h]
    falhas += len(mudou)
    print(f"  {len(hashes)} arquivos conferidos por hash; alterados: {mudou or 'nenhum'}")

    print("\nTUDO OK" if falhas == 0 else f"\n{falhas} FALHAS")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
