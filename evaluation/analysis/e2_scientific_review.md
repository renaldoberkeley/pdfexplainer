# E2 Scientific Review
**Status:** Post-hoc analysis of frozen E2 results  
**Source results commit:** `f7e2d562f30b3bad9c899eecba8568079e9ac4bf`

## Guardrails (confirmed)
- No inference was rerun.
- No scoring was rerun.
- No frozen methodology was changed.
- No E2 result artifacts were modified.

---

## 0) Inputs reviewed

Primary artifacts:
- [blind_scoring_input.json](../results/e2_20261004/blind_scoring_input.json)
- [blind_scoring_mapping.secure.json](../results/e2_20261004/blind_scoring_mapping.secure.json)
- [blind_scoring_output.json](../results/e2_20261004/blind_scoring_output.json)
- [e2_summary.json](../results/e2_20261004/e2_summary.json)
- [interruption_audit_snapshot.json](../results/e2_20261004/interruption_audit_snapshot.json)
- [scoring_metadata.json](../results/e2_20261004/scoring_metadata.json)

Documentation context:
- [experiment_log.md](../../docs/experiment_log.md)
- [evaluation_plan.md](../../docs/evaluation_plan.md)
- [research_paper.md](../../docs/research_paper.md)

Frozen methodology references (unchanged vs prereg `f2ca496`):
- [e2_multimodal_v1.yaml](../specs/e2_multimodal_v1.yaml)
- [e2_scoring_rubric_v1.yaml](../specs/e2_scoring_rubric_v1.yaml)

---

## 1) Paired-response reconstruction (text vs text+image)

All 12 case pairs were reconstructed from blind input + secure mapping (post-hoc only):
- Group A: `A_N1, A_N2, A_N3, A_L2, A_L3, A_H1`
- Group B: `V1, V2, V3, V4, V5, V6`

Observed pattern at answer level:
- Most pairs are **structurally similar explanations** with text+image versions generally longer and more elaborative.
- In many cases, multimodal answers appear to add formatting/examples more than new grounded facts.
- A_H1 refusal behavior is consistent across both conditions (correctly declines unavailable derivation).

Case-level metrics snapshot (from `e2_summary.json`):

|Case|F text/mm|G text/mm|C text/mm|T text/mm|VG text/mm|VD text/mm|Latency text/mm (s)|Δlatency (s)|Δoutput tokens|
|-|-|-|-|-|-|-|-|-|-|
|A_N1|4/4|4/4|4/4|4/4|—|—|197.780/261.328|+63.548|+120|
|A_N2|4/4|4/4|4/4|4/4|—|—|144.500/180.454|+35.954|+134|
|A_N3|4/4|4/4|4/4|4/4|—|—|264.284/228.816|-35.468|+0|
|A_L2|4/4|4/4|4/4|4/4|—|—|261.299/306.631|+45.332|+0|
|A_L3|4/4|4/4|4/4|4/4|—|—|355.376/360.031|+4.655|+0|
|A_H1|0/0|0/0|0/0|3/4|—|—|35.382/78.153|+42.771|+64|
|V1|4/4|4/4|4/4|4/4|4/4|4/4|127.675/298.912|+171.237|+394|
|V2|4/3|4/4|4/4|4/4|2/3|2/3|211.249/230.468|+19.219|+0|
|V3|4/4|4/4|4/4|4/4|3/0|3/0|129.960/148.051|+18.091|+97|
|V4|4/4|4/4|4/4|4/4|3/4|3/4|194.826/217.808|+22.982|+166|
|V5|4/4|4/4|4/4|4/4|3/3|3/3|160.558/223.016|+62.458|+223|
|V6|4/4|4/4|4/4|4/4|3/3|3/4|161.451/357.497|+196.046|+202|

---

## 2) Answer-level comparison findings

### Group A (A_N1–A_L3, A_H1)
- `A_N1/A_N2/A_N3/A_L2/A_L3`: text and multimodal answers are substantively aligned on claims and reasoning; multimodal variants are mostly longer and more tutorial-like.
- `A_H1`: both conditions correctly refuse to derive unavailable equations from insufficient source content.

### Group B (V1–V6): did image input add unique visual information?

Classification scale:
- **A** clear multimodal benefit
- **B** modest multimodal benefit
- **C** effectively equivalent
- **D** multimodal regression
- **E** ambiguous/inconclusive

|Case|Classification|Rationale from paired answers|
|-|-|-|
|V1|C (effectively equivalent)|Both answers describe the two-cluster projection similarly; multimodal version is much longer but not clearly more grounded.|
|V2|E (ambiguous/inconclusive)|Both identify multimodal distribution and separated groups; multimodal does not clearly add image-exclusive facts, while rubric deltas conflict across dimensions.|
|V3|E (ambiguous/inconclusive)|Text and multimodal answers both explain low-rank/redundancy similarly; large visual-score drop in summary is not well-explained by answer content.|
|V4|B (modest benefit)|Multimodal answer appears somewhat richer on taxonomy sub-branches/examples, but core hierarchical explanation already present in text-only answer.|
|V5|C (effectively equivalent)|Both explain matrix factorization flow and dimension alignment well; multimodal is longer but not clearly more specific.|
|V6|B (modest benefit)|Multimodal answer adds more explicit trend detail (k-vs-RMSE narrative), but at very large latency cost; improvement magnitude appears modest.|

No case showed unambiguous **A-level** (clear) multimodal benefit in this dataset.

---

## 3) Automated-score review (credibility vs questionable regions)

Scorer metadata:
- model: `google/gemma-3-4b-it`
- scorer type: `llm_rubric`
- rubric: `e2-rubric-v1`
- prompt version: `e2-rubric-v1-prompt-20261004b`
- condition labels hidden: `true`

### Well-supported
- Many core `4/4/4/4` scores for clear explanatory responses appear directionally plausible.
- `A_H1` teaching clarity increase (`3 -> 4`) is plausible: multimodal refusal is more explicit and better structured.

### Questionable / potentially inconsistent
1. **Ceiling compression:** a very high mass at maximum scores (details below) reduces sensitivity to genuine incremental differences.
2. **A_H1 rubric behavior:** `0/0/0` despite correct refusal suggests rubric under-models “correct abstention under insufficient evidence.”
3. **V3 visual drop (`3 -> 0`, `3 -> 0`)** appears difficult to reconcile with answer-level similarity.
4. **Artifact consistency issue:** in [blind_scoring_output.json](../results/e2_20261004/blind_scoring_output.json), `visual_grounding` and `visual_detail_accuracy` are `null` for all 24 scored rows, while [e2_summary.json](../results/e2_20261004/e2_summary.json) reports non-null visual deltas for Group B. This provenance mismatch should be treated as a reliability caveat for visual-subscore interpretations.

Bottom line: core scorer outputs are useful as weak directional evidence, but not sufficient alone for strong quality claims.

---

## 4) Ceiling-effect analysis

### Group A (n=6)
- factual_correctness: text 4s = 5/6 (83.3%), mm 4s = 5/6 (83.3%)
- document_grounding: text 4s = 5/6 (83.3%), mm 4s = 5/6 (83.3%)
- completeness: text 4s = 5/6 (83.3%), mm 4s = 5/6 (83.3%)
- teaching_clarity: text 4s = 5/6 (83.3%), mm 4s = 6/6 (100%)

### Group B (n=6)
- factual_correctness: text 4s = 6/6 (100%), mm 4s = 5/6 (83.3%)
- document_grounding: text 4s = 6/6 (100%), mm 4s = 6/6 (100%)
- completeness: text 4s = 6/6 (100%), mm 4s = 6/6 (100%)
- teaching_clarity: text 4s = 6/6 (100%), mm 4s = 6/6 (100%)
- visual_grounding: text 4s = 1/6 (16.7%), mm 4s = 2/6 (33.3%)
- visual_detail_accuracy: text 4s = 1/6 (16.7%), mm 4s = 3/6 (50.0%)

### Overall (core dimensions, n=12)
- factual_correctness: text 4s = 11/12 (91.7%), mm 4s = 10/12 (83.3%)
- document_grounding: text 4s = 11/12 (91.7%), mm 4s = 11/12 (91.7%)
- completeness: text 4s = 11/12 (91.7%), mm 4s = 11/12 (91.7%)
- teaching_clarity: text 4s = 11/12 (91.7%), mm 4s = 12/12 (100%)

### Ceiling implication
For each core dimension, **11/12 paired comparisons (91.7%)** had text baseline already at the max (4), making positive multimodal deltas impossible for those pairs in that dimension.

Conclusion: E2 core rubric is heavily ceiling-constrained for this case set.

---

## 5) Visual-case deep dive (V1–V6)

### V1 (projection geometry / separability)
- Text-only: describes two clusters and separability intuition.
- Multimodal: same core claims, more elaboration.
- Image contribution: not clearly unique.
- Errors introduced: none clear.
- Score fairness: equivalent scoring seems reasonable.

### V2 (multimodal distribution / category structure)
- Text-only: identifies multimodal peaks and empty regions; discusses Gaussian fitting.
- Multimodal: similar interpretation; somewhat richer wording.
- Image contribution: possible modest support, but not clearly exclusive.
- Errors introduced: factual subscore dropped in summary despite similar content.
- Score fairness: mixed; visual gain + factual drop appears unstable vs answer similarity.

### V3 (table low-rank redundancy)
- Text-only: explains redundancy among rectangle-derived columns.
- Multimodal: highly similar explanation and claims.
- Image contribution: not clearly additional.
- Errors introduced: no clear new errors in answer text.
- Score fairness: summary’s `visual_grounding/detail = 3 -> 0` looks inconsistent with pair similarity; likely scoring/rubric artifact or provenance issue.

### V4 (taxonomy hierarchy)
- Text-only: correct hierarchy and branch explanations.
- Multimodal: more detailed examples/subcategories.
- Image contribution: plausible modest help in richer structuring.
- Errors introduced: none obvious.
- Score fairness: modest visual improvement (`3 -> 4`) is plausible.

### V5 (factorization flow diagram)
- Text-only: explains X, Z, W and dimensional alignment.
- Multimodal: same structure with extra pedagogical detail.
- Image contribution: not clearly unique.
- Errors introduced: none obvious.
- Score fairness: equivalence is reasonable.

### V6 (reconstruction tradeoff figure)
- Text-only: explains compression-quality tradeoff and RMSE meaning.
- Multimodal: adds more explicit trend narrative and concrete setting detail.
- Image contribution: plausible modest benefit.
- Errors introduced: none obvious.
- Score fairness: slight visual-detail gain (`3 -> 4`) is plausible.

---

## 6) H1 insufficient-information review

Case `A_H1` asks for derivation/equation not present in source pages.

Observed:
- Both conditions correctly refused and stated missing information.
- Scores: factual/document_grounding/completeness = `0/0/0`; teaching clarity `3 -> 4`.

Interpretation:
- This likely reflects a rubric-design limitation: correct abstention is not rewarded under current factual/grounding/completeness definitions.
- This should be treated as a **rubric semantics issue**, not model hallucination.

---

## 7) Length / token effect

From E2 summary:
- mean output tokens: text `531.25` vs multimodal `647.917` (`+116.667`)

Pattern:
- Multimodal answers are often longer and more didactic.
- Additional length frequently appears as elaboration/formatting, not necessarily new grounded content.
- Higher length does **not** reliably map to higher rubric improvement (many no-change pairs despite longer multimodal outputs).

---

## 8) Latency-quality tradeoff

Given:
- mean latency: text `187.028s`, multimodal `240.930s` -> **+28.82%**
- median latency: text `178.138s`, multimodal `229.642s` -> **+28.91%**

Case-level tradeoff patterns:
- **Higher latency, no clear quality gain:** A_N1, A_N2, A_L2, A_L3, V1, V5.
- **Higher latency with modest gain:** A_H1 (clarity), V4 (visual), V6 (visual detail).
- **Higher latency with regression/mixed:** V2 (factual down, visual up), V3 (visual down in summary).
- **Unexpected faster multimodal:** A_N3 (`-35.468s`) with no quality change.

Conclusion:
- The latency increase is robust at aggregate level.
- Quality effects are mixed and mostly modest; several expensive multimodal calls yielded little or no measured quality benefit.

---

## 9) Scorer limitations (observed behavior vs methodological risk)

### Observed behavior
- High concentration at top scores on core dimensions.
- Limited separation power on many pairs.
- Inconsistency/caveat around visual-subscore provenance (`blind_scoring_output` null vs `e2_summary` non-null).

### Methodological risk (not proof of occurrence)
- Same model family for generation and scoring may introduce:
  - self-preference or stylistic affinity
  - correlated blind spots
  - leniency toward similarly phrased explanations
  - weaker detection of subtle unsupported claims

Interpretation: treat LLM-rubric scoring as provisional; independent validation is needed for stronger claims.

---

## 10) Proposed small human-validation study (design only)

Recommended minimal design:
- Scope: all 12 paired cases (24 responses) if feasible; if not, prioritize `A_H1` + `V1–V6` + one long technical pair (`A_L3`).
- Raters: **3 independent raters**.
- Blinding: keep condition labels hidden (same as current blind protocol).
- Rubric: reuse `e2-rubric-v1` for comparability, plus an explicit instruction for “correct abstention under missing evidence.”
- Reliability metric: Krippendorff’s alpha (ordinal) per dimension; report percent exact agreement too.
- Comparison to LLM scores: per-dimension correlation + disagreement heatmap; explicitly audit discordant cases (`A_H1`, `V2`, `V3`, `V6`).

This is the highest-value near-term validity booster for the paper with moderate workload.

---

## 11) Was E2 visual challenge hard enough?

Likely not hard enough for strong multimodal separation:
- Several V cases appear answerable from extracted text/context alone.
- Many multimodal responses do not show clearly image-exclusive facts.

Future harder visual benchmark characteristics:
- critical information absent from OCR/text extraction
- spatial relationships and geometry
- color/legend decoding
- arrow/connectivity interpretation
- multi-panel comparison
- equation layout structure not reducible to linear text
- visually encoded table structure where row/column layout matters

---

## 12) What E2 supports vs does not support

### Supported by E2
- Under this setup, multimodal requests increased latency (~29% mean and median).
- Quality effects were mixed and case-dependent, not uniformly positive.
- Correct refusal behavior occurred on insufficient-information case (`A_H1`), though rubric handling is debatable.

### Tentatively suggested
- Some visual tasks (e.g., V4/V6) may gain modestly from image input.
- Many tasks in this benchmark may be near-saturated under current rubric/model pairing.

### Not supported
- Strong claim that multimodal consistently improves answer quality.
- Strong claim that visual-score deltas are robust, given artifact/provenance caveat.
- Generalization beyond this small PCA-focused benchmark.

---

## 13) Research paper review (no edits made)

Review target: [research_paper.md](../../docs/research_paper.md)

### Appropriately supported
- “mixed quality deltas” framing
- latency increase with multimodal condition
- explicit limitation notes (small sample, no human evaluation, scorer-model caveats)

### Needs added qualification (conceptual recommendation)
1. Any sentence implying visual-subscore precision should acknowledge the visual-score provenance caveat (`blind_scoring_output` has null visual fields).
2. Strong causal wording around multimodal quality should remain cautious (“suggests” / “mixed” / “preliminary”).
3. Discussion should explicitly state ceiling constraints on core dimensions (91.7% text-at-4).

### Should wait for human validation
- Claims about subtle superiority on visual grounding/detail.
- Claims about robustness of rubric-level improvements.

No evidence of major overclaiming was found, but the above caveats should be explicit in final manuscript polishing.

---

## 14) Ranked next research steps (A–E)

Ranking by scientific value for current paper:
1. **Option A — Human validation of E2** (highest immediate validity gain)
2. **Option B — Harder visual-dependence benchmark** (addresses construct validity of multimodal benefit)
3. **Option C — Additional open-weight model comparison** (improves external validity)
4. **Option D — Prompt optimization** (may improve outcomes but less diagnostic scientifically right now)
5. **Option E — LoRA/fine-tuning** (high effort; premature before resolving measurement validity)

### Recommended next step
**Option A (Human validation) first**, then Option B.

Reason:
- Current bottleneck is **measurement credibility**, not only model capability.
- Human blind ratings can test whether observed LLM-rubric differences are trustworthy, especially for `A_H1`, `V2`, `V3`, `V6`.
- Once scoring validity is strengthened, a harder visual benchmark can more cleanly test true multimodal advantage.

---

## 15) Final scientific summary statement check

The following statement is supported by current evidence:

> “On this initial technical-document benchmark, adding rendered page images increased response latency while producing mixed, task-dependent quality effects under blinded model-based rubric evaluation.”

Why supported:
- latency increase is clear and substantial (~29% aggregate),
- quality deltas are mixed across cases/dimensions,
- evaluation is blinded and model-based,
- limitations are material (small sample, PCA domain, same-family scorer, ceiling, no human raters, missing persisted server/payload telemetry in benchmark rows).

