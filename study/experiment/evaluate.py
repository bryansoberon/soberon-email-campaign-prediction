"""Single held-out evaluation after models/selection have been frozen."""
from experiment.core import *
from experiment.models import baseline
import joblib
import time
from threadpoolctl import threadpool_limits


def interval(frame, difference, block_weeks=4, repeats=2000):
    company_codes,companies=pd.factorize(frame.client_id,sort=True)
    # Integer weeks from start of test. Aggregate losses, not predictions, for paired inference.
    dates=frame.campaign_sent_time
    week=((dates-pd.Timestamp('2024-01-01T00:00Z')).dt.total_seconds()/(7*86400)).astype(int).to_numpy()
    nw=int(week.max())+1; nc=len(companies)
    total=np.zeros((nc,nw)); count=np.zeros((nc,nw))
    np.add.at(total,(company_codes,week),np.asarray(difference,float))
    np.add.at(count,(company_codes,week),1)
    rng=np.random.default_rng(SEED+block_weeks)
    estimates=[]
    with threadpool_limits(limits=1):
        for _ in range(repeats):
            cw=np.bincount(rng.integers(0,nc,nc),minlength=nc)
            starts=rng.integers(0,nw,int(np.ceil(nw/block_weeks)))
            sampled=(starts[:,None]+np.arange(block_weeks))%nw
            ww=np.bincount(sampled.ravel()[:nw],minlength=nw)
            denominator=float(cw@(count@ww))
            if denominator: estimates.append(float(cw@(total@ww))/denominator)
    lo,hi=np.quantile(estimates,[.0125,.9875])
    return {'difference_mae_pp':float(np.mean(difference)), 'ci_level':.975,
            'lower_pp':float(lo),'upper_pp':float(hi),'block_weeks':block_weeks,
            'repeats':repeats,'companies':nc,'calendar_weeks':nw,
            'method':'company resampling x circular moving calendar blocks; percentile'}


def main():
    result_path=ROOT/'results/final_evaluation.json'
    if result_path.exists():
        raise SystemExit('El test ya tiene salida. No reevaluar sin registrar una corrección justificada.')
    selection_file=ROOT/'results/selection.json'
    selection=json.loads(selection_file.read_text(encoding='utf-8'))
    assert selection['test_opened'] is False
    assert selection['protocol_sha256']==sha256(ROOT/'05_plan/PROTOCOLO_EXPERIMENTAL_V1.md')
    df=pd.read_parquet(ROOT/'data/processed/campaigns.parquet',filters=[('split','==','test')])
    primary=df.loc[df.eligible_primary].copy()
    cold=df.loc[~df.eligible_primary].copy()
    report={'selection_sha256':sha256(selection_file),'protocol_sha256':selection['protocol_sha256'],
            'period':['2024-01-01','2024-12-29 exclusive'],'primary_n':len(primary),
            'primary_companies':int(primary.client_id.nunique()),'limited_history_n':len(cold),
            'targets':{},'interpretation':'observational temporal prediction; no external or causal validation'}
    preds=primary[['campaign_id','client_id','campaign_sent_time','campaign_subscribers_count','history_n']].copy()
    grouped=[]
    for target,item in selection['targets'].items():
        print('Test final:',target,flush=True)
        y=primary['y_'+target].to_numpy(float)
        output={}
        for kind in ['full','history']:
            path=ROOT/f'artifacts/models/{target}_{kind}.joblib'
            assert sha256(path)==item[kind]['sha256']
            bundle=joblib.load(path)
            start=time.perf_counter()
            output[kind]=np.clip(bundle['model'].predict(primary[bundle['features']].to_numpy(float)),0,100)
            report.setdefault('prediction_seconds',{})[target+'_'+kind]=time.perf_counter()-start
        output['reference']=baseline(item['reference'],primary,target,item['global_mean'],item['global_median'])
        output['product']=output['full'] if item['product']==item['ml'] else output['reference']
        m={name:metrics(y,p,primary.campaign_subscribers_count,primary.client_id) for name,p in output.items()}
        diff=np.abs(output['full']-y)-np.abs(output['reference']-y)
        ci=interval(primary,diff)
        sensitivity=[interval(primary,diff,w,1000) for w in [2,8]]
        ablation=interval(primary,np.abs(output['full']-y)-np.abs(output['history']-y))
        cold_pred=np.full(len(cold),item['global_median'])
        report['targets'][target]={'ml':item['ml'],'reference':item['reference'],'product':item['product'],
              'metrics':m,'comparison':ci,'block_sensitivity':sensitivity,'message_ablation':ablation,
              'limited_history_global_median':metrics(cold['y_'+target],cold_pred,cold.campaign_subscribers_count,cold.client_id),
              'relative_mae_reduction_pct':100*(m['reference']['mae_pp']-m['full']['mae_pp'])/m['reference']['mae_pp'] if m['reference']['mae_pp'] else None}
        preds['observed_'+target]=y
        for name,p in output.items():preds[name+'_'+target]=p
        months=primary.campaign_sent_time.dt.strftime('%Y-%m')
        for month in sorted(months.unique()):
            mask=months.eq(month).to_numpy()
            for name,p in output.items():
                grouped.append({'month':month,'target':target,'method':name,**metrics(y[mask],p[mask])})
        print(target,'MAE',m['full']['mae_pp'],'ref',m['reference']['mae_pp'],'IC',ci['lower_pp'],ci['upper_pp'],flush=True)
    report['joint_hypothesis_supported']=all(v['comparison']['upper_pp']<0 for v in report['targets'].values())
    preds.to_parquet(ROOT/'data/processed/test_predictions.parquet',index=False)
    pd.DataFrame(grouped).to_csv(ROOT/'results/monthly_test.csv',index=False)
    save_json(result_path,report)
    print('Evaluación final guardada. No se cambiaron modelos usando test.',flush=True)


if __name__=='__main__':main()
