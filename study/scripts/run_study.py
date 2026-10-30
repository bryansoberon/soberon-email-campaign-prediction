"""Reanuda etapas pendientes sin repetir una evaluación final ya guardada."""
from pathlib import Path
import subprocess
import sys
import json
import hashlib

ROOT=Path(__file__).resolve().parents[1]


def run(*args):
    subprocess.run([sys.executable,'-X','utf8','-u',*args],cwd=ROOT,check=True)


def main():
    manifest=ROOT/'results/execution_manifest.json'
    if manifest.exists():
        for file,digest in json.loads(manifest.read_text(encoding='utf-8'))['files'].items():
            with (ROOT/file).open('rb') as handle: current=hashlib.file_digest(handle,'sha256').hexdigest()
            if current!=digest: raise SystemExit('El código/protocolo difiere de la ejecución guardada: '+file)
    run('-m','unittest','discover','-s','tests','-p','test_temporal.py','-v')
    run('-m','unittest','discover','-s','tests','-p','test_metrics.py','-v')
    if not (ROOT/'data/processed/campaigns.parquet').exists():run('-m','experiment.prepare')
    if not (ROOT/'results/selection.json').exists():run('-m','experiment.develop')
    if not (ROOT/'results/final_evaluation.json').exists():run('-m','experiment.evaluate')
    run('scripts/verify_experiment.py')
    run('-m','experiment.figures')
    run('-m','experiment.report')
    run('scripts/build_demo.py')
    run('scripts/verify_app.py')


if __name__=='__main__':main()
