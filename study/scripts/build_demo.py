from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiment.core import *


def main():
    df=pd.read_parquet(ROOT/'data/processed/campaigns.parquet')
    dev=df.loc[df.split.eq('development')]
    test=pd.read_parquet(ROOT/'data/processed/test_predictions.parquet')
    counts=dev.groupby('client_id').size()
    eligible=counts.loc[counts.between(60,200)&counts.index.isin(test.client_id)]
    ranking=pd.DataFrame({'client_id':eligible.index,'distance':abs(eligible.values-100)})
    companies=ranking.sort_values(['distance','client_id']).head(12).client_id.tolist()
    demo=df.loc[df.client_id.isin(companies)].copy()
    cases=test.loc[test.client_id.isin(companies)].sort_values(['campaign_sent_time','campaign_id']).copy()
    folder=ROOT/'runtime';folder.mkdir(exist_ok=True)
    demo.to_parquet(folder/'demo.parquet',index=False)
    demo[REQUIRED].to_csv(folder/'historial_real_ejemplo.csv',index=False)
    cases.to_parquet(folder/'comparison.parquet',index=False)
    features=dev.loc[dev.eligible_primary & (dev.campaign_sent_time+HORIZON<pd.Timestamp('2024-01-01T00:00Z')),MESSAGE]
    bounds={c:{'min':float(features[c].min()),'max':float(features[c].max())} for c in MESSAGE}
    save_json(folder/'feature_bounds.json',bounds)
    example=cases.iloc[0]
    save_json(folder/'demo_info.json',{'source':'SendGuard900K v1.0.0','real_records':True,
        'selection_rule':'12 companies closest to 100 development campaigns, between 60 and 200; ties by opaque ID; no error-based selection',
        'rows':len(demo),'companies':len(companies),'default_campaign':str(example.campaign_id)})
    print('Demostración real:',len(demo),'campañas,',len(companies),'empresas')


if __name__=='__main__':main()
