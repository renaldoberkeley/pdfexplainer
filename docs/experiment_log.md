# AI PDF Tutor — Experiment Log

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
