"""Recompute archived metrics and, optionally, paired intervals without fitting."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import math
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--study', type=Path, required=True)
    p.add_argument('--intervals', action='store_true')
    args = p.parse_args()
    root = args.study.resolve()
    sys.path.insert(0, str(root))
    import numpy as np
    import pandas as pd
    from experiment.core import metrics
    from experiment.evaluate import interval
    final = json.loads((root / 'results/final_evaluation.json').read_text(encoding='utf-8'))
    selection = json.loads((root / 'results/selection.json').read_text(encoding='utf-8'))
    development = json.loads((root / 'results/development_summary.json').read_text(encoding='utf-8'))
    pred = pd.read_parquet(root / 'data/processed/test_predictions.parquet')
    monthly = pd.read_csv(root / 'results/monthly_test.csv')
    checks = []

    def equal(name, actual, expected, tolerance=1e-10):
        if not math.isclose(float(actual), float(expected), abs_tol=tolerance, rel_tol=1e-10):
            raise AssertionError((name, actual, expected))
        checks.append(name)

    equal('primary_campaigns', len(pred), final['primary_n'], 0)
    equal('primary_companies', pred.client_id.nunique(), final['primary_companies'], 0)
    months = pred.campaign_sent_time.dt.strftime('%Y-%m')
    group_rows = []
    for target, item in final['targets'].items():
        y = pred['observed_' + target].to_numpy(float)
        for kind in ['full', 'history', 'reference', 'product']:
            prediction = pred[kind + '_' + target].to_numpy(float)
            calculated = metrics(y, prediction, pred.campaign_subscribers_count, pred.client_id)
            for key, value in calculated.items():
                equal(f'{target}/{kind}/{key}', value, item['metrics'][kind][key])
            for month in sorted(months.unique()):
                mask = months.eq(month).to_numpy()
                row = monthly.loc[(monthly.target == target) & (monthly.method == kind) & (monthly.month == month)]
                if len(row) != 1:
                    raise AssertionError(('monthly row count', target, kind, month))
                for key, value in metrics(y[mask], prediction[mask]).items():
                    equal(f'{target}/{kind}/{month}/{key}', value, row.iloc[0][key])
        full_loss = np.abs(pred['full_' + target].to_numpy() - y)
        reference_loss = np.abs(pred['reference_' + target].to_numpy() - y)
        history_loss = np.abs(pred['history_' + target].to_numpy() - y)
        equal(target + '/paired_mean', np.mean(full_loss - reference_loss), item['comparison']['difference_mae_pp'])
        equal(target + '/ablation_mean', np.mean(full_loss - history_loss), item['message_ablation']['difference_mae_pp'])
        equal(target + '/relative_reduction', 100 * (reference_loss.mean() - full_loss.mean()) / reference_loss.mean(), item['relative_mae_reduction_pct'])
        for candidate, score in selection['development_scores'][target].items():
            rows = [r for r in development['rows'] if r['target'] == target and r['candidate'] == candidate]
            if len(rows) != 3:
                raise AssertionError(('three development windows', target, candidate))
            equal(target + '/development/' + candidate,
                  sum(r['mae_pp'] * r['n'] for r in rows) / sum(r['n'] for r in rows), score)
        values = pred['full_' + target]
        bins = pd.Series(0, index=values.index) if values.nunique() < 2 else pd.qcut(values, 10, duplicates='drop')
        g = pd.DataFrame({'prediction': values, 'observed': y, 'bin': bins}).groupby('bin', observed=True).agg(
            prediction=('prediction', 'mean'), observed=('observed', 'mean'), n=('prediction', 'size')).reset_index(drop=True)
        for index, row in g.iterrows():
            group_rows.append({'prediction': row.prediction, 'observed': row.observed, 'n': int(row.n), 'target': target, 'group': index + 1})
        if args.intervals:
            pairs = [(item['comparison'], full_loss - reference_loss), (item['message_ablation'], full_loss - history_loss)]
            pairs += [(r, full_loss - reference_loss) for r in item['block_sensitivity']]
            for reference, difference in pairs:
                result = interval(pred, difference, reference['block_weeks'], reference['repeats'])
                for key in ['difference_mae_pp', 'lower_pp', 'upper_pp', 'companies', 'calendar_weeks']:
                    equal(f"{target}/interval/{reference['block_weeks']}/{len(checks)}/{key}", result[key], reference[key])
    groups = pd.DataFrame(group_rows)
    archived_groups = root / 'results/figures_tesis/diagnostic_groups.csv'
    if archived_groups.exists():
        expected = pd.read_csv(archived_groups)
        if not groups[['target', 'group', 'n']].equals(expected[['target', 'group', 'n']]):
            raise AssertionError('Prediction-group membership/counts differ.')
        for name in ['prediction', 'observed']:
            for index in range(len(groups)):
                equal(f'prediction_groups/{name}/{index}', groups.iloc[index][name], expected.iloc[index][name])
    else:
        archived_groups.parent.mkdir(parents=True, exist_ok=True)
        groups.to_csv(archived_groups, index=False)
    out = root / 'review_outputs'
    out.mkdir(parents=True, exist_ok=True)
    groups.to_csv(out / 'recomputed_prediction_groups.csv', index=False)
    report = {'status': 'PASS', 'finished_utc': datetime.now(timezone.utc).isoformat(),
              'numeric_checks': len(checks), 'checks': checks, 'bootstrap_intervals_recomputed': args.intervals,
              'model_fitting': False, 'principal_campaigns': len(pred),
              'scope': 'Archived principal-test predictions, monthly results, development arithmetic and prediction groups; limited-history observations require source-data reproduction.'}
    (out / 'saved_results_verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'PASS: {len(checks)} numerical checks; bootstrap intervals recomputed: {args.intervals}.')


if __name__ == '__main__':
    main()
