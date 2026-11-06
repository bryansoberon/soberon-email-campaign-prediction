"""Development-only helpers for phase 2 of the round-1 revision.

Same 2023 validation windows, maturity rule, thread limit, clipping and campaign-weighted pooled MAE as
experiment/develop.py. Only development rows (sent before 2024) are loaded. Each fit is cached in its own JSON
under results/revision_1/fase2_cache/, so an interrupted run resumes; results/development/ is never written."""
from experiment.revision_1.common import *
from experiment.revision_1.fase1_diagnosticos import topk_weights
from experiment.develop import WINDOWS, MemoryPeak
from experiment.models import BASELINES, baseline
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler, FunctionTransformer
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from lightgbm import LGBMRegressor
import platform
import time

CACHE = OUT/'fase2_cache'
LOCAL = ROOT/'data/processed/revision_1'  # git-ignored: development predictions and rebuilt horizons
# Parameters of experiment/models.py written out; build() with them reproduces make_model().
ORIGINAL = {
    'ridge_1': ('ridge', {'alpha': 1.0}),
    'ridge_100': ('ridge', {'alpha': 100.0}),
    'rf_30': ('rf', {'n_estimators': 160, 'max_depth': 14, 'min_samples_leaf': 30, 'max_features': .8, 'max_samples': .7}),
    'rf_100': ('rf', {'n_estimators': 160, 'max_depth': 14, 'min_samples_leaf': 100, 'max_features': .8, 'max_samples': .7}),
    'lgbm_15': ('lgbm', {'objective': 'regression_l1', 'n_estimators': 400, 'learning_rate': .04, 'num_leaves': 15,
                         'min_child_samples': 100, 'reg_lambda': 1.}),
    'lgbm_31': ('lgbm', {'objective': 'regression_l1', 'n_estimators': 400, 'learning_rate': .04, 'num_leaves': 31,
                         'min_child_samples': 100, 'reg_lambda': 1.})}
SELECTED = {'clicks': 'lgbm_15', 'unsubscribes': 'lgbm_31'}
DEVELOPMENT_SELECTED_BASELINE = {'clicks': 'last5_median', 'unsubscribes': 'global_median'}


def development():
    """Principal development population, loaded as in experiment/develop.py."""
    df = pd.read_parquet(ROOT/'data/processed/campaigns.parquet', filters=[('split', '==', 'development')])
    return df.loc[df.eligible_primary].copy()


def splits(df, horizon=HORIZON):
    """Expanding origins of experiment/develop.py: a training label must mature before the origin."""
    out = []
    for window, (start, end) in enumerate(WINDOWS, 1):
        start, end = pd.Timestamp(start, tz='UTC'), pd.Timestamp(end, tz='UTC')
        out.append((window, df.loc[df.campaign_sent_time+horizon < start],
                    df.loc[(df.campaign_sent_time >= start) & (df.campaign_sent_time < end)]))
    return out


def build(family, params):
    if family == 'ridge':
        return make_pipeline(FunctionTransformer(np.log1p), StandardScaler(), Ridge(**params))
    if family == 'rf':
        return RandomForestRegressor(bootstrap=True, n_jobs=6, random_state=SEED, **params)
    if family == 'lgbm':
        return LGBMRegressor(verbosity=-1, n_jobs=6, random_state=SEED, deterministic=True, force_col_wise=True, **params)
    raise ValueError(family)


def fit_predict(model, train, valid, target, features):
    """Fitting, thread limit, memory sampling and clipping of experiment.develop.fit."""
    start = time.perf_counter()
    with MemoryPeak() as memory, threadpool_limits(limits=6):
        model.fit(train[features].to_numpy(float), train['y_'+target].to_numpy(float))
    seconds = time.perf_counter()-start
    start = time.perf_counter()
    pred = np.clip(model.predict(valid[features].to_numpy(float)), 0, 100)
    return pred, {'fit_seconds': seconds, 'predict_seconds': time.perf_counter()-start,
                  'peak_process_rss_mb': memory.peak/2**20}


def sums(y, pred):
    """Additive error totals, so that windows and subsets pool with equal weight per campaign."""
    e = np.asarray(pred, float)-np.asarray(y, float)
    return {'n': int(len(e)), 'sum_abs': float(np.abs(e).sum()), 'sum_sq': float((e**2).sum()),
            'sum_err': float(e.sum()), 'n_obs_le_pred': int((e >= 0).sum())}


def score(valid, target, pred):
    """Per-window record: the metrics of experiment/develop.py plus additive totals."""
    y = valid['y_'+target]
    return {**metrics(y, pred, valid.campaign_subscribers_count, valid.client_id), **sums(y, pred)}


def pool(parts):
    """Pooled over windows. MAE uses the develop.py formula (window MAE weighted by campaigns) when available."""
    n = sum(p['n'] for p in parts)
    if not n:
        return {'n': 0}
    mae = (sum(p['mae_pp']*p['n'] for p in parts) if all('mae_pp' in p for p in parts) else sum(p['sum_abs'] for p in parts))/n
    return {'n': n, 'mae_pp': mae, 'rmse_pp': float(np.sqrt(sum(p['sum_sq'] for p in parts)/n)),
            'bias_pp': sum(p['sum_err'] for p in parts)/n,
            'share_obs_at_or_below_pred': sum(p['n_obs_le_pred'] for p in parts)/n}


def tails(train, valid, target, pred):
    """Errors among validation campaigns whose observed rate reaches high percentiles of that window's training labels."""
    y = valid['y_'+target].to_numpy(float)
    out = {}
    for q in [.90, .95, .99]:
        cut = float(np.quantile(train['y_'+target], q))
        mask = y >= cut
        out[f'P{q*100:.0f}'] = {'cut_pp': cut, **sums(y[mask], np.asarray(pred, float)[mask])}
    return out


def risk(train, valid, score_values):
    """Phase-1 unsubscribe risk counts with thresholds from the window's training labels."""
    y = valid.y_unsubscribes.to_numpy(float)
    s = np.asarray(score_values, float)
    out = {}
    for q in [.90, .95]:
        tau = float(np.quantile(train.y_unsubscribes, q))
        positive, alarm = y >= tau, s >= tau
        k = int(positive.sum())
        out[f'P{q*100:.0f}'] = {'tau_pp': tau, 'campaigns': int(len(y)), 'positives': k, 'alarms': int(alarm.sum()),
                                'hits': int((positive & alarm).sum()),
                                'topk_hits': float(topk_weights(s, k)[positive].sum()) if k else 0.}
    return out


def pool_risk(parts):
    out = {}
    for level in parts[0]:
        c = {k: sum(p[level][k] for p in parts) for k in ['campaigns', 'positives', 'alarms', 'hits', 'topk_hits']}
        out[level] = {'positive_share': c['positives']/c['campaigns'], 'alarm_rate': c['alarms']/c['campaigns'],
                      'recall': c['hits']/c['positives'], 'precision': c['hits']/c['alarms'] if c['alarms'] else np.nan,
                      'recall_at_k_positives': c['topk_hits']/c['positives']}
    return out


def baselines(train, valid, target, subsets=None, with_tails=False):
    """The six baselines of experiment/models.py with training-window mean and median."""
    mean, median = float(train['y_'+target].mean()), float(train['y_'+target].median())
    out = {}
    for name in BASELINES:
        pred = baseline(name, valid, target, mean, median)
        row = score(valid, target, pred)
        if subsets:
            row['subsets'] = {k: sums(valid['y_'+target].to_numpy(float)[m], pred[m]) for k, m in subsets.items()}
        if with_tails:
            row['tails'] = tails(train, valid, target, pred)
        out[name] = row
    return out


def best_baseline(records, target):
    """Same choice as experiment/develop.py: lowest pooled MAE, ties broken by name."""
    scores = {name: pool([r[name] for r in records])['mae_pp'] for name in BASELINES}
    return min(BASELINES, key=lambda n: (scores[n], n)), scores


def cached(key, identity, compute):
    """Loads a finished fit or computes and stores it; a stored record must match the requested identity."""
    path = CACHE/f'{key}.json'
    if path.exists():
        row = json.loads(path.read_text(encoding='utf-8'))
        if any(row.get(k) != v for k, v in identity.items()):
            raise SystemExit(f'La caché {path} no corresponde a la configuración pedida')
        return row
    row = {**identity, **compute()}
    save_json(path, row)
    return row


def original_development():
    """Per-window development values saved by experiment/develop.py, for reproduction checks."""
    rows = json.loads((ROOT/'results/development_summary.json').read_text(encoding='utf-8'))['rows']
    return {(r['candidate'], r['target'], r['window']): r for r in rows}


def development_files():
    folder = ROOT/'results/development'
    return {p.name: sha256(p) for p in sorted(folder.iterdir()) if p.is_file()}


class Guard:
    """Checks that frozen artifacts and results/development are identical before and after a stage."""
    def __enter__(self):
        check_frozen()
        self.before = (frozen_hashes(), development_files())
        return self

    def __exit__(self, kind, *args):
        if kind is None:
            assert (frozen_hashes(), development_files()) == self.before, 'Cambió un artefacto congelado'
            self.unchanged = True


def write_controls(name, payload):
    save_json(OUT/f'fase2_{name}_controles.json', {**payload, 'environment': {
        'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
        'platform': platform.platform()}})
