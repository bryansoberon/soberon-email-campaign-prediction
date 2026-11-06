"""Phase 2 (g), R2.4 and R1: LightGBM fitting losses with the selected configuration, development windows only.

Run: .venv\\Scripts\\python.exe -X utf8 -m experiment.revision_1.fase2_perdidas
Writes results/revision_1/fase2_g_*.csv, fase2_g_controles.json and one cached JSON per fit.
"""
from experiment.revision_1.desarrollo import *

LOSSES = {'l1': {'objective': 'regression_l1'}, 'l2': {'objective': 'regression'}, 'huber': {'objective': 'huber'},
          'tweedie': {'objective': 'tweedie'}, 'quantile_0.6': {'objective': 'quantile', 'alpha': .6},
          'quantile_0.7': {'objective': 'quantile', 'alpha': .7}, 'quantile_0.8': {'objective': 'quantile', 'alpha': .8}}


def run():
    fits, refs = [], []
    for window, train, valid in splits(development()):
        for target in TARGETS:
            name = SELECTED[target]
            for loss, extra in LOSSES.items():
                params = {**ORIGINAL[name][1], **extra}

                def compute():
                    pred, resources = fit_predict(build('lgbm', params), train, valid, target, FEATURES)
                    path = LOCAL/'g'/f'{target}_{loss}_w{window}.parquet'
                    path.parent.mkdir(parents=True, exist_ok=True)
                    pd.DataFrame({'campaign_id': valid.campaign_id.to_numpy(), 'prediction': pred}).to_parquet(path, index=False)
                    row = {'train_n': len(train), **score(valid, target, pred), 'tails': tails(train, valid, target, pred), **resources}
                    if target == 'unsubscribes':
                        row['risk'] = risk(train, valid, pred)
                    return row
                fits.append(cached(f'g/{target}_{loss}_w{window}', {'analysis': 'g', 'target': target, 'loss': loss,
                                   'window': window, 'config': name, 'params': params}, compute))
                print('g', target, loss, 'ventana', window, 'MAE', round(fits[-1]['mae_pp'], 6), flush=True)

            def compute_refs():
                row = {'baselines': baselines(train, valid, target, with_tails=True)}
                if target == 'unsubscribes':
                    row['risk_last5_median'] = risk(train, valid, valid.history_unsubscribes_last5_median)
                return row
            refs.append(cached(f'g/{target}_referencias_w{window}', {'analysis': 'g', 'target': target, 'window': window},
                               compute_refs))
    return fits, refs


def error_rows(target, method, parts):
    """Pooled and per-window errors, with the high-rate tails of each window's training labels."""
    out = []
    for scope, chosen in [('pooled', parts)] + [(f'window_{w}', [p]) for w, p in enumerate(parts, 1)]:
        row = {'target': target, 'method': method, 'scope': scope, **pool(chosen)}
        for level in ['P90', 'P95', 'P99']:
            tail = pool([p['tails'][level] for p in chosen])
            row.update({f'{level}_n': tail['n'], f'{level}_mae_pp': tail.get('mae_pp', np.nan),
                        f'{level}_bias_pp': tail.get('bias_pp', np.nan)})
        if 'fit_seconds' in parts[0]:
            row['fit_seconds'] = sum(p['fit_seconds'] for p in chosen)
        out.append(row)
    return out


def risk_rows(method, parts):
    out = []
    for scope, chosen in [('pooled', parts)] + [(f'window_{w}', [p]) for w, p in enumerate(parts, 1)]:
        for level, values in pool_risk(chosen).items():
            out.append({'method': method, 'scope': scope, 'positive_definition': f'observed >= training {level}', **values})
    return out


def main():
    with Guard() as guard:
        fits, refs = run()
        original = original_development()
        errors, risks, checks = [], [], {}
        for target in TARGETS:
            by_window = lambda rows: sorted([r for r in rows if r['target'] == target], key=lambda r: r['window'])
            for loss in LOSSES:
                parts = by_window([f for f in fits if f['loss'] == loss])
                errors += error_rows(target, 'lightgbm_'+loss, parts)
                if target == 'unsubscribes':
                    risks += risk_rows('lightgbm_'+loss, [p['risk'] for p in parts])
            ref = by_window(refs)
            reference = DEVELOPMENT_SELECTED_BASELINE[target]
            errors += error_rows(target, 'baseline_'+reference, [r['baselines'][reference] for r in ref])
            if target == 'unsubscribes':
                risks += risk_rows('rule_last5_median', [r['risk_last5_median'] for r in ref])
            l1 = by_window([f for f in fits if f['loss'] == 'l1'])
            checks[target] = {
                'l1_vs_original_max_abs_diff': max(abs(p['mae_pp']-original[(SELECTED[target], target, p['window'])]['mae_pp']) for p in l1),
                'baselines_vs_original_max_abs_diff': max(abs(r['baselines'][b]['mae_pp']-original[(b, target, r['window'])]['mae_pp'])
                                                           for r in ref for b in BASELINES)}
        pd.DataFrame(errors).to_csv(OUT/'fase2_g_perdidas.csv', index=False)
        pd.DataFrame(risks).to_csv(OUT/'fase2_g_riesgo_bajas.csv', index=False)
    write_controls('g', {'reproduction_of_results_development': checks, 'frozen_and_development_unchanged': guard.unchanged,
                         'losses': LOSSES, 'huber_note': 'LightGBM default transition parameter (alpha = 0.9 pp)',
                         'tweedie_note': 'LightGBM default variance power 1.5, log link'})
    print('g guardado; reproducción:', checks, flush=True)


if __name__ == '__main__':
    main()
