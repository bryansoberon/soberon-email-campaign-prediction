from experiment.core import *
import os
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.cache/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT=ROOT/'results/figures'
LABELS={'clicks':'Clics únicos','unsubscribes':'Bajas de suscripción'}
COLORS={'full':'#167E82','reference':'#E79F47','history':'#7784A3','product':'#163454'}


def save(fig,name):
    fig.savefig(OUT/(name+'.png'),dpi=240,bbox_inches='tight')
    fig.savefig(OUT/(name+'.svg'),bbox_inches='tight')
    plt.close(fig)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    final=json.loads((ROOT/'results/final_evaluation.json').read_text(encoding='utf-8'))
    prep=json.loads((ROOT/'results/preparation.json').read_text(encoding='utf-8'))
    fig,axes=plt.subplots(1,2,figsize=(11,4.4))
    for ax,(target,res) in zip(axes,final['targets'].items()):
        names=['reference','history','full']; labels=['Referencia','Solo historial','Historial + mensaje']
        values=[res['metrics'][n]['mae_pp'] for n in names]
        bars=ax.bar(labels,values,color=[COLORS[n] for n in names],width=.65)
        ax.bar_label(bars,fmt='%.4f',padding=4,fontsize=10)
        ax.set_title(LABELS[target]);ax.set_ylabel('MAE (puntos porcentuales)');ax.set_ylim(0,max(values)*1.22)
        ax.tick_params(axis='x',labelsize=9)
    fig.suptitle('Evaluación temporal reservada · 2024',fontweight='bold');fig.tight_layout()
    save(fig,'01_error_final')
    monthly=pd.read_csv(ROOT/'results/monthly_test.csv')
    fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True)
    for ax,target in zip(axes,TARGETS):
        for name,label in [('reference','Referencia'),('full','Método ML'),('history','Solo historial')]:
            part=monthly.loc[(monthly.target==target)&(monthly.method==name)]
            ax.plot(part.month,part.mae_pp,'o-',label=label,color=COLORS[name])
        ax.set_title(LABELS[target]);ax.set_ylabel('MAE (pp)');ax.grid(alpha=.15);ax.legend()
    axes[-1].tick_params(axis='x',rotation=45);fig.tight_layout();save(fig,'02_estabilidad_mensual')
    pred=pd.read_parquet(ROOT/'data/processed/test_predictions.parquet')
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for ax,target in zip(axes,TARGETS):
        p=pred['full_'+target]; y=pred['observed_'+target]
        bins=pd.Series(0,index=p.index) if p.nunique()<2 else pd.qcut(p,10,duplicates='drop')
        grouped=pd.DataFrame({'p':p,'y':y,'bin':bins}).groupby('bin',observed=True).mean(numeric_only=True)
        limit=max(grouped.p.max(),grouped.y.max(),.001)*1.08
        ax.plot([0,limit],[0,limit],'--',color='#9AA6AF');ax.plot(grouped.p,grouped.y,'o-',color=COLORS['full'])
        ax.set_title(LABELS[target]);ax.set_xlabel('Predicción media por grupo (%)');ax.set_ylabel('Tasa observada media (%)')
    fig.suptitle('Diagnóstico de sesgo por grupos de predicción · no calibración individual',fontsize=12)
    fig.tight_layout();save(fig,'03_observado_estimado')
    fig,ax=plt.subplots(figsize=(10,5))
    flow_labels=['Archivo de origen','IDs y fechas válidos','ID de campaña no repetido','Sin pruebas A/B u optimización','Envíos positivos','Respuestas válidas','Atributos válidos','Borde final de 72 horas']
    labels=flow_labels if len(prep['flow'])==len(flow_labels) else [r['step'].replace('_',' ') for r in prep['flow']]
    values=[r['rows'] for r in prep['flow']]
    bars=ax.barh(labels[::-1],values[::-1],color='#167E82');ax.bar_label(bars,fmt='%d',padding=5)
    ax.set_xlim(0,max(values)*1.2);ax.set_xlabel('Campañas conservadas');ax.set_title('Flujo de elegibilidad')
    fig.tight_layout();save(fig,'04_flujo_datos')
    fig,ax=plt.subplots(figsize=(12,2.5));ax.axis('off')
    steps=['Campañas\nreales','Historia madura\n72 horas','Validación\n2023','Selección\ncongelada','Test temporal\n2024','Sistema web']
    for i,label in enumerate(steps):
        x=.005+i*.168
        ax.add_patch(FancyBboxPatch((x,.3),.145,.4,boxstyle='round,pad=.005',facecolor='#EEF5F7',edgecolor='#167E82',transform=ax.transAxes))
        ax.text(x+.0725,.5,label,ha='center',va='center',transform=ax.transAxes,fontsize=10)
        if i<5: ax.annotate('',xy=(x+.163,.5),xytext=(x+.15,.5),xycoords='axes fraction',arrowprops={'arrowstyle':'->','color':'#163454'})
    save(fig,'05_metodo')
    dev=json.loads((ROOT/'results/development_summary.json').read_text(encoding='utf-8'))
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,target in zip(axes,TARGETS):
        scores=dev['scores'][target]
        names=sorted(scores,key=scores.get)
        ax.barh(names[::-1],[scores[n] for n in names[::-1]],color=[
            '#167E82' if n.startswith(('lgbm','rf','ridge')) else '#E79F47' for n in names[::-1]])
        ax.set_title(LABELS[target]);ax.set_xlabel('MAE combinado de desarrollo (pp)')
    fig.suptitle('Comparadores y candidatos · ventanas de 2023');fig.tight_layout();save(fig,'06_comparacion_desarrollo')
    resources=pd.DataFrame(dev['rows'])
    resources=resources.loc[resources.fit_seconds.notna()]
    summed=resources.groupby('candidate').fit_seconds.sum().sort_values()
    fig,axes=plt.subplots(1,2,figsize=(12,4.8));ax=axes[0]
    bars=ax.barh(summed.index,summed.values,color='#163454');ax.bar_label(bars,fmt='%.1f s',padding=4)
    ax.set_xlabel('Tiempo de ajuste total (s)\nDos respuestas y tres ventanas')
    ax.set_xlim(0,float(summed.max())*1.2);ax.set_title('Tiempo de desarrollo')
    memory=resources.groupby('candidate').peak_process_rss_mb.max().reindex(summed.index)/1024
    bars=axes[1].barh(memory.index,memory.values,color='#167E82');axes[1].bar_label(bars,fmt='%.2f',padding=4)
    axes[1].set_xlabel('Máximo RSS muestreado del proceso (GiB)\nIncluye datos y otras estructuras; no es memoria incremental')
    axes[1].set_title('Memoria observada');axes[1].set_xlim(0,float(memory.max())*1.2)
    fig.tight_layout();save(fig,'07_recursos_desarrollo')
    fig,ax=plt.subplots(figsize=(11,5));ax.axis('off')
    boxes=[(.05,.62,.24,.22,'CSV de campañas reales\nContrato de 72 horas'),(.38,.62,.24,.22,'Validación y preparación\nCódigo compartido'),
           (.71,.62,.24,.22,'Historial disponible\nCorte anterior al envío'),(.71,.15,.24,.22,'Modelos congelados\nClics y bajas'),
           (.38,.15,.24,.22,'Servicio local\nEstimación y registro'),(.05,.15,.24,.22,'Interfaz y exportación\nConsulta y comparación')]
    for x,y,w,h,label in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.01',facecolor='#EEF5F7',edgecolor='#167E82'))
        ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=11)
    for start,end in [((.3,.73),(.37,.73)),((.63,.73),(.7,.73)),((.83,.61),(.83,.38)),((.7,.26),(.63,.26)),((.37,.26),(.3,.26))]:
        ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'->','color':'#163454','lw':1.5})
    ax.set_title('Arquitectura funcional del sistema local',fontweight='bold',pad=20)
    save(fig,'08_arquitectura_sistema')
    print('Figuras PNG/SVG generadas a partir de resultados ejecutados.')


if __name__=='__main__':main()
