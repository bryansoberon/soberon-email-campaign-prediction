# Supplementary File S1 — Reproducibility archive

Development of a Machine Learning-Based Method for Predicting Key Metrics in Digital Marketing Campaigns

This archive accompanies the SendGuard900K study. It includes the recorded protocol, source code, dependency lock file, development comparisons, frozen selection, four fitted models, principal-test predictions, partition manifest, aggregate outputs, and software-verification evidence. The article figures and the English interface screenshots are included. No private user workspace, university documents, credentials, or unrelated business exports are included.

## Data provenance and attribution

Bobek, S.; Nalepa, G.J.; Obara, S.; Suszalski, P.; Bałec, Ł. SendGuard900K: Massive Dataset for Metadata-Based Quality Assurance of Email Marketing, version 1.0.0. Zenodo (2025). https://doi.org/10.5281/zenodo.17985618.

The source release is distributed under CC BY 4.0. The derived prediction and partition files retain coded company/campaign identifiers from that public source. These identifiers refer to sender companies and campaigns, not named email recipients. Attribution and the source license apply to the underlying data; third-party software retains its own licenses.

The full source CSV is obtained from its original repository rather than duplicated here:

https://zenodo.org/records/17985618/files/SendGuard900K.csv?download=1

Expected source-file SHA-256:

`4e83e286426ca43d0a5a0f4bb6157b83fc1ad0ae90751b8891a5822ae6eb3956`

## Inspecting the recorded results

`results/preparation.json` records sequential exclusions and cohorts. `results/development_summary.json` and `results/development/comparison.csv` contain development comparisons. `results/selection.json` records the selections saved before final testing and their model hashes. `results/final_evaluation.json` contains the reserved-test evaluation, paired intervals, sensitivities, ablation, limited-history results, and batch prediction times. `results/monthly_test.csv` and `results/figures_tesis/diagnostic_groups.csv` underlie the article plots.

`data/processed/test_predictions.parquet` contains observations and saved predictions for the 275,535 principal test campaigns. `data/processed/partition_manifest.parquet` records the eligible partition. The original fitted full and history-only models are in `artifacts/models/`. Model files use joblib serialization and should be loaded only from a trusted archive whose hashes match the supplied manifest.

## Environment and verification

The recorded environment is Windows 11, Python 3.14.2; all package versions are pinned in `requirements-lock.txt`. Exact runtime and process-memory figures depend on hardware, environment, and measurement boundaries. Use a compatible Python environment and install the dependencies:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.venv\Scripts\python.exe -X utf8 scripts\verify_experiment.py
```

That verification reads the archived predictions and hashes; it does not fit models or perform another predictive evaluation. The saved local demo records and feature bounds also allow the application to run using the frozen models:

```powershell
.venv\Scripts\python.exe -X utf8 scripts\serve_local.py
```

The server binds to `127.0.0.1:8765`. Its examples are historical replays from the public source, not predictions issued at the original sending dates. Local workspace files created while running the application are not part of this supplied archive.

## Independent reproduction from source data

The following command creates a new directory under `reproductions/`, retrieves or copies the original public source CSV, checks its hash, and runs the scientific pipeline in that independent directory:

```powershell
.venv\Scripts\python.exe -X utf8 scripts\reproduce.py --name independent_01
```

Use a new name for each reproduction. The command performs fitting and evaluation in the new directory; it does not replace the original archived outputs. Numerical agreement and resource measurements should be assessed with the recorded versions and platform assumptions. No reproduction was executed during preparation of the manuscript.

## Statistical interpretation

The model/reference selections use 2022–2023 development data. The final test is later-period data from the same provider, not an external-provider or entirely unseen-company validation. Historical response windows must satisfy prior send + 72 h < query send. Fitted weights remain fixed as histories update.

The paired bootstrap weights cross company multiplicities with circular moving blocks of calendar weeks. The reported intervals concern mean error differences conditional on the fitted procedures. They are approximate, not individual prediction intervals. The message ablation does not identify a causal effect of editing a message, and the functional checks do not establish user comprehension or business impact.

`MANIFEST_SHA256.json` lists the SHA-256 digest of every archive member other than the manifest itself.
