"""Testes curtos do ambiente Multi-Agent Insper (episodios curtos de 900-1500 s, sem treino real).

uso: python -B -X utf8 semaforo/integracao_insper/testar_ambiente_marl_insper.py
"""

from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import insper_comum as ic  # noqa: E402
import ambiente_marl_insper as amb  # noqa: E402
import treinar_marl_insper as tr  # noqa: E402


def checar(cond, msg):
    print(("OK   " if cond else "FALHA") + " " + msg, flush=True)
    if not cond:
        raise SystemExit(1)


def main():
    import torch
    torch.set_num_threads(1)
    antes = ic.hashes_cenario()
    tr.preparar_demandas_treino()
    cfg = tr.cfg_treino(1001)
    pasta = ic.nova_pasta("teste_ambiente_marl")
    m = amb.rodar_episodio(cfg, pasta / "original", 1001, None, "original", monitor_completo=True, limite=1500)
    checar(m["seguranca"]["violacoes"] == 0 and all(v["erros"] == 0 for v in m["outros_semaforos"].values())
           and len(m["outros_semaforos"]) == 11, "original: 11 semaforos nao controlados no programa original")
    for modelo in ("independente", "hierarquico"):
        agentes = amb.criar_agentes(modelo, 7, aquecimento=64)  # replay curto so para exercitar o gradiente
        m = amb.rodar_episodio(cfg, pasta / modelo, 1001, agentes, modelo, treinando=True,
                               monitor_completo=True, limite=1500)
        checar(m["seguranca"]["violacoes"] == 0, f"{modelo}: transicoes seguras (verificador independente)")
        v = m["seguranca"]["verificacao"]
        checar(all(x["amarelos"].get("min") == 3 == x["amarelos"].get("max") and x["vermelhos_gerais"].get("min") == 2
                   and x["verdes"].get("min", 99) >= 10 for x in v.values()), f"{modelo}: amarelo 3 s, vermelho 2 s, verde >= 10 s")
        checar(all(x["erros"] == 0 for x in m["outros_semaforos"].values()) and len(m["outros_semaforos"]) == 11,
               f"{modelo}: os outros 11 semaforos inalterados")
        checar(all(isinstance(r, float) for r in m["recompensas"]) and len(m["recompensas"]) == len(agentes),
               f"{modelo}: recompensas finitas {m['recompensas']}")
        # o supervisor decide a cada 30 s: em 1200 s de controle nao chega aos 64 do aquecimento do replay
        checar(all(a.memoria.n > 0 and (a.gradientes > 0 or a.acoes == 4) for a in agentes),
               f"{modelo}: replay e gradientes {[(a.memoria.n, a.gradientes) for a in agentes]}")
        acoes_ok = all(set(a.memoria.a[:a.memoria.n].tolist()) <= set(range(a.acoes)) for a in agentes)
        dims_ok = all(a.memoria.s.shape[1] == (13 if a.acoes == 2 else 48) for a in agentes)
        checar(acoes_ok and dims_ok, f"{modelo}: acoes validas e observacoes 13/48")
        if modelo == "hierarquico":
            checar(any(k.startswith("supervisor_") for k in m["decisoes"]), "hierarquico: supervisor decidiu")
        with tempfile.TemporaryDirectory() as tmp:
            ck = Path(tmp) / "c.pt"
            tr.salvar(ck, agentes, modelo, 7, 1, completo=True)
            _, novos = tr.carregar(ck, modelo)
            x = agentes[0].memoria.s[0]
            checar(all(torch.equal(a.rede(torch.from_numpy(a.memoria.s[0])), b.rede(torch.from_numpy(a.memoria.s[0])))
                       for a, b in zip(agentes, novos)) and novos[0].memoria.n == agentes[0].memoria.n,
                   f"{modelo}: checkpoint salvo e recarregado com as mesmas saidas")
        print(f"     {modelo}: {m['duracao_real_s']} s para 1500 s simulados; decisoes {m['decisoes']}", flush=True)
    ic.conferir_cenario(antes)
    print("todos os testes passaram; saida em", pasta)


if __name__ == "__main__":
    main()
