# First-round revision analyses: code

These scripts were added after the original submission of manuscript applsci-4697740, to answer the first round of review. They are not part of Supplementary File S1 and they do not modify any archived file. Their outputs are in [`../../results/revision_1/`](../../results/revision_1/README.md). They correspond to Sections 2.8, 3.7 and 3.8, Tables 8–13 and Supplementary Tables S1–S7 of the revised manuscript.

## Rules

- **Phase 1 (`fase1_diagnosticos.py`) fits no model.** It uses the saved 2024 predictions (`data/processed/test_predictions.parquet`) and pre-send columns of `data/processed/campaigns.parquet`. Risk thresholds and subgroup boundaries come from the 546,759 final-training campaigns. Only the cutoffs for the 1%, 5% and 10% of campaigns with the highest observed rates refer, by definition, to the evaluated 2024 sample.
- **Phase 2 (`fase2_*.py`) refits models only on 2022–2023 development campaigns.** It keeps the three 2023 validation windows, the 72-h maturity rule and the pooled-MAE criterion of `experiment/develop.py`. No phase-2 model was evaluated on the 2024 test, and none replaces the frozen selection.
- **Frozen files are checked.** Each script records the SHA-256 digests of the frozen models, selection, final evaluation and processed data when it starts, and checks that they are unchanged when it ends. The phase-2 scripts also check that they reproduce exactly the published development MAE of the original configurations and baselines.
- **Intervals** use the resampling of `experiment/evaluate.py`: companies × circular four-week blocks, 2,000 replicates, 1.25th and 98.75th percentiles, seed 20261024 + 4. They are nominal 97.5% intervals and are not adjusted for the number of subgroups. For recall, precision and alarm rate, the alarms are fixed on the full test and campaigns are resampled.

## Files

| File | Purpose |
|---|---|
| `common.py` | Hashes of the frozen artifacts, the 546,759-campaign final training set, the 1:1 join of the saved 2024 predictions with pre-send columns, and the resampling of ratios such as recall and precision. |
| `fase1_diagnosticos.py` | Identification of high-unsubscribe campaigns (Table 8; Table S1), calibration (Table 9; Table S2; medians in Figure 4), subgroups (Table S3) and companies without development participation (Table S4). |
| `desarrollo.py` | Shared phase-2 helpers: development windows, model fitting, pooled metrics, high-rate tails, risk metrics and a cache with one JSON file per fit. |
| `fase2_busqueda.py` | Expanded search with 20 random configurations per family (Table 10; Table S5). Accepts `--familias lgbm ridge rf`. |
| `fase2_perdidas.py` | Alternative LightGBM training objectives (Table 11; Table S6). |
| `fase2_atributos.py` | Transformed message attributes and the check of the dataset dictionary (Table 12; Table S7, panel A). |
| `fase2_horizontes.py` | Response horizons of 24 and 48 h and minimum histories of 3, 5 and 10 campaigns (Table 13; Table S7, panel B). `--solo-preparar` only rebuilds the data. |

File names and options keep their original Spanish labels: *fase* (phase), *desarrollo* (development), *búsqueda* (search), *pérdidas* (losses), *atributos* (attributes), *horizontes* (horizons), *familias* (families) and *solo preparar* (prepare only). Some comments and printed messages are also in Spanish. `fase1_diagnosticos.py` additionally writes a Spanish summary, `FASE1_RESUMEN.md`; it is not included in `results/revision_1/` because the CSV and JSON files contain the same values.

## Commands

The archived outputs were produced by running these modules, in this order, from the root of the original project, which has the layout of `study/` plus the processed data and the original CSV:

```powershell
python -X utf8 -m experiment.revision_1.fase1_diagnosticos
python -X utf8 -m experiment.revision_1.fase2_perdidas
python -X utf8 -m experiment.revision_1.fase2_atributos
python -X utf8 -m experiment.revision_1.fase2_horizontes --solo-preparar
python -X utf8 -m experiment.revision_1.fase2_busqueda --familias lgbm ridge
python -X utf8 -m experiment.revision_1.fase2_horizontes
python -X utf8 -m experiment.revision_1.fase2_busqueda --familias rf
```

A full reproduction (`review.py reproduce`, see the main README) creates a directory with that layout under `runs/<name>/`, including a copy of this folder. Run the modules from that directory with the package environment. Its outputs are written to `runs/<name>/results/revision_1/` and can be compared with the archived files in `study/results/revision_1/`. They use the models and predictions of that reproduction.

The archived outputs were computed with the archived models, in the environment recorded in `study/requirements-lock.txt`. On that machine, phase 1 took about 30 s. The expanded Random Forest search alone required about 2.7 h of fitting time (Table 10). Each finished fit is cached in `results/revision_1/fase2_cache/`, so an interrupted command can be repeated without refitting completed configurations. If a cached file does not match the requested configuration, the script stops. Development predictions and rebuilt horizon data are written to `data/processed/revision_1/`.
