"""Ejecuta pruebas reales de integración y guarda su resultado."""
from pathlib import Path
import sys
import unittest
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiment.core import ROOT,save_json

if __name__=='__main__':
    start=time.perf_counter()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_app.py')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    save_json(ROOT/'results/verification_app.json',{
        'status':'PASS' if result.wasSuccessful() else 'FAIL', 'date':'2026-10-24',
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'elapsed_seconds':time.perf_counter()-start,
        'scope':'Integración local con datos reales; no validación externa ni de usabilidad con participantes',
        'checks':['Reproducción de predicción reservada','Importación y equivalencia de predicción',
                  'Referencia con empresa nueva','Entradas inválidas','Importación inválida preserva estado',
                  'Exportación íntegra','Protección de operaciones locales','Vistas y evidencia archivada',
                  'Persistencia tras reinicio y asociación de respuestas','Cambio de mensaje no hereda respuesta ajena']})
    sys.exit(0 if result.wasSuccessful() else 1)
