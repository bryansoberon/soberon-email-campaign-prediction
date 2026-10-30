"""Export the numerical cells of manuscript Tables 4--7 and Figure 2."""
from pathlib import Path
import argparse
import csv
import json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--study', required=True, type=Path)
    root = p.parse_args().study.resolve()
    final = json.loads((root / 'results/final_evaluation.json').read_text(encoding='utf-8'))
    selected = json.loads((root / 'results/selection.json').read_text(encoding='utf-8'))
    out = root / 'review_outputs/article_tables'
    out.mkdir(parents=True, exist_ok=True)

    def table(name, rows):
        with (out / name).open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    order = ['ridge_1', 'ridge_100', 'rf_30', 'rf_100', 'lgbm_15', 'lgbm_31', 'global_mean', 'global_median', 'company_mean', 'last5_median', 'last', 'zero']
    table('table04_development.csv', [{'configuration': c, **{t: f"{selected['development_scores'][t][c]:.4f}" for t in ['clicks', 'unsubscribes']}} for c in order])
    rows = []; ablation = []; resources = []; intervals = []
    for target, item in final['targets'].items():
        for kind in ['full', 'reference']:
            m = item['metrics'][kind]
            rows.append({'outcome': target, 'procedure': item['ml'] if kind == 'full' else item['reference'],
                         **{key: f'{m[key]:.4f}' for key in ['mae_pp', 'rmse_pp', 'bias_pp']}})
        ci = item['message_ablation']
        ablation.append({'outcome': target, 'history_only_mae_pp': f"{item['metrics']['history']['mae_pp']:.6f}",
                         'full_minus_history_pp': f"{ci['difference_mae_pp']:.6f}",
                         'lower_97_5_pp': f"{ci['lower_pp']:.6f}", 'upper_97_5_pp': f"{ci['upper_pp']:.6f}"})
        fit = selected['targets'][target]['full']
        resources.append({'outcome': target, 'model': item['ml'], 'fit_seconds': f"{fit['fit_seconds']:.3f}",
                          'test_prediction_seconds': f"{final['prediction_seconds'][target + '_full']:.3f}",
                          'peak_process_rss_mib': f"{fit['peak_process_rss_mb']:.2f}"})
        for ci in [item['comparison'], *item['block_sensitivity']]:
            intervals.append({'outcome': target, **{key: ci[key] for key in ['block_weeks', 'difference_mae_pp', 'lower_pp', 'upper_pp', 'ci_level', 'repeats']}})
    table('table05_test_metrics.csv', rows)
    table('table06_message_ablation.csv', ablation)
    table('table07_recorded_resources.csv', resources)
    table('figure02_paired_intervals.csv', intervals)
    print('Exported Tables 4--7 and Figure 2 numerical data. Resource values describe the archived run.')


if __name__ == '__main__':
    main()
