from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261024
HORIZON = pd.Timedelta(hours=72)
TARGETS = {'clicks': 'campaign_unique_clicks_count_4320', 'unsubscribes': 'campaign_resigned_count_4320'}
MESSAGE = ['message_content_size', 'message_images_count', 'message_embedded_images_count',
           'message_embedded_images_size', 'message_embedded_files_count', 'message_embedded_files_size',
           'message_links_count', 'message_personalization_tags_count',
           'message_personalization_tags_in_sender_email_count', 'message_personalization_tags_in_subject_count',
           'message_personalization_tags_in_html_body_count', 'message_personalization_tags_in_text_body_count']
BASE = ['client_id', 'campaign_id', 'campaign_sent_time', 'campaign_test_type', 'campaign_subscribers_count']
REQUIRED = BASE + MESSAGE + list(TARGETS.values())
HISTORY = ['history_n', 'history_days_since_last', 'history_mean_sent'] + [
    f'history_{t}_{kind}' for t in TARGETS for kind in ['mean', 'weighted', 'last', 'last5_mean', 'last5_median']]
FEATURES = MESSAGE + HISTORY


def sha256(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def save_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False, default=str), encoding='utf-8')


def read_campaigns(source):
    df = pd.read_csv(source, usecols=lambda c: c in REQUIRED,
                     dtype={'client_id': 'str', 'campaign_id': 'str', 'campaign_test_type': 'str'})
    missing = set(REQUIRED) - set(df)
    if missing:
        raise ValueError('Faltan columnas: ' + ', '.join(sorted(missing)))
    raw_dates = df['campaign_sent_time'].astype('str')
    has_timezone = raw_dates.str.contains(r'(?:Z|[+-]\d{2}:?\d{2})$', regex=True)
    df['campaign_sent_time'] = pd.to_datetime(raw_dates.where(has_timezone), utc=True, errors='coerce', format='mixed')
    for c in MESSAGE + ['campaign_subscribers_count'] + list(TARGETS.values()):
        df[c] = pd.to_numeric(df[c], errors='coerce')
    return df


def clean_campaigns(df, end=None):
    df = df.copy()
    flow = [{'step': 'archivo', 'rows': len(df), 'excluded': 0}]
    rules = [
        ('ids_y_fecha_validos', df.client_id.notna() & df.campaign_id.notna() & df.campaign_sent_time.notna()
         & df.client_id.astype(str).str.strip().ne('') & df.campaign_id.astype(str).str.strip().ne('')),
        ('id_no_repetido', ~df.campaign_id.duplicated(keep=False)),
        ('sin_pruebas_ab_optimizer', df.campaign_test_type.eq('0')),
        ('envios_positivos', np.isfinite(df.campaign_subscribers_count) & df.campaign_subscribers_count.gt(0)),
        ('respuestas_validas', np.logical_and.reduce([df[c].ge(0) & df[c].le(df.campaign_subscribers_count)
                                                      & np.isfinite(df[c]) for c in TARGETS.values()])),
        ('atributos_validos', np.isfinite(df[MESSAGE]).all(axis=1) & df[MESSAGE].ge(0).all(axis=1)),
    ]
    if end is not None:
        rules.append(('ventana_final_72h', df.campaign_sent_time.lt(pd.Timestamp(end))))
    keep = pd.Series(True, index=df.index)
    for name, valid in rules:
        before = int(keep.sum())
        keep &= valid
        flow.append({'step': name, 'rows': int(keep.sum()), 'excluded': before - int(keep.sum())})
    df = df.loc[keep].copy().sort_values(['client_id', 'campaign_sent_time', 'campaign_id']).reset_index(drop=True)
    for target, column in TARGETS.items():
        df['y_' + target] = 100 * df[column] / df.campaign_subscribers_count
    return df, flow


def history_features(history, queries):
    """Only rows whose 72h window matured strictly before each query are used."""
    values_out = np.zeros((len(queries), len(HISTORY)))
    columns = {name: i for i, name in enumerate(HISTORY)}
    values_out[:, columns['history_days_since_last']] = 3650.
    groups = {str(k): g.sort_values(['campaign_sent_time', 'campaign_id']) for k, g in history.groupby('client_id', sort=False)}
    for client, q in queries.groupby('client_id', sort=False):
        h = groups.get(str(client))
        if h is None or h.empty:
            continue
        # Unit conversion is explicit: pandas can use microseconds or nanoseconds.
        ht = h.campaign_sent_time.to_numpy(dtype='datetime64[ns]').astype('int64')
        qt = q.campaign_sent_time.to_numpy(dtype='datetime64[ns]').astype('int64')
        n = np.searchsorted(ht, qt - HORIZON.value, side='left')
        seen = n > 0
        ix = queries.index.get_indexer(q.index)
        def assign(name, value):
            values_out[ix, columns[name]] = value
        assign('history_n', n)
        sent = h.campaign_subscribers_count.to_numpy(float)
        cs = np.r_[0., np.cumsum(sent)]
        assign('history_mean_sent', np.divide(cs[n], n, out=np.zeros(len(n)), where=seen))
        days = np.where(seen, (qt - ht[np.maximum(n-1, 0)]) / (86400 * 1e9), 3650.)
        assign('history_days_since_last', days)
        lo = np.maximum(n - 5, 0)
        for target in TARGETS:
            values = h['y_' + target].to_numpy(float)
            accum = np.r_[0., np.cumsum(values)]
            weighted = np.r_[0., np.cumsum(values * sent)]
            prefix = 'history_' + target + '_'
            assign(prefix + 'mean', np.divide(accum[n], n, out=np.zeros(len(n)), where=seen))
            assign(prefix + 'weighted', np.divide(weighted[n], cs[n], out=np.zeros(len(n)), where=seen))
            assign(prefix + 'last', np.where(seen, values[np.maximum(n-1, 0)], 0.))
            assign(prefix + 'last5_mean', np.divide(accum[n]-accum[lo], n-lo, out=np.zeros(len(n)), where=seen))
            # All preceding history is mature. The rolling median is indexed at the last mature row.
            med = pd.Series(values).rolling(5, min_periods=1).median().to_numpy()
            assign(prefix + 'last5_median', np.where(seen, med[np.maximum(n-1, 0)], 0.))
    return pd.DataFrame(values_out, index=queries.index, columns=HISTORY)


def metrics(y, prediction, sent=None, clients=None):
    y, p = np.asarray(y, float), np.asarray(prediction, float)
    if not len(y):
        return {'n': 0}
    error = p-y
    out = {'n': len(y), 'mae_pp': float(np.mean(abs(error))), 'rmse_pp': float(np.sqrt(np.mean(error**2))),
           'bias_pp': float(np.mean(error))}
    if sent is not None:
        out['weighted_mae_pp'] = float(np.average(abs(error), weights=sent))
    if clients is not None:
        out['company_macro_mae_pp'] = float(pd.Series(abs(error)).groupby(np.asarray(clients)).mean().mean())
    return out
