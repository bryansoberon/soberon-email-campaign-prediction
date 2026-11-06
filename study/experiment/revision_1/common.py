"""Shared helpers for the round-1 revision: frozen inputs, hashes and the protocol resampling."""
from experiment.core import *
from threadpoolctl import threadpool_limits

OUT = ROOT/'results/revision_1'
FINAL_ORIGIN = pd.Timestamp('2024-01-01T00:00Z')
FROZEN = ['artifacts/models/clicks_full.joblib', 'artifacts/models/clicks_history.joblib',
          'artifacts/models/unsubscribes_full.joblib', 'artifacts/models/unsubscribes_history.joblib',
          'results/selection.json', 'results/final_evaluation.json', 'results/monthly_test.csv',
          'data/processed/campaigns.parquet', 'data/processed/partition_manifest.parquet',
          'data/processed/test_predictions.parquet']


def frozen_hashes():
    return {path: sha256(ROOT/path) for path in FROZEN}


def check_frozen():
    """Stops if the selection or a model differs from the hashes saved before the test was opened."""
    selection = json.loads((ROOT/'results/selection.json').read_text(encoding='utf-8'))
    final = json.loads((ROOT/'results/final_evaluation.json').read_text(encoding='utf-8'))
    assert final['selection_sha256'] == sha256(ROOT/'results/selection.json')
    for target, item in selection['targets'].items():
        for kind in ['full', 'history']:
            assert sha256(ROOT/f'artifacts/models/{target}_{kind}.joblib') == item[kind]['sha256']
    return selection, final


def campaigns(columns):
    return pd.read_parquet(ROOT/'data/processed/campaigns.parquet', columns=columns)


def final_training(df):
    """The 546,759 matured development rows used to fit the frozen models."""
    return df.loc[df.split.eq('development') & df.eligible_primary & (df.campaign_sent_time + HORIZON < FINAL_ORIGIN)]


def test_frame(extra):
    """Saved 2024 predictions joined 1:1 with pre-send columns of the same campaigns."""
    pred = pd.read_parquet(ROOT/'data/processed/test_predictions.parquet')
    df = campaigns(['campaign_id', 'split', 'eligible_primary', 'y_clicks', 'y_unsubscribes'] + extra)
    df = df.loc[df.split.eq('test') & df.eligible_primary].drop(columns=['split', 'eligible_primary'])
    out = pred.merge(df, on='campaign_id', how='left', validate='1:1')
    for target in TARGETS:
        assert np.array_equal(out['observed_'+target].to_numpy(), out['y_'+target].to_numpy())
    return out.drop(columns=['y_clicks', 'y_unsubscribes'])


def ratio_interval(frame, numerator, denominator, block_weeks=4, repeats=2000):
    """Ratio of sums with the company x circular week-block resampling of experiment/evaluate.py.

    Same weeks, seed, replicate draws and percentiles: with a denominator of one per campaign it
    reproduces evaluate.interval exactly. Rows keep their numerator and denominator in every replicate."""
    codes, companies = pd.factorize(frame.client_id, sort=True)
    week = ((frame.campaign_sent_time-FINAL_ORIGIN).dt.total_seconds()/(7*86400)).astype(int).to_numpy()
    nw = int(week.max())+1; nc = len(companies)
    num = np.zeros((nc, nw)); den = np.zeros((nc, nw))
    np.add.at(num, (codes, week), np.asarray(numerator, float))
    np.add.at(den, (codes, week), np.asarray(denominator, float))
    if not den.sum():
        return {'estimate': np.nan, 'lower': np.nan, 'upper': np.nan, 'valid_replicates': 0}
    rng = np.random.default_rng(SEED+block_weeks)
    estimates = []
    with threadpool_limits(limits=1):
        for _ in range(repeats):
            cw = np.bincount(rng.integers(0, nc, nc), minlength=nc)
            starts = rng.integers(0, nw, int(np.ceil(nw/block_weeks)))
            sampled = (starts[:, None]+np.arange(block_weeks)) % nw
            ww = np.bincount(sampled.ravel()[:nw], minlength=nw)
            d = float(cw@(den@ww))
            if d: estimates.append(float(cw@(num@ww))/d)
    lo, hi = np.quantile(estimates, [.0125, .9875])
    return {'estimate': float(num.sum()/den.sum()), 'lower': float(lo), 'upper': float(hi),
            'valid_replicates': len(estimates)}


def markdown(df, digits=4):
    """Plain Markdown table without optional dependencies."""
    def cell(v):
        if isinstance(v, (float, np.floating)):
            return '' if np.isnan(v) else f'{v:,.{digits}f}'
        if isinstance(v, (int, np.integer)):
            return f'{v:,}'
        return str(v)
    lines = ['| '+' | '.join(map(str, df.columns))+' |', '|'+'---|'*len(df.columns)]
    lines += ['| '+' | '.join(cell(v) for v in row)+' |' for row in df.itertuples(index=False)]
    return '\n'.join(lines)
