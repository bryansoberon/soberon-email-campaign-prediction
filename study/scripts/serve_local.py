from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from waitress import serve
from app.server import create_app
from experiment.core import ROOT

if __name__=='__main__':
    required=['results/final_evaluation.json','results/selection.json','artifacts/models/clicks_full.joblib',
              'artifacts/models/unsubscribes_full.joblib','runtime/demo.parquet','runtime/comparison.parquet']
    missing=[p for p in required if not (ROOT/p).exists()]
    if missing:raise SystemExit('Faltan artefactos locales: '+', '.join(missing)+'. Consulta EJECUTAR_ESTUDIO.md para reproducción independiente.')
    print('Sistema local: http://127.0.0.1:8765',flush=True)
    serve(create_app(),host='127.0.0.1',port=8765,threads=4,max_request_body_size=400*1024*1024)
