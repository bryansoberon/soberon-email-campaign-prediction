# Package preparation and portability checks — 28 October 2026

The reviewer package was copied to a separate directory and executed using the existing project environment: **Windows 11, Python 3.14.2**. All **47 pinned dependency versions** matched `study/requirements-lock.txt`. The independent folder did not depend on thesis documents or the original project working directory for its commands.

| Check performed | Result |
|---|---|
| Original S1 members and recorded digests | 140 files preserved byte for byte; 139 original member checksums verified |
| Frozen code, protocol, selection and four model hashes | PASS |
| Principal-test count, dates, mature-history rule and prediction ranges | PASS; 275,535 campaigns |
| Metrics, monthly summaries, development arithmetic and prediction-group means/counts | PASS |
| Main, sensitivity and ablation intervals recomputed from saved predictions | All eight match within numerical tolerance; original seeds and repetition counts |
| Numerical comparisons in the reviewer checker | **538 passed**, including interval comparisons |
| Existing software tests | **17 passed**: 10 application, 5 temporal-integrity, 2 metric/interval tests |
| Exported numerical cells vs manuscript Tables 4–7 | **50 matched** at the article's displayed precision |
| Regenerated article Figures 1–4 | PNG files match the embedded article images byte for byte on the tested platform; PNG/PDF/SVG generated; text-bound checks passed |
| Article Figure 5 | Exact archived screenshot extracted from the manuscript |
| Fresh source-data reproduction setup | PASS; supplied original 322 MB CSV checksum verified; seven frozen source/protocol/environment files verified |
| Fresh setup isolation | No archived selection, models, predictions or final evaluation copied into the new reproduction |
| Run overwrite, path traversal and modified source | Refused as intended |

The isolated `verify --intervals` execution ran from **15:53:54 to 15:54:45 UTC** on 28 October 2026. This is a verification-run observation, not a performance guarantee for other machines. Portable machine-readable evidence is in `validation/preparation_validation.json` and `validation/saved_results_verification.json`.

**Not executed during package preparation:** full model retraining from the raw CSV, installation into a new virtual environment, a new network download of the dataset, or testing on another operating system. The full reproduction route is supplied; only its source-data setup was exercised. Thus these checks establish independent-folder verification of the archived outputs and runnable setup, not an independently completed retraining replication.

The original application tests emitted `ResourceWarning` messages for three HTTP response files that the test client did not explicitly close. All 17 tests returned `OK`; the frozen test code was preserved. The bootstrap verification reads archived observations/predictions and does not adjust any model, variable, configuration or threshold.

## Font portability correction

The presentation code now chooses the first installed family among Arial, Liberation Sans and DejaVu Sans. The original strict margin assertions remain when Arial is used. With an alternative font, the same checks issue recorded warnings rather than aborting numerical verification. Scientific errors, missing inputs and genuine rendering failures still fail. The method, dataset, fitted models, random seeds and interval calculations are unchanged.

A new isolated Windows/Python 3.14.2 execution forced **DejaVu Sans** through `verify --intervals --font "DejaVu Sans"`. It completed all 538 numerical comparisons, eight interval recomputations, 17 tests, table exports and all four article figures. One Figure 1 header-margin warning was recorded, and the wrapper returned `VERIFICATION_PASS`. This reproduces the missing-Arial failure condition without claiming a new Linux test. The original five reference images remain unchanged.
