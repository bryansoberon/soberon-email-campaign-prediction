"""Verifica artefactos de ejecución; no entrena ni vuelve a abrir la selección."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiment.core import *


def main():
    selection=json.loads((ROOT/'results/selection.json').read_text(encoding='utf-8'))
    final=json.loads((ROOT/'results/final_evaluation.json').read_text(encoding='utf-8'))
    execution=json.loads((ROOT/'results/execution_manifest.json').read_text(encoding='utf-8'))
    for file,digest in execution['files'].items():
        assert sha256(ROOT/file)==digest, f'Código o protocolo cambió después de fijar ejecución: {file}'
    assert final['selection_sha256']==sha256(ROOT/'results/selection.json')
    assert selection['protocol_sha256']==sha256(ROOT/'05_plan/PROTOCOLO_EXPERIMENTAL_V1.md')
    manifest=pd.read_parquet(ROOT/'data/processed/partition_manifest.parquet')
    assert manifest.campaign_id.is_unique
    pred=pd.read_parquet(ROOT/'data/processed/test_predictions.parquet')
    assert pred.campaign_id.is_unique and len(pred)==final['primary_n']
    assert pred.campaign_sent_time.min()>=pd.Timestamp('2024-01-01T00:00Z')
    assert pred.campaign_sent_time.max()<pd.Timestamp('2024-12-29T00:00Z')
    assert pred.history_n.ge(5).all()
    prediction_columns=[kind+'_'+target for kind in ['full','history','reference','product','observed'] for target in TARGETS]
    numeric=pred[prediction_columns]
    assert np.isfinite(numeric).all().all()
    assert numeric.ge(0).all().all() and numeric.le(100).all().all()
    for target,item in selection['targets'].items():
        for kind in ['full','history']:
            assert sha256(ROOT/f'artifacts/models/{target}_{kind}.joblib')==item[kind]['sha256']
        recomputed=metrics(pred['observed_'+target],pred['full_'+target])
        assert abs(recomputed['mae_pp']-final['targets'][target]['metrics']['full']['mae_pp'])<1e-10
    output={'status':'PASS','checks':['frozen_execution_source_hashes','protocol_and_selection_hashes','unique_partition_ids',
        'test_calendar','five_mature_campaigns','finite_predictions_in_support','model_hashes','recomputed_metrics'],
        'primary_test_campaigns':len(pred)}
    save_json(ROOT/'results/verification_experiment.json',output)
    print(json.dumps(output,indent=2))


if __name__=='__main__':main()
