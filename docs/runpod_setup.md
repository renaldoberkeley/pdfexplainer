# RunPod Setup (Gemma Remote Inference)

This guide documents how this project uses RunPod for remote Gemma inference, including:

- RunPod pod specs
- Docker build/push workflow
- Pod configuration in the RunPod UI
- local-backend integration via `RemoteGemmaProvider`
- validation/testing workflow on real GPU

It complements [implementation_details.md](./implementation_details.md), which explains internal code behavior.

## Documentation map (NotebookLM quick orientation)

Use this file for **operational deployment/testing steps on RunPod**.  
For other project views:

- [implementation_details.md](./implementation_details.md): internal backend/provider behavior and interfaces.
- [experiment_log.md](./experiment_log.md): what was actually validated on real GPU.
- [evaluation_plan.md](./evaluation_plan.md): benchmark methodology and controls.
- [research_paper.md](./research_paper.md): broader analysis and results framing.
- [pdf_explainer_design_doc.md](./pdf_explainer_design_doc.md): high-level system goals.

---

## 1) RunPod deployment target

Current deployment target for remote testing:

- Service image: `renaldoberkeleydocker/pdf-explainer-gemma-service:<version-tag>`
- Runtime container source: [runpod_service/Dockerfile](../runpod_service/Dockerfile)
- Pod class: single GPU pod
- Verified GPU class used in project experiments: `NVIDIA GeForce RTX 4090` (24 GB VRAM)
- Inference port: `8080`

Use explicit semantic tags (for example `v0.2.0`), not `latest`, to keep experiments reproducible.

---

## 2) Required environment variables (RunPod pod)

Set these in the Pod environment configuration:

- `GEMMA_MODEL_ID=google/gemma-3-4b-it`
- `HUGGING_FACE_HUB_TOKEN=<secret>` (for Hugging Face gated model access)
- `RUNPOD_API_KEY=<secret>` (required by `runpod_service` API key middleware)

Do not store real secret values in Git-tracked files.

---

## 3) Build and push the RunPod service image

Run service tests first:

```bash
cd runpod_service
pytest
```

Build for RunPod target architecture:

```bash
cd runpod_service
docker build --platform=linux/amd64 -t renaldoberkeleydocker/pdf-explainer-gemma-service:v0.2.0 .
```

Push to Docker Hub:

```bash
docker push renaldoberkeleydocker/pdf-explainer-gemma-service:v0.2.0
```

Record the published digest from `docker push` output for traceability.

---

## 4) Update the existing RunPod Pod (UI steps)

This project uses one persistent Pod for remote benchmarking/validation.  
Do not create extra pods unless intentionally changing infrastructure.

In the RunPod UI:

1. Open the existing Pod.
2. Edit container image to the new tag (for example `...:v0.2.0`).
3. Confirm exposed service port remains `8080`.
4. Confirm environment variables are present (Section 2).
5. Save and manually restart/start the Pod.

---

## 5) Connect local backend to RunPod

On local machine, configure backend to use remote inference:

```bash
export LLM_PROVIDER=gemma_remote
export GEMMA_MODEL_ID=google/gemma-3-4b-it
export GEMMA_MAX_NEW_TOKENS=750
export GEMMA_REMOTE_URL=https://<runpod-proxy-host>
export GEMMA_REMOTE_API_KEY=<same RUNPOD_API_KEY value configured on pod>
```

Start backend:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

This wiring activates `RemoteGemmaProvider` in [remote_gemma.py](../backend/app/services/llm/remote_gemma.py).

---

## 6) Service health and runtime checks

Run direct checks against RunPod service:

```bash
curl https://<runpod-proxy-host>/health
curl -H "X-API-Key: <redacted>" https://<runpod-proxy-host>/model/status
```

`/model/status` reports:

- `model`
- `device`
- `loaded`
- `cuda_available`
- `gpu_name` (when CUDA is available and torch has initialized)

Note: model loading is lazy; `loaded=false` before first generation is expected.

---

## 7) Application interface path (for testing)

Testing through the actual application path should follow:

`Local frontend/backend -> /api/explain -> RemoteGemmaProvider -> RunPod /generate -> Gemma -> response`

Key backend endpoint:

- `POST /api/explain` in [explain.py](../backend/app/api/explain.py)

Modes:

- `input_mode=text`
- `input_mode=text_image` (renders page image(s) in backend before remote call)

---

## 8) Remote generation contract (v0.2.0)

### `POST /generate`

Text-only request (JSON):

```json
{
  "model": "google/gemma-3-4b-it",
  "prompt": "...",
  "max_new_tokens": 750,
  "input_mode": "text"
}
```

Multimodal request (multipart form):

- form fields:
  - `model`
  - `prompt`
  - `max_new_tokens`
  - `input_mode=text_image`
  - `images_meta` (JSON array; preserves page/image association and order)
- files:
  - repeated `images` entries in same order as `images_meta`

Typical response fields:

```json
{
  "text": "...",
  "model": "google/gemma-3-4b-it",
  "device": "cuda",
  "input_tokens": 1234,
  "output_tokens": 600,
  "generation_seconds": 12.4,
  "loaded": true,
  "image_count": 1,
  "image_preprocessing_seconds": 0.0213
}
```

### `GET /health`

Returns liveness (`{"status":"ok"}` when healthy).

### `GET /model/status`

Returns model/device/load/CUDA status; requires `X-API-Key`.

---

## 9) Recommended validation workflow (non-benchmark)

Use synthetic fixtures for implementation validation before running frozen experiments:

1. **Warm-path text check** (`input_mode=text`) through local backend `/api/explain`.
2. **Positive multimodal check** (`input_mode=text_image`) where image contains essential info not present in extracted text.
3. **Text-only negative control** with same question and same synthetic document to detect answer leakage.
4. **Small multi-image transport check** (for example two images/pages) to verify ordering and metadata association.
5. Confirm telemetry fields where available:
   - `input_mode`, `image_count`
   - image metadata (`width`, `height`, `format`, `rendered_dpi`, `bytes`)
   - request payload size
   - preprocessing time
   - `input_tokens`, `output_tokens`
   - generation latency and total client latency

Keep integration validation observations separate from benchmark experiment rows.

---

## 10) Cost and operational safety

- A running RunPod Pod is billable continuously.
- Stop the Pod when not actively testing/inferencing.
- Keep versioned image tags tied to experiment phases (for example E1 image tag vs E2 image tag) to preserve reproducibility.
