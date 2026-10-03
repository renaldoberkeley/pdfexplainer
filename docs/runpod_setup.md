# RunPod Setup (Gemma Remote Inference)

This guide prepares remote Gemma inference for experiment **E1b**.

## 1) Recommended initial GPU class

Start with a single mid-range CUDA GPU (for example an RTX 4090/A5000-class pod) for initial bring-up and latency comparison.

## 2) Create the RunPod Pod

1. Create a new RunPod GPU Pod.
2. Use the container image built from [runpod_service/Dockerfile](../runpod_service/Dockerfile).
3. Expose service port `8080`.

## 3) Container/image setup

Build image locally or via your registry:

```bash
cd runpod_service
docker build -t <registry>/pdf-explainer-gemma-service:latest .
docker push <registry>/pdf-explainer-gemma-service:latest
```

Use that image in RunPod.

## 4) Required ports

- Inference API: `8080` (HTTP inside pod; terminate TLS at ingress/proxy).

## 5) Hugging Face authentication

Set Hugging Face credentials in RunPod environment so the service can download gated Gemma weights:

- `HUGGING_FACE_HUB_TOKEN` (or equivalent token variable used by your runtime)
- `GEMMA_MODEL_ID=google/gemma-3-4b-it`

## 6) Gemma model loading

Model loads lazily on first `/generate` request.

## 7) API key setup

Set:

- `RUNPOD_API_KEY=<strong-random-value>`

Local backend uses the same value as:

- `GEMMA_REMOTE_API_KEY`

## 8) Health/status verification

```bash
curl https://<runpod-host>/health
curl -H "X-API-Key: <key>" https://<runpod-host>/model/status
```

## 9) Connect local FastAPI app to RunPod

Set local backend env:

```bash
export LLM_PROVIDER=gemma_remote
export GEMMA_MODEL_ID=google/gemma-3-4b-it
export GEMMA_MAX_NEW_TOKENS=750
export GEMMA_REMOTE_URL=https://<runpod-host>
export GEMMA_REMOTE_API_KEY=<same-key>
```

Then start backend normally.

## 10) Stop/terminate GPU resources

When not actively running E1b, stop or terminate the RunPod Pod to avoid unnecessary charges.

---

## Remote inference contract

### `POST /generate`

Request:

```json
{
  "model": "google/gemma-3-4b-it",
  "prompt": "...",
  "max_new_tokens": 750
}
```

Response:

```json
{
  "text": "...",
  "model": "google/gemma-3-4b-it",
  "device": "cuda",
  "input_tokens": 1234,
  "output_tokens": 600,
  "generation_seconds": 12.4,
  "loaded": true
}
```

### `GET /health`

Returns basic liveness status.

### `GET /model/status`

Returns model/device/load status and CUDA metadata (requires API key).

