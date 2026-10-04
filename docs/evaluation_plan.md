# AI PDF Tutor — Evaluation Plan

This document defines **how to evaluate whether the AI PDF Tutor is improving** as an ML system.

It focuses on evaluation methodology, not implementation details.

---

## 1. Evaluation Goals

Primary goal:

> Determine whether changes to model, prompt, document processing, multimodal inputs, or inference configuration produce **more correct, grounded, and useful explanations**.

Evaluation dimensions:

- factual accuracy
- document grounding
- teaching/explanation quality
- equation understanding
- figure/diagram understanding
- hallucination resistance
- follow-up question consistency
- latency
- memory/compute efficiency

The key question is not “did it answer?” but:

> “Did it produce a correct, grounded, pedagogically useful explanation for the selected document content?”

---

## 2. Evaluation Principles

- Use the **same evaluation cases** when comparing models/prompts.
- Separate **quality evaluation** from **performance evaluation**.
- Distinguish:
  - document-grounded claims
  - model prior knowledge
- Record full experiment metadata (model/config/prompt/input mode).
- Keep experiments reproducible.
- Change one major variable at a time when possible.
- Explicitly mark hypotheses; do not assume outcomes.

---

## 3. Evaluation Dataset

Define a future dataset format (e.g., JSONL), one case per row:

```json
{
  "id": "string",
  "document": "string",
  "pages": [4],
  "question": "string",
  "question_type": "string",
  "expected_concepts": ["string"],
  "reference_answer": "string",
  "requires_visual_understanding": false,
  "difficulty": "easy|medium|hard"
}
```

Illustrative examples:

```json
{
  "id": "attn-eq-p4",
  "document": "attention_is_all_you_need.pdf",
  "pages": [4],
  "question": "What does scaled dot-product attention compute?",
  "question_type": "equation_understanding",
  "expected_concepts": ["query-key similarity", "softmax weighting", "value aggregation", "scaling by sqrt(d_k)"],
  "reference_answer": "Should explain purpose, variables, operation, and intuition.",
  "requires_visual_understanding": false,
  "difficulty": "medium"
}
```

```json
{
  "id": "fig2-encoder-decoder",
  "document": "attention_is_all_you_need.pdf",
  "pages": [3],
  "question": "Explain Figure 2 and how its components relate.",
  "question_type": "figure_understanding",
  "expected_concepts": ["encoder stack", "decoder stack", "attention connections"],
  "reference_answer": "Should map visible blocks/arrows to their role.",
  "requires_visual_understanding": true,
  "difficulty": "hard"
}
```

```json
{
  "id": "insufficient-info-p1",
  "document": "toy_ml_intro.pdf",
  "pages": [1],
  "question": "What optimizer hyperparameters were used in the experiments on page 9?",
  "question_type": "insufficient_information",
  "expected_concepts": ["state insufficient information"],
  "reference_answer": "Should explicitly say selected page does not contain enough info.",
  "requires_visual_understanding": false,
  "difficulty": "easy"
}
```

```json
{
  "id": "cross-page-method-result",
  "document": "paper_x.pdf",
  "pages": [5, 8],
  "question": "How does the method on page 5 relate to the result on page 8?",
  "question_type": "cross_page_reasoning",
  "expected_concepts": ["method-result linkage", "assumptions", "limitations"],
  "reference_answer": "Should connect method details to reported outcome.",
  "requires_visual_understanding": false,
  "difficulty": "hard"
}
```

---

## 4. Question Categories

- **Basic comprehension**  
  “What is the main point of this page?”

- **Technical mechanism**  
  “How does this algorithm work?”

- **Equation understanding**  
  “What does this equation calculate?”

- **Figure understanding**  
  “Explain Figure 2.”

- **Cross-page reasoning**  
  “How does the method on page 5 relate to the result on page 8?”

- **Terminology**  
  “What does X mean in this context?”

- **Insufficient-information tests**  
  Questions intentionally not answerable from selected pages.

- **Follow-up questions**  
  Questions whose meaning depends on prior turns.

Insufficient-information and follow-up categories are critical for hallucination and consistency analysis.

---

## 5. Quality Metrics

Use explicit rubrics; do not treat generation success as quality.

### Document Grounding
Does the answer reflect supplied pages?

### Factual Accuracy
Are claims correct with respect to document content (and known facts when relevant)?

### Completeness
Does the answer cover key concepts required by the question?

### Explanation Quality
Is it understandable, structured, and pedagogically useful?

### Equation Fidelity
Does it correctly identify:
- variables
- operations
- relationships
- purpose/intuition

### Visual Grounding
When visuals are required, does explanation match the actual figure/table/diagram?

### Hallucination Rate
Does it invent claims/equations/figures/citations/page content?

### Page Attribution
If it attributes content to page(s), is attribution correct?

### Follow-up Consistency
Does it stay coherent and non-contradictory across turns?

Suggested manual scoring rubric (0–4) per metric:
- 4 excellent
- 3 good
- 2 partially correct/useful
- 1 major problems
- 0 incorrect/unusable

These are not currently automated in the repo.

---

## 6. Performance Metrics

Track separately:

- model load time
- time to first token (when measurable)
- total inference latency
- tokens generated
- tokens/second
- memory usage
- input context size
- output size

Always separate:
- **COLD** inference (model load required)
- **WARM** inference (model already loaded)

---

## 7. Experiment Metadata

Each experiment record should include:

- date/time
- model ID
- model revision/version (if available)
- parameter size
- quantization mode
- device
- dtype
- prompt version
- input mode (text-only vs text+image)
- max_new_tokens
- document name
- page list
- question
- latency metrics
- output text
- quality scores

Without this, comparisons are hard to trust or reproduce.

---

## 8. Baseline

Initial intended baseline (E1a local):

- Model: `google/gemma-3-4b-it`
- Input: extracted PDF text
- Device: Apple MPS (when available)
- No RAG
- No fine-tuning
- No page image input
- TTS excluded from LLM answer-quality measurement

Baseline V1 for E1a was established from stable real-Gemma local runs.
E1b (same cases/prompts/config on remote CUDA) is now recorded under experiment key `e1b_gemma3_4b_text_runpod_cuda`.

### Baseline V1b observation (2026-10-04, E1b text-only Runpod CUDA)

Measured run configuration:
- Model: `google/gemma-3-4b-it`
- Provider mode: `LLM_PROVIDER=gemma_remote`
- Generation cap: `GEMMA_MAX_NEW_TOKENS=750`
- Input mode: text-only extracted page text (no rendered images sent to model)
- Runtime path: local backend `RemoteGemmaProvider` -> real Runpod pod -> CUDA

Persisted aggregate outcomes (10 cases, same case set as E1a):
- Completed cases: 10/10 (0 failed)
- Sum of per-case latency: `321.55s` (E1a: `1428.64s`)
- Avg per-case latency: `32.16s` (E1a: `142.86s`)
- Overall latency speedup vs E1a: `4.44x` by both sum and average
- Output token totals remained similar (`3886` vs E1a `3872`)
- Token-cap hits (`output_tokens >= 750`) remained `3/10` (same as E1a)

### Baseline V1 observation (2026-10-03, E1a text-only local)

Measured run configuration:
- Model: `google/gemma-3-4b-it`
- Provider mode: `LLM_PROVIDER=gemma`
- Generation cap: `GEMMA_MAX_NEW_TOKENS=750`
- Input mode: text-only extracted page text (no rendered images sent to model)
- Device reported by runtime status: `mps`
- Provider status transitioned from `loaded: false` before first request to `loaded: true` after first request.

Evaluated prompts/pages in this run:

- Synthetic smoke tests (single-page synthetic PDF):
  - S1 basic comprehension (page 1)
  - S2 technical detail (page 1)
  - S3 insufficient-information (page 1)
- Notebook tests using `evaluation/documents/notebook_lecture3.pdf`:
  - N1 pages `[3,4,5]`
  - N2 page `[10]`
  - N3 page `[12]`
- Slide tests using `evaluation/documents/lecture_03_dimensionality_reduction.pdf`:
  - L1 pages `[20,21]`
  - L2 pages `[25,26,27,28]`
  - L3 pages `[30..39]`
- Hallucination/grounding check:
  - Early pages `[3,4]` from lecture slides with a question about later derivation content.

Latency observations (seconds):
- Cold inference (first explain after startup): **32.37**
- Warm inference samples: **9.31**, **9.90**, **193.40**, **110.23**, **253.85**, **196.34**, **234.13**, **335.21**, **53.90**

Observed behavior summary:
- Synthetic insufficient-information prompt: model explicitly stated missing information instead of inventing optimizer/schedule details.
- Notebook N2 quantitative answer matched extracted values on page 10 (`~0.803`, `~0.0526`, combined `~0.8556`).
- Early-page hallucination test: model stated that full later derivation/eigenvalue equation was not present in supplied pages.
- Longer multi-page technical prompts (e.g., N3/L2/L3) often reached the configured output cap (750 tokens), indicating response-length pressure under current settings.

---

## 9. Text vs Multimodal Experiment

Planned early core experiment:

**A:** Gemma with extracted PDF text  
**B:** Gemma with extracted PDF text + rendered page image

Hold constant:
- model
- pages
- questions
- generation settings

Evaluate especially on:
- equations
- figures
- charts
- tables
- diagrams

Hypothesis (to test, not assume):
> Multimodal input improves quality on visual/spatial questions.

---

## 10. Model Comparison

Compare models fairly by holding constant:
- evaluation dataset
- prompt version
- generation settings (where reasonable)

Compare across:
- quality
- latency
- memory
- operational cost

Do not label a single model “best” using only one metric.

---

## 11. Prompt Experiments

Define explicit prompt versions:
- Prompt V1
- Prompt V2
- …

Never silently modify prompt during an experiment.
Log prompt version with every run.

Potential experiments:
- generic assistant prompt
- tutor-oriented prompt
- structured equation prompt
- stronger grounding instructions

---

## 12. Quantization Experiments

Planned comparison:
- standard/full precision
- 8-bit
- 4-bit

Measure impact on:
- answer quality
- equation understanding
- visual understanding
- latency
- memory

Goal:
Determine whether memory savings materially hurt tutoring quality.

---

## 13. RAG Evaluation

**PLANNED** (if RAG is introduced for large documents).

Evaluate retrieval and generation separately.

Retrieval metrics:
- Recall@K
- Precision@K / relevance
- correct-page retrieval

Generation metrics:
- grounding quality
- correctness
- citation/page correctness

Separate retrieval failure from generator failure in analysis.

---

## 14. Fine-Tuning / LoRA Evaluation

**PLANNED**.

Compare:
- base Gemma
- LoRA/fine-tuned Gemma

Use held-out evaluation set not used in training.

Assess:
- technical explanation quality
- equation explanation quality
- pedagogical value
- grounding fidelity
- regressions in general behavior

---

## 15. TTS Evaluation

**PLANNED**.

TTS quality must be evaluated separately from LLM answer quality.

For Qwen3-TTS, evaluate:
- intelligibility
- technical term pronunciation
- equation pronunciation
- naturalness
- latency
- time to first audio
- streaming behavior

Example difficult terms:
- softmax
- KL divergence
- eigenvalue
- PyTorch
- “Q K transpose divided by square root of d-k”

---

## 16. Speech-to-Text Evaluation

**PLANNED**.

For Whisper (or alternative STT):
- word error rate (where suitable)
- technical vocabulary recognition
- paper/model names
- math terminology
- latency

---

## 17. End-to-End Voice Tutor Evaluation

**PLANNED**.

Pipeline:
Speech -> STT -> Gemma -> TTS -> spoken response

Evaluate:
- end-to-end latency
- factual correctness
- conversational continuity
- interruption/recovery behavior
- follow-up understanding

---

## 18. Human Evaluation

Not all quality properties are reliably captured by automation initially.

Use a human rubric (0–4 per dimension):
- correctness
- grounding
- clarity
- completeness
- teaching usefulness

Avoid collapsing everything into one overall score too early.

---

## 19. Automated Evaluation

Future automation options:
- deterministic checks
- expected-concept matching
- page-citation verification
- retrieval metrics
- LLM-as-judge

LLM-as-judge limitations:
- judge bias/model leakage
- false confidence
- sensitivity to rubric phrasing

LLM judge outputs are signals, not ground truth.

---

## 20. Regression Testing

Define a small “golden evaluation set” for frequent comparison.

Any major change should be checked against this set:
- prompt updates
- model upgrades
- quantization changes
- multimodal pipeline changes
- inference optimizations

Goal:
Prevent silent quality regressions.

---

## 21. Experiment Results

Reserve summarized reporting table:

| Experiment | Model | Input | Quality | Warm Latency | Notes |
|---|---|---|---|---|---|

Do not populate uncollected measurements.
Detailed raw outputs should live in dedicated experiment artifacts.

---

## 22. Evaluation Artifacts

Current implementation artifacts:

```text
evaluation/
├── documents/
│   ├── notebook_lecture3.pdf
│   └── lecture_03_dimensionality_reduction.pdf
├── specs/
│   ├── e2_multimodal_v1.yaml
│   ├── e2_scoring_rubric_v1.yaml
│   └── README.md
└── runner/
    ├── cases.py
    ├── storage.py
    └── run_evaluation.py
```

Persisted run state:
- Database tables: `evaluation_experiments`, `evaluation_cases` (via Alembic migration in `backend/alembic/versions/20261003_0001_create_evaluation_tables.py`).
- Existing E1 observation artifact: `e1_baseline_results.json` (importable with `--import-e1`).

Still planned:
- standardized prompt snapshots under `evaluation/prompts/`
- rubric/score outputs and aggregate reports under `evaluation/results/`
- evaluator README focused on reproducible scoring workflow

---

## 23. Initial Experiment Roadmap

- **E0 — Mock pipeline validation**  
  Question: Are endpoint wiring, schema handling, and UI flow stable?

- **E1a — Gemma 3 4B text baseline (local MPS)**  
  Question: What quality/latency do we get from text-only grounding today?
  - Status: completed and documented (2026-10-03 observation)

- **E1b — Gemma 3 4B text baseline (RunPod CUDA)**  
  Question: How does the same text-only baseline perform on remote CUDA?
  - Status: completed (2026-10-04); persisted under `e1b_gemma3_4b_text_runpod_cuda`.

- **E2 — Text vs text+image comparison**  
  Question: Does multimodal input improve visual/equation-heavy questions?
  - Status: preregistered; see [`evaluation/specs/e2_multimodal_v1.yaml`](../evaluation/specs/e2_multimodal_v1.yaml) and [`evaluation/specs/e2_scoring_rubric_v1.yaml`](../evaluation/specs/e2_scoring_rubric_v1.yaml). Not run yet.

- **E3 — Prompt optimization**  
  Question: Which prompt structure best improves grounded pedagogy?

- **E4 — Model-size comparison**  
  Question: What quality/latency/memory tradeoff across model sizes?

- **E5 — Quantization comparison**  
  Question: How much quality is lost (if any) for memory/speed gains?

- **E6 — Qwen3-TTS evaluation**  
  Question: Is spoken output intelligible and fast enough?

- **E7 — Whisper evaluation**  
  Question: Is speech input accurate enough for technical dialogue?

- **E8 — End-to-end conversational tutor**  
  Question: Is the full voice loop usable and consistent?

- **E9 — RAG (if needed)**  
  Question: Does retrieval improve large-document grounding?

- **E10 — LoRA/fine-tuning experiments**  
  Question: Can domain adaptation improve pedagogy without regressions?

---

## 24. Relationship to Other Documents

- [pdf_explainer_design_doc.md](./pdf_explainer_design_doc.md)  
  Defines **what** we are building and **why**.

- [implementation_details.md](./implementation_details.md)  
  Describes **how current code works today**.

- `evaluation_plan.md` (this document)  
  Defines **how we decide whether changes improve the system**.

---

## What can be evaluated now vs later

### Evaluations possible today (with current implementation)

- Text-only answer quality on selected pages (manual rubric)
- Grounding behavior on page-scoped questions
- Insufficient-information behavior
- Cold vs warm latency measurement
- Prompt-version comparisons (text-only path)
- Basic regression checks across repeated prompts/questions
- Persistent experiment tracking with resume/status/compare metadata
- Importing previously captured E1 results into evaluation tables

### Evaluations requiring future functionality

- Visual grounding quality (needs text+image multimodal path wired)
- TTS quality/intelligibility benchmarking (needs real Qwen3-TTS inference)
- STT quality/latency benchmarking (needs real Whisper/STT endpoint)
- RAG retrieval metrics (requires retrieval subsystem)
- Fine-tuning/LoRA comparisons (requires training pipeline/artifacts)
