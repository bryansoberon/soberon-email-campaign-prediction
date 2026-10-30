# Method and experimental protocol — English guide

This guide explains the executed study using the frozen protocol, scientific modules and archived outputs. It does not introduce another experiment. The original protocol is preserved byte for byte at `study/05_plan/PROTOCOLO_EXPERIMENTAL_V1.md`; its Spanish administrative notes describe the state when it was frozen on 24 October 2026. This English guide describes the completed method and its reproducibility routes.

## 1. Prediction task and source

For a campaign with sending instant `t`, estimate two continuous campaign-level rates over the first **4,320 minutes (72 hours)**:

```text
unique_click_rate = 100 × campaign_unique_clicks_count_4320 / campaign_subscribers_count
unsubscribe_rate  = 100 × campaign_resigned_count_4320 / campaign_subscribers_count
```

The denominator is the number of emails sent under the source definition. These are recorded campaign rates, not individual recipient probabilities or causal effects. The study accepts the provider's observation-window definitions; independent capture completeness was not established.

Source: **SendGuard900K v1.0.0**, https://doi.org/10.5281/zenodo.17985618, CC BY 4.0. The source contains 908,229 rows from 2022–2024. The audited CSV SHA-256 is `4e83e286426ca43d0a5a0f4bb6157b83fc1ad0ae90751b8891a5822ae6eb3956`. The CSV is downloaded from its original release or supplied by the reviewer, then checked before training.

## 2. Eligibility and preparation

`experiment/prepare.py` applies `read_campaigns`, `clean_campaigns` and `history_features` from `experiment/core.py`.

Eligible records require valid identifiers/timestamps, a nonduplicated campaign identifier, positive sending volume, response counts between zero and sending volume, and finite nonnegative message attributes. A/B-test and optimizer records are excluded using the source campaign-test field. Sending dates from **29 December 2024 00:00 UTC onward** are excluded to retain a 72-hour margin at the end of the published period. This endpoint rule does not establish that earlier response capture is complete.

The archived sequential exclusions yield **847,458 eligible campaigns**. `study/results/preparation.json` records every exclusion step and cohort. Company and campaign identifiers are matching/grouping keys, not numeric predictors. Manual tags, domains, moderation variables and current response counts are not model inputs. The current campaign's sending volume is used to define its observed response, not as a pre-send predictor.

## 3. Inputs and strictly mature company history

The full model uses **25 inputs**: 12 structural message properties and 13 historical features.

| Input group | Definitions |
|---|---|
| Message structure: 7 | Content size; image count; embedded-image count and total size; embedded-file count and total size; link count |
| Personalization: 5 | Total personalization-tag count and counts in sender email, subject, HTML body and text body |
| History activity: 3 | Mature-campaign count; days since the last mature campaign was sent; mean historical sending volume |
| Click history: 5 | Mean, sending-volume-weighted mean, last rate, mean of last five mature rates, median of last five mature rates |
| Unsubscribe history: 5 | The same five summaries for unsubscribe rates |

A historical campaign is admissible only if:

```text
historical sending instant + 72 hours < query sending instant
```

The inequality is strict and histories are company-specific. During validation/test, histories can incorporate earlier outcomes once mature; model weights and baseline rules remain fixed. The **principal population requires at least five mature previous campaigns**. Lower-history cases are reported separately using a development-fixed global-median fallback.

Message properties are assumed obtainable before sending; historical snapshots proving their invariability were unavailable. Calendar/time is used for splitting and history admissibility, not as a predictor.

## 4. Development and reserved test

| Stage | Fitting origin | Validation sending interval |
|---|---|---|
| Development window 1 | 1 January 2023 | [1 January, 1 May 2023) |
| Development window 2 | 1 May 2023 | [1 May, 1 September 2023) |
| Development window 3 | 1 September 2023 | [1 September, 29 December 2023) |
| Final fit | 1 January 2024 | Earlier development rows whose 72-hour labels had matured |
| Reserved test | Frozen final models | [1 January, 29 December 2024) |

Fitting at each origin uses only earlier eligible development campaigns with mature responses. The last validation window ends on 29 December 2023 to keep its labels before the final fitting origin. The principal reserved test has **275,535 campaigns from 3,528 companies**; 1,615 lower-history test campaigns are assessed separately.

For each outcome, select the ML candidate and baseline with the smallest **pooled campaign MAE** over the three validation windows. The pooled score is `sum(window MAE × window campaign count) / sum(window campaign count)`, not an equally weighted mean of window MAEs. Ties are resolved by configuration name. The original selection and fitted-model hashes were saved before final testing. The product uses the better development-selected ML/baseline procedure, without changing that decision from test performance.

## 5. Candidate models and baselines

Seed: **20261024**. Computation uses six workers where specified. Predictions are clipped to [0, 100] using the rule fixed before fitting.

| Family | Compared settings | Fixed settings |
|---|---|---|
| Ridge | `alpha` 1 or 100 | `log1p` of nonnegative inputs; scaler fitted only on training data; L2-penalized squared-error regression with unpenalized intercept |
| Random Forest | Minimum leaf size 30 or 100 | 160 trees; maximum depth 14; feature fraction 0.8; bootstrap sample fraction 0.7; squared-error criterion; six workers |
| LightGBM | Maximum leaves 15 or 31 | L1 regression; 400 trees; learning rate 0.04; minimum child samples 100; L2 regularization 1; deterministic and column-wise modes; six workers |

The six baselines are global mean, global median, company historical mean, median of the last five mature campaigns, last mature rate and zero. Global quantities are fixed from fitting data. Full parameter construction is in `experiment/models.py`.

Development selected `lgbm_15` for unique clicks and `lgbm_31` for unsubscribes. Their selected baselines are `last5_median` and `global_median`, respectively. The predefined ablation refits the selected ML configuration with **history features only**, preserving the configuration. It measures incremental predictive information from message features; it does not estimate the effect of editing a message.

## 6. Error, uncertainty and resources

Primary metric: campaign-average MAE in **percentage points (pp)**, separately for each outcome. Secondary metrics: RMSE, signed bias (`prediction − observation`), sending-volume-weighted MAE and company-average MAE. Monthly summaries assess temporal stability. Regression metrics are used because the outcomes are continuous rates; classification thresholds, confusion matrices, AUC and F1 are not substituted for this task.

The paired loss difference is:

```text
absolute error of full ML model − absolute error of selected baseline
```

The bootstrap crosses resampled company multiplicities with circular moving blocks of calendar weeks. The primary block length is **four weeks**, with **2,000 repetitions** and percentile **97.5% intervals** per outcome. The nominal per-outcome level reflects the predefined two-outcome Bonferroni rule. Sensitivities use two/eight weeks and 1,000 repetitions. Main message-ablation intervals use the four-week/2,000-repetition procedure. Seeds and implementation are in `experiment/evaluate.py`.

These are approximate intervals for mean error differences conditional on fitted procedures, not exact guarantees or individual campaign prediction intervals. Joint support requires an upper limit below zero for both outcomes under the predefined criterion. No minimum economically relevant error reduction was established.

Fitting/prediction time and sampled process RSS describe the original execution. RSS is whole-process memory, not isolated incremental algorithm memory. Hardware and software changes can alter resource measurements and model serialization.

## 7. Shared implementation and local application

The local Flask/Waitress application uses the same `experiment.core.history_features` definitions and frozen fitted models. It validates/imports compatible CSV histories, estimates rates before the query instant, persists estimates with timestamps and model information, and matches later observed records. It does not retrain models when a user imports a CSV.

The demo selects 12 companies by development campaign counts, not prediction errors. Its public historical examples support functional replay. Functional checks do not establish user comprehension, external-provider validity or commercial impact. An external provider requires verified field definitions, response horizon, admissible inputs and separate predictive evaluation; matching column names alone is insufficient.

## 8. Reproduction and evidence

1. `review.py integrity` checks exact archived/package bytes.
2. `review.py verify --intervals --name check_01` recalculates principal-test statistics from archived observations/predictions, all eight interval results, and the table/figure data; it runs the existing software tests without model fitting.
3. `review.py reproduce --name repetition_01` obtains/checks the raw CSV and repeats preparation, development, fitting and reserved-test evaluation in a fresh directory. It does not import archived selection/predictions to skip these stages.
4. `review.py app --name demo_01` creates a separate runnable application copy. Open `http://127.0.0.1:8765/?lang=en`.

New outputs are isolated under `runs/`. The original archived study is unchanged. A repeated experiment can be compared to the archived metrics and decisions; original source/data checksums are exact, whereas model-byte equality and hardware measurements are not promised across environments. See the main README for the evidence map and `VALIDATION.md` for what was actually tested.
