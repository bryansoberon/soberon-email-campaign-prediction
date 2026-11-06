"""Phase 2 (h), R2.5: representations of the structural message attributes, selected configuration, development only.

Run: .venv\\Scripts\\python.exe -X utf8 -m experiment.revision_1.fase2_atributos
Writes results/revision_1/fase2_h_atributos.csv, fase2_h_controles.json and one cached JSON per fit.
"""
from experiment.revision_1.desarrollo import *

RAW = ROOT/'data/raw/elegibilidad/SendGuard900K.csv'
LOCATIONS = ['sender_email', 'subject', 'html_body', 'text_body']
PRESENCE = {'has_images': 'message_images_count', 'has_embedded_images': 'message_embedded_images_count',
            'has_embedded_files': 'message_embedded_files_count', 'has_links': 'message_links_count',
            'has_personalization': 'message_personalization_tags_count',
            'has_subject_personalization': 'message_personalization_tags_in_subject_count'}


def transformed(df):
    """log1p of the 12 attributes, densities per KiB of content, personalization shares by location and presence flags.

    Shares divide by the sum of the four location counts, which exceeds the total tag count in about 9% of campaigns."""
    out = pd.DataFrame({'log1p_'+c: np.log1p(df[c]) for c in MESSAGE}, index=df.index)
    size = df.message_content_size.to_numpy(float)
    for name, column in [('links', 'message_links_count'), ('images', 'message_images_count'),
                         ('embedded_images', 'message_embedded_images_count')]:
        out[name+'_per_kib'] = np.where(size > 0, 1024*df[column].to_numpy(float)/np.maximum(size, 1), 0.)
    located = df[[f'message_personalization_tags_in_{place}_count' for place in LOCATIONS]].to_numpy(float)
    total = located.sum(axis=1)
    for i, place in enumerate(LOCATIONS):
        out['personalization_share_'+place] = np.where(total > 0, located[:, i]/np.maximum(total, 1), 0.)
    for name, column in PRESENCE.items():
        out[name] = (df[column] > 0).astype(float)
    return out


def dictionary_check():
    """Confirms that the source has no subject or body text: header names and non-numeric columns of the raw file."""
    sample = pd.read_csv(RAW, nrows=20000)
    words = ['subject', 'body', 'text', 'html', 'content']
    return {'raw_columns': len(sample.columns),
            'non_numeric_columns': [c for c in sample.columns if not pd.api.types.is_numeric_dtype(sample[c])],
            'columns_mentioning_subject_body_text_html_content': [c for c in sample.columns if any(w in c.lower() for w in words)],
            'zenodo_record': 'https://zenodo.org/records/17985618, version 1.0.0, consulted 2026-11-05. Data summary: '
                             '"No personal data, no message bodies, no recipient-level records"; overview: "without exposing '
                             'message content". The only free-text field, client_tag_name, is a manual client label.',
            'protocol_exclusions': '05_plan/PROTOCOLO_EXPERIMENTAL_V1.md excludes blocked links, moderation, manual tags, '
                                   'domains, identifiers as numbers and current-campaign responses.'}


def main():
    with Guard() as guard:
        df = development()
        extra = transformed(df)
        df = pd.concat([df, extra], axis=1)
        sets = {'history_only': HISTORY, 'history_plus_original_12': FEATURES,
                'history_plus_transformed': list(extra.columns)+HISTORY}
        fits = []
        for window, train, valid in splits(df):
            for target in TARGETS:
                name = SELECTED[target]
                for label, features in sets.items():
                    def compute():
                        pred, resources = fit_predict(build('lgbm', ORIGINAL[name][1]), train, valid, target, features)
                        return {'train_n': len(train), **score(valid, target, pred), **resources}
                    fits.append(cached(f'h/{target}_{label}_w{window}', {'analysis': 'h', 'target': target, 'features': label,
                                       'feature_columns': features, 'window': window, 'config': name}, compute))
                    print('h', target, label, 'ventana', window, 'MAE', round(fits[-1]['mae_pp'], 6), flush=True)
        original = original_development()
        rows, checks = [], {}
        for target in TARGETS:
            pooled = {}
            for label in sets:
                parts = sorted([f for f in fits if f['target'] == target and f['features'] == label], key=lambda f: f['window'])
                pooled[label] = pool(parts)['mae_pp']
                rows.append({'target': target, 'features': label, 'feature_count': len(sets[label]), **pool(parts),
                             **{f'mae_w{p["window"]}': p['mae_pp'] for p in parts},
                             'fit_seconds': sum(p['fit_seconds'] for p in parts)})
            for row in rows[-len(sets):]:
                row['delta_vs_history_only_pp'] = row['mae_pp']-pooled['history_only']
                row['delta_vs_original_12_pp'] = row['mae_pp']-pooled['history_plus_original_12']
            same = [f for f in fits if f['target'] == target and f['features'] == 'history_plus_original_12']
            checks[target] = {'original_12_vs_results_development_max_abs_diff':
                              max(abs(p['mae_pp']-original[(SELECTED[target], target, p['window'])]['mae_pp']) for p in same)}
        pd.DataFrame(rows).to_csv(OUT/'fase2_h_atributos.csv', index=False)
    write_controls('h', {'reproduction_of_results_development': checks, 'frozen_and_development_unchanged': guard.unchanged,
                         'feature_sets': sets, 'dictionary_check': dictionary_check()})
    print('h guardado; reproducción:', checks, flush=True)


if __name__ == '__main__':
    main()
