from pathlib import Path
import io
import re
import time
import threading
import secrets
import json
import numpy as np
import pandas as pd
import joblib
from flask import Flask, jsonify, request, render_template, send_file, abort
from werkzeug.exceptions import HTTPException
from experiment.core import ROOT, MESSAGE, HISTORY, REQUIRED, TARGETS, HORIZON, read_campaigns, clean_campaigns, history_features, sha256
from experiment.models import baseline

FIELD_LABELS={
 'message_content_size':'Tamaño del contenido (bytes)', 'message_images_count':'Imágenes',
 'message_embedded_images_count':'Imágenes embebidas', 'message_embedded_images_size':'Tamaño de imágenes embebidas (bytes)',
 'message_embedded_files_count':'Archivos adjuntos', 'message_embedded_files_size':'Tamaño de adjuntos (bytes)',
 'message_links_count':'Enlaces', 'message_personalization_tags_count':'Marcas de personalización (total)',
 'message_personalization_tags_in_sender_email_count':'Personalización en remitente',
 'message_personalization_tags_in_subject_count':'Personalización en asunto',
 'message_personalization_tags_in_html_body_count':'Personalización en cuerpo HTML',
 'message_personalization_tags_in_text_body_count':'Personalización en texto plano'}


def create_app(workspace_dir=None):
    app=Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=400*1024*1024,JSON_SORT_KEYS=False)
    app.json.ensure_ascii=False
    selection=json.loads((ROOT/'results/selection.json').read_text(encoding='utf-8'))
    final=json.loads((ROOT/'results/final_evaluation.json').read_text(encoding='utf-8'))
    assert final['selection_sha256']==sha256(ROOT/'results/selection.json')
    bundles={}
    for t,item in selection['targets'].items():
        path=ROOT/f'artifacts/models/{t}_full.joblib'
        assert sha256(path)==item['full']['sha256']
        bundles[t]=joblib.load(path)
    bounds=json.loads((ROOT/'runtime/feature_bounds.json').read_text(encoding='utf-8'))
    info=json.loads((ROOT/'runtime/demo_info.json').read_text(encoding='utf-8'))
    demo=pd.read_parquet(ROOT/'runtime/demo.parquet')
    comparison=pd.read_parquet(ROOT/'runtime/comparison.parquet')
    lock=threading.RLock()
    state={'data':demo.copy(),'source':'Demostración · SendGuard900K','is_demo':True,'flow':[], 'last':None}
    workspace=Path(workspace_dir) if workspace_dir else ROOT/'runtime/workspace'
    workspace.mkdir(parents=True,exist_ok=True)
    predictions_path=workspace/'predictions.json'
    saved=json.loads(predictions_path.read_text(encoding='utf-8')) if predictions_path.exists() else []
    meta_path=workspace/'history.json'
    if meta_path.exists():
        meta=json.loads(meta_path.read_text(encoding='utf-8'))
        state.update(data=pd.read_parquet(workspace/'history.parquet'),**meta)
    if saved:state['last']=saved[-1]
    token=secrets.token_urlsafe(24)

    def persist_history():
        temp=workspace/'history.pending.parquet'
        state['data'].to_parquet(temp,index=False)
        temp.replace(workspace/'history.parquet')
        temp=workspace/'history.pending.json'
        temp.write_text(json.dumps({k:state[k] for k in ['source','is_demo','flow']},ensure_ascii=False),encoding='utf-8')
        temp.replace(meta_path)

    @app.before_request
    def local_write_guard():
        if request.method=='POST' and request.headers.get('X-Workspace-Token')!=token:
            abort(403,description='Recarga la página para iniciar una operación local válida.')

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Cache-Control']='no-store' if request.path.startswith('/api/') else 'no-cache'
        response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; frame-ancestors 'none'"
        return response

    @app.errorhandler(ValueError)
    def bad_value(error): return jsonify(error=str(error)),400

    @app.errorhandler(HTTPException)
    def http_error(error): return jsonify(error=error.description),error.code

    @app.get('/')
    def index():return render_template('index.html')

    @app.get('/api/summary')
    def summary():
        with lock:
            d=state['data']
            companies=d.groupby('client_id').agg(campaigns=('campaign_id','size')).reset_index().sort_values('client_id')
            monthly=d.assign(month=d.campaign_sent_time.dt.strftime('%Y-%m')).groupby('month').agg(
                campaigns=('campaign_id','size'), clicks=('y_clicks','mean'), unsubscribes=('y_unsubscribes','mean')).reset_index()
            return jsonify(token=token,source=state['source'],is_demo=state['is_demo'],rows=len(d),
                companies=companies.to_dict('records'),first=d.campaign_sent_time.min().isoformat(),last=d.campaign_sent_time.max().isoformat(),
                monthly=monthly.to_dict('records'),flow=state['flow'],fields=FIELD_LABELS,
                test_n=final['primary_n'],model_version=final['selection_sha256'][:12],horizon_hours=72)

    @app.post('/api/demo')
    def reset_demo():
        with lock:
            state.update(data=demo.copy(),source='Demostración · SendGuard900K',is_demo=True,flow=[],last=None)
            persist_history()
        return jsonify(ok=True)

    @app.post('/api/import')
    def import_csv():
        uploaded=request.files.get('file')
        if uploaded is None or not uploaded.filename.lower().endswith('.csv'):raise ValueError('Selecciona un archivo CSV.')
        try:raw=read_campaigns(uploaded.stream)
        except (ValueError,UnicodeError,pd.errors.ParserError) as error:
            raise ValueError('No se pudo interpretar el CSV. '+str(error)) from error
        clean,flow=clean_campaigns(raw)
        if clean.empty:raise ValueError('El archivo no contiene campañas válidas con el contrato de 72 horas.')
        for col in ['client_id','campaign_id']:
            if not clean[col].astype(str).str.fullmatch(r'[A-Za-z0-9_.-]{1,80}').all():
                raise ValueError('Usa identificadores opacos de hasta 80 letras, números, guiones o puntos.')
        # Imports validate their own records; they do not create new external evaluation evidence.
        with lock:
            state.update(data=clean,source='Archivo local · '+Path(uploaded.filename).name,is_demo=False,flow=flow,last=None)
            persist_history()
        return jsonify(ok=True,accepted=len(clean),excluded=len(raw)-len(clean),flow=flow)

    @app.get('/api/history')
    def history():
        client=request.args.get('client','')
        with lock:d=state['data'].loc[state['data'].client_id.eq(client)].sort_values('campaign_sent_time',ascending=False)
        records=[]
        for _,r in d.head(150).iterrows():records.append({'campaign_id':str(r.campaign_id),'date':r.campaign_sent_time.isoformat(),
            'sent':int(r.campaign_subscribers_count),'clicks':float(r.y_clicks),'unsubscribes':float(r.y_unsubscribes)})
        return jsonify(rows=records,total=len(d),displayed=len(records))

    @app.get('/api/example')
    def example():
        with lock:
            d=state['data']
            if state['is_demo']:
                row=d.loc[d.campaign_id.eq(info['default_campaign'])].iloc[0]
                when=row.campaign_sent_time
                kind='Campaña real reservada · reproducción histórica'
            else:
                row=d.sort_values('campaign_sent_time').iloc[-1]
                when=row.campaign_sent_time+HORIZON+pd.Timedelta(minutes=1)
                kind='Datos de la última campaña como punto de partida; revisa las entradas de la nueva campaña'
            return jsonify(client_id=str(row.client_id),campaign_id=str(row.campaign_id),when=when.isoformat(),kind=kind,
                           fields={c:float(row[c]) for c in MESSAGE})

    def predict_payload(payload):
        if not isinstance(payload,dict) or not isinstance(payload.get('fields'),dict):
            raise ValueError('Envía los datos de la campaña y sus campos en un objeto válido.')
        client=str(payload.get('client_id','')).strip()
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',client):raise ValueError('Indica un identificador de empresa válido.')
        campaign=str(payload.get('campaign_id','')).strip()
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',campaign):raise ValueError('Indica un identificador de campaña válido.')
        try:
            when=pd.Timestamp(payload.get('when'))
            if pd.isna(when) or when.tzinfo is None:raise ValueError('Incluye la zona horaria en la fecha.')
            when=when.tz_convert('UTC')
        except (ValueError,TypeError) as error:raise ValueError('Indica una fecha válida con zona horaria.') from error
        fields={}
        for col in MESSAGE:
            value=payload.get('fields',{}).get(col)
            try:value=float(value)
            except (TypeError,ValueError) as error:raise ValueError('Completa: '+FIELD_LABELS[col]) from error
            if not np.isfinite(value) or value<0 or value!=int(value):raise ValueError('Usa enteros no negativos en '+FIELD_LABELS[col])
            fields[col]=value
        q=pd.DataFrame([{'client_id':client,'campaign_sent_time':when,**fields}])
        with lock:h=state['data'].loc[state['data'].client_id.eq(client)].copy(); external=not state['is_demo']
        hist=history_features(h,q)
        f=pd.concat([q,hist],axis=1)
        n=int(hist.iloc[0].history_n)
        outputs={};start=time.perf_counter()
        for target,item in selection['targets'].items():
            if n<5:
                value=item['global_median']; method='Referencia global · historial insuficiente'
            elif item['product']==item['ml']:
                b=bundles[target]
                value=float(np.clip(b['model'].predict(f[b['features']].to_numpy(float)),0,100)[0]);method='Modelo evaluado'
            else:
                value=float(baseline(item['product'],f,target,item['global_mean'],item['global_median'])[0]);method='Referencia histórica seleccionada'
            outputs[target]={'rate_pct':value,'method':method}
        warnings=[]
        if n<5:warnings.append('Se requieren cinco campañas maduras para utilizar el modelo; se muestra la referencia global.')
        outside=[FIELD_LABELS[c] for c,v in fields.items() if v<bounds[c]['min'] or v>bounds[c]['max']]
        if outside:warnings.append('Valores fuera del rango observado durante entrenamiento: '+', '.join(outside))
        if when>=pd.Timestamp('2024-12-29T00:00Z'):warnings.append('Esta fecha está fuera del periodo evaluado; el rendimiento actual no ha sido medido.')
        if external:warnings.append('La evaluación publicada corresponde a SendGuard; este archivo importado no constituye validación externa.')
        now=pd.Timestamp.now(tz='UTC')
        result={'client_id':client,'campaign_id':campaign,'when':when.isoformat(),'mature_campaigns':n,'outputs':outputs,'warnings':warnings,
            'inference_ms':(time.perf_counter()-start)*1000,'horizon_hours':72,'model_version':final['selection_sha256'][:12],
            'registered_at':now.isoformat(),'mode':'Reproducción histórica' if when<=now else 'Estimación anterior al envío',
            'fields':fields,
            'interpretation':'Estimación central orientada al error absoluto; no es una media de conteos esperados.'}
        with lock:
            state['last']=result
            saved.append(result)
            temp=workspace/'predictions.pending.json'
            temp.write_text(json.dumps(saved,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
            temp.replace(predictions_path)
        return result

    app.extensions['predict_payload']=predict_payload

    @app.post('/api/predict')
    def predict():return jsonify(predict_payload(request.get_json(force=True)))

    @app.get('/api/comparison')
    def compare():
        records=[]
        for _,r in comparison.head(100).iterrows():
            records.append({'campaign_id':str(r.campaign_id),'client_id':str(r.client_id),'date':r.campaign_sent_time.isoformat(),
                'observed_clicks':r.observed_clicks,'predicted_clicks':r.product_clicks,
                'observed_unsubscribes':r.observed_unsubscribes,'predicted_unsubscribes':r.product_unsubscribes})
        return jsonify(rows=records,source='Casos reales reservados de SendGuard; selección independiente del error',total=len(comparison))

    @app.get('/api/saved')
    def saved_predictions():
        with lock:
            d=state['data']; records=[];now=pd.Timestamp.now(tz='UTC')
            for p in saved[-100:][::-1]:
                matched=d.loc[d.client_id.eq(p['client_id']) & d.campaign_id.eq(p['campaign_id']) & d.campaign_sent_time.eq(pd.Timestamp(p['when']))]
                observed=None
                same_fields=not matched.empty and all(float(matched.iloc[0][c])==p['fields'][c] for c in MESSAGE)
                if same_fields and pd.Timestamp(p['when'])+HORIZON<now:
                    row=matched.iloc[0]
                    observed={'clicks':float(row.y_clicks),'unsubscribes':float(row.y_unsubscribes)}
                status='Respuesta disponible' if observed is not None else ('Las propiedades no coinciden con la campaña observada' if not matched.empty and not same_fields else 'Pendiente de respuesta madura en el historial')
                records.append({**p,'observed':observed,'status':status})
            return jsonify(rows=records,total=len(saved))

    @app.get('/api/evaluation')
    def evaluation():return jsonify(final)

    @app.get('/download/example.csv')
    def download_example():return send_file(ROOT/'runtime/historial_real_ejemplo.csv',as_attachment=True,download_name='historial_real_sendguard.csv')

    @app.get('/download/template.csv')
    def template():return send_file(io.BytesIO((','.join(REQUIRED)+'\n').encode('utf-8-sig')),as_attachment=True,
                                   download_name='plantilla_historial.csv',mimetype='text/csv')

    @app.get('/download/prediction.json')
    def export_prediction():
        with lock:r=state['last']
        if r is None:raise ValueError('Primero genera una estimación.')
        return send_file(io.BytesIO(json.dumps(r,ensure_ascii=False,indent=2).encode('utf-8')),as_attachment=True,
                         download_name='estimacion_campana.json',mimetype='application/json')

    @app.get('/figures/<name>')
    def figure(name):
        if not re.fullmatch(r'[a-z0-9_]+\.(?:png|svg)',name):abort(404)
        return send_file(ROOT/'results/figures'/name)

    return app
