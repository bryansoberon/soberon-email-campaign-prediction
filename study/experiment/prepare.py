from experiment.core import *
import platform
import psutil


def main():
    raw = ROOT / 'data/raw/elegibilidad/SendGuard900K.csv'
    assert sha256(raw) == '4e83e286426ca43d0a5a0f4bb6157b83fc1ad0ae90751b8891a5822ae6eb3956'
    df, flow = clean_campaigns(read_campaigns(raw), '2024-12-29T00:00:00Z')
    print('Preparando historia madura para', len(df), 'campañas', flush=True)
    features = history_features(df, df)
    df = pd.concat([df, features], axis=1)
    df['eligible_primary'] = df.history_n.ge(5)
    df['split'] = np.where(df.campaign_sent_time < pd.Timestamp('2024-01-01T00:00:00Z'), 'development', 'test')
    out = ROOT / 'data/processed'
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / 'campaigns.parquet', index=False)
    counts = df.groupby(['split', 'eligible_primary']).agg(campaigns=('campaign_id', 'size'), companies=('client_id', 'nunique')).reset_index()
    report = {'source_sha256': sha256(raw), 'protocol_sha256': sha256(ROOT / '05_plan/PROTOCOLO_EXPERIMENTAL_V1.md'),
              'flow': flow, 'cohorts': counts.to_dict('records'), 'feature_columns': FEATURES,
              'horizon_hours': 72, 'history_rule': 'prior_send + 72h < query_send',
              'platform': platform.platform(), 'python': platform.python_version(),
              'logical_cpus': psutil.cpu_count(), 'memory_gb': psutil.virtual_memory().total / 2**30}
    save_json(ROOT / 'results/preparation.json', report)
    df[['campaign_id', 'client_id', 'campaign_sent_time', 'split', 'eligible_primary']].to_parquet(out/'partition_manifest.parquet', index=False)
    print(counts.to_string(index=False), flush=True)


if __name__ == '__main__':
    main()
