# Email Campaign Prediction — Soberón

Companion to the submitted manuscript **Development of a Machine Learning-Based Method for Predicting Key Metrics in Digital Marketing Campaigns**. Authors: Bernabe B. Soberón-Quintana, Efraín A. Muro-Nuñez and Victor A. Tuesta-Monteza, Universidad Señor de Sipán, Peru.

This repository contains the complete local application and scientific method for pre-send unique-click and unsubscribe rate prediction. It supports inspection of the archived experiment and an independent repetition from the original data. It preserves the 140 files of the original Supplementary File S1 archive byte for byte under `study/`. The Supplementary File S1 submitted with the manuscript differs only in `article_figures/`, which contains the exact manuscript figures also provided here in `reference_figures/`, in a README section describing those figures, and in its updated `MANIFEST_SHA256.json`. The reviewer tools add numerical checks, the manuscript figures and isolated execution directories.

Start with the [application manual](docs/APPLICATION_USER_GUIDE.md), [method and experimental protocol in English](docs/METHOD_AND_PROTOCOL_EN.md), or the reviewer commands below. The application has an English interface at `http://127.0.0.1:8765/?lang=en`. Original frozen source files, identifiers, API routes and protocol evidence remain unchanged; some historical comments and terminal messages are in Spanish.

## Submitted supplementary file

**[Download S1_Reproducibility_Soberon.zip](https://github.com/bryansoberon/soberon-email-campaign-prediction/raw/refs/heads/main/S1_Reproducibility_Soberon.zip)** — the supplementary archive identified by the corresponding author as submitted to Applied Sciences on 30 October 2026 with manuscript `applsci-4697740` (V14).

The archive is provided unchanged: **143 files**, including its manifest with **142 SHA-256 entries**. It contains the frozen method, application, models, predictions, results and the updated manuscript figures. Its SHA-256 is:

```text
1d9ecd5c7c7a0755d04234f15133673ae57645bc000e48792753fd49a617538a
```

For the submitted figures, use `article_figures/` inside this ZIP or [reference_figures/](reference_figures/) in this repository; all 13 figure files match byte for byte. The repository's `study/article_figures/` retains the figures from the original archived package. The 128 scientific and application files outside the figures, README and manifest are identical between the submitted ZIP and `study/`.

The GitHub **Code → Download ZIP** command downloads this entire repository, including the manuals and additional reviewer tools. Use the link above to obtain the submitted S1 archive itself. The repository integrity command below also checks that archive's SHA-256.

## Reviewer routes

| Route | What it does | Original CSV needed? | Fits models? |
|---|---|---|---|
| `integrity` | Checks package and original S1 SHA-256 digests | No | No |
| `verify` | Recomputes principal-test metrics and monthly summaries; checks development arithmetic and prediction groups; runs the existing 17 tests; exports article tables and figures | No | No |
| `verify --intervals` | Also recomputes the main, sensitivity and ablation bootstrap intervals from archived predictions | No | No |
| `reproduce` | Repeats preparation, development comparisons, selection, final fitting and reserved-test evaluation in a fresh directory | Yes; downloaded automatically or supplied locally | Yes |
| `app` | Runs the local application using the archived models and historical public demo | No | No |

All commands start with integrity checks. Outputs and logs go under `runs/<new-name>/`. The launcher refuses an existing run name. Original `study/` files remain unchanged. Run commands from this package root, not from inside `study/`.

## Environment and first check

The recorded and locally tested platform is Windows 11, 64-bit Python **3.14.2**. Package versions are pinned in `study/requirements-lock.txt`. Verification evidence and portability checks are documented in `VALIDATION.md`.

Article plots now choose the first installed font from **Arial, Liberation Sans, DejaVu Sans**. Without Arial, figures may look slightly different. Font-dependent margin differences produce recorded warnings rather than failing otherwise valid numerical verification; other rendering and numerical errors still fail. With Arial, the original strict layout checks remain. Timing, peak process memory, model-file serialization and figure rendering can depend on the platform. See [validation scope](VALIDATION.md).

The integrity command requires only the Python standard library:

```powershell
python -X utf8 review.py integrity
```

Create a clean environment for numerical verification or reproduction:

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -r study\requirements-lock.txt
.venv\Scripts\python.exe -X utf8 review.py verify --name verify_01
```

`verify` recalculates numbers from saved observations/predictions and checks the application with the supplied frozen models. It does not repeat feature preparation or model fitting. To recompute all reported principal-test bootstrap intervals as well:

```powershell
.venv\Scripts\python.exe -X utf8 review.py verify --intervals --name intervals_01
```

To exercise the alternative-font path even on a machine with Arial installed, add `--font "DejaVu Sans"` and choose a new run name. This affects article rendering only. The numerical checks and model parameters are unchanged. Rendering font, layout policy and any margin warnings are recorded in `review_outputs/article_figures/render_manifest.json`.

Inspect `runs/<name>/review_outputs/RUN.json`, `saved_results_verification.json`, `article_tables/`, `article_figures/` and `logs/`. A successful run prints `PASS`; failures return a nonzero process exit code. The preparation-time checks are documented in `VALIDATION.md`.

## Repeat the complete scientific pipeline

The full source CSV has 908,229 rows and is approximately 322 MB. It is retrieved from its original public release, rather than duplicated in this repository:

- SendGuard900K version 1.0.0: https://doi.org/10.5281/zenodo.17985618
- CSV: https://zenodo.org/records/17985618/files/SendGuard900K.csv?download=1
- Required SHA-256: `4e83e286426ca43d0a5a0f4bb6157b83fc1ad0ae90751b8891a5822ae6eb3956`.

```powershell
.venv\Scripts\python.exe -X utf8 review.py reproduce --name reproduction_01
```

If the original CSV is already available:

```powershell
.venv\Scripts\python.exe -X utf8 review.py reproduce --name reproduction_02 --dataset "C:\data\SendGuard900K.csv"
```

`--setup-only` validates and copies the source data and frozen code into a new run without training. That setup-only run cannot be reused as a full run: use another name when executing the full command.

Each full reproduction starts with **no archived selection, predictions or final evaluation**. It executes the original scientific modules unchanged, retains the frozen protocol/seed/configurations, and evaluates the later test after development selection. It creates its own models and outputs. It neither overwrites the archived experiment nor searches for new settings using test outcomes. Allow additional disk space and time for the CSV, processed data and all candidate fits; no wall-time guarantee is made.

A repetition should be compared numerically to the archived outputs, with the recorded environment and statistical procedure held fixed. Hash equality is required for supplied source files and the original dataset; it is not a promise that retrained model files or resource measurements will be byte-identical on another system. New execution timestamps are recorded in `review_outputs/RUN.json` and step logs. Historical evidence files within `study/results/verification_*` describe the original execution, not a new run.

## Local application

```powershell
.venv\Scripts\python.exe -X utf8 review.py app --name application_01
```

Open http://127.0.0.1:8765/?lang=en for the **English interface**. Stop the local server with Ctrl+C. The interface uses compatible public campaign records and frozen models; examples are historical replays, not forecasts issued at the original sending dates. New imports and estimates are stored only in that run's local workspace. No connection to a commercial email or advertising platform is required. The [application manual](docs/APPLICATION_USER_GUIDE.md) explains each screen, the CSV contract, persisted records and common errors.

## Map from article to evidence

| Article component | Archived evidence / code | Reviewer output |
|---|---|---|
| Inputs, history gate and temporal design; Tables 1–3 | `study/05_plan/PROTOCOLO_EXPERIMENTAL_V1.md`; `experiment/core.py`, `prepare.py`, `models.py`, `develop.py` | Inspect protocol and the temporal/metric tests |
| Table 4: development MAE | `results/development_summary.json`, `selection.json` | `article_tables/table04_development.csv` |
| Table 5: held-out MAE, RMSE and bias | `data/processed/test_predictions.parquet`, `results/final_evaluation.json` | `article_tables/table05_test_metrics.csv`; independent metric checks |
| Table 6: history-only ablation | Same predictions and final evaluation | `article_tables/table06_message_ablation.csv`; means and optional interval recomputation |
| Table 7: recorded runtime and memory | `results/selection.json`, `final_evaluation.json` | `article_tables/table07_recorded_resources.csv`; original-run measurements |
| Figure 1: method/application workflow | `tools/article_figures.py` | PNG/PDF/SVG rendering |
| Figure 2: paired mean-error intervals | `experiment/evaluate.py`; archived predictions | `article_tables/figure02_paired_intervals.csv`; plot and optional bootstrap recomputation |
| Figure 3: monthly MAE | `results/monthly_test.csv`; archived predictions | Independent monthly checks and rendered plot |
| Figure 4: prediction-group diagnostic | `results/figures_tesis/diagnostic_groups.csv`; archived predictions | Recomputed group means/counts and rendered plot |
| Figure 5: local application | `app/`, public `runtime/` demo and archived English screenshots | `reference_figures/figure05.png`; local application |

Paths in the evidence column are relative to `study/` unless prefixed `tools/`. `reference_figures/figure01`–`figure05` contain the actual images embedded in the submitted manuscript. The PNG bytes are checked against that document by the package builder; Figures 1–4 also include their original vector files. The older `study/article_figures/` are preserved S1 history. Use `reference_figures/` and the new plotting tool for the current article.

## Expected recorded results and scope

The archived preparation yielded **847,458 eligible campaigns**. The principal 2024 test contains **275,535 campaigns from 3,528 companies**, each with at least five mature previous campaigns. Development uses 2022–2023 data. A previous campaign contributes outcomes only when its sending time + 72 h is strictly earlier than the prediction instant. The test excludes sending dates from 29 December 2024 onward.

| Outcome | Model MAE (pp) | Selected-baseline MAE (pp) | Relative MAE reduction | Main nominal 97.5% interval for model minus baseline MAE (pp) |
|---|---:|---:|---:|---|
| Unique clicks | 3.0198414373 | 3.3331196437 | 9.3989487% | [−0.5258106117, −0.1550518271] |
| Unsubscribes | 0.2898811733 | 0.3041481156 | 4.6907877% | [−0.0177936122, −0.0113539154] |

Intervals use crossed company multiplicities and circular moving calendar blocks; the main block length is four weeks with 2,000 repetitions, and sensitivity checks use two/eight weeks with 1,000 repetitions. The intervals concern mean error differences conditional on the fitted procedures; they are not individual prediction intervals. Limited-history results require the source-data route to reconstruct their observations. The test is a later period from the same provider; it does not establish external-provider transfer or causal business effects.

## Attribution, integrity and citation

Bobek, S.; Nalepa, G.J.; Obara, S.; Suszalski, P.; Bałec, Ł. **SendGuard900K: Massive Dataset for Metadata-Based Quality Assurance of Email Marketing**, version 1.0.0. Zenodo (2025). https://doi.org/10.5281/zenodo.17985618. The source is distributed under **CC BY 4.0**. Derived data retain coded company/campaign identifiers from that source. Attribution applies to the source and derivatives; third-party software retains its own licenses. See `REUSE_AND_PROVENANCE.md` for the software-license status.

`CHECKSUMS_SHA256.json` covers every distributable package file except itself; `study/MANIFEST_SHA256.json` independently preserves the original S1 file hashes. `PROVENANCE.json` records source-archive/manuscript/plotting hashes. `CITATION.cff` records the authors and package version. Model files are joblib serializations: load only the trusted, checksum-verified supplied models.
