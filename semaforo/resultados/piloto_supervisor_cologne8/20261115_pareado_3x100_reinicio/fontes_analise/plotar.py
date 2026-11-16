import os,json,statistics
from pathlib import Path
os.environ['MPLCONFIGDIR']=str(Path('tmp/piloto_supervisor_cologne8/matplotlib').resolve())
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path('semaforo/resultados/piloto_supervisor_cologne8/20261115_pareado_3x100_reinicio')
data=json.loads((root/'ANALISE.json').read_text(encoding='utf-8'))
assert (root/'TUDO_CONCLUIDO.json').exists()
target=root/'comparacao_piloto.png'
assert not target.exists()
colors={'com_supervisor':'#166da6','sem_supervisor':'#d66b19','max_pressure':'#626262','original_fixo':'#8760a3'}
labels={'com_supervisor':'Com supervisor','sem_supervisor':'Sem supervisor','max_pressure':'Max-Pressure','original_fixo':'Original'}
fig,axs=plt.subplots(2,2,figsize=(11.5,8),layout='constrained')
for variant in ('com_supervisor','sem_supervisor'):
    curves=[]
    for seed in range(3):
        d=json.loads((root/f'{variant}_seed{seed}/resumo.json').read_text())
        vals=d['validacoes'];xs=[v['episodio'] for v in vals]
        ys=[[statistics.mean(v['metricas'][i][key] for i in range(3)) for v in vals] for key in ('espera','colisoes')]
        curves.append(ys)
        for j in range(2):
            axs[0,j].plot(xs,ys[j],color=colors[variant],alpha=.3,linewidth=1)
            idx=xs.index(d['melhor_ep'])
            axs[0,j].scatter([xs[idx]],[ys[j][idx]],color=colors[variant],s=22,zorder=4)
    for j in range(2):
        avg=[statistics.mean(curve[j][k] for curve in curves) for k in range(4)]
        axs[0,j].plot(xs,avg,color=colors[variant],linewidth=2.5,label=labels[variant])
axs[0,0].set_title('Validação: espera média');axs[0,0].set_ylabel('Segundos por viagem')
axs[0,1].set_title('Validação: contatos por simulação');axs[0,1].set_ylabel('Eventos')
for ax in axs[0]:
    ax.set_xlabel('Episódio');ax.set_xticks([25,50,75,100]);ax.grid(axis='y',alpha=.18)
axs[0,0].legend(frameon=False,fontsize=9)
groups=['com_supervisor','sem_supervisor','max_pressure','original_fixo']
for j,key in enumerate(('espera','colisoes')):
    ax=axs[1,j];values=[data['medias'][v][key] for v in groups]
    ax.bar(range(4),values,color=[colors[v] for v in groups],width=.65)
    for i,v in enumerate(values):ax.text(i,v+.015*max(values),f'{v:.2f}',ha='center',fontsize=9)
    ax.set_xticks(range(4),[labels[v].replace(' ','\n',1) for v in groups],fontsize=9)
    ax.set_ylim(0,max(values)*1.18);ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
axs[1,0].set_title('Teste reservado: espera média');axs[1,0].set_ylabel('Segundos por viagem')
axs[1,1].set_title('Teste reservado: contatos por simulação');axs[1,1].set_ylabel('Eventos')
fig.suptitle('Cologne8 — piloto pareado com e sem supervisor\n3 inicializações · 4 demandas reservadas · colisões não terminais',fontsize=13)
fig.savefig(target,dpi=160)
plt.close(fig)
with (root/'fontes_analise/plotar.py').open('xb') as f:f.write(Path(__file__).read_bytes())
print(target)
