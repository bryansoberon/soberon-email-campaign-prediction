from experiment.core import *
from experiment.models import *
import joblib
import time
import threading
import psutil
from threadpoolctl import threadpool_limits

WINDOWS = [('2023-01-01','2023-05-01'),('2023-05-01','2023-09-01'),('2023-09-01','2023-12-29')]


class MemoryPeak:
    def __enter__(self):
        self.peak = 0
        self.stop = threading.Event()
        def sample():
            while not self.stop.is_set():
                self.peak = max(self.peak,psutil.Process().memory_info().rss)
                self.stop.wait(.1)
        self.thread = threading.Thread(target=sample,daemon=True)
        self.thread.start()
        return self
    def __exit__(self,*args):
        self.stop.set(); self.thread.join()


def fit(name,train,valid,target,features):
    model=make_model(name)
    start=time.perf_counter()
    with MemoryPeak() as memory, threadpool_limits(limits=6):
        model.fit(train[features].to_numpy(float),train['y_'+target].to_numpy(float))
    seconds=time.perf_counter()-start
    predict_start=time.perf_counter()
    pred=np.clip(model.predict(valid[features].to_numpy(float)),0,100)
    return model,pred,{'fit_seconds':seconds,'predict_seconds':time.perf_counter()-predict_start,'peak_process_rss_mb':memory.peak/2**20}


def main():
    path=ROOT/'results/development'
    path.mkdir(parents=True,exist_ok=True)
    # Only development rows are loaded by this stage. Never evaluates a 2024 response.
    df=pd.read_parquet(ROOT/'data/processed/campaigns.parquet',filters=[('split','==','development')])
    df=df.loc[df.eligible_primary].copy()
    rows=[]
    for window,(start,end) in enumerate(WINDOWS,1):
        start,end=pd.Timestamp(start,tz='UTC'),pd.Timestamp(end,tz='UTC')
        train=df.loc[df.campaign_sent_time+HORIZON < start]
        valid=df.loc[(df.campaign_sent_time>=start)&(df.campaign_sent_time<end)]
        print('Ventana',window,'train',len(train),'valid',len(valid),flush=True)
        for target in TARGETS:
            mean=float(train['y_'+target].mean()); median=float(train['y_'+target].median())
            for name in BASELINES+CANDIDATES:
                cache=path/f'{target}_{name}_{window}.json'
                if cache.exists():
                    rows.append(json.loads(cache.read_text(encoding='utf-8'))); continue
                if name in BASELINES:
                    pred=baseline(name,valid,target,mean,median); resources={}
                else:
                    _,pred,resources=fit(name,train,valid,target,FEATURES)
                row={'window':window,'target':target,'candidate':name,'train_n':len(train),
                     **metrics(valid['y_'+target],pred,valid.campaign_subscribers_count,valid.client_id),**resources}
                rows.append(row);save_json(cache,row)
                pd.DataFrame(rows).to_csv(path/'comparison.csv',index=False)
                print(target,name,'MAE',round(row['mae_pp'],6),flush=True)
    scores={}
    for target in TARGETS:
        scores[target]={}
        for name in BASELINES+CANDIDATES:
            parts=[r for r in rows if r['target']==target and r['candidate']==name]
            scores[target][name]=sum(r['mae_pp']*r['n'] for r in parts)/sum(r['n'] for r in parts)
    selection={'seed':SEED,'protocol_sha256':sha256(ROOT/'05_plan/PROTOCOLO_EXPERIMENTAL_V1.md'),
               'development_scores':scores,'targets':{},'test_opened':False,'features':FEATURES}
    models_dir=ROOT/'artifacts/models';models_dir.mkdir(parents=True,exist_ok=True)
    train=df.loc[df.campaign_sent_time+HORIZON < pd.Timestamp('2024-01-01T00:00Z')]
    for target in TARGETS:
        best=min(CANDIDATES,key=lambda n:(scores[target][n],n))
        ref=min(BASELINES,key=lambda n:(scores[target][n],n))
        product=best if scores[target][best]<scores[target][ref] else ref
        item={'ml':best,'reference':ref,'product':product,'train_n':len(train),
              'global_mean':float(train['y_'+target].mean()),'global_median':float(train['y_'+target].median())}
        # Ablation is fixed from the selected ML configuration, no extra search.
        for kind,features in [('full',FEATURES),('history',HISTORY)]:
            model,_,resources=fit(best,train,train.iloc[:1000],target,features)
            file=models_dir/f'{target}_{kind}.joblib'
            joblib.dump({'model':model,'features':features,'target':target,'selection':item},file,compress=3)
            item[kind]={'sha256':sha256(file),**resources}
        selection['targets'][target]=item
        print('Selección',target,item['ml'],'referencia',ref,'producto',product,flush=True)
    save_json(ROOT/'results/selection.json',selection)
    save_json(ROOT/'results/development_summary.json',{'windows':WINDOWS,'scores':scores,'rows':rows})
    print('Selección congelada. No se ha evaluado el test.',flush=True)


if __name__=='__main__':main()
