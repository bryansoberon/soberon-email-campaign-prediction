# First-round revision analyses: aggregate outputs

These files are the outputs of the scripts in [`../../experiment/revision_1/`](../../experiment/revision_1/README.md), copied without modification from the original execution. Supplementary Tables S1–S7 of the revised manuscript reproduce their values without recalculation. They are not part of Supplementary File S1. The frozen selection, the models and the 2024 evaluation are unchanged.

Files `fase1_*` are diagnostics on the reserved 2024 test, computed from the saved predictions without refitting. Files `fase2_*` are sensitivity analyses restricted to the 2022–2023 development data; none of their models was evaluated on 2024.

| File | Content | Revised manuscript |
|---|---|---|
| `fase1_a_riesgo_bajas.csv` | Identification of high-unsubscribe campaigns: thresholds, positives, alarms, recall, precision, lift and intervals, for the selected model, the history-only model and the last-five median rule | Table 8; Table S1 |
| `fase1_b_calibracion.csv` | Calibration by prediction group: mean prediction, observed mean and median, bias, share observed at or below the prediction, MAE | Figure 4; Table S2 |
| `fase1_subgrupos.csv` | Model and baseline errors by company size, campaign volume, historical response level, mature-history length, observed-response band and development participation, with paired intervals | Tables S3 and S4 |
| `fase1_resumen.json` | Training thresholds, subgroup boundaries, calibration summary (slopes, intercepts, shares), development-participation counts, reproduction of the published intervals and hashes of the frozen files | Table 9; Sections 2.8 and 3.7 |
| `fase2_f_busqueda.csv` | Every configuration of the expanded search, with pooled and per-window errors, fitting and prediction times, and peak memory | Table S5 |
| `fase2_f_configuraciones.json` | Search spaces, seeds and drawn configurations | Table S5 |
| `fase2_f_resumen_familias.csv` | Best original and best random configuration of each family | Table 10 |
| `fase2_f_controles.json` | Exact reproduction of the published development MAE of the original configurations and baselines | Section 3.8 |
| `fase2_g_perdidas.csv` | Errors of each LightGBM objective, pooled and by window, including campaigns at or above the 90th, 95th and 99th training percentiles | Table 11; Table S6 |
| `fase2_g_riesgo_bajas.csv` | Identification of high-unsubscribe campaigns for each objective and for the last-five median rule | Table 11; Table S6 |
| `fase2_g_controles.json` | Reproduction checks and objective parameters | Section 3.8 |
| `fase2_h_atributos.csv` | Errors with history only, with the 12 original attributes and with 25 transformed attributes | Table 12; Table S7 |
| `fase2_h_controles.json` | Reproduction checks, feature lists and the check of the dataset dictionary | Section 3.8 |
| `fase2_i_horizontes_umbrales.csv` | Errors by response horizon and minimum history | Table 13; Table S7 |
| `fase2_i_preparacion.json` | Checks of the response counts rebuilt at 24 and 48 h, and eligible development campaigns at each horizon | Section 3.8 |
| `fase2_i_controles.json` | Reproduction checks of the horizon analysis | Section 3.8 |

Rates, errors and biases are in percentage points. Recall, precision, alarm rates, positive rates and shares observed at or below the prediction are stored as proportions; columns ending in `_pct` are percentages. File names keep the original Spanish labels: *riesgo de bajas* (unsubscribe risk), *calibración* (calibration), *subgrupos* (subgroups), *resumen* (summary), *búsqueda* (search), *configuraciones* (configurations), *familias* (families), *controles* (checks), *pérdidas* (losses), *atributos* (attributes), *horizontes y umbrales* (horizons and thresholds) and *preparación* (preparation).

Not included: the per-fit cache (`fase2_cache/`), which the scripts regenerate, and two Spanish summaries of the same values (`FASE1_RESUMEN.md` and `FASE2_RESUMEN.md`).
