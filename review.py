"""Reviewer entry point. Archived study files are never modified."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parent
STUDY = ROOT / 'study'
DATA_URL = 'https://zenodo.org/records/17985618/files/SendGuard900K.csv?download=1'
DATA_SHA = '4e83e286426ca43d0a5a0f4bb6157b83fc1ad0ae90751b8891a5822ae6eb3956'


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def integrity():
    manifest = json.loads((ROOT / 'CHECKSUMS_SHA256.json').read_text(encoding='utf-8'))
    for name, expected in manifest.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or sha(path) != expected:
            raise SystemExit('Integrity check failed: ' + name)
    original = json.loads((STUDY / 'MANIFEST_SHA256.json').read_text(encoding='utf-8'))
    for name, expected in original.items():
        path = (STUDY / name).resolve()
        if not path.is_relative_to(STUDY) or not path.is_file() or sha(path) != expected:
            raise SystemExit('Original S1 checksum failed: ' + name)
    print(f'PASS: {len(manifest)} package files and {len(original)} original S1 checksums.', flush=True)
    return len(manifest)


def destination(name):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,70}', name):
        raise SystemExit('Use a new run name containing only letters, numbers, _ or -.')
    base = (ROOT / 'runs').resolve()
    dest = (base / name).resolve()
    if not dest.is_relative_to(base) or dest == base or dest.exists():
        raise SystemExit('Run already exists or is outside runs/. Choose a new name.')
    dest.mkdir(parents=True)
    return dest


def copy_archived(dest):
    for source in STUDY.iterdir():
        if source.is_dir():
            shutil.copytree(source, dest / source.name)
        else:
            shutil.copyfile(source, dest / source.name)


def command(dest, label, *arguments):
    logs = dest / 'review_outputs' / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['MPLCONFIGDIR'] = str(dest / '.cache' / 'matplotlib')
    cmd = [sys.executable, '-X', 'utf8', '-u', *map(str, arguments)]
    print('Running:', label, flush=True)
    start = now()
    with (logs / (label + '.log')).open('w', encoding='utf-8') as log:
        proc = subprocess.Popen(cmd, cwd=dest, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding='utf-8')
        for line in proc.stdout:
            log.write(line)
            print(line, end='', flush=True)
        code = proc.wait()
    record = {'step': label, 'arguments': list(map(str, arguments)),
              'started_utc': start, 'finished_utc': now(), 'returncode': code}
    with (logs / 'steps.jsonl').open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record) + '\n')
    if code:
        raise RuntimeError(f'{label} failed with exit code {code}; see review_outputs/logs/.')


def check_outputs(dest, intervals=False, font='auto'):
    command(dest, 'frozen_artifacts', 'scripts/verify_experiment.py')
    extra = ['--intervals'] if intervals else []
    command(dest, 'saved_results', ROOT / 'tools' / 'verify_saved_results.py', '--study', dest, *extra)
    command(dest, 'application_figures', '-m', 'experiment.figures')
    command(dest, 'existing_17_tests', '-m', 'unittest', 'discover', '-s', 'tests', '-v')
    command(dest, 'article_tables', ROOT / 'tools' / 'article_tables.py', '--study', dest)
    command(dest, 'article_figures', ROOT / 'tools' / 'article_figures.py', '--study', dest, '--font', font)


def prepare_reproduction(dest, dataset):
    for name in ['experiment', 'app', 'scripts', 'tests']:
        shutil.copytree(STUDY / name, dest / name)
    for name in ['05_plan/PROTOCOLO_EXPERIMENTAL_V1.md', 'requirements-lock.txt']:
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(STUDY / name, target)
    manifest = json.loads((STUDY / 'results/execution_manifest.json').read_text(encoding='utf-8'))
    manifest.update(stage='independent_reproduction_before_training', date=now())
    write_json(dest / 'results/execution_manifest.json', manifest)
    target = dest / 'data/raw/elegibilidad/SendGuard900K.csv'
    target.parent.mkdir(parents=True, exist_ok=True)
    if dataset:
        source = Path(dataset).expanduser().resolve()
        if not source.is_file() or sha(source) != DATA_SHA:
            raise RuntimeError('Supplied dataset does not match the audited original SHA-256.')
        shutil.copyfile(source, target)
    else:
        print('Downloading the public 322 MB CSV from Zenodo.', flush=True)
        with urllib.request.urlopen(DATA_URL, timeout=120) as response, target.open('wb') as handle:
            shutil.copyfileobj(response, handle)
    if sha(target) != DATA_SHA:
        raise RuntimeError('Dataset SHA-256 mismatch. No training was started.')
    for name, expected in manifest['files'].items():
        if sha(dest / name) != expected:
            raise RuntimeError('Frozen source mismatch: ' + name)
    if (dest / 'results/selection.json').exists() or (dest / 'results/final_evaluation.json').exists():
        raise RuntimeError('An independent reproduction must start without archived selection or final results.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('integrity', help='Check archive bytes; standard library only.')
    for action in ['verify', 'reproduce', 'app']:
        p = sub.add_parser(action)
        p.add_argument('--name', default=action + '_' + datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S'))
        if action == 'verify':
            p.add_argument('--intervals', action='store_true', help='Also recompute all paired bootstrap intervals from saved predictions.')
            p.add_argument('--font', choices=['auto', 'Arial', 'Liberation Sans', 'DejaVu Sans'], default='auto', help='Override the article font for a portability check.')
        if action == 'reproduce':
            p.add_argument('--dataset', help='Existing original CSV; otherwise download from Zenodo.')
            p.add_argument('--setup-only', action='store_true', help='Prepare and validate the fresh run without training.')
    args = parser.parse_args()
    integrity()
    if args.action == 'integrity':
        return
    dest = destination(args.name)
    info = {'action': args.action, 'started_utc': now(), 'python': platform.python_version(),
            'platform': platform.platform(), 'status': 'RUNNING', 'trained': False,
            'package_version': '1.0.4-review', 'run_name': args.name}
    report = dest / 'review_outputs/RUN.json'
    write_json(report, info)
    try:
        if args.action == 'reproduce':
            prepare_reproduction(dest, args.dataset)
            if args.setup_only:
                info['status'] = 'SETUP_ONLY_PASS'
            else:
                command(dest, 'pre_training_tests', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_temporal.py', '-v')
                command(dest, 'metric_tests', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_metrics.py', '-v')
                command(dest, 'prepare', '-m', 'experiment.prepare')
                command(dest, 'develop', '-m', 'experiment.develop')
                info['trained'] = True
                command(dest, 'reserved_test', '-m', 'experiment.evaluate')
                command(dest, 'public_demo', 'scripts/build_demo.py')
                check_outputs(dest)
                info['status'] = 'REPRODUCTION_PASS'
        else:
            copy_archived(dest)
            if args.action == 'verify':
                check_outputs(dest, args.intervals, args.font)
                info['bootstrap_intervals_recomputed'] = args.intervals
                rendering = json.loads((dest / 'review_outputs/article_figures/render_manifest.json').read_text(encoding='utf-8'))
                info['article_font'] = rendering['font_used']
                info['presentation_warnings'] = rendering['layout_warnings']
                info['status'] = 'VERIFICATION_PASS'
            else:
                command(dest, 'application_figures', '-m', 'experiment.figures')
                print('English interface: http://127.0.0.1:8765/?lang=en', flush=True)
                command(dest, 'local_application', 'scripts/serve_local.py')
                info['status'] = 'APPLICATION_STOPPED'
        integrity()
    except BaseException as error:
        info.update(status='FAILED_OR_INTERRUPTED', error=str(error))
        raise
    finally:
        info['finished_utc'] = now()
        write_json(report, info)
    print('Outputs:', dest / 'review_outputs', flush=True)


if __name__ == '__main__':
    main()
