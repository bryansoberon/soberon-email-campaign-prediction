"""Phase 2 (f), R2.2: expanded hyperparameter search with an equal budget per family, development windows only.

Run: .venv\\Scripts\\python.exe -X utf8 -m experiment.revision_1.fase2_busqueda --familias lgbm ridge rf
Families can be run separately; the tables are rebuilt from every cached fit. Writes fase2_f_* in results/revision_1/.
"""
from experiment.revision_1.desarrollo import *
from experiment.models import make_model
import argparse
import itertools

DRAWS = 20
SEEDS = {'ridge': SEED+101, 'rf': SEED+102, 'lgbm': SEED+103}
GRIDS = {
    'rf': {'n_estimators': [100, 160, 300], 'max_depth': [8, 14, 20, None], 'min_samples_leaf': [10, 30, 100, 300],
           'max_features': [.5, .8, 1.], 'max_samples': [.5, .7, 1.]},
    'lgbm': {'num_leaves': [7, 15, 31, 63, 127], 'learning_rate': [.02, .04, .08], 'n_estimators': [200, 400, 800],
             'min_child_samples': [20, 100, 300], 'reg_lambda': [0., 1., 10.], 'colsample_bytree': [.7, 1.]}}
DEFAULTS = {'colsample_bytree': 1.}
FAMILY_LOSS = {'ridge': 'squared error', 'rf': 'squared error', 'lgbm': 'absolute error (regression_l1)'}


def sample():
    """Six original configurations plus 20 draws per family. Grid draws are without replacement and exclude the originals."""
    configs = {name: (family, params, 'original') for name, (family, params) in ORIGINAL.items()}
    rng = np.random.default_rng(SEEDS['ridge'])
    for i, alpha in enumerate(10**rng.uniform(-3, 4, DRAWS), 1):
        configs[f'ridge_r{i:02d}'] = ('ridge', {'alpha': float(alpha)}, 'random')
    for family, grid in GRIDS.items():
        originals = [p for f, p in ORIGINAL.values() if f == family]
        combos = [dict(zip(grid, values)) for values in itertools.product(*grid.values())]
        combos = [c for c in combos if not any(all(p.get(k, DEFAULTS.get(k)) == v for k, v in c.items()) for p in originals)]
        rng = np.random.default_rng(SEEDS[family])
        for i, j in enumerate(rng.choice(len(combos), DRAWS, replace=False), 1):
            extra = {'objective': 'regression_l1'} if family == 'lgbm' else {}
            configs[f'{family}_r{i:02d}'] = (family, {**extra, **combos[int(j)]}, 'random')
    return configs


def run(families, configs):
    parts = splits(development())
    for window, train, valid in parts:
        for target in TARGETS:
            cached(f'f/referencias_{target}_w{window}', {'analysis': 'f', 'target': target, 'window': window},
                   lambda: {'baselines': baselines(train, valid, target)})
    for family in families:
        for name, (fam, params, origin) in configs.items():
            if fam != family:
                continue
            for window, train, valid in parts:
                for target in TARGETS:
                    def compute():
                        model = make_model(name) if origin == 'original' else build(family, params)
                        pred, resources = fit_predict(model, train, valid, target, FEATURES)
                        return {'train_n': len(train), **score(valid, target, pred), **resources}
                    row = cached(f'f/{name}_{target}_w{window}', {'analysis': 'f', 'family': family, 'config': name,
                                 'params': params, 'target': target, 'window': window}, compute)
                    print('f', name, target, 'ventana', window, 'MAE', round(row['mae_pp'], 6),
                          f"{row['fit_seconds']:.1f} s", flush=True)


def tables(configs):
    """Aggregates every completed configuration (all three windows) found in the cache."""
    rows, original = [], original_development()
    for name, (family, params, origin) in configs.items():
        for target in TARGETS:
            files = [CACHE/'f'/f'{name}_{target}_w{w}.json' for w in (1, 2, 3)]
            if not all(f.exists() for f in files):
                continue
            parts = [json.loads(f.read_text(encoding='utf-8')) for f in files]
            row = {'family': family, 'config': name, 'origin': origin, 'params': json.dumps(params), 'target': target,
                   **pool(parts), **{f'mae_w{p["window"]}': p['mae_pp'] for p in parts},
                   'fit_seconds_total': sum(p['fit_seconds'] for p in parts),
                   'fit_seconds_max': max(p['fit_seconds'] for p in parts),
                   'predict_seconds_total': sum(p['predict_seconds'] for p in parts),
                   'peak_process_rss_mb_max': max(p['peak_process_rss_mb'] for p in parts)}
            if origin == 'original':
                row['max_abs_diff_vs_results_development'] = max(
                    abs(p['mae_pp']-original[(name, target, p['window'])]['mae_pp']) for p in parts)
            rows.append(row)
    table = pd.DataFrame(rows)
    summary, checks = [], {}
    for target in TARGETS:
        refs = [json.loads((CACHE/'f'/f'referencias_{target}_w{w}.json').read_text(encoding='utf-8')) for w in (1, 2, 3)]
        reference, ref_scores = best_baseline([r['baselines'] for r in refs], target)
        checks[target] = {'baselines_vs_results_development_max_abs_diff': max(
            abs(r['baselines'][b]['mae_pp']-original[(b, target, r['window'])]['mae_pp']) for r in refs for b in BASELINES)}
        part = table.loc[table.target.eq(target)] if len(table) else table
        for family in ['ridge', 'rf', 'lgbm']:
            fam = part.loc[part.family.eq(family)] if len(part) else part
            if fam.empty or not fam.origin.eq('original').any():
                continue
            best = fam.sort_values(['mae_pp', 'config']).iloc[0]
            best_original = fam.loc[fam.origin.eq('original')].sort_values(['mae_pp', 'config']).iloc[0]
            summary.append({'target': target, 'family': family, 'loss': FAMILY_LOSS[family],
                            'configs_completed': len(fam), 'best_original': best_original.config,
                            'best_original_mae_pp': best_original.mae_pp, 'best_expanded': best.config,
                            'best_expanded_params': best.params, 'best_expanded_mae_pp': best.mae_pp,
                            'improvement_over_original_pp': best_original.mae_pp-best.mae_pp,
                            'reference': reference, 'reference_mae_pp': ref_scores[reference],
                            'beats_reference': bool(best.mae_pp < ref_scores[reference]),
                            'relative_reduction_vs_reference_pct': 100*(ref_scores[reference]-best.mae_pp)/ref_scores[reference],
                            'fit_seconds_total': fam.fit_seconds_total.sum(), 'fit_seconds_median_per_window':
                            float(np.median([json.loads((CACHE/'f'/f'{c}_{target}_w{w}.json').read_text(encoding='utf-8'))['fit_seconds']
                                             for c in fam.config for w in (1, 2, 3)])),
                            'peak_process_rss_mb_max': fam.peak_process_rss_mb_max.max()})
    return table, pd.DataFrame(summary), checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--familias', nargs='+', choices=['lgbm', 'ridge', 'rf'], default=['lgbm', 'ridge', 'rf'])
    args = parser.parse_args()
    configs = sample()
    save_json(OUT/'fase2_f_configuraciones.json', {
        'draws_per_family': DRAWS, 'seeds': SEEDS, 'grids': GRIDS, 'ridge_alpha': 'log-uniform on [1e-3, 1e4]',
        'losses': FAMILY_LOSS, 'configs': {n: {'family': f, 'origin': o, 'params': p} for n, (f, p, o) in configs.items()}})
    with Guard() as guard:
        run(args.familias, configs)
        table, summary, checks = tables(configs)
        table.to_csv(OUT/'fase2_f_busqueda.csv', index=False)
        summary.to_csv(OUT/'fase2_f_resumen_familias.csv', index=False)
    column = 'max_abs_diff_vs_results_development'
    originals = (table.loc[table.origin.eq('original'), ['config', 'target', column]].to_dict('records')
                 if column in table else [])
    write_controls('f', {'reproduction_of_results_development': {'baselines': checks, 'original_configs': originals},
        'frozen_and_development_unchanged': guard.unchanged, 'families_run_in_last_call': args.familias,
        'completed_configs': int(len(table))})
    print(summary.to_string(index=False), flush=True)


if __name__ == '__main__':
    main()
