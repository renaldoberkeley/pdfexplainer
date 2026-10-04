# AI PDF Tutor — Experiment Log

## Documentation map (NotebookLM quick orientation)

Use this file for **what was actually executed and observed chronologically**.  
For other project views:

- [evaluation_plan.md](./evaluation_plan.md): preregistered/planned methodology and scoring.
- [implementation_details.md](./implementation_details.md): code implementation supporting experiments.
- [runpod_setup.md](./runpod_setup.md): operational RunPod deployment/testing workflow.
- [research_paper.md](./research_paper.md): manuscript framing of completed vs pending results.
- [pdf_explainer_design_doc.md](./pdf_explainer_design_doc.md): original product/research intent.

## Current Progress Snapshot (single source of truth)

Last updated: 2026-10-04 (post-E2 execution)

### Completed milestones

- E1a — Gemma 3 4B text baseline on Apple M1/MPS (**completed**).
- E1b — Gemma 3 4B text baseline on RunPod RTX 4090/CUDA (**completed**).
- E2 preregistration freeze (**completed**):
  - [e2_multimodal_v1.yaml](../evaluation/specs/e2_multimodal_v1.yaml)
  - [e2_scoring_rubric_v1.yaml](../evaluation/specs/e2_scoring_rubric_v1.yaml)
- E2 implementation milestone (multimodal pipeline + tests + migration) (**completed**, commit `3f5edba5a94c58919e8756d4bcdfe604399ccab9`).
- E2.6 real multimodal GPU integration validation (**completed**, non-benchmark).
- E2 preregistered benchmark execution + blind scoring (**completed**):
  - `e2a_gemma3_4b_text_control_runpod_cuda`
  - `e2b_gemma3_4b_multimodal_runpod_cuda`
  - 24/24 condition runs completed
  - Scoring rubric: `e2-rubric-v1`

### Current phase

- **Post-E2 execution analysis and write-up**:
  - update evaluation/manuscript docs with measured E2 results
  - preserve prereg integrity trail
  - prepare eventual E3 prompt-optimization phase entry point

### Not started yet

- E3+ phases (`E3` through `E10`) remain not started.

### Integrity constraints in force

- E2 benchmark was executed against frozen prereg specs/rubric from commit `f2ca496` without methodology edits.
- E2.6 integration observations remain historically separate from E2 benchmark rows.
- Any new evaluation phase must use a new versioned spec/rubric (no post-hoc edits to v1 artifacts).

## Purpose

This document is the chronological engineering/ML experiment journal for this project.  
It records what we actually ran, what happened (including failures), what was measured, what changed, and what conclusions were (or were not) justified.

Raw structured experiment state and case-level outputs live in PostgreSQL (`evaluation_experiments`, `evaluation_cases`) and results artifacts (for example [`e1_baseline_results.json`](/Users/renaldowilliams/.copilot/session-state/3ee9ca63-e860-43c9-81bf-0f218e46425b/files/e1_baseline_results.json)).  
This file is the human-readable narrative.

---

## E1a — Gemma 3 4B Text Baseline — Apple M1/MPS

**Status:** **COMPLETED**  
**Experiment key:** `e1a_gemma3_4b_text_m1_mps`  
**Date:** 2026-10-03 (run timestamp in artifact: `2026-10-03 11:03:54 -0700`)

### Configuration

- Model: `google/gemma-3-4b-it`
- Hardware: Apple M1
- Backend/device: MPS (`gemma_local`)
- Input mode: text-only
- `max_new_tokens`: 750
- Prompt/config version: `v1`

### Evaluation documents and cases

Documents:
- `synthetic_e1_smoke.pdf`
- `notebook_lecture3.pdf`
- `lecture_03_dimensionality_reduction.pdf`

Cases (10 total): `S1,S2,S3,N1,N2,N3,L1,L2,L3,H1`

### Model load behavior

From baseline artifact:
- Before first explain call: `loaded=false`, `device=mps`
- After run: `loaded=true`, `device=mps`

### Measured per-case values (persisted)

Source: PostgreSQL `evaluation_cases` for `e1a_gemma3_4b_text_m1_mps`.

| Case | Document | Pages | Latency (s) | Input tokens | Output tokens | Hit 750 cap |
|---|---|---:|---:|---:|---:|---|
| S1 | synthetic_e1_smoke.pdf | 1 | 32.37 | 33 | 30 | No |
| S2 | synthetic_e1_smoke.pdf | 1 | 9.31 | 37 | 28 | No |
| S3 | synthetic_e1_smoke.pdf | 1 | 9.90 | 36 | 35 | No |
| N1 | notebook_lecture3.pdf | 3,4,5 | 193.40 | 893 | 603 | No |
| N2 | notebook_lecture3.pdf | 10 | 110.23 | 323 | 326 | No |
| N3 | notebook_lecture3.pdf | 12 | 253.85 | 1296 | 750 | Yes |
| L1 | lecture_03_dimensionality_reduction.pdf | 20,21 | 196.34 | 293 | 516 | No |
| L2 | lecture_03_dimensionality_reduction.pdf | 25,26,27,28 | 234.13 | 646 | 750 | Yes |
| L3 | lecture_03_dimensionality_reduction.pdf | 30–39 | 335.21 | 2221 | 750 | Yes |
| H1 | lecture_03_dimensionality_reduction.pdf | 3,4 | 53.90 | 208 | 84 | No |

Aggregate from persisted rows:
- Cases: 10
- Min latency: 9.31s
- Max latency: 335.21s
- Avg latency: 142.86s
- Cap hits (`output_tokens >= 750`): 3/10

### Total experiment duration

- Approximate wall-clock duration: **~48m 21s** (historical session note).
- Note: current structured artifacts preserve per-case latencies and run metadata, but do not store a single canonical wall-clock end-to-end timer for E1a in one field.

### Grounding/quality observations

- **Insufficient-information behavior:** S3 correctly stated optimizer/schedule details were not present.
- **Quantitative PCA grounding:** N2 answer matched extracted notebook values (`~0.803`, `~0.0526`, sum `~0.8556`).
- **Hallucination resistance check:** H1 did not invent full later derivation/eigenvalue equations and explicitly stated insufficiency for pages 3–4.
- **Response length pressure:** N3/L2/L3 reached the 750-token cap.

---

## PostgreSQL Evaluation Infrastructure

Introduced after E1a to support durable, reproducible experiment operations:

- Durable experiment state
- Case-level checkpointing
- Resume from interrupted runs
- Completed-case skipping
- Failed/interrupted-case recovery
- Explicit experiment provenance/configuration persistence
- Better future E1/E2 comparison workflows

Historical E1a results were imported into PostgreSQL and are represented under experiment key `e1a_gemma3_4b_text_m1_mps`.

---

## Remote Inference Architecture

Architecture change for Phase B:

- `LocalGemmaProvider` -> local Apple MPS inference
- `RemoteGemmaProvider` -> HTTP call -> Runpod Pod service -> CUDA inference

Unchanged and still local:

- PDF processing (PyMuPDF)
- Next.js frontend
- FastAPI application logic
- Evaluation runner orchestration
- PostgreSQL experiment/result persistence

Only Gemma inference execution is offloaded.

---

## Phase B — Remote Contract Validation

**Status:** **COMPLETED — INTEGRATION TEST, NOT GPU BENCHMARK**  
**Experiment key:** `phase_b_remote_contract_validation`

What was done:
- Executed remote-provider integration flow against a contract-compatible local stub service.
- Validated request/response wiring through `RemoteGemmaProvider` path.

Why not E1b:
- Not executed on real Runpod GPU hardware.
- Metadata intentionally marked:
  - `hardware_backend=stub`
  - `execution_environment=remote_stub`
  - `device=simulated_cuda`
- `total_estimated_cost_usd=0.00063048` is simulated/stub metadata.

This run was later reclassified to keep E1b integrity clean.

---

## Runpod Deployment

- Docker image: `renaldoberkeleydocker/pdf-explainer-gemma-service:v0.1.0`
- Build target platform: `linux/amd64`
- GPU: `NVIDIA GeForce RTX 4090`
- VRAM: 24 GB
- Displayed Runpod rate during this session: ~`$0.74` GPU/hour (about `$0.75`/hour including configured container disk shown in UI)
- CUDA: 12.8
- HTTP service port: 8080

No secrets are recorded here.

---

## First Real Runpod Cold-Start Test

Real pod was online and health-checked.

Observed sequence:

1. `GET /health` succeeded (`{"status":"ok"}`).
2. Initial `GET /model/status` showed model not yet loaded.
3. On first real `/generate` request:
   - model download in logs: ~66s (`Fetching 2 files ... 01:06`)
   - checkpoint load in logs: ~5s
   - runtime transitioned to loaded model on CUDA
4. Server-side logs showed `/generate` completed `200 OK`.
5. Client received `HTTP 524` at ~125s before receiving response payload.

Diagnosis:
- This was a cold-start proxy timeout (Cloudflare/Runpod HTTP proxy path), not a Gemma inference correctness failure.

---

## Warm Runpod Smoke Test

Prompt: `"Explain PCA in one sentence."`  
`max_new_tokens=50`

Measured warm results (programmatic request to real pod URL):

- HTTP status: 200
- Client total latency: **1.651s**
- Server generation latency: **1.25s**
- Input tokens: **7**
- Output tokens: **50**
- Approx throughput: **~40 tokens/sec** (`50 / 1.25`)

Additional notes:
- Model already resident (`loaded=true`)
- Device reported as `cuda`
- Real provider path verification subsequently succeeded:
  - Mac -> `RemoteGemmaProvider` -> Runpod -> Gemma -> CUDA -> Mac

---

## Key Findings So Far

1. Gemma 3 4B runs successfully locally on Apple MPS.
2. Local M1 inference is functional but can be slow for repeated technical evaluation.
3. Gemma 3 4B runs successfully on RTX 4090/CUDA in Runpod.
4. Warm CUDA inference is substantially faster in smoke testing.
5. Cold startup can exceed Runpod HTTP proxy timeout when model download/load happens synchronously.
6. Keeping persistent pod/model warm avoids that cold-start issue for normal inference traffic.
7. Controlled MPS-vs-CUDA benchmark conclusions required a real E1b run and were completed in the entry below.

---

## E1b — Gemma 3 4B Text Baseline — Runpod RTX 4090/CUDA

**Status:** **COMPLETED**  
**Experiment key:** `e1b_gemma3_4b_text_runpod_cuda`
**Date:** 2026-10-04

### Controls

Same as E1a:
- model
- prompt
- PDFs
- selected pages
- questions
- `max_new_tokens`
- text-only input

Changed variable only:
- Apple M1/MPS -> Runpod RTX 4090/CUDA

### Results

Run completed with real remote path:
- Local Mac -> local backend `RemoteGemmaProvider` -> real Runpod pod -> Gemma on RTX 4090/CUDA -> response.

Persisted aggregate metrics (PostgreSQL):
- Cases: 10/10 completed, 0 failed
- Sum of per-case latencies: **321.55s**
- Avg per-case latency: **32.16s**
- Min/Max per-case latency: **2.85s / 70.88s**
- Output tokens total: **3886**
- Cap hits (`output_tokens >= 750`): **3/10**

Per-case latency and speedup vs E1a:

| Case | E1a latency (s) | E1b latency (s) | Speedup (E1a / E1b) |
|---|---:|---:|---:|
| S1 | 32.37 | 29.38 | 1.10x |
| S2 | 9.31 | 50.62 | 0.18x |
| S3 | 9.90 | 2.85 | 3.47x |
| N1 | 193.40 | 70.88 | 2.73x |
| N2 | 110.23 | 10.91 | 10.10x |
| N3 | 253.85 | 55.24 | 4.60x |
| L1 | 196.34 | 17.00 | 11.55x |
| L2 | 234.13 | 24.53 | 9.54x |
| L3 | 335.21 | 56.70 | 5.91x |
| H1 | 53.90 | 3.44 | 15.67x |

Overall latency comparison:
- Sum-of-cases speedup: **4.44x** (`1428.64s / 321.55s`)
- Average-case speedup: **4.44x**
- Historical wall-clock comparison (session narrative): E1a ~48m 21s vs E1b ~4m 52.51s (~9.92x), noted as approximate because E1a wall clock came from historical session timing rather than one persisted DB field.

Warm-run throughput snapshot within E1b cases (client-observed output tokens per second):
- Highest: **30.57 tok/s** (L2)
- Lowest: **0.59 tok/s** (S2)
- Indicates prompt/content-dependent variance despite warm model residency.

Cost estimate for this completed E1b run:
- Runtime used for estimate: **292.51s**
- At `$0.74`/GPU-hour: **~$0.06013**
- At `$0.75`/hour (GPU + configured disk): **~$0.06094**

Quality/grounding observations from persisted outputs:
- No transport/runtime failures were recorded (10/10 completed).
- Quantitative and grounding-oriented responses remained present (for example, notebook/slide technical prompts still produced structured explanations).
- Response-length behavior was similar to E1a for longest prompts (same 3 cap-hit cases), so speed improved substantially without changing the cap-pressure pattern.

---

## E2 — Text + Rendered Page Image Evaluation

**Status:** **COMPLETED (SEE E2.7 ENTRY BELOW)**  
**Spec:** [`e2_multimodal_v1.yaml`](../evaluation/specs/e2_multimodal_v1.yaml)  
**Rubric:** [`e2_scoring_rubric_v1.yaml`](../evaluation/specs/e2_scoring_rubric_v1.yaml)

Methodology was frozen before execution to reduce post-hoc bias:
- paired text vs text+image conditions per case
- controlled E1-overlap group plus visual challenge group
- deterministic counterbalanced execution order
- blind scoring with condition-masked response IDs

Historical note: this section describes the prereg frozen design state before execution.  
Measured E2 outputs are recorded in the **E2.7** entry below.

---

## E2 Implementation Readiness (No Benchmark Execution)

**Status:** **COMPLETED (IMPLEMENTATION ONLY) / E2 NOT RUN**  
**Date:** 2026-10-04

Implemented to support preregistered E2 execution later without modifying frozen specs:

- Backend multimodal request plumbing (`input_mode`, page-context/image association, render options).
- PDF page rendering pipeline for explain calls (PyMuPDF render path, ordered mapping to pages).
- Local provider multimodal execution path in Gemma provider.
- Remote provider multimodal transport path (text-only JSON, text+image multipart).
- RunPod service multimodal request contract handling.
- Evaluation persistence extensions for E2 metadata/scoring tables (additive migration).
- Synthetic multimodal fixtures/tests for pipeline/contract validation.

Validation completed in this implementation phase:
- Backend tests passed.
- RunPod service tests passed.
- Frontend lint/typecheck passed.
- YAML specs parse passed.
- E1 experiment records remained unchanged.
- Frozen preregistration files remained unchanged.

Interpretation constraints:
- This entry is implementation readiness only.
- No E2 benchmark runs, quality scores, or conclusions were produced.

---

## E2.6 — Real Multimodal GPU Validation

**Status:** **COMPLETED**  
**Classification:** **INTEGRATION VALIDATION — NOT E2 BENCHMARK**  
**Date:** 2026-10-04

### Deployment and infrastructure context

- Service image: `renaldoberkeleydocker/pdf-explainer-gemma-service:v0.2.0`
- Published image digest: `sha256:74f351ba6bddbc4cce1a223d8d7c38276329190bae62636e743947898808f3d7`
- RunPod Pod used for validation: `54bwa4z3xukpqw`
- GPU: `NVIDIA GeForce RTX 4090`
- Host CUDA version reported by RunPod pod metadata: `13.0`
- Endpoint used for all E2.6 calls: `https://54bwa4z3xukpqw-8080.proxy.runpod.net`

Migration/replacement operational observation:

- Original stopped Pod (`belllhnlh84cci`) could not be resumed on its previous host.
- RunPod migrated to replacement Pod `54bwa4z3xukpqw` (same GPU class).
- HTTP endpoint changed with Pod replacement.
- Local remote config therefore required endpoint revalidation/update before testing.

### Phase 3 — Service/GPU verification

- `GET /health` on current endpoint: `200`, `{"status":"ok"}`
- `GET /model/status` after warm-up:
  - `model: google/gemma-3-4b-it`
  - `device: cuda`
  - `loaded: true`
  - `cuda_available: true`
  - `gpu_name: NVIDIA GeForce RTX 4090`

### Phase 4 — Synthetic multimodal positive test

Fixture:

- Development-only synthetic 2-page PDF generated at runtime.
- Page 1 text intentionally avoided direct answer tokens (no `blue`, `square`, `triangle`, `blue square` in extracted text).
- Question: **“What shape does the arrow point toward? Answer with just the target shape.”**
- Mode: `input_mode=text_image`

Observed result (real path: local backend -> `RemoteGemmaProvider` -> RunPod v0.2.0 -> Gemma/CUDA):

- HTTP success via backend `/api/explain`
- Answer: **“The arrow points toward a square.”**
- `image_count: 1`
- `pages_used: [1]`
- Telemetry:
  - `request_payload_bytes: 24891`
  - `image_preprocessing_seconds: 0.0484`
  - `server_generation_seconds: 0.69`
  - `client_latency_seconds: 2.062`
  - `input_tokens: 461`
  - `output_tokens: 8`

### Cold-start behavior on migrated pod

- First synthetic multimodal request attempt on this migrated pod returned proxy timeout (`HTTP 524`) while model was not yet resident.
- A subsequent warm request succeeded after model residency.
- Treated as startup/proxy behavior, not as multimodal-path correctness failure.

### Phase 5 — Text-only negative control

Same synthetic fixture, same question, same generation config, but `input_mode=text` (no image sent).

Observed result:

- Answer: **“The document does not provide information about the shapes that the arrow points toward.”**
- This supports the absence of answer leakage from extracted text for this fixture.
- Telemetry:
  - `image_count: 0`
  - `request_payload_bytes: 893`
  - `server_generation_seconds: 0.65`
  - `client_latency_seconds: 1.478`
  - `input_tokens: 180`
  - `output_tokens: 18`

### Phase 6 — Synthetic multi-image transport test

Fixture:

- Same synthetic document, pages `[1,2]` with two diagrams.
- Mode: `input_mode=text_image`
- Question: asked for ordered target shapes across page 1 then page 2.

Observed result:

- Generation succeeded via backend path.
- `image_count: 2`
- `pages_used: [1,2]`
- Request payload and timing:
  - `request_payload_bytes: 49836`
  - `image_preprocessing_seconds: 0.08`
  - `server_generation_seconds: 70.47`
  - `client_latency_seconds: 71.336`
  - `input_tokens: 765`
  - `output_tokens: 64` (hit configured cap for this validation run)

Interpretation:

- Confirms multi-image transport, deterministic ordering, and page association plumbing through the live remote path.
- Output completeness for two-page answer was constrained by token cap in this integration test (not a benchmark run).

### Text-only backward compatibility check

Development-only text prompt (non-benchmark) on same fixture:

- Mode: `input_mode=text`
- Response succeeded and remained coherent.
- Confirms v0.2.0 multimodal additions did not break text-only remote inference contract.

### E2 benchmark integrity confirmations

- No preregistered E2 benchmark case IDs were executed (`A_*`, `V*` untouched).
- No E2 benchmark experiment rows were created for:
  - `e2a_gemma3_4b_text_control_runpod_cuda`
  - `e2b_gemma3_4b_multimodal_runpod_cuda`
- Frozen preregistration files remained unchanged from commit `f2ca496`.

---

## E2.7 — Frozen Preregistered Benchmark Execution + Blind Scoring

**Status:** **COMPLETED**  
**Date:** 2026-10-04  
**Execution key pair:**  
- `e2a_gemma3_4b_text_control_runpod_cuda`  
- `e2b_gemma3_4b_multimodal_runpod_cuda`

### Execution integrity

- Frozen methodology source: [`e2_multimodal_v1.yaml`](../evaluation/specs/e2_multimodal_v1.yaml)
- Frozen rubric source: [`e2_scoring_rubric_v1.yaml`](../evaluation/specs/e2_scoring_rubric_v1.yaml)
- Counterbalanced condition order persisted per prereg strategy.
- A_L3 multimodal condition executed with full prereg payload (pages 30–39 text + 10 page images); no image-count reduction.
- Completed runs: **24/24**.
- Failed runs at completion: **0**.

### Infrastructure context

- Service image: `renaldoberkeleydocker/pdf-explainer-gemma-service:v0.2.0`
- Digest: `sha256:74f351ba6bddbc4cce1a223d8d7c38276329190bae62636e743947898808f3d7`
- Pod endpoint: `https://54bwa4z3xukpqw-8080.proxy.runpod.net`
- GPU: `NVIDIA GeForce RTX 4090`
- Device: `cuda`
- Pod rate used for estimate: `$0.74/hour`

### Blind scoring execution

- Blind export artifacts:
  - [`blind_scoring_input.json`](../evaluation/results/e2_20261004/blind_scoring_input.json)
  - [`blind_scoring_mapping.secure.json`](../evaluation/results/e2_20261004/blind_scoring_mapping.secure.json)
  - [`blind_scoring_output.json`](../evaluation/results/e2_20261004/blind_scoring_output.json)
- Scoring metadata: [`scoring_metadata.json`](../evaluation/results/e2_20261004/scoring_metadata.json)
- Scorer type: `llm_rubric`
- Scorer model: `google/gemma-3-4b-it` (RunPod service)
- Prompt version: `e2-rubric-v1-prompt-20261004b`
- Condition labels hidden during scoring: `true`

### Result artifacts

- Aggregate summary: [`e2_summary.json`](../evaluation/results/e2_20261004/e2_summary.json)
- Score rows persisted in PostgreSQL `evaluation_scores`: 24

### Quality summary (paired deltas: multimodal minus text)

Group A criterion averages:
- factual_correctness: `0.000`
- document_grounding: `0.000`
- completeness: `0.000`
- teaching_clarity: `+0.167`

Group B criterion averages:
- factual_correctness: `-0.167`
- document_grounding: `0.000`
- completeness: `0.000`
- teaching_clarity: `0.000`
- visual_grounding: `-0.167`
- visual_detail_accuracy: `0.000`

Interpretation boundary:
- No significance claims are made.
- Observed paired effects are mixed and small in aggregate under this rubric pass.

### Performance summary

- Mean latency (text): `187.028s`
- Mean latency (multimodal): `240.930s`
- Mean latency delta (multimodal - text): `+53.902s`
- Median latency (text): `178.138s`
- Median latency (multimodal): `229.642s`
- Median latency delta: `+51.504s`

Token usage averages:
- Input tokens: text `750.5` vs multimodal `1392.833` (delta `+642.333`)
- Output tokens: text `531.25` vs multimodal `647.917` (delta `+116.667`)

Telemetry caveat (important):
- `request_payload_bytes`, `image_preprocessing_seconds`, and `server_generation_seconds` were null for all 24 benchmark rows (fields persisted as null).
- This is tracked as an implementation/telemetry issue for future phase reliability analysis.

### Wall-clock and estimated infrastructure cost

- Earliest case start (persisted): `2026-10-04T09:32:28.522009-07:00`
- Latest case completion (persisted): `2026-10-04T12:58:42.735117-07:00`
- Total persisted interval between first start and last completion: `12374.213s` (`3.4373h`)
- Estimated total RunPod billable wall-clock cost for that interval: `3.4373h × $0.74/h = $2.5436`

Interpretation guardrail (post-hoc interruption audit):
- The `12374.213s` interval should be treated as a **wall-clock/session envelope**, not pure model-execution time.
- Sum of successful per-condition client latencies (`24` completed rows) was `5135.505s` (`~1.4265h`), indicating substantial non-request overhead and interruption/recovery idle inside the larger wall-clock envelope.
- Without complete host/process telemetry for the restart window, exact partitioning of active execution vs interruption downtime is not claimed.

### Anomalies / operational notes

- Initial local-runner attempt targeted a non-backend local service path and produced immediate local `404` transport failures; rows were later rerun in-place under the same frozen conditions and completed.
- No `HTTP 524` occurred during final benchmark completion window.

### Execution interruption integrity note (post-hoc audit)

- Local Mac host unexpectedly restarted during E2 execution.
- PostgreSQL checkpointing preserved completed case rows and persisted runner state.
- Recovery resumed from persisted state: already-completed conditions were skipped; incomplete/interrupted work was resumed/retried under the same frozen configuration.
- Final benchmark completion remained `24/24` condition runs (`12` text + `12` text-image), with no duplicate completed rows counted in analysis.
- Post-hoc audit conclusion: interruption affected orchestration timing/accounting, but no evidence was found that it altered final scientific result content or frozen-methodology compliance.

### Frozen-spec verification after E2

- [`e2_multimodal_v1.yaml`](../evaluation/specs/e2_multimodal_v1.yaml): unchanged
- [`e2_scoring_rubric_v1.yaml`](../evaluation/specs/e2_scoring_rubric_v1.yaml): unchanged

---

## Experiment Log Rules

- Never overwrite historical observations.
- Record failures as well as successes.
- Distinguish measured values from estimates.
- Distinguish integration/stub tests from real model experiments.
- Record model ID.
- Record hardware.
- Record device/backend.
- Record prompt/config version.
- Record Docker image/version for remote experiments.
- Record costs when relevant.
- Never record credentials or secrets.
- Link/reference PostgreSQL experiment keys where appropriate.
- Structured case-level data belongs in PostgreSQL; this document summarizes findings.
