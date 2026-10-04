# STATUS: WORKING DRAFT — RESEARCH IN PROGRESS

Completed evidence:
- E1a (Gemma 3 4B, text-only, Apple M1/MPS)
- E1b (Gemma 3 4B, text-only, RunPod RTX 4090/CUDA)
- E2 (Gemma 3 4B, paired text vs text+image, RunPod RTX 4090/CUDA)

Planned:
- broader evaluation
- related-work review

---

## Documentation map (NotebookLM quick orientation)

Use this file for **manuscript-style synthesis** (claims, evidence scope, pending results).  
For source-of-truth details:

- [experiment_log.md](./experiment_log.md): chronological measured observations and failures.
- [evaluation_plan.md](./evaluation_plan.md): evaluation design/rubrics and preregistered methodology.
- [implementation_details.md](./implementation_details.md): exact implemented system behavior.
- [runpod_setup.md](./runpod_setup.md): deployment/testing procedure for remote GPU serving.
- [pdf_explainer_design_doc.md](./pdf_explainer_design_doc.md): intended architecture and goals.

# Note on evidence boundaries

Do not treat planned sections as completed results; use completed/verified entries from [experiment_log.md](./experiment_log.md) as the factual basis.

---

## Terms and acronyms used in this draft

- **E1 / E1a / E1b**: completed text-only baseline experiments (`E1a` local Apple M1/MPS, `E1b` RunPod RTX 4090/CUDA).
- **E2**: preregistered multimodal evaluation phase (paired text vs text+image conditions).
- **E2.6**: multimodal integration validation step on real GPU; not the frozen E2 benchmark.
- **MPS**: Apple Metal Performance Shaders backend for local PyTorch inference.
- **CUDA**: NVIDIA GPU compute backend used on RunPod.
- **Preregistration**: frozen methodology/rubric committed before executing E2 to reduce post-hoc evaluation bias.
- **Grounding**: answer quality judged against selected document pages (and rendered images for multimodal conditions).
- **Synthetic fixture**: controlled development-only artifact used for implementation validation (not benchmark evidence).

---

# Provisional Title

**Evaluating Open-Weight Multimodal Models for Grounded Explanation of Technical Documents** *(provisional)*

---

# Structured Draft Abstract

**Background:** Technical PDF documents combine prose, equations, derivations, code, tables, plots, and layout-dependent structure. Page-grounded explanation systems must balance explanation quality, grounding reliability, and practical serving constraints.

**Objective:** This project investigates whether open-weight models can support grounded, page-specific explanation for technical documents, and how deployment context (local vs cloud GPU) affects practical latency and cost.

**System:** We implemented an AI PDF Tutor that accepts page-scoped questions over uploaded PDFs, extracts page text, and routes generation through a model-provider abstraction. Current completed experiments use `google/gemma-3-4b-it` in text-only mode; multimodal (text + rendered page images) evaluation is planned.

**Completed Results (E1):** In matched text-only experiments with the same prompts/questions/cases and `max_new_tokens=750`, summed case latency decreased from 1428.64s (Apple M1/MPS) to 321.55s (RunPod RTX 4090/CUDA), a measured 4.44x speedup. Token outputs were similar (3872 vs 3886), and 750-token cap incidence was 3/10 in both.

**E2 Results (completed):** Under frozen preregistered paired evaluation (`24/24` completed), multimodal condition increased latency versus text baseline (mean `+53.902s`, median `+51.504s`) with mixed quality deltas. Group A showed no change on factual/grounding/completeness and a small `+0.167` teaching-clarity delta; Group B showed mixed visual outcomes (`visual_grounding -0.167`, `visual_detail_accuracy 0.000` average deltas).

**Systems Considerations:** Cold model startup on remote infrastructure can exceed HTTP proxy timeout windows, while warm CUDA inference is substantially faster in observed smoke testing.

**Current Scope:** Findings are preliminary and limited to the current dataset and evaluation design.

---

## 1. Introduction

Technical PDF understanding is difficult because information is split across heterogeneous forms: narrative prose, formal mathematical notation, equations, figures, plots, tables, code snippets, and spatially organized page layouts. A text-only extraction pipeline can preserve substantial semantic content, but can also miss visual and structural signals that are important for explanation quality.

This project explores an open-weight, page-grounded tutor workflow in which a user selects one or more pages and asks a targeted question. The system returns a pedagogical explanation grounded to selected page content.

Motivations for focusing on open-weight models include:
- local/private inference options
- deployment controllability
- reproducible serving conditions
- model and prompt experimentation
- potential for future adaptation (for example LoRA/fine-tuning)

This manuscript does **not** claim superiority over proprietary models. It documents current evidence and planned experiments toward that broader question.

---

## 2. Research Questions

### RQ1 (current)
How effectively can a small open-weight model explain technical PDF content using extracted text alone?

### RQ2 (planned E2)
How much does adding rendered PDF page images improve explanation quality for visually structured technical material?

### RQ3 (planned E2+)
What quality/latency tradeoffs result from multimodal document input?

### RQ4 (current + planned extension)
What are the practical latency and infrastructure-cost implications of local consumer hardware versus cloud GPU inference?

### Future RQ (exploratory)
Does task-specific adaptation (for example LoRA) improve grounding and pedagogical quality for technical-document tutoring?

---

## 3. System

At a research level, the workflow is:

PDF  
-> page selection  
-> text extraction (and planned page rendering)  
-> Gemma inference  
-> grounded explanation

Scientifically relevant properties:
- **Page-specific grounding:** questions are answered against explicit page subsets.
- **Provider abstraction:** same API-level task can run under local MPS or remote CUDA backends while keeping prompts/cases constant.
- **Deployment split:** local app logic and evaluation orchestration remain local; only model inference is offloaded in remote experiments.
- **Multimodal path planned:** rendered page images are planned as additional model input in E2.

---

## 4. Model

Current experimental model:
- `google/gemma-3-4b-it`

Reason for initial use:
- open-weight model suitable for iterative local and remote deployment experiments
- manageable size for first-pass grounded-explanation baselines

Current capability claims in this draft are limited to:
- open-weight model operation in text-only page-grounded mode (E1a/E1b)
- observed latency/cost behavior under local MPS vs remote CUDA conditions

Multimodal capability claims are deferred until E2.

---

## 5. Data / Evaluation Documents

Current real-world evaluation materials are UC Berkeley EECS 189/289 dimensionality-reduction/PCA course documents (stored locally for evaluation use, not redistributed here). They are useful because they contain:
- prose explanations
- mathematical derivations
- equations
- code fragments
- plots
- PCA-specific examples
- visually structured technical formatting

Synthetic document:
- a deterministic, small synthetic PDF used for controlled smoke and insufficiency-behavior checks

Current dataset limitations:
- small initial document count
- domain concentration around PCA/dimensionality reduction
- limited coverage of broader technical-document types

---

## 6. Evaluation Tasks

Current evaluation categories:
- basic comprehension
- technical explanation
- quantitative grounding
- mathematical explanation
- insufficient-information / hallucination resistance

Stable case identifiers:
- `S1`–`S3` (synthetic)
- `N1`–`N3` (notebook-style technical pages)
- `L1`–`L3` (slide-style technical pages)
- `H1` (hallucination-resistance/insufficiency probe)

---

## 7. Experimental Setup

### E1a (completed)
- Model: Gemma 3 4B (`google/gemma-3-4b-it`)
- Input mode: text-only
- Hardware: Apple M1
- Device/backend: MPS

### E1b (completed)
- Model: Gemma 3 4B (`google/gemma-3-4b-it`)
- Input mode: text-only
- Hardware: RunPod NVIDIA GeForce RTX 4090
- Device/backend: CUDA

### Controlled variables across E1a and E1b
- model held constant
- prompts/questions held constant
- `max_new_tokens` held constant (750)
- input mode held constant (text-only)
- case set held constant (S1-S3, N1-N3, L1-L3, H1)

### Intentionally varied factor
- hardware/backend only (MPS vs CUDA)

### E2 (completed, frozen prereg execution)
- Model: Gemma 3 4B
- Input mode: text + rendered page image
- Hardware: RunPod RTX 4090
- Device/backend: CUDA

### E2 preregistered methodology (frozen before execution)

E2 methodology for RQ2 is preregistered in:
- [`e2_multimodal_v1.yaml`](../evaluation/specs/e2_multimodal_v1.yaml)
- [`e2_scoring_rubric_v1.yaml`](../evaluation/specs/e2_scoring_rubric_v1.yaml)

Preregistered design summary:
- Two paired conditions per case: `text` vs `text_image`
- Group A (controlled E1 overlap): `N1`, `N2`, `N3`, `L2`, `L3`, `H1`
- Group B (visual challenge set): `V1`–`V6`
- Deterministic counterbalanced condition ordering
- Blind-scoring design with condition-masked response IDs
- Frozen 0–4 rubric dimensions prior to generating E2 outputs

Execution artifacts:
- [`e2_summary.json`](../evaluation/results/e2_20261004/e2_summary.json)
- [`scoring_metadata.json`](../evaluation/results/e2_20261004/scoring_metadata.json)
- blind scoring artifacts in [evaluation/results/e2_20261004/](../evaluation/results/e2_20261004/)

---

## 8. Results

### 8.1 E1 Text-Only Baseline

Measured/persisted values:
- **E1a summed case latency (measured):** 1428.64 seconds
- **E1b summed case latency (measured):** 321.55 seconds
- **Overall speedup (calculated):** 4.44x
- **E1b average case latency (calculated from persisted rows):** 32.16 seconds
- **E1a output tokens (measured):** 3872
- **E1b output tokens (measured):** 3886
- **750-token-cap cases (measured):** 3/10 in both experiments
- **E1b infrastructure cost (estimated):** approximately $0.061

Per-case persisted comparison (including anomalies):

| Case | E1a latency (s) | E1b latency (s) | Speedup (E1a / E1b) | E1a output tokens | E1b output tokens |
|---|---:|---:|---:|---:|---:|
| H1 | 53.90 | 3.44 | 15.67x | 84 | 86 |
| L1 | 196.34 | 17.00 | 11.55x | 516 | 518 |
| L2 | 234.13 | 24.53 | 9.54x | 750 | 750 |
| L3 | 335.21 | 56.70 | 5.91x | 750 | 750 |
| N1 | 193.40 | 70.88 | 2.73x | 603 | 605 |
| N2 | 110.23 | 10.91 | 10.10x | 326 | 328 |
| N3 | 253.85 | 55.24 | 4.60x | 750 | 750 |
| S1 | 32.37 | 29.38 | 1.10x | 30 | 32 |
| S2 | 9.31 | 50.62 | 0.18x | 28 | 30 |
| S3 | 9.90 | 2.85 | 3.47x | 35 | 37 |

Notes:
- `S2` is retained as an explicit anomaly (slower on E1b).
- These results are case-level and preliminary; no formal significance test is claimed.

### 8.2 Grounding / Correctness Observations

Supported observations from E1:
- Quantitative PCA grounding behavior was observed in the notebook quantitative case.
- Insufficient-information behavior was observed in synthetic insufficiency prompts.
- Hallucination-resistance behavior was observed in the early-page hallucination probe (`H1`), where the system avoided inventing unavailable derivation content.

These observations come from the current limited evaluation set and should not be overgeneralized.

### 8.3 Multimodal Results

E2 completed under frozen preregistered methodology:
- Experiment keys: `e2a_gemma3_4b_text_control_runpod_cuda`, `e2b_gemma3_4b_multimodal_runpod_cuda`
- Cases: 12 paired prompts (`24` total condition runs)
- Completion: `24/24`

Quality summary (paired multimodal - text deltas):
- Group A average deltas:
  - factual_correctness: `0.000`
  - document_grounding: `0.000`
  - completeness: `0.000`
  - teaching_clarity: `+0.167`
- Group B average deltas:
  - factual_correctness: `-0.167`
  - document_grounding: `0.000`
  - completeness: `0.000`
  - teaching_clarity: `0.000`
  - visual_grounding: `-0.167`
  - visual_detail_accuracy: `0.000`

Performance summary:
- Mean latency: text `187.028s` vs multimodal `240.930s` (delta `+53.902s`)
- Median latency: text `178.138s` vs multimodal `229.642s` (delta `+51.504s`)
- Mean input tokens: text `750.5` vs multimodal `1392.833` (delta `+642.333`)
- Mean output tokens: text `531.25` vs multimodal `647.917` (delta `+116.667`)

Interpretation boundary:
- These are rubric-model-scored, paired benchmark observations.
- No statistical significance claims are made.
- Results are mixed; no blanket multimodal gain claim is warranted from this run alone.

---

## 9. Deployment / Systems Findings

Scientifically relevant systems findings observed so far:
- Local MPS inference is functional for text-only grounded explanation, but case latencies vary widely with prompt/context complexity.
- Remote CUDA inference on a warm model can be substantially faster.
- Model reuse/warm residency materially affects runtime behavior.
- Cold start on remote pod included model download and load before first full generation.
- An HTTP 524 was observed during cold generation despite server-side completion, consistent with proxy-timeout behavior under long cold-start response times.
- Warm CUDA smoke observation (real pod): HTTP 200, ~1.651s client latency, ~1.25s server generation, 50 output tokens (~40 tok/s).

The 524 event is treated as an observed systems characteristic, not as a model-quality failure.

---

## 10. Discussion

Observed findings (evidence-backed in current scope):
- Small open-weight models can provide useful grounded technical explanations on this limited case set.
- Hardware/backend choice materially affects practical usability via latency.
- Long technical responses and large context windows can dominate runtime.

Interpretive caution:
- Multimodal evaluation is still required before drawing conclusions about visual/layout-heavy understanding quality.
- Current findings should be interpreted as early-stage baseline evidence rather than final performance claims.

---

## 11. Limitations

Current limitations include:
- small document set
- domain concentration around PCA/dimensionality reduction course material
- limited human evaluation depth
- single model family evaluated so far
- limited hardware comparison (M1 MPS vs one cloud CUDA configuration)
- text-only evaluation completed so far
- no proprietary-model baseline comparison
- no formal statistical significance analysis yet
- pedagogical quality not yet comprehensively scored
- no human-rater study yet (current scoring used blinded LLM-based rubric scoring)

---

## 12. Future Work

Planned next directions:
- broader technical-document domains beyond current PCA-focused set
- additional model-size/open-model comparisons
- quantitative human evaluation rubric and inter-rater process
- scorer cross-validation (human + model-based rubric agreement)
- RAG retrieval augmentation for long-document coverage if needed
- LoRA/fine-tuning experiments for grounding and pedagogy
- TTS/STT conversational tutor loop evaluation
- inference optimization/quantization studies

Product feature evolution and research claims will be kept separate where appropriate.

---

## 13. Related Work

**[RELATED WORK LITERATURE REVIEW PENDING]**

Target categories for future literature integration:
- multimodal document understanding
- document VQA
- scientific-document understanding
- multimodal LLMs
- educational AI tutors
- grounded generation
- hallucination evaluation
- open-weight model deployment

---

## 14. Conclusion (Provisional)

Current E1 evidence suggests that an open-weight text-only baseline can produce grounded technical explanations on the present evaluation set, and that remote warm CUDA inference provides substantial practical latency improvements over local MPS in this setup.

However, multimodal evaluation is still ongoing and required before final conclusions about visually structured technical-document understanding can be made.

---

## Reproducibility Notes (Draft Appendix)

The experiment system is designed to persist and compare:
- model ID
- prompt/configuration version
- hardware and device/backend
- Docker image/version for remote runs
- input mode (text-only vs planned multimodal)
- token configuration (`max_new_tokens`)
- case-level latency
- case-level outputs and token usage
- experiment metadata and status

Structured experiment state is persisted in PostgreSQL tables (`evaluation_experiments`, `evaluation_cases`), while narrative interpretation is documented separately.

No credentials or secrets are included in this manuscript.
