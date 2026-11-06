"""Phase 2 (i), R2.7: response horizons of 24 h and 48 h and history thresholds of 3, 5 and 10, development only.

Run: .venv\\Scripts\\python.exe -X utf8 -m experiment.revision_1.fase2_horizontes [--solo-preparar]
Rebuilds rates and mature history per horizon with experiment.core.history_features (core.py is not edited),
keeping the windows of experiment/develop.py. Writes fase2_i_* in results/revision_1/.
"""
from experiment.revision_1.desarrollo import *
import experiment.core as core
from contextlib import contextmanager
import argparse

RAW = ROOT/'data/raw/elegibilidad/SendGuard900K.csv'
RAW_SHA256 = '4e83e286426ca43d0a5a0f4bb6157b83fc1ad0ae90751b8891a5822ae6eb3956'
COUNTS = {24: ['campaign_unique_clicks_count_1440', 'campaign_resigned_count_1440'],
          48: ['campaign_unique_clicks_count_2880', 'campaign_resigned_count_2880'],
          72: list(TARGETS.values())}
SCENARIOS = [(24, 5), (48, 5), (72, 3), (72, 5), (72, 10)]  # (horizon in hours, minimum mature campaigns)


@contextmanager
def horizon(hours):
    """Evaluates core.history_features with another maturity horizon (t_j + h < t_c) and restores it afterwards."""
    kept = core.HORIZON
    core.HORIZON = pd.Timedelta(hours=hours)
    try:
        yield
    finally:
        core.HORIZON = kept


def frame_path(hours):
    return LOCAL/f'horizonte_{hours}h.parquet'


def prepare():
    """Rates and mature history for every development campaign at each horizon. 2024 rows are discarded on reading."""
    assert sha256(RAW) == RAW_SHA256
    dev = pd.read_parquet(ROOT/'data/processed/campaigns.parquet', filters=[('split', '==', 'development')])
    raw = pd.read_csv(RAW, usecols=['campaign_id']+COUNTS[24]+COUNTS[48], dtype={'campaign_id': 'str'})
    raw = raw.loc[raw.campaign_id.isin(set(dev.campaign_id))]
    dev = dev.merge(raw, on='campaign_id', how='left', validate='1:1')
    counts = COUNTS[24]+COUNTS[48]+COUNTS[72]
    checks = {'development_campaigns': len(dev), 'missing_counts': int(dev[counts].isna().sum().sum()),
              'negative_counts': int((dev[counts] < 0).sum().sum()),
              'counts_above_sent': int(dev[counts].gt(dev.campaign_subscribers_count, axis=0).sum().sum()),
              'non_monotone_24_48_72': int(sum(((dev[COUNTS[24][i]] > dev[COUNTS[48][i]]) | (dev[COUNTS[48][i]] > dev[COUNTS[72][i]])).sum()
                                               for i in range(2)))}
    assert checks['missing_counts'] == checks['negative_counts'] == checks['counts_above_sent'] == 0
    base = ['client_id', 'campaign_id', 'campaign_sent_time', 'campaign_subscribers_count']+MESSAGE
    for hours, (clicks, unsubscribes) in COUNTS.items():
        frame = dev[base].copy()
        frame['y_clicks'] = 100*dev[clicks]/dev.campaign_subscribers_count
        frame['y_unsubscribes'] = 100*dev[unsubscribes]/dev.campaign_subscribers_count
        with horizon(hours):
            frame = pd.concat([frame, core.history_features(frame, frame)], axis=1)
        if hours == 72:
            same = {c: bool(np.array_equal(frame[c].to_numpy(), dev[c].to_numpy())) for c in HISTORY+['y_clicks', 'y_unsubscribes']}
            checks['rebuilt_72h_equals_campaigns_parquet'] = all(same.values())
            assert all(same.values()), same
        checks[f'eligible_at_{hours}h_min5'] = int(frame.history_n.ge(5).sum())
        frame_path(hours).parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(frame_path(hours), index=False)
        print('Horizonte', hours, 'h preparado', flush=True)
    save_json(OUT/'fase2_i_preparacion.json', checks)
    return checks


def run():
    frames = {h: pd.read_parquet(frame_path(h)) for h in COUNTS}
    history72 = frames[72].set_index('campaign_id').history_n
    records = []
    for hours, minimum in SCENARIOS:
        frame = frames[hours]
        for window, train, valid in splits(frame.loc[frame.history_n.ge(minimum)], pd.Timedelta(hours=hours)):
            n72 = history72.reindex(valid.campaign_id).to_numpy()
            subsets = {'original_population': n72 >= 5, 'history_at_least_10': n72 >= 10}
            for target in TARGETS:
                name = SELECTED[target]

                def compute():
                    pred, resources = fit_predict(build('lgbm', ORIGINAL[name][1]), train, valid, target, FEATURES)
                    y = valid['y_'+target].to_numpy(float)
                    return {'train_n': len(train), **score(valid, target, pred), **resources,
                            'subsets': {k: sums(y[m], pred[m]) for k, m in subsets.items()},
                            'baselines': baselines(train, valid, target, subsets)}
                records.append(cached(f'i/h{hours}_m{minimum}_{target}_w{window}', {
                    'analysis': 'i', 'horizon_hours': hours, 'min_history': minimum, 'target': target, 'window': window,
                    'config': name}, compute))
                print('i', f'{hours} h', f'mín. {minimum}', target, 'ventana', window, 'MAE', round(records[-1]['mae_pp'], 6), flush=True)
    return records


def tables(records):
    rows = []
    for hours, minimum in SCENARIOS:
        for target in TARGETS:
            parts = sorted([r for r in records if (r['horizon_hours'], r['min_history'], r['target']) == (hours, minimum, target)],
                           key=lambda r: r['window'])
            reference, scores = best_baseline([p['baselines'] for p in parts], target)
            model = pool(parts)
            row = {'horizon_hours': hours, 'min_history': minimum, 'target': target, 'train_n_by_window': '/'.join(str(p['train_n']) for p in parts),
                   'valid_n': model['n'], 'model_mae_pp': model['mae_pp'], 'model_bias_pp': model['bias_pp'],
                   'reference': reference, 'reference_mae_pp': scores[reference],
                   'relative_reduction_pct': 100*(scores[reference]-model['mae_pp'])/scores[reference],
                   **{f'model_mae_w{p["window"]}': p['mae_pp'] for p in parts},
                   **{f'reference_mae_w{p["window"]}': p['baselines'][reference]['mae_pp'] for p in parts}}
            for subset in ['original_population', 'history_at_least_10']:
                m = pool([p['subsets'][subset] for p in parts])
                b = pool([p['baselines'][reference]['subsets'][subset] for p in parts])
                row.update({f'{subset}_n': m['n'], f'{subset}_model_mae_pp': m['mae_pp'], f'{subset}_reference_mae_pp': b['mae_pp'],
                            f'{subset}_relative_reduction_pct': 100*(b['mae_pp']-m['mae_pp'])/b['mae_pp']})
            rows.append(row)
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--solo-preparar', action='store_true')
    args = parser.parse_args()
    with Guard() as guard:
        ready = all(frame_path(h).exists() for h in COUNTS) and (OUT/'fase2_i_preparacion.json').exists()
        preparation = json.loads((OUT/'fase2_i_preparacion.json').read_text(encoding='utf-8')) if ready else prepare()
        if args.solo_preparar:
            return
        records = run()
        table = tables(records)
        table.to_csv(OUT/'fase2_i_horizontes_umbrales.csv', index=False)
        original = original_development()
        same = [r for r in records if (r['horizon_hours'], r['min_history']) == (72, 5)]
        checks = {'model_72h_min5_vs_results_development_max_abs_diff': max(
                      abs(r['mae_pp']-original[(SELECTED[r['target']], r['target'], r['window'])]['mae_pp']) for r in same),
                  'baselines_72h_min5_vs_results_development_max_abs_diff': max(
                      abs(r['baselines'][b]['mae_pp']-original[(b, r['target'], r['window'])]['mae_pp']) for r in same for b in BASELINES)}
    write_controls('i', {'preparation': preparation, 'reproduction_of_results_development': checks,
                         'frozen_and_development_unchanged': guard.unchanged, 'scenarios': SCENARIOS})
    print(table[['horizon_hours', 'min_history', 'target', 'model_mae_pp', 'reference', 'reference_mae_pp', 'relative_reduction_pct']]
          .to_string(index=False), '\nreproducción:', checks, flush=True)


if __name__ == '__main__':
    main()
