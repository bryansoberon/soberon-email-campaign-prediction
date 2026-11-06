"""Phase 1 of the round-1 revision: diagnostics from the saved 2024 predictions, without refitting.

Run: .venv\\Scripts\\python.exe -X utf8 -m experiment.revision_1.fase1_diagnosticos
Reads the frozen selection, models and predictions; writes only results/revision_1/fase1_* and FASE1_RESUMEN.md.
"""
from experiment.revision_1.common import *
from experiment.evaluate import interval
from experiment.develop import WINDOWS
import platform
import time

EXTRA = ['history_mean_sent', 'history_clicks_mean', 'history_unsubscribes_mean', 'history_unsubscribes_last5_median']
LEVELS = [.5, .75, .9, .95, .99]
HISTORY_BANDS = [('5-9', 5, 9), ('10-19', 10, 19), ('20-49', 20, 49), ('50+', 50, np.inf)]
HISTORY_DETAIL = [('50-199', 50, 199), ('200-999', 200, 999), ('1000+', 1000, np.inf)]


def topk_weights(score, k):
    """Expected top-k alarm indicator: campaigns tied at the boundary share the remaining alarms equally."""
    score = np.asarray(score, float)
    cut = np.sort(score)[::-1][k-1]
    above, tied = score > cut, score == cut
    weight = above.astype(float)
    weight[tied] = (k-above.sum())/tied.sum()
    return weight


def alarm_metrics(frame, alarm, positive):
    hit = alarm*positive
    out = {}
    for name, num, den in [('recall', hit, positive), ('precision', hit, alarm),
                           ('alarm_rate', alarm, np.ones(len(frame)))]:
        r = ratio_interval(frame, num, den)
        out.update({name: r['estimate'], name+'_lower': r['lower'], name+'_upper': r['upper']})
    out['lift'] = out['precision']/positive.mean()
    # Random alarms at the same rate: expected recall equals the alarm rate, precision the prevalence.
    out['random_recall'] = out['alarm_rate']
    out['random_precision'] = positive.mean()
    return out


def unsubscribe_risk(test, train):
    """R1: identification of high-unsubscribe campaigns, with thresholds fixed from training labels only."""
    y = test.observed_unsubscribes.to_numpy(float)
    scores = {'full_model': test.full_unsubscribes, 'history_only_model': test.history_unsubscribes,
              'last5_median': test.history_unsubscribes_last5_median}
    rows = []
    for q in [.90, .95]:
        tau = float(np.quantile(train.y_unsubscribes, q))
        positive = (y >= tau).astype(float); k = int(positive.sum())
        base = {'positive_definition': f'observed >= training P{q*100:.0f}', 'threshold_pp': tau,
                'training_positive_share': float(train.y_unsubscribes.ge(tau).mean()), 'positive_share': positive.mean()}
        for method, score in scores.items():
            s = score.to_numpy(float)
            rows.append({**base, 'alarm_rule': 'score >= threshold', 'method': method,
                         **alarm_metrics(test, (s >= tau).astype(float), positive)})
            rows.append({**base, 'alarm_rule': 'top k, k = positives', 'method': method,
                         **alarm_metrics(test, topk_weights(s, k), positive)})
    for share in [.01, .05, .10]:
        cut = float(np.quantile(y, 1-share))
        positive = (y >= cut).astype(float); k = int(round(share*len(y)))
        base = {'positive_definition': f'top {share:.0%} observed in 2024', 'threshold_pp': cut,
                'training_positive_share': np.nan, 'positive_share': positive.mean()}
        for method, score in scores.items():
            rows.append({**base, 'alarm_rule': f'top {share:.0%} scores', 'method': method,
                         **alarm_metrics(test, topk_weights(score.to_numpy(float), k), positive)})
    return pd.DataFrame(rows)


def calibration(test):
    """R2.4: mean and median agreement within prediction groups, grouped as in manuscript Figure 4."""
    rows, summary = [], {}
    for target in TARGETS:
        p, y = test['full_'+target], test['observed_'+target]
        frame = pd.DataFrame({'p': p, 'y': y, 'below': y.le(p), 'error': (p-y).abs(),
                              'group': pd.qcut(p, 10, duplicates='drop')})
        for i, (group, g) in enumerate(frame.groupby('group', observed=True), 1):
            rows.append({'target': target, 'group': i, 'prediction_range': str(group), 'n': len(g),
                         'pred_mean': g.p.mean(), 'obs_mean': g.y.mean(), 'obs_median': g.y.median(),
                         'bias_mean': g.p.mean()-g.y.mean(), 'share_obs_at_or_below_pred': g.below.mean(),
                         'mae': g.error.mean()})
        slope, intercept = np.polyfit(p, y, 1)
        summary[target] = {'groups': int(frame.group.nunique()), 'obs_mean_minus_pred_mean_pp': float(y.mean()-p.mean()),
                           'ols_slope_obs_on_pred': float(slope), 'ols_intercept_pp': float(intercept),
                           'share_obs_at_or_below_pred': float(y.le(p).mean()),
                           'reference_share_obs_at_or_below_pred': float(y.le(test['reference_'+target]).mean())}
    return pd.DataFrame(rows), summary


def compare(frame, target):
    """Selected model versus its development-selected baseline, with the primary-analysis interval."""
    y = frame['observed_'+target].to_numpy(float)
    f = frame['full_'+target].to_numpy(float); r = frame['reference_'+target].to_numpy(float)
    ci = interval(frame, np.abs(f-y)-np.abs(r-y))
    mae_f, mae_r = float(np.abs(f-y).mean()), float(np.abs(r-y).mean())
    return {'n': len(frame), 'companies': int(frame.client_id.nunique()), 'obs_mean': y.mean(),
            'pred_mean_full': f.mean(), 'pred_mean_reference': r.mean(), 'bias_full': (f-y).mean(),
            'bias_reference': (r-y).mean(), 'median_residual_full': float(np.median(f-y)),
            'mae_full': mae_f, 'mae_reference': mae_r, 'delta_mae': ci['difference_mae_pp'],
            'delta_lower': ci['lower_pp'], 'delta_upper': ci['upper_pp'],
            'relative_mae_reduction_pct': 100*(mae_r-mae_f)/mae_r if mae_r else np.nan}


def quintiles(train_values, values):
    edges = np.quantile(train_values, [.2, .4, .6, .8])
    labels = pd.cut(values, [-np.inf, *edges, np.inf], labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5']).astype(object)
    return labels, ['Q1', 'Q2', 'Q3', 'Q4', 'Q5'], [float(e) for e in edges]


def observed_bands(train_values, values):
    """Bands of the observed rate with training percentiles as limits; zero is its own band."""
    keep = [(f'P{q*100:g}', float(e)) for q, e in zip(LEVELS, np.quantile(train_values, LEVELS)) if e > 0]
    names = [n for n, _ in keep]
    order = ['0', f'(0, {names[0]}]'] + [f'({a}, {b}]' for a, b in zip(names, names[1:])] + [f'> {names[-1]}']
    labels = pd.cut(values, [0, *[e for _, e in keep], np.inf], labels=order[1:]).astype(object)
    labels[values.eq(0)] = '0'
    return labels, order, dict(keep)


def ranges(values, bands):
    labels = pd.Series(None, index=values.index, dtype=object)
    for name, lo, hi in bands:
        labels[values.between(lo, hi)] = name
    return labels, [name for name, _, _ in bands]


def participation(test, df, train):
    """R2.3: companies of the 2024 test with no campaign in any development fitting or validation set."""
    unseen_ids = set(test.client_id) - set(train.client_id)
    before = set(df.loc[df.campaign_sent_time < FINAL_ORIGIN, 'client_id'])
    dev = df.loc[df.split.eq('development') & df.eligible_primary]
    windows = []
    for start, end in WINDOWS:
        start, end = pd.Timestamp(start, tz='UTC'), pd.Timestamp(end, tz='UTC')
        fit = dev.loc[dev.campaign_sent_time+HORIZON < start]
        valid = dev.loc[(dev.campaign_sent_time >= start) & (dev.campaign_sent_time < end)]
        windows.append({'origin': str(start.date()), 'unseen_in_fit': len(unseen_ids & set(fit.client_id)),
                        'unseen_in_validation': len(unseen_ids & set(valid.client_id))})
    unseen = test.client_id.isin(unseen_ids)
    labels = pd.Series('seen_in_final_training', index=test.index, dtype=object)
    labels[unseen & test.client_id.isin(before)] = 'unseen, campaigns before 2024'
    labels[unseen & ~test.client_id.isin(before)] = 'unseen, first campaign in 2024'
    info = {'definition': 'test companies without rows in the 546,759-campaign final fitting set',
            'seen_companies': int(test.loc[~unseen, 'client_id'].nunique()), 'unseen_companies': len(unseen_ids),
            'unseen_campaigns': int(unseen.sum()), 'unseen_with_campaigns_before_2024': len(unseen_ids & before),
            'unseen_first_campaign_in_2024': len(unseen_ids - before),
            'unseen_with_eligible_development_rows_unmatured_at_final_origin': len(unseen_ids & set(dev.client_id)),
            'participation_in_development_windows': windows}
    return labels, unseen, info


def subgroup_table(test, df, train):
    rows, edges = [], {}

    def add(dimension, target, labels, order):
        for group in order:
            mask = labels.eq(group).to_numpy()
            if mask.any():
                rows.append({'dimension': dimension, 'group': group, 'target': target, **compare(test.loc[mask], target)})
        print('Subgrupos', dimension, target, flush=True)

    size, size_order, edges['company_size_history_mean_sent'] = quintiles(train.history_mean_sent, test.history_mean_sent)
    volume, volume_order, edges['campaign_volume_sent'] = quintiles(train.campaign_subscribers_count, test.campaign_subscribers_count)
    length, length_order = ranges(test.history_n, HISTORY_BANDS)
    detail, detail_order = ranges(test.history_n, HISTORY_DETAIL)
    company, unseen, participation_info = participation(test, df, train)
    for target in TARGETS:
        band, band_order, edges['observed_rate_band_'+target] = observed_bands(train['y_'+target], test['observed_'+target])
        level, level_order, edges['historical_rate_level_'+target] = quintiles(train[f'history_{target}_mean'], test[f'history_{target}_mean'])
        add('observed_rate_band', target, band, band_order)
        add('company_size', target, size, size_order)
        add('campaign_volume', target, volume, volume_order)
        add('historical_rate_level', target, level, level_order)
        add('history_length', target, length, length_order)
        add('history_length_50plus_detail', target, detail, detail_order)
        add('development_participation', target, company, ['seen_in_final_training', 'unseen, campaigns before 2024',
                                                          'unseen, first campaign in 2024'])
        add('development_participation', target, pd.Series(np.where(unseen, 'unseen (all)', ''), index=test.index), ['unseen (all)'])
    return pd.DataFrame(rows), edges, participation_info


def summary_markdown(risk, calib, calib_summary, groups, info):
    pct = lambda v, lo, hi: 'sin alarmas' if np.isnan(v) else f'{100*v:.2f} [{100*lo:.2f}, {100*hi:.2f}]'
    risk_view = pd.DataFrame({
        'Positivo': risk.positive_definition, 'Umbral (pp)': risk.threshold_pp, 'Alarma': risk.alarm_rule,
        'Método': risk.method, 'Positivos (%)': 100*risk.positive_share,
        'Alarmas (%)': [pct(*v) for v in risk[['alarm_rate', 'alarm_rate_lower', 'alarm_rate_upper']].to_numpy()],
        'Recall (%)': [pct(*v) for v in risk[['recall', 'recall_lower', 'recall_upper']].to_numpy()],
        'Precisión (%)': [pct(*v) for v in risk[['precision', 'precision_lower', 'precision_upper']].to_numpy()],
        'Lift': risk.lift})
    calib_view = calib[['target', 'group', 'prediction_range', 'n', 'pred_mean', 'obs_mean', 'obs_median',
                        'bias_mean', 'share_obs_at_or_below_pred']]
    words = lambda r: ('no definido: la referencia no tiene error' if np.isnan(r)
                       else f"{abs(r):.2f} % {'menos' if r > 0 else 'más'} error")
    group_view = pd.DataFrame({
        'Dimensión': groups.dimension, 'Grupo': groups.group, 'Respuesta': groups.target, 'n': groups.n,
        'Empresas': groups.companies, 'MAE modelo': groups.mae_full, 'MAE referencia': groups.mae_reference,
        'Δ MAE [IC 97.5 %]': [f'{d:.6f} [{lo:.6f}, {hi:.6f}]' for d, lo, hi in groups[['delta_mae', 'delta_lower', 'delta_upper']].to_numpy()],
        'Modelo frente a referencia': [words(r) for r in groups.relative_mae_reduction_pct],
        'Sesgo modelo': groups.bias_full, 'Sesgo referencia': groups.bias_reference})
    unseen = groups.loc[groups.group.eq('unseen (all)')].set_index('target')
    lines = [
        '# Fase 1 — diagnósticos sin reentrenar (ronda 1, applsci-4697740)', '',
        'Generado por `experiment/revision_1/fase1_diagnosticos.py` a partir de las predicciones guardadas de 2024. '
        'No se ajustó ni se seleccionó ningún modelo; las huellas de los artefactos congelados son iguales antes y después. '
        'Intervalos: remuestreo empresa × bloques circulares de cuatro semanas de `experiment/evaluate.py`, 2,000 réplicas, '
        'percentiles 1.25 y 98.75 (nominal 97.5 %), sin ajuste por el número de subgrupos. En recall y precisión, el conjunto '
        'de alarmas queda fijado en la muestra completa y se remuestrean las campañas.', '',
        '## (a) R1 — identificación de campañas con bajas altas', '',
        'Los umbrales τ son percentiles de la tasa observada de bajas en las 546,759 campañas del ajuste final '
        '(solo etiquetas de entrenamiento). La alarma usa el mismo τ sobre la predicción. «Top k» ordena por puntuación; '
        'los empates en el borde se reparten por igual. Un ordenamiento al azar tendría recall igual a la tasa de alarmas '
        'y precisión igual a la proporción de positivos (lift 1).', '', markdown(risk_view, 4), '',
        '## (b) R2.4 — calibración por grupos de predicción (agrupación de la Figura 4)', '',
        markdown(calib_view, 4), '',
        '| Respuesta | Media observada − media predicha (pp) | Pendiente MCO obs. ~ pred. | Observado ≤ predicho, modelo | Observado ≤ predicho, referencia |',
        '|---|---|---|---|---|']
    lines += [f"| {t} | {s['obs_mean_minus_pred_mean_pp']:.4f} | {s['ols_slope_obs_on_pred']:.4f} | "
              f"{100*s['share_obs_at_or_below_pred']:.2f} % | {100*s['reference_share_obs_at_or_below_pred']:.2f} % |"
              for t, s in calib_summary.items()]
    lines += [
        '', 'Advertencia para los tramos de tasa observada: agrupar por el resultado observado produce errores negativos '
        'en los tramos altos y positivos en los bajos aun con un predictor calibrado (regresión a la media). '
        'El diagnóstico de calibración es la tabla anterior, agrupada por la predicción.', '',
        '## (b–e) R2.4, R2.6, R2.7 y R2.3 — modelo frente a referencia por subgrupos', '',
        'Δ MAE = MAE del modelo − MAE de la referencia (negativo favorece al modelo). Límites de grupos en '
        '`fase1_resumen.json`. Tamaño de empresa: audiencia media de sus campañas previas maduras (`history_mean_sent`); '
        'volumen: envíos de la campaña; nivel histórico: tasa media previa de la empresa; quintiles del ajuste final.', '',
        markdown(group_view, 4), '',
        '## (e) R2.3 — empresas sin participación en desarrollo', '',
        f"{info['unseen_companies']} empresas y {info['unseen_campaigns']:,} campañas de 2024 no tienen filas en el ajuste final "
        f"ni en ninguna ventana de desarrollo: {info['unseen_first_campaign_in_2024']} aparecen por primera vez en 2024 y "
        f"{info['unseen_with_campaigns_before_2024']} tenían campañas anteriores que no entraron en ajuste ni validación "
        f"({info['unseen_with_eligible_development_rows_unmatured_at_final_origin']} de ellas, solo con filas de los últimos días de 2023 "
        'cuyas respuestas no habían madurado en el origen final).', '']
    for target, label in [('clicks', 'En clics'), ('unsubscribes', 'En bajas')]:
        r = unseen.loc[target]
        lines.append(f"- {label}, {words(r.relative_mae_reduction_pct)} que la referencia "
                     f"({r.mae_full:.4f} vs {r.mae_reference:.4f} pp); Δ = {r.delta_mae:.6f} pp, "
                     f"IC 97.5 % [{r.delta_lower:.6f}, {r.delta_upper:.6f}].")
    return '\n'.join(lines)+'\n'


def main():
    started = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    before = frozen_hashes()
    selection, final = check_frozen()
    df = campaigns(['client_id', 'campaign_sent_time', 'campaign_subscribers_count', 'split', 'eligible_primary',
                    'y_clicks', 'y_unsubscribes', 'history_mean_sent', 'history_clicks_mean', 'history_unsubscribes_mean'])
    train = final_training(df)
    assert len(train) == selection['targets']['clicks']['train_n'] == selection['targets']['unsubscribes']['train_n']
    test = test_frame(EXTRA)
    assert len(test) == final['primary_n'] and test.client_id.nunique() == final['primary_companies']
    checks = {}
    for target in TARGETS:
        y = test['observed_'+target]
        diff = ((test['full_'+target]-y).abs()-(test['reference_'+target]-y).abs()).to_numpy()
        published = final['targets'][target]['comparison']
        again, ratio = interval(test, diff), ratio_interval(test, diff, np.ones(len(test)))
        checks[target] = {'published': [published['lower_pp'], published['upper_pp']],
                          'evaluate_interval': [again['lower_pp'], again['upper_pp']],
                          'ratio_interval': [ratio['lower'], ratio['upper']]}
        assert np.allclose(checks[target]['published'], checks[target]['evaluate_interval'], rtol=0, atol=1e-12)
        assert np.allclose(checks[target]['published'], checks[target]['ratio_interval'], rtol=0, atol=1e-12)
    print('Intervalos publicados reproducidos con ambas funciones', flush=True)
    risk = unsubscribe_risk(test, train)
    print('Riesgo de bajas listo', flush=True)
    calib, calib_summary = calibration(test)
    groups, edges, info = subgroup_table(test, df, train)
    risk.to_csv(OUT/'fase1_a_riesgo_bajas.csv', index=False)
    calib.to_csv(OUT/'fase1_b_calibracion.csv', index=False)
    groups.to_csv(OUT/'fase1_subgrupos.csv', index=False)
    (OUT/'FASE1_RESUMEN.md').write_text(summary_markdown(risk, calib, calib_summary, groups, info), encoding='utf-8')
    after = frozen_hashes()
    assert after == before, 'Un artefacto congelado cambió durante la fase 1'
    save_json(OUT/'fase1_resumen.json', {
        'scope': 'Round-1 phase 1: diagnostics from saved 2024 predictions; no fitting, selection or threshold tuning on 2024.',
        'interval_method': 'experiment.evaluate.interval resampling: companies x circular 4-week blocks, 2,000 replicates, '
                           '1.25/98.75 percentiles (nominal 97.5%), seed 20261024+4; ratios keep each row numerator/denominator.',
        'final_training_n': len(train), 'test_n': len(test), 'test_companies': int(test.client_id.nunique()),
        'unsubscribe_thresholds_training_pp': {f'P{q*100:.0f}': float(np.quantile(train.y_unsubscribes, q)) for q in [.9, .95]},
        'group_edges': edges, 'calibration_summary': calib_summary, 'development_participation': info,
        'published_interval_reproduction': checks, 'frozen_sha256_before': before, 'frozen_sha256_unchanged_after': after == before,
        'environment': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
                        'platform': platform.platform()},
        'runtime_seconds': time.perf_counter()-started})
    print('Fase 1 guardada en', OUT, flush=True)


if __name__ == '__main__':
    main()
