"""Reproducción independiente en una carpeta nueva; preserva resultados originales."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name',default=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S'))
    args=parser.parse_args()
    base=(ROOT/'reproductions').resolve(); destination=(base/args.name).resolve()
    if not destination.is_relative_to(base) or destination==base or destination.exists():
        raise SystemExit('Elige un nombre nuevo dentro de reproductions/. No se sobrescribe una ejecución.')
    destination.mkdir(parents=True)
    for name in ['experiment','app','scripts','tests']:
        shutil.copytree(ROOT/name,destination/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (destination/'05_plan').mkdir();(destination/'results').mkdir()
    for name in ['05_plan/PROTOCOLO_EXPERIMENTAL_V1.md','requirements-lock.txt']:
        shutil.copyfile(ROOT/name,destination/name)
    manifest=json.loads((ROOT/'results/execution_manifest.json').read_text(encoding='utf-8'))
    manifest.update(stage='independent_reproduction_before_training',date=datetime.now(timezone.utc).isoformat())
    (destination/'results/execution_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    dataset=destination/'data/raw/elegibilidad/SendGuard900K.csv';dataset.parent.mkdir(parents=True)
    original=ROOT/'data/raw/elegibilidad/SendGuard900K.csv'
    if original.exists():shutil.copyfile(original,dataset)
    else:
        print('Descargando el archivo público original desde Zenodo (322 MB).',flush=True)
        with urllib.request.urlopen('https://zenodo.org/records/17985618/files/SendGuard900K.csv?download=1',timeout=120) as response,dataset.open('wb') as out:
            shutil.copyfileobj(response,out)
    with dataset.open('rb') as handle:digest=hashlib.file_digest(handle,'sha256').hexdigest()
    if digest!='4e83e286426ca43d0a5a0f4bb6157b83fc1ad0ae90751b8891a5822ae6eb3956':
        raise SystemExit('El archivo descargado no coincide con la versión auditada. No se ejecutó el estudio.')
    print('Reproducción independiente en:',destination,flush=True)
    subprocess.run([sys.executable,'-X','utf8','-u',str(destination/'scripts/run_study.py')],cwd=destination,check=True)
    print('Completado. Para utilizar su sistema, ejecutar con este Python:',destination/'scripts/serve_local.py')


if __name__=='__main__':main()
