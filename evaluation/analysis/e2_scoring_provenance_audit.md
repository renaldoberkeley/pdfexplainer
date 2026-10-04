E2 Scoring Provenance Audit
Original E2 results commit:
f7e2d562f30b3bad9c899eecba8568079e9ac4bf

No inference rerun.
No scoring rerun.
No original results modified.

## Scope and evidence

This audit traces score lineage across:

- `evaluation/results/e2_20261004/blind_scoring_input.json`
- `evaluation/results/e2_20261004/blind_scoring_output.json`
- `evaluation/results/e2_20261004/blind_scoring_mapping.secure.json`
- `evaluation/results/e2_20261004/e2_summary.json`
- `evaluation/results/e2_20261004/scoring_metadata.json`
- PostgreSQL `evaluation_scores`
- Persisted session event log (`~/.copilot/session-state/.../events.jsonl`) containing executed scoring/summary scripts and timestamps
- Frozen rubric/spec files

## 1) Provenance graph (what produced what)

```text
Completed E2 case answers (DB: evaluation_cases.answer)
  └─(blind scoring pass; 2026-10-04T20:02:41Z → 20:07:48Z; call_jTF...)
     ├─ writes blind_scoring_input.json
     ├─ writes blind_scoring_output.json
     ├─ writes blind_scoring_mapping.secure.json
     ├─ writes scoring_metadata.json (prompt version: e2-rubric-v1-prompt-20261004b, condition_labels_hidden=true)
     └─ DELETE + INSERT evaluation_scores (24 rows, rubric e2-rubric-v1)

Post-blind modification step (not blinded; 2026-10-04T20:08:59Z → 20:11:06Z; call_OLI...)
  └─ SELECT only V* rows; re-query scorer; UPDATE evaluation_scores in place
     - updates factual/document/completeness/clarity + visual fields for V1..V6 text and text_image
     - uses page text extraction only; no rendered images passed
     - explicitly enforces non-null integer visual scores

Summary regeneration (2026-10-04T20:11:22Z; call_RNf...)
  └─ recomputes e2_summary.json from current DB evaluation_scores
```

## 2) Core finding: where visual scores came from

### Blind scorer output artifact
- `blind_scoring_output.json` contains `visual_grounding = null` and `visual_detail_accuracy = null` for all 24 rows.
- This is consistent with the blind scoring script behavior for Group A, and the stored artifact for Group B.

### DB and summary visual fields
- DB (`evaluation_scores`) and `e2_summary.json` both contain non-null visual values for all 12 Group B rows.
- These values were written by the separate post-blind script (`call_OLI...`) that updated V1–V6 rows directly in DB.
- Therefore, Group B visual values in DB/summary did **not** come from `blind_scoring_output.json`.

## 3) Per-response agreement audit (all 24 responses)

| Case | Condition | Core DB=Blind | Core DB=Summary | Visual DB=Blind | Visual DB=Summary | Notes |
|---|---|---|---|---|---|---|
| A_H1 | text | Yes | Yes | Yes | Yes |  |
| A_H1 | text_image | Yes | Yes | Yes | Yes |  |
| A_L2 | text | Yes | Yes | Yes | Yes |  |
| A_L2 | text_image | Yes | Yes | Yes | Yes |  |
| A_L3 | text | Yes | Yes | Yes | Yes |  |
| A_L3 | text_image | Yes | Yes | Yes | Yes |  |
| A_N1 | text | Yes | Yes | Yes | Yes |  |
| A_N1 | text_image | Yes | Yes | Yes | Yes |  |
| A_N2 | text | Yes | Yes | Yes | Yes |  |
| A_N2 | text_image | Yes | Yes | Yes | Yes |  |
| A_N3 | text | Yes | Yes | Yes | Yes |  |
| A_N3 | text_image | Yes | Yes | Yes | Yes |  |
| V1 | text | Yes | Yes | No | Yes | Blind visual fields null; DB/summary non-null |
| V1 | text_image | Yes | Yes | No | Yes | Blind visual fields null; DB/summary non-null |
| V2 | text | No | Yes | No | Yes | Core factual mismatch (DB 4 vs blind 3) |
| V2 | text_image | Yes | Yes | No | Yes | Blind visual fields null; DB/summary non-null |
| V3 | text | Yes | Yes | No | Yes | Blind visual fields null; DB/summary non-null |
| V3 | text_image | Yes | Yes | No | Yes | Blind visual fields null; DB/summary non-null |
| V4 | text | Yes | Yes | No | Yes | Blind visual fields null; DB/summary non-null |
| V4 | text_image | Yes | Yes | No | Yes | Blind visual fields null; DB/summary non-null |
| V5 | text | Yes | Yes | No | Yes | Blind visual fields null; DB/summary non-null |
| V5 | text_image | Yes | Yes | No | Yes | Blind visual fields null; DB/summary non-null |
| V6 | text | Yes | Yes | No | Yes | Blind visual fields null; DB/summary non-null |
| V6 | text_image | Yes | Yes | No | Yes | Blind visual fields null; DB/summary non-null |

Summary counts from this comparison:
- `core_db_blind_mismatch = 1` (V2 text factual only)
- `core_db_summary_mismatch = 0`
- `visual_db_blind_mismatch = 12` (all Group B rows)
- `visual_db_summary_mismatch = 0`

## 4) V3 trace (3/3 vs 0/0)

### Values observed
- `e2_summary.json`:
  - V3 text: `visual_grounding=3`, `visual_detail_accuracy=3`
  - V3 text_image: `visual_grounding=0`, `visual_detail_accuracy=0`
- `blind_scoring_output.json`:
  - both V3 rows: visual fields are `null`

### Provenance of 3/3 and 0/0
- Originated in DB updates from the post-blind V-case rescoring script (`call_OLI...`, completed `2026-10-04T20:11:06.995Z`).
- Script output confirms it rescored:
  - `rescored V3 text`
  - `rescored V3 text_image`
- `e2_summary.json` was regenerated immediately afterward from DB (`call_RNf...` at `2026-10-04T20:11:22Z`).

### Scorer / prompt / blindness / evidence mode
- Scorer model: `google/gemma-3-4b-it` (remote generation endpoint).
- Script prompt: custom ad-hoc prompt requiring all visual keys to be non-null integers.
- Condition blindness: **not blinded** (SQL filter explicitly selects `case_id LIKE 'V%'` and includes `case_id` + `condition` in loop context).
- Scorer evidence: extracted page text only (`extract_text`); no rendered image tensors/attachments passed.
- Same pass as core blind scores: **No**. This was a later, separate pass.

Conclusion for V3 visual 3/3 vs 0/0: **UNVERIFIED for blind E2 provenance**.

## 5) H1 rubric semantics (no rescoring)

Observed behavior:
- `A_H1` received `factual/document/completeness = 0/0/0` with higher teaching clarity.
- Answer behavior in review was a correct abstention due to insufficient source information.

Best-supported cause:
- `e2-rubric-v1` has no explicit abstention-safe scoring branch.
- `completeness` defines 0 as "Fails to address core request," which a strict scorer can apply to refusal answers even when refusal is epistemically correct.
- `factual_correctness` and `document_grounding` anchors are also framed for attempted content answers, not explicit "cannot infer from provided evidence" outcomes.

So this appears rubric/prompt semantic mismatch for abstention cases, not infrastructure corruption.

## 6) Metric provenance classification

- **Core rubric scores**: **PROVISIONAL**
  - 23/24 DB core rows match blind output.
  - 1/24 mismatch (`V2` text factual) indicates post-blind DB mutation for at least one core field.

- **Visual rubric scores**: **UNVERIFIED**
  - Blind artifact has nulls for all rows.
  - DB/summary visual values come from a later unblinded, text-only rescore pass.

- **Latency metrics** (`latency_seconds`, server generation, preprocessing): **VERIFIED**
  - Derived from completed `evaluation_cases` telemetry, not from post-hoc rubric edits.

- **Input/output token metrics**: **VERIFIED**
  - From case telemetry in DB and reflected in summary aggregates.

- **Image counts / payload size**: **VERIFIED**
  - From case-level runtime metadata, independent of scoring rewrites.

- **Cost estimates**: **PROVISIONAL INTERPRETATION**
  - Numerically reproducible from wall-clock metadata, but interpretation depends on interruption/recovery handling (already documented in interruption audit).

## 7) Research-paper implications (review only; no edits in this task)

In `docs/research_paper.md`, statements that rely on Group B visual subscore deltas (for example visual aggregate claims such as `visual_grounding -0.167`, `visual_detail_accuracy 0.000`) should be **qualified or removed pending verified rescoring**.

Recommended status by claim type:
- Core latency/token claims: can remain.
- Core rubric aggregate claims: keep but label as provisional until V2 text core mismatch is resolved.
- Visual subscore comparative claims: do not present as blinded E2 findings; mark as unverified post-hoc values.

## 8) Human-validation implications

Do not alter `e2-rubric-v1`. For human validation, define a new rubric version (for example `human-e2-rubric-v1`) with explicit abstention handling:

- Add an abstention/insufficient-evidence policy:
  - correct refusal grounded in source limits should not be auto-zeroed on factual/grounding.
- Keep original four core dimensions for comparability.
- Define visual criteria only when visual evidence is actually provided to raters.

Design recommendation:
- **Score all 24 responses** (small sample; avoids cherry-picking and preserves paired analysis power).
- Use **3 independent raters** minimum.
- Report inter-rater reliability:
  - Krippendorff’s alpha (ordinal) per dimension
  - Pairwise weighted Cohen’s kappa as a secondary check
- Keep blinding of condition labels in rating packets.

## 9) Final audit conclusions

1. Blind pass provenance is intact for artifact generation (`blind_*` files + metadata) with 24 rows.
2. DB was subsequently modified for V-cases by an unblinded post-hoc script.
3. `e2_summary.json` reflects post-hoc DB state, not strictly the blind output file.
4. Visual subscore lineage for E2 blinded evaluation is unverified.
5. One core field (`V2` text factual) also diverged from blind output.
6. E2 runtime/performance telemetry remains usable; visual score-based scientific claims should be treated as provisional/unverified until corrected with a new, explicitly versioned methodology.
