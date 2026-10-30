'use strict';
let summary=null;
const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number=(value,digits=0)=>new Intl.NumberFormat(window.CampaignI18n?.locale||'es-PE',{minimumFractionDigits:digits,maximumFractionDigits:digits}).format(value);
const date=value=>new Date(value).toISOString().replace('T',' ').slice(0,16);
const pct=(value,digits=3)=>number(value,digits)+' %';
function notice(message,error=false){$('notice').textContent=message;$('notice').classList.toggle('error',error);$('notice').hidden=false;}
async function api(url,options={}){
 const headers={...(options.headers||{})};
 if(options.method==='POST')headers['X-Workspace-Token']=summary?.token||'';
 const res=await fetch(url,{...options,headers});
 const body=await res.json();if(!res.ok)throw new Error(body.error||'No se pudo completar la operación.');return body;
}
function card(label,value,detail){return `<article class="metric-card"><div class="label">${esc(label)}</div><div class="value">${esc(value)}</div><div class="detail">${esc(detail)}</div></article>`;}
function clearPrediction(){ $('prediction-result').innerHTML='<div class="empty-state"><span>↗</span><h3>Una estimación con historia</h3><p>Calcula la estimación con las entradas actuales para consultar ambas tasas.</p></div>'; }
function chart(rows){
 if(rows.length<2){$('history-chart').textContent='Se necesitan al menos dos meses para mostrar la evolución.';return;}
 const w=620,h=230,pad=37,max=Math.max(...rows.map(r=>r.clicks),.01)*1.15;
 const point=(r,i)=>[pad+i*(w-2*pad)/(rows.length-1),h-pad-r.clicks/max*(h-2*pad)];
 const points=rows.map(point);const line=points.map(p=>p.join(',')).join(' ');
 const area=`${pad},${h-pad} ${line} ${w-pad},${h-pad}`;
 const grid=[0,.5,1].map(r=>{const y=h-pad-r*(h-2*pad);return `<line class="grid-line" x1="${pad}" y1="${y}" x2="${w-pad}" y2="${y}"/><text x="${pad-8}" y="${y+4}" text-anchor="end">${number(r*max,1)}</text>`;}).join('');
 const labels=rows.map((r,i)=>i%Math.max(1,Math.floor(rows.length/5))===0||i===rows.length-1?`<text x="${points[i][0]}" y="${h-8}" text-anchor="middle">${esc(r.month)}</text>`:'').join('');
 const dots=points.map((p,i)=>`<circle cx="${p[0]}" cy="${p[1]}" r="3"><title>${esc(rows[i].month)}: ${pct(rows[i].clicks)} · ${number(rows[i].campaigns)} campañas</title></circle>`).join('');
 $('history-chart').innerHTML=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Tasa de clics por mes">${grid}<polygon class="area" points="${area}"/><polyline class="trend" points="${line}"/>${dots}${labels}</svg>`;
}
async function refresh(){
 summary=await api('/api/summary');$('source').textContent=summary.source;
 $('summary-cards').innerHTML=card('Campañas disponibles',number(summary.rows),'En el archivo cargado')+card('Empresas emisoras',number(summary.companies.length),'Identificadores anonimizados')+card('Ventana de respuesta','72 horas','Clics únicos y bajas')+card('Campañas de evaluación',number(summary.test_n),'Periodo reservado · 2024');
 const options=summary.companies.map(r=>`<option value="${esc(r.client_id)}">Emisor ${esc(r.client_id)} · ${number(r.campaigns)} campañas</option>`).join('');
 $('history-client').innerHTML=options;$('clients-list').innerHTML=summary.companies.map(r=>`<option value="${esc(r.client_id)}">Emisor ${esc(r.client_id)}</option>`).join('');
 const primary=['message_content_size','message_images_count','message_links_count','message_personalization_tags_count'];
 $('message-fields').innerHTML='';$('advanced-fields').innerHTML='';
 for(const [field,label] of Object.entries(summary.fields)){
  const html=`<label>${esc(label)}<input type="number" id="${field}" data-field="${field}" required min="0" step="1"></label>`;
  $(primary.includes(field)?'message-fields':'advanced-fields').insertAdjacentHTML('beforeend',html);
 }
 chart(summary.monthly);await fillExample();
}
async function fillExample(){
 const data=await api('/api/example');$('predict-client').value=data.client_id;
 $('predict-campaign').value=data.campaign_id;clearPrediction();
 $('predict-when').value=new Date(data.when).toISOString().slice(0,19);$('example-context').textContent=data.kind;
 for(const [name,value] of Object.entries(data.fields))$(name).value=value;
}
async function loadHistory(){
 const data=await api('/api/history?client='+encodeURIComponent($('history-client').value));
 $('history-count').textContent=`${number(data.total)} campañas · mostrando ${number(data.displayed)}`;
 $('history-rows').innerHTML=data.rows.map(r=>`<tr><td>${esc(r.campaign_id)}</td><td>${esc(date(r.date))}</td><td>${number(r.sent)}</td><td>${pct(r.clicks)}</td><td>${pct(r.unsubscribes)}</td></tr>`).join('');
}
async function loadComparison(){
 const saved=await api('/api/saved');
 $('saved-count').textContent=`${number(saved.total)} estimaciones guardadas · se muestran las últimas 100`;
 $('saved-rows').innerHTML=saved.rows.map(r=>`<tr><td>${esc(r.campaign_id)}<br><span class="muted">${esc(r.mode)}</span></td><td>${esc(date(r.registered_at))}</td><td>${pct(r.outputs.clicks.rate_pct)}</td><td>${r.observed?pct(r.observed.clicks):'—'}</td><td>${pct(r.outputs.unsubscribes.rate_pct,4)}</td><td>${r.observed?pct(r.observed.unsubscribes,4):'—'}</td><td>${esc(r.status)}</td></tr>`).join('')||'<tr><td colspan="7">Aún no hay estimaciones guardadas. Genera una desde Estimar campaña.</td></tr>';
 const data=await api('/api/comparison');
 $('comparison-rows').innerHTML=data.rows.map(r=>`<tr><td>${esc(r.campaign_id)}<br><span class="muted">Emisor ${esc(r.client_id)}</span></td><td>${date(r.date)}</td><td>${pct(r.predicted_clicks)}</td><td>${pct(r.observed_clicks)}</td><td>${pct(r.predicted_unsubscribes,4)}</td><td>${pct(r.observed_unsubscribes,4)}</td></tr>`).join('');
 $('comparison-count').textContent=`Se muestran ${number(data.rows.length)} de ${number(data.total)} campañas de demostración. Esta vista conserva los casos reservados, aunque se cargue otro historial.`;
}
async function loadEvaluation(){
 const data=await api('/api/evaluation');
 $('evaluation-cards').innerHTML=card('Campañas reservadas',number(data.primary_n),'Sin ajuste de modelos en test')+card('Empresas evaluadas',number(data.primary_companies),'Con cinco campañas maduras previas')+card('Evaluación','2024','Hasta el 28 de diciembre')+card('Comparación','2 tasas','Referencia elegida en desarrollo');
 $('evaluation-rows').innerHTML=Object.entries(data.targets).map(([key,r])=>`<tr><td>${key==='clicks'?'Clics únicos':'Bajas'}</td><td>${number(r.metrics.full.mae_pp,4)} pp</td><td>${number(r.metrics.reference.mae_pp,4)} pp</td><td class="positive">${number(r.relative_mae_reduction_pct,2)} %</td><td>${number(r.metrics.full.bias_pp,4)} pp</td></tr>`).join('');
 $('evaluation-findings').innerHTML='<p>El método redujo el error absoluto frente a las referencias en ambas tasas dentro del periodo evaluado.</p>'+Object.entries(data.targets).map(([key,r])=>`<p><strong>${key==='clicks'?'Clics únicos':'Bajas'}.</strong> Intervalo del 97,5 % para la diferencia de MAE: [${number(r.comparison.lower_pp,4)}, ${number(r.comparison.upper_pp,4)}] pp.</p>`).join('')+'<p class="small muted">Diferencia negativa favorece al método. Remuestreo por empresas y bloques temporales; intervalos aproximados con ajuste para dos tasas.</p>';
 $('model-version').textContent=summary.model_version;
}
async function show(view){
 const allowed=['resumen','historial','estimar','comparar','evaluacion'];if(!allowed.includes(view))view='resumen';
 document.querySelectorAll('.view').forEach(el=>el.hidden=el.id!==view);
 document.querySelectorAll('.nav').forEach(el=>{el.classList.toggle('active',el.dataset.view===view);if(el.dataset.view===view)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');});
 $('section-name').textContent={resumen:'Resumen',historial:'Historial',estimar:'Estimar campaña',comparar:'Comparar resultados',evaluacion:'Evaluación'}[view];
 history.replaceState(null,'','#'+view);window.scrollTo({top:0});
 try{if(view==='historial')await loadHistory();if(view==='comparar')await loadComparison();if(view==='evaluacion')await loadEvaluation();}catch(e){notice(e.message,true);}
}
document.querySelectorAll('[data-view],[data-go]').forEach(el=>el.addEventListener('click',()=>show(el.dataset.view||el.dataset.go)));
window.addEventListener('hashchange',()=>{if(summary)show(location.hash.slice(1));});
$('history-client').addEventListener('change',()=>loadHistory().catch(e=>notice(e.message,true)));
$('example-button').addEventListener('click',()=>fillExample().catch(e=>notice(e.message,true)));
$('predict-form').addEventListener('input',clearPrediction);
$('csv-file').addEventListener('change',()=>{$('csv-filename').textContent=$('csv-file').files[0]?.name||'Ningún archivo seleccionado';});
$('demo-button').addEventListener('click',async()=>{try{await api('/api/demo',{method:'POST'});await refresh();notice('Demostración restaurada con registros reales de SendGuard.');}catch(e){notice(e.message,true);}});
$('import-button').addEventListener('click',async()=>{
 const file=$('csv-file').files[0];if(!file){notice('Selecciona un CSV antes de importar.',true);return;}
 const button=$('import-button');button.disabled=true;button.textContent='Validando archivo…';
 try{const form=new FormData();form.append('file',file);const result=await api('/api/import',{method:'POST',body:form});await refresh();$('import-result').textContent=`${number(result.accepted)} filas válidas · ${number(result.excluded)} excluidas`;
 notice('Archivo cargado. Se verificó su estructura; la compatibilidad externa depende también de sus definiciones.');
 }catch(e){notice(e.message,true);}finally{button.disabled=false;button.textContent='Validar e importar';}
});
$('predict-form').addEventListener('submit',async event=>{
 event.preventDefault();const button=$('predict-button');button.disabled=true;button.textContent='Calculando…';
 try{const fields={};document.querySelectorAll('[data-field]').forEach(el=>fields[el.dataset.field]=el.value);
 const when=$('predict-when').value+'Z';const result=await api('/api/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({client_id:$('predict-client').value,campaign_id:$('predict-campaign').value,when,fields})});
 const rates=Object.entries(result.outputs).map(([key,r])=>`<div class="rate-result"><div class="rate-label">${key==='clicks'?'Tasa de clics únicos':'Tasa de bajas de suscripción'}</div><div class="rate-number">${number(r.rate_pct,key==='clicks'?3:4)}<span>%</span></div><div class="small muted">${esc(r.method)}</div></div>`).join('');
 $('prediction-result').innerHTML=rates+`<div class="result-info"><strong>${number(result.mature_campaigns)}</strong> campañas con 72 horas completas<br><span class="muted">Historial anterior al ${esc(date(result.when))} UTC</span></div>`+result.warnings.map(w=>`<div class="warning">${esc(w)}</div>`).join('')+`<p class="small muted">Estimación central por campaña. Una tasa cercana a cero no garantiza ausencia de bajas.</p><p class="small">${esc(result.mode)} · guardada para consulta.</p><a class="secondary full" href="/download/prediction.json">Descargar estimación</a><p class="small muted">Modelo ${esc(result.model_version)} · inferencia ${number(result.inference_ms,1)} ms</p>`;
 }catch(e){notice(e.message,true);}finally{button.disabled=false;button.innerHTML='Calcular estimación <span>↗</span>';}
});
(async()=>{try{await refresh();await show(location.hash.slice(1)||'resumen');window.appReady=true;}catch(e){notice(e.message,true);}})();
