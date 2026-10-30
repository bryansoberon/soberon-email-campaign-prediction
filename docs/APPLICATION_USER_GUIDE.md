# Application user guide

## 1. What is included

This repository contains the complete **local email campaign prediction application**, its shared feature-construction method, the fitted models and a compatible public-data demonstration. It estimates 72-hour unique-click and unsubscribe rates before a campaign is sent. It does not send email, connect to an advertising account or retrain models during normal application use.

The interface is bilingual. Open the explicit English address below; the **EN / ES** links switch the presentation language. Internal field names, matching identifiers and API routes remain stable.

## 2. Install and launch

Use the recorded environment when possible: Windows 11 and Python 3.14.2. See `VALIDATION.md` for the tested environment and font-portability checks. Install the pinned dependencies in a virtual environment:

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -r study\requirements-lock.txt
.venv\Scripts\python.exe -X utf8 review.py app --name application_01
```

For an already configured Linux environment, the entry command is the same with that environment's Python executable:

```bash
python -X utf8 review.py app --name application_01
```

Open **http://127.0.0.1:8765/?lang=en**. The server listens only on the local machine. Keep the terminal open; press Ctrl+C there to stop. Use a new run name for each fresh application copy. To reopen an existing application workspace, run that copy's original launcher:

```powershell
.venv\Scripts\python.exe -X utf8 runs\application_01\scripts\serve_local.py
```

The wrapper prepares the archived application figures before starting the server. It uses existing models and public demo data; the 322 MB source CSV is not needed for this route.

## 3. Explore the public demonstration

1. **Overview:** inspect the loaded campaign count and historical response summary. The supplied demo contains records from the public dataset, not private client uploads.
2. **History:** choose a sender company and inspect recorded sending times, sent-email counts, unique clicks and unsubscribes.
3. **Estimate campaign:** use **Load example** to populate a compatible historical case. The query instant controls which earlier responses are available. Review the company/campaign identifiers, UTC date and message properties, then choose **Calculate estimate**.
4. Inspect both estimated rates, available mature-history count and any fallback/scope warnings. A saved historical query is a replay performed now; it is not presented as a forecast made at the historical sending date.
5. **Compare outcomes:** inspect saved estimates and the recorded reserved-test examples. The application distinguishes the registration time from the campaign sending time and matches observations using company, campaign, time and message properties.
6. **Temporal evaluation:** review archived method/baseline errors and monthly evidence. MAE reductions describe error reduction, not click uplift, accuracy percentages or business gains.

The archived English screenshots are under `study/results/capturas/en/`. The current article interface image is `reference_figures/figure05.png`.

## 4. Import a compatible campaign history

On **Overview**, use **CSV template** or **Real-data example** to obtain the exact column structure. Select a CSV and choose **Validate and import**. The original compatible example is also in `study/runtime/historial_real_ejemplo.csv`.

The history contract has 19 required columns:

| Group | Required columns |
|---|---|
| Matching and time | `client_id`, `campaign_id`, `campaign_sent_time` |
| Campaign eligibility and volume | `campaign_test_type`, `campaign_subscribers_count` |
| Message size/counts | `message_content_size`, `message_images_count`, `message_embedded_images_count`, `message_embedded_images_size`, `message_embedded_files_count`, `message_embedded_files_size`, `message_links_count` |
| Personalization | `message_personalization_tags_count`, `message_personalization_tags_in_sender_email_count`, `message_personalization_tags_in_subject_count`, `message_personalization_tags_in_html_body_count`, `message_personalization_tags_in_text_body_count` |
| Mature observed responses | `campaign_unique_clicks_count_4320`, `campaign_resigned_count_4320` |

Use unambiguous UTC/timezone-aware timestamps and preserve stable company/campaign identifiers. Counts and structural attributes must be finite and nonnegative; sending volume must be positive and response counts cannot exceed it. The principal study excludes A/B/optimizer campaign types. Imported historical response counts must follow the same cumulative 72-hour definitions. Do not treat missing message properties as zeros unless zero is the actual value.

A compatible schema alone does not establish equivalent measurements from another provider. Verify definitions and timing first, then evaluate transfer separately. No recipient-level personal details or message bodies are required by this contract.

## 5. Estimate a new campaign

Supply the company identifier, a unique campaign identifier, the planned/query sending instant and all 12 message properties. **Do not supply the new campaign's future clicks, unsubscribes or final sending volume as predictors.** The application derives histories from eligible earlier records whose sending time + 72 hours is strictly before the query instant.

With at least five mature prior campaigns, it uses the frozen selected models. With less history, it uses the fixed global-median fallback and identifies that condition. A new company therefore does not imply validated unseen-company transfer.

Outputs are central rate estimates in percent. The models were selected for mean absolute error; their outputs are not validated individual probabilities, expected event counts, prediction intervals or promises of improved campaign outcomes. High rates were systematically underestimated in the archived diagnostics.

## 6. Persist, compare and export

Saved estimates and user imports belong to that run's local `runtime/workspace/`. Reopening the same run preserves them. They are excluded from repository/ZIP distribution.

Use the application's saved-result download link to export recorded estimates. To associate an observed response later, import a matching completed historical record with the same identifiers, sending instant and message properties. A modified message must not inherit another message's observed outcome; this is covered by an integration test.

**Restore demo** changes the active loaded history back to the supplied public example; it is not a model-training operation. Use a new application run for an entirely separate workspace.

## 7. Common issues

| Symptom | Action |
|---|---|
| `Run already exists` | Choose a new name, or reopen the existing run with its `scripts/serve_local.py` launcher |
| `Integrity check failed` | Use the unmodified delivered package or inspect the named file; do not regenerate hashes merely to hide an unintended edit |
| Missing Python package or incompatible model loader | Use the pinned dependency file and recorded Python environment; do not assume the Linux report validates arbitrary versions |
| Port 8765 is occupied | Stop another instance of this local application before launching a new one |
| Interface appears in Spanish | Open the address with `?lang=en` or select EN |
| CSV rejected | Compare with the supplied template, exact column names, timestamp formats, uniqueness and count constraints |
| Limited-history warning | Fewer than five previous response windows were mature at the query instant; inspect dates rather than adding future outcomes |
| Article font warning | Alternative-font rendering may differ; inspect the provided reference figures and `review_outputs/article_figures/render_manifest.json` |

For scientific design and interpretation, see [Method and protocol](METHOD_AND_PROTOCOL_EN.md). For result verification or a full retraining run, follow the separate reviewer routes in the main README.
