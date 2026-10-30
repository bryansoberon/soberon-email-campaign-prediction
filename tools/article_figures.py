"""Article Figures 1--4 from frozen results; original vector plotting functions.
Only font selection and presentation-only layout checks differ from the author source.
Figure 5 is an archived interface screenshot, not a statistical plot.
"""
from pathlib import Path
import argparse, hashlib, json, os, warnings
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--study',type=Path,required=True)
parser.add_argument('--font',choices=['auto','Arial','Liberation Sans','DejaVu Sans'],default='auto',help='Override font selection for a portability check; auto prefers Arial, Liberation Sans, then DejaVu Sans.')
args=parser.parse_args()
ROOT=args.study.resolve()
OUT=ROOT/'review_outputs/article_figures'
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.cache/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch,Rectangle,Ellipse,Arc,Circle
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
BLUE='#173f67';TEAL='#167d8d';GREEN='#246746';AMBER='#ad641c';INK='#203244';GRAY='#667482'
FONT_PREFERENCES=['Arial','Liberation Sans','DejaVu Sans']
available=[]
for family in FONT_PREFERENCES:
    try:
        font_manager.findfont(font_manager.FontProperties(family=[family]),fallback_to_default=False)
        available.append(family)
    except ValueError:
        pass
FONT_USED=available[0] if args.font=='auto' else args.font
if FONT_USED not in available:
    raise SystemExit('Requested font is unavailable: '+FONT_USED)
FONT_FAMILIES=[FONT_USED]+[family for family in available if family!=FONT_USED]
STRICT_LAYOUT=FONT_USED=='Arial'
plt.rcParams.update({'font.family':FONT_FAMILIES,'font.size':12,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'white','pdf.fonttype':42})
CHECKS=[];FIGURES={};TEXT_BOUNDS=[];LAYOUT_WARNINGS=[]
if not STRICT_LAYOUT:
    warnings.warn('Using '+FONT_USED+' instead of Arial. Figure appearance may differ; presentation-only margin differences are warnings.',RuntimeWarning)

def layout_issue(detail):
    if STRICT_LAYOUT:
        raise AssertionError(detail)
    message=str(detail)
    LAYOUT_WARNINGS.append(message)
    warnings.warn('Figure layout with '+FONT_USED+': '+message,RuntimeWarning)


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def label(es,en,lang):return en if lang=='en' else es

def save(fig,name,lang):
    fig.canvas.draw()
    renderer=fig.canvas.get_renderer()
    from matplotlib.text import Text
    hidden_ticks=set()
    for ax in fig.axes:
        for axis,limits in [(ax.xaxis,ax.get_xlim()),(ax.yaxis,ax.get_ylim())]:
            for tick in axis.get_major_ticks()+axis.get_minor_ticks():
                if not min(limits)-1e-12<=tick.get_loc()<=max(limits)+1e-12:
                    hidden_ticks.update([id(tick.label1),id(tick.label2)])
    for text in fig.findobj(Text):
        if not text.get_visible() or not text.get_text() or id(text) in hidden_ticks:continue
        actual=text.get_window_extent(renderer)
        if actual.x0<-.8 or actual.y0<-.8 or actual.x1>fig.bbox.x1+.8 or actual.y1>fig.bbox.y1+.8:
            layout_issue(('Text outside figure',name,lang,text.get_text(),tuple(actual.extents),tuple(fig.bbox.extents)))
    for text,bounds,ax in TEXT_BOUNDS:
        if text.figure is not fig:continue
        actual=text.get_window_extent(renderer).transformed(ax.transData.inverted())
        x0,y0,x1,y1=bounds
        if not (actual.x0>=x0-.025 and actual.x1<=x1+.025 and actual.y0>=y0-.025 and actual.y1<=y1+.025):
            layout_issue((name,lang,text.get_text(),tuple(actual.extents),bounds))
    dest=OUT/lang;dest.mkdir(parents=True,exist_ok=True)
    for ext in ['svg','pdf','png']:
        path=dest/f'{name}.{ext}'
        fig.savefig(path,dpi=450,facecolor='white')
        FIGURES[str(path.relative_to(ROOT)).replace('\\','/')]=sha(path)
    plt.close(fig)

def arrow(ax,start,end,color=GRAY,dashed=False,route=None,lw=1.4):
    if route:
        points=[start]+route+[end]
        for a,b in zip(points[:-2],points[1:-1]):ax.plot([a[0],b[0]],[a[1],b[1]],color=color,lw=lw,ls='--' if dashed else '-')
        start=points[-2]
    ax.add_patch(FancyArrowPatch(start,end,arrowstyle='-|>',mutation_scale=13,color=color,lw=lw,linestyle='--' if dashed else '-',zorder=3))

def icon(ax,kind,x,y,s,color):
    # Small original line icons, drawn with vector primitives.
    if kind=='data':
        ax.add_patch(Rectangle((x-s*.42,y-s*.28),s*.84,s*.56,ec=color,fc='white',lw=1.1))
        for dy in [-.28,0,.28]:ax.add_patch(Ellipse((x,y+s*dy),s*.84,s*.23,ec=color,fc='white',lw=1.1))
    elif kind=='lock':
        ax.add_patch(Arc((x,y+s*.15),s*.56,s*.67,theta1=0,theta2=180,color=color,lw=1.3))
        ax.add_patch(FancyBboxPatch((x-s*.36,y-s*.35),s*.72,s*.50,boxstyle='round,pad=0.01',fc='white',ec=color,lw=1.2))
        ax.add_patch(Circle((x,y-s*.10),s*.055,color=color))
    elif kind=='chart':
        for i,h in enumerate([.32,.62,.88]):ax.add_patch(Rectangle((x-s*.4+i*s*.3,y-s*.4),s*.16,s*h,fc=color,ec=color))
    elif kind=='app':
        ax.add_patch(FancyBboxPatch((x-s*.48,y-s*.34),s*.96,s*.68,boxstyle='round,pad=0.01',fc='white',ec=color,lw=1.2))
        ax.plot([x-s*.45,x+s*.45],[y+s*.16,y+s*.16],color=color,lw=1)
        for dx in [-.32,-.2,-.08]:ax.add_patch(Circle((x+s*dx,y+s*.25),s*.025,color=color))
    elif kind=='tree':
        for px,py in [(x-s*.3,y-s*.28),(x+s*.3,y-s*.28)]:ax.plot([x,px],[y+s*.26,py],color=color,lw=1.1)
        for px,py in [(x,y+s*.26),(x-s*.3,y-s*.28),(x+s*.3,y-s*.28)]:ax.add_patch(Circle((px,py),s*.12,fc='white',ec=color,lw=1.1))
    else:
        ax.add_patch(Rectangle((x-s*.36,y-s*.4),s*.72,s*.8,ec=color,fc='white',lw=1.1))
        for dy in [.2,0,-.2]:ax.plot([x-s*.22,x+s*.22],[y+s*dy,y+s*dy],color=color,lw=1.1)

def box(ax,x,top,w,h,title,lines,color=BLUE,kind='list',font=13.8,titlefont=15):
    bottom=top-h
    ax.add_patch(FancyBboxPatch((x,bottom),w,h,boxstyle='round,pad=0.025,rounding_size=0.065',ec=color,fc='#f6f9fc' if color==BLUE else '#f3f8f4' if color==GREEN else '#fff8ef',lw=1.0,zorder=1))
    ax.add_patch(Rectangle((x+.015,top-.08),w-.03,.06,fc=color,ec='none',zorder=2))
    icon(ax,kind,x+.25,top-.33,.35,color)
    t=ax.text(x+.54,top-.31,title,va='center',ha='left',fontsize=titlefont,weight='bold',color=color)
    TEXT_BOUNDS.append((t,(x+.49,top-.55,x+w-.07,top-.10),ax))
    t=ax.text(x+.16,top-.60,'\n'.join(lines),va='top',fontsize=font,color=INK,linespacing=1.38)
    TEXT_BOUNDS.append((t,(x+.12,bottom+.07,x+w-.07,top-.55),ax))

def article_flow(lang):
    fig,ax=plt.subplots(figsize=(10.2,9.6));fig.subplots_adjust(0,0,1,1);ax.set(xlim=(0,10.2),ylim=(0,9.6));ax.axis('off')
    cols=[.23,5.72];w=4.25
    for x,c,title in [(cols[0],BLUE,label('A. Desarrollo y evaluación temporal','A. Development and temporal evaluation',lang)),(cols[1],GREEN,label('B. Aplicación local del método','B. Local application of the method',lang))]:
        ax.add_patch(FancyBboxPatch((x,9.07),w,.35,boxstyle='round,pad=.025,rounding_size=.05',fc=c,ec=c))
        t=ax.text(x+w/2,9.24,title,ha='center',va='center',color='white',fontsize=14,weight='bold')
        TEXT_BOUNDS.append((t,(x,9.08,x+w,9.42),ax))
    left_es=[
      ('Auditoría de la fuente',['SendGuard900K · 2022–2024','847,458 campañas elegibles','Dos tasas de respuesta a 72 h'],'data'),
      ('Entradas previas al envío',['12 atributos del mensaje + 13 históricos','Solo respuestas anteriores maduras','Corte temporal por empresa'],'list'),
      ('Desarrollo · 2022–2023',['Ridge · Random Forest · LightGBM','6 configuraciones y 6 referencias','3 ventanas de validación · selección por MAE'],'tree'),
      ('Congelación antes de la prueba',['Ajuste final con datos de desarrollo','Modelos y reglas de referencia fijados','Código común de características'],'lock'),
      ('Prueba reservada · 2024',['275,535 campañas · 3,528 empresas','Error pareado e intervalos · MAE mensual','Ablación de atributos · recursos'],'chart')]
    left_en=[
      ('Source audit',['SendGuard900K · 2022–2024','847,458 eligible campaigns','Two 72-h response rates'],'data'),
      ('Pre-send inputs',['12 message attributes + 13 history features','Only earlier mature responses','Company-specific temporal cutoff'],'list'),
      ('Development · 2022–2023',['Ridge · Random Forest · LightGBM','6 configurations and 6 baselines','3 validation windows · MAE selection'],'tree'),
      ('Freeze before testing',['Final fit using development data','Frozen models and baseline rules','Shared feature-construction code'],'lock'),
      ('Reserved test · 2024',['275,535 campaigns · 3,528 companies','Paired intervals · monthly MAE','Message ablation · resources'],'chart')]
    right_es=[
      ('Registros de entrada compatibles',['Historial de empresa y campaña consultada','Validación de campos y fechas','Propiedades previas al envío'],'data'),
      ('Construcción común de variables',['Las mismas 25 definiciones de entrada','Actualización solo con historia madura','Se excluyen las respuestas actuales'],'list'),
      ('Disponibilidad de historial',['≥5 campañas maduras: modelo fijado','<5 campañas maduras: mediana global','Referencia calculada en el entrenamiento'],'tree'),
      ('Tasas estimadas y registro',['Clics únicos y bajas de suscripción (%)','Guardar estimación, versión y advertencias','Consulta con parámetros fijos'],'app'),
      ('Contraste y verificación',['Vincular respuestas posteriores maduras','Diez pruebas de integración registradas','Aplicación local y reproducción histórica'],'chart')]
    right_en=[
      ('Compatible input records',['Company history and queried campaign','Validate fields and timestamps','Use pre-send message properties'],'data'),
      ('Shared feature construction',['The same 25 input definitions','Update only mature history','Current outcomes are excluded'],'list'),
      ('History availability',['≥5 mature campaigns: frozen model','<5 mature campaigns: global median','Fallback median fixed from training data'],'tree'),
      ('Rate estimates and records',['Unique clicks and unsubscribes (%)','Store estimate, version and warnings','Queries use fixed model parameters'],'app'),
      ('Comparison and verification',['Match later mature observations','Ten recorded integration tests','Local application and historical replay'],'chart')]
    top=[8.85,7.23,5.61,3.99,2.37];h=1.43
    for side,rows in enumerate([left_en if lang=='en' else left_es,right_en if lang=='en' else right_es]):
        x=cols[side]
        for i,(title,lines,kind) in enumerate(rows):
            c=AMBER if side==0 and i==4 else BLUE if side==0 else GREEN
            box(ax,x,top[i],w,h,title,lines,c,kind,font=13.2,titlefont=14.8)
            if i<4:arrow(ax,(x+w/2,top[i]-h-.025),(x+w/2,top[i+1]+.025),c)
    y=top[1]-.75
    arrow(ax,(cols[0]+w+.03,y),(cols[1]-.035,y),TEAL,True)
    ax.text(5.10,y+.18,label('Misma\nfunción','Same\nfunction',lang),ha='center',va='bottom',fontsize=11.7,color=TEAL,linespacing=1.12)
    y0=top[3]-.88;y1=top[2]-.74
    arrow(ax,(cols[0]+w+.025,y0),(cols[1]-.035,y1),BLUE,True,[(5.10,y0),(5.10,y1)])
    ax.text(5.10,(y0+y1)/2,label('Modelos fijados','Frozen models',lang),ha='center',va='center',rotation=90,fontsize=11.7,color=BLUE,bbox={'facecolor':'white','edgecolor':'none','pad':2})
    ax.text(5.10,.56,label('Regla del historial: envío anterior + 72 h < instante de predicción.','History gate: earlier sending time + 72 h < prediction instant.',lang),ha='center',va='center',fontsize=13,color=INK,weight='bold')
    ax.text(5.10,.24,label('Parámetros fijos en prueba e inferencia · Historial actualizado solo con respuestas maduras','Fixed parameters in testing and inference · History updated only with mature outcomes',lang),ha='center',va='center',fontsize=12.2,color=GRAY)
    save(fig,'01_flujo_articulo',lang)

def paired(lang,final):
    fig,axes=plt.subplots(1,2,figsize=(8.8,4.5));fig.subplots_adjust(left=.25,right=.97,bottom=.24,top=.76,wspace=.40)
    names=[label('Principal · 4 semanas','Main · 4 weeks',lang),label('Sensibilidad · 2 semanas','Sensitivity · 2 weeks',lang),label('Sensibilidad · 8 semanas','Sensitivity · 8 weeks',lang)]
    payload=[]
    for index,(ax,target,title) in enumerate(zip(axes,['clicks','unsubscribes'],[label('(a) Clics únicos','(a) Unique clicks',lang),label('(b) Bajas de suscripción','(b) Unsubscribes',lang)])):
        result=final['targets'][target];rows=[result['comparison']]+result['block_sensitivity']
        lo=min(r['lower_pp'] for r in rows);right=abs(lo)*.075;left=lo*1.1
        ax.axvspan(left,0,color='#f0f6f5',zorder=0);ax.axvline(0,color=GRAY,lw=1.1,ls='--')
        for y,r in zip([2,1,0],rows):
            c=BLUE if y==2 else TEAL
            estimate=r['difference_mae_pp'];err=np.array([[estimate-r['lower_pp']],[r['upper_pp']-estimate]])
            ax.errorbar(estimate,y,xerr=err,fmt='D' if y==2 else 'o',color=c,markersize=6.5,capsize=4,lw=2 if y==2 else 1.5,zorder=3)
            payload.append({'target':target,'block_weeks':r['block_weeks'],'difference_mae_pp':estimate,'lower_pp':r['lower_pp'],'upper_pp':r['upper_pp'],'ci_level':r['ci_level'],'repeats':r['repeats']})
        ax.set(xlim=(left,right),ylim=(-.55,2.55),yticks=[2,1,0])
        ax.set_yticklabels(names if index==0 else ['','',''],fontsize=11)
        ax.set_title(title,fontsize=13.3,weight='bold',loc='left',pad=43,color=INK)
        main=result['comparison']
        annotation='Δ MAE = '+f"{main['difference_mae_pp']:.6f}"+'\n'+label('IC','CI',lang)+f" [{main['lower_pp']:.6f}, {main['upper_pp']:.6f}]"
        ax.text(0,1.04,annotation,transform=ax.transAxes,fontsize=10.5,color=BLUE,linespacing=1.35)
        ax.grid(axis='x',alpha=.15)
        ax.set_xlabel(label('Diferencia de MAE (pp)','MAE difference (pp)',lang),fontsize=12)
        ax.tick_params(axis='y',length=0);ax.spines['left'].set_visible(False)
        ax.xaxis.set_major_locator(plt.MaxNLocator(4));ax.tick_params(axis='x',labelsize=10.6)
    fig.text(.5,.95,label('Comparación pareada frente a la referencia','Paired comparison against the baseline',lang),ha='center',fontsize=15,weight='bold',color=BLUE)
    fig.text(.5,.08,label('IC nominales del 97.5% · Valores negativos: menor MAE del método','Nominal 97.5% intervals · Negative values: lower model MAE',lang),ha='center',fontsize=11.6,color=INK)
    fig.text(.5,.025,label('Escalas independientes · 4 semanas: 2,000 réplicas; 2 y 8 semanas: 1,000 réplicas','Independent scales · 4 weeks: 2,000 replicates; 2 and 8 weeks: 1,000 replicates',lang),ha='center',fontsize=10.7,color=GRAY)
    (OUT/lang/'02_comparacion_pareada_datos.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    save(fig,'02_comparacion_pareada',lang)

def monthly(lang,frame):
    fig,axes=plt.subplots(2,1,figsize=(8,5.5),sharex=True);fig.subplots_adjust(left=.14,right=.97,bottom=.13,top=.86,hspace=.28)
    for ax,target,title in zip(axes,['clicks','unsubscribes'],[label('(a) Clics únicos','(a) Unique clicks',lang),label('(b) Bajas de suscripción','(b) Unsubscribes',lang)]):
        for method,name,color,marker in [('full',label('Modelo seleccionado','Selected model',lang),BLUE,'o'),('reference',label('Referencia seleccionada','Selected baseline',lang),AMBER,'s')]:
            g=frame[(frame.target==target)&(frame.method==method)]
            assert len(g)==12
            ax.plot(range(1,13),g.mae_pp,marker=marker,markersize=4.8,lw=1.8,color=color,label=name)
        ax.set_title(title,loc='left',fontsize=13.5,weight='bold',color=INK)
        ax.set_ylabel('MAE (pp)',fontsize=12);ax.grid(axis='y',alpha=.18);ax.tick_params(labelsize=11)
    handles,names=axes[0].get_legend_handles_labels();fig.legend(handles,names,loc='upper center',bbox_to_anchor=(.55,.98),ncol=2,frameon=False,fontsize=12)
    ticks=['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'] if lang=='es' else ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    axes[-1].set_xticks(range(1,13),ticks);axes[-1].set_xlabel(label('Mes de 2024 · diciembre hasta el día 28','Month in 2024 · December through day 28',lang),fontsize=12,labelpad=9)
    save(fig,'03_estabilidad_mensual',lang)

def grouped(lang,frame):
    fig,axes=plt.subplots(1,2,figsize=(8.4,4.2));fig.subplots_adjust(left=.10,right=.98,bottom=.21,top=.82,wspace=.34)
    for ax,target,title in zip(axes,['clicks','unsubscribes'],[label('(a) Clics únicos','(a) Unique clicks',lang),label('(b) Bajas de suscripción','(b) Unsubscribes',lang)]):
        g=frame[frame.target==target];limit=max(g.prediction.max(),g.observed.max())*1.08
        ax.plot([0,limit],[0,limit],ls='--',color=GRAY,lw=1.5,zorder=1)
        ax.scatter(g.prediction,g.observed,s=39,color=TEAL,edgecolors='white',linewidths=.6,zorder=2,clip_on=False)
        ax.set(xlim=(0,limit),ylim=(0,limit));ax.set_aspect('equal',adjustable='box')
        ax.set_title(title,fontsize=13.2,loc='left',weight='bold',color=INK)
        ax.text(.96,.05,label(f'{len(g)} grupos',f'{len(g)} groups',lang),ha='right',transform=ax.transAxes,fontsize=10.7,color=GRAY)
        ax.set_xlabel(label('Predicción media (%)','Mean prediction (%)',lang),fontsize=11.9)
        ax.set_ylabel(label('Tasa observada media (%)','Mean observed rate (%)',lang),fontsize=11.9)
        ax.grid(alpha=.15);ax.tick_params(labelsize=10.6)
        ax.xaxis.set_major_locator(plt.MaxNLocator(4));ax.yaxis.set_major_locator(plt.MaxNLocator(4))
    handles=[Line2D([0],[0],color=GRAY,ls='--',lw=1.5,label=label('Igualdad de medias','Equal means',lang)),Line2D([0],[0],marker='o',color=TEAL,lw=0,label=label('Grupos de predicción','Prediction groups',lang))]
    fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.52,.995),ncol=2,frameon=False,fontsize=11.7)
    save(fig,'04_diagnostico_grupos',lang)

if __name__=='__main__':
    final=json.loads((ROOT/'results/final_evaluation.json').read_text(encoding='utf-8'))
    article_flow('en')
    paired('en',final)
    monthly('en',pd.read_csv(ROOT/'results/monthly_test.csv'))
    grouped('en',pd.read_csv(ROOT/'results/figures_tesis/diagnostic_groups.csv'))
    (OUT/'render_manifest.json').write_text(json.dumps({'files':FIGURES,'inputs':'Saved summaries; no fitting or new interval estimation.','font_preferences':FONT_PREFERENCES,'font_used':FONT_USED,'available_families':available,'strict_layout':STRICT_LAYOUT,'layout_warnings':LAYOUT_WARNINGS,'status':'PASS_WITH_LAYOUT_WARNINGS' if LAYOUT_WARNINGS else 'PASS'},indent=2)+'\n',encoding='utf-8')
    print('Rendered article Figures 1--4 in PNG/PDF/SVG; font='+FONT_USED+'; layout warnings='+str(len(LAYOUT_WARNINGS))+'.')
