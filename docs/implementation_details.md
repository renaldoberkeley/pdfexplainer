# AI PDF Tutor — Implementation Details

This document describes the **current implementation** in this repository.
It complements (and does not replace) [pdf_explainer_design_doc.md](./pdf_explainer_design_doc.md).

---

## 1. Current Implementation Status

The app currently supports end-to-end local PDF tutoring with:
- PDF upload and temporary filesystem storage
- Browser PDF rendering/navigation
- Page range selection
- `POST /api/explain` using provider abstraction (`mock`, `gemma_local`, `gemma_remote`, `gemma`)
- Gemma local inference via Transformers/PyTorch (text and text+image paths)
- Remote Gemma inference via HTTP provider adapter (`gemma_remote`) with text JSON and text+image multipart support
- Mock speech generation through `POST /api/speech`
- Provider config and runtime status endpoints
- DB-backed evaluation experiment/case storage and resume/import tooling

| Feature | Status | Implementation |
|---|---|---|
| PDF upload | Implemented | FastAPI upload endpoint + local storage in [documents.py](../backend/app/api/documents.py) and [pdf_service.py](../backend/app/services/pdf_service.py) |
| PDF text extraction | Implemented | PyMuPDF `page.get_text("text")` in [pdf_service.py](../backend/app/services/pdf_service.py) |
| PDF rendering | Implemented | `react-pdf` in [PDFViewer.tsx](../frontend/components/PDFViewer.tsx) |
| Gemma text inference | Implemented | [gemma.py](../backend/app/services/llm/gemma.py) + prompt builder in [prompt_builder.py](../backend/app/services/llm/prompt_builder.py) |
| Gemma multimodal inference (text + image) | Implemented (execution path) | Backend page rendering + provider multimodal interface + local/remote multimodal request handling |
| TTS | Partial | Backend mock TTS + frontend audio playback implemented; Qwen3 provider is placeholder |
| STT | Planned | Interface/placeholder only; no API endpoint or frontend integration |
| RAG / vector retrieval | Planned | Not present in backend/frontend |
| Evaluation framework | Partial | SQLAlchemy models + Alembic migration + resumable runner CLI implemented, including per-case and per-experiment estimated cost tracking; scoring/rubrics and multimodal comparisons still planned |

Status legend:
- **Implemented** = working code path exists and is wired
- **Partial** = some scaffolding works, production target not implemented
- **Planned** = design intent only (not wired)

---

## 2. Repository Structure

Actual source-focused tree (dependency/build folders omitted):

```text
pdf_explainer/
  backend/
    alembic/
      env.py
      script.py.mako
      versions/
        20261003_0001_create_evaluation_tables.py
    alembic.ini
    app/
      main.py
      dependencies.py
      api/
        documents.py
        explain.py
        providers.py
        speech.py
      models/
        schemas.py
      evaluation/
        database.py
        models.py
      services/
        pdf_service.py
        provider_factory.py
        llm/
          base.py
          mock.py
          gemma.py
          remote_gemma.py
          prompt_builder.py
        tts/
          base.py
          mock.py
          qwen3_tts.py
        stt/
          base.py
          whisper.py
    tests/
      test_api.py
      test_integration.py
      test_llm_configuration.py
      test_evaluation_storage.py
      test_remote_gemma_provider.py
    requirements.txt
  evaluation/
    runner/
      cases.py
      storage.py
      run_evaluation.py
    documents/
      notebook_lecture3.pdf
      lecture_03_dimensionality_reduction.pdf
  frontend/
    app/
      layout.tsx
      page.tsx
      globals.css
    components/
      PDFUploader.tsx
      PDFViewer.tsx
      PageSelector.tsx
      TutorPanel.tsx
      ChatMessage.tsx
      AudioPlayer.tsx
      ProviderConfigPanel.tsx
    lib/
      api.ts
    package.json
  docs/
    pdf_explainer_design_doc.md
    implementation_details.md
    evaluation_plan.md
    runpod_setup.md
  .env.example
  runpod_service/
    app/
      main.py
    requirements.txt
    Dockerfile
```

Key responsibilities:

- [main.py](../backend/app/main.py): FastAPI app creation, CORS, service initialization, router registration.
- [documents.py](../backend/app/api/documents.py): upload/get-page endpoints.
- [explain.py](../backend/app/api/explain.py): explain endpoint; gets page text and dispatches to `LLMProvider`.
- [providers.py](../backend/app/api/providers.py): provider config + runtime status endpoints.
- [speech.py](../backend/app/api/speech.py): speech endpoint via `TTSProvider`.
- [pdf_service.py](../backend/app/services/pdf_service.py): upload validation/storage, document lookup, page text extraction.
- [base.py (LLM)](../backend/app/services/llm/base.py): provider interface.
- [gemma.py](../backend/app/services/llm/gemma.py): local Gemma loading/inference/reuse logic (`LocalGemmaProvider`).
- [remote_gemma.py](../backend/app/services/llm/remote_gemma.py): remote inference adapter (`RemoteGemmaProvider`) for an HTTP model service.
- [prompt_builder.py](../backend/app/services/llm/prompt_builder.py): prompt template + page grounding.
- [mock.py (LLM)](../backend/app/services/llm/mock.py): deterministic development provider.
- [provider_factory.py](../backend/app/services/provider_factory.py): env-based provider selection/config/status mapping.
- [database.py](../backend/app/evaluation/database.py): SQLAlchemy engine/session factory wiring from `DATABASE_URL`.
- [models.py](../backend/app/evaluation/models.py): `evaluation_experiments`/`evaluation_cases` ORM models.
- [run_evaluation.py](../evaluation/runner/run_evaluation.py): `--new/--resume/--status/--import-e1/--compare-with` CLI runner.
- [cases.py](../evaluation/runner/cases.py): canonical E1 case set + experiment definitions.
- [storage.py](../evaluation/runner/storage.py): idempotent creation, resume filtering, status aggregation utilities.
- [runpod_service/main.py](../runpod_service/app/main.py): optional remote inference service contract for `gemma_remote`.
- [page.tsx](../frontend/app/page.tsx): orchestrates upload, viewer state, tutor conversation, provider config panel.
- [PDFViewer.tsx](../frontend/components/PDFViewer.tsx): page render/navigation/zoom.
- [TutorPanel.tsx](../frontend/components/TutorPanel.tsx): page selector + message input + send.
- [ChatMessage.tsx](../frontend/components/ChatMessage.tsx): markdown rendering + listen action.
- [api.ts](../frontend/lib/api.ts): typed frontend API client.

---

## 3. Request Flow

Current explain flow (actual classes/files):

1. **Upload PDF**
   - Frontend: [page.tsx](../frontend/app/page.tsx) calls `uploadDocument` from [api.ts](../frontend/lib/api.ts).
   - Backend route: `POST /api/documents` in [documents.py](../backend/app/api/documents.py).
   - Service: `PDFService.store_pdf` in [pdf_service.py](../backend/app/services/pdf_service.py).

2. **Select page/page range in UI**
   - Frontend only: [PageSelector.tsx](../frontend/components/PageSelector.tsx) parses user input to page list.
   - No backend call happens on selection alone.

3. **Ask question**
   - Frontend: [TutorPanel.tsx](../frontend/components/TutorPanel.tsx) -> `onSendQuestion`.
   - Frontend API call: `requestExplanation` in [api.ts](../frontend/lib/api.ts).
   - Backend route: `POST /api/explain` in [explain.py](../backend/app/api/explain.py).

4. **Backend page retrieval and grounding**
   - `PDFService.get_pages_text` in [pdf_service.py](../backend/app/services/pdf_service.py) extracts text for selected pages.
   - Route passes `question`, `pages`, `page_texts` to `LLMProvider.explain`.

5. **Prompt construction**
   - Gemma path uses `build_prompt` in [prompt_builder.py](../backend/app/services/llm/prompt_builder.py).

6. **Model inference**
   - Local path: `LocalGemmaProvider.explain` in [gemma.py](../backend/app/services/llm/gemma.py).
   - Remote path (when selected): `RemoteGemmaProvider.explain` in [remote_gemma.py](../backend/app/services/llm/remote_gemma.py).
   - Transformers `AutoTokenizer` + `AutoModelForCausalLM`.
   - PyTorch device selected MPS/CUDA/CPU; generation under `torch.inference_mode()`.

7. **Response**
   - Backend returns `ExplainResponse` from [schemas.py](../backend/app/models/schemas.py).
   - Frontend appends assistant message and renders markdown in [ChatMessage.tsx](../frontend/components/ChatMessage.tsx).

---

## 4. PDF Processing Implementation

Current behavior:

- Upload handled in `POST /api/documents` ([documents.py](../backend/app/api/documents.py)).
- Files are copied from `UploadFile.file` to local disk in `PDFService.store_pdf` ([pdf_service.py](../backend/app/services/pdf_service.py)).
- Document IDs are UUIDv4 strings generated per upload.
- Filename on disk: `{document_id}_{original_filename}`.
- In-memory index: `PDFService._documents: dict[str, StoredDocument]`.
- Page numbering exposed through API is **1-based**.
- Text extraction uses PyMuPDF:
  - `pdf.load_page(page_number - 1)` then `get_text("text")`.

Error handling implemented:
- Non-PDF content type -> HTTP 400 `"Only PDF uploads are supported."`
- Missing filename -> HTTP 400
- Invalid PDF parse -> HTTP 400 `"Uploaded file is not a valid PDF."`
- Unknown `document_id` -> HTTP 404
- Invalid page numbers -> HTTP 400 with valid range

Current file lifecycle:
- Uploaded files persist on local filesystem for process lifetime and beyond restart unless manually cleaned.
- There is no expiry/cleanup worker in current code.

Current limitations:
- `_documents` map is in-memory only; restart loses document index.
- Rendered page images are generated on demand (not cached or persisted).
- No expiry/cleanup worker for uploaded files.

---

## 5. LLM Provider Interface

Defined in [base.py](../backend/app/services/llm/base.py):

- `LLMProvider.explain(question, pages: list[PageContext], input_mode) -> LLMExplanation`
- `LLMExplanation` includes:
  - `answer: str`
  - `pages_used: list[int]`
  - `provider: str`
  - token/cost metadata (when available)
  - multimodal/perf metadata fields (`image_count`, `request_payload_bytes`, `image_preprocessing_seconds`, `server_generation_seconds`, `approximate_tokens_per_second`)

Implementations:

- `MockLLMProvider` ([mock.py](../backend/app/services/llm/mock.py))
  - Produces grounded mock markdown answer from supplied page text snippets.
  - Exposes `status()` returning `{"provider": "mock", "loaded": True}`.

- `LocalGemmaProvider` ([gemma.py](../backend/app/services/llm/gemma.py))
  - Real Transformers + PyTorch inference path.
  - Exposes `status()` with provider/model/device/loaded.

- `RemoteGemmaProvider` ([remote_gemma.py](../backend/app/services/llm/remote_gemma.py))
  - Sends the constructed prompt to a remote `/generate` endpoint.
  - Requires explicit `GEMMA_REMOTE_URL` and `GEMMA_REMOTE_API_KEY`.
  - Surfaces timeout/HTTP/malformed-response errors; does not silently fall back to local/mock.

Provider selection:

- `build_llm_provider()` in [provider_factory.py](../backend/app/services/provider_factory.py)
  - `LLM_PROVIDER=mock` -> `MockLLMProvider`
  - `LLM_PROVIDER=gemma` or `gemma_local` -> `LocalGemmaProvider(model_id, max_new_tokens)`
  - `LLM_PROVIDER=gemma_remote` -> `RemoteGemmaProvider(model_id, base_url, api_key, ...)`
  - Missing required env vars for selected mode -> raises `ValueError`.

---

## 6. Gemma Implementation

Current local Gemma provider is in [gemma.py](../backend/app/services/llm/gemma.py).

### Configuration
- `GEMMA_MODEL_ID` (required when `LLM_PROVIDER=gemma` or `gemma_local`)
- `GEMMA_MAX_NEW_TOKENS` (default `"1000"` in factory)

### Loading and reuse
- **Lazy loading**: model/tokenizer are loaded on first `explain` call via `_ensure_loaded()`.
- **Reuse**: `_loaded` flag and instance-held `_model` / `_tokenizer` avoid reloading per request.

### Device selection
- Preference order implemented:
  1. MPS (`torch.backends.mps.is_available()`)
  2. CUDA (`torch.cuda.is_available()`)
  3. CPU fallback

### Inference paths
- Text mode:
  - Prompt built using `build_prompt(...)`.
  - Tokenization via tokenizer and deterministic generation (`do_sample=False`) in `torch.inference_mode()`.
  - Prompt tokens are removed from returned output by slicing generated ids after prompt length.
- Text+image mode:
  - Prompt preserves page-number grounding and includes image markers.
  - Rendered page images are decoded to PIL and passed through `AutoProcessor`.
  - Chat-template + image-aware model inputs are used when processor support is available.
  - Generation remains wrapped in `torch.inference_mode()`.

Remote variant:
- `RemoteGemmaProvider` now supports:
  - JSON contract for text-only requests.
  - Multipart contract for text+image requests, including ordered `images_meta` and image files.

---

## 7. Prompt Construction

Prompt builder: [prompt_builder.py](../backend/app/services/llm/prompt_builder.py)

Sections in order:
1. `INSTRUCTIONS`
2. `DOCUMENT CONTENT`
3. `USER QUESTION`
4. `EXPLANATION:` suffix to cue model output

Page grounding format:

```text
--- PAGE 4 ---
<page text>

--- PAGE 5 ---
<page text>
```

Minimal example:

```text
INSTRUCTIONS:
You are an AI tutor helping a student understand a document.
...

DOCUMENT CONTENT:
--- PAGE 1 ---
Neural networks learn patterns...

USER QUESTION:
What are weights and how are they used?

EXPLANATION:
```

---

## 8. API Endpoints

Schemas are defined in [schemas.py](../backend/app/models/schemas.py).

### `POST /api/documents`
Purpose: upload a PDF and register it in memory.

Request:
- `multipart/form-data` with `file`.

Response (`DocumentUploadResponse`):
- `document_id: str`
- `filename: str`
- `page_count: int`

Important errors:
- 400 non-PDF or invalid PDF
- 400 missing filename

### `GET /api/documents/{document_id}/pages/{page_number}`
Purpose: retrieve extracted text and page metadata.

Response (`PageResponse`):
- `document_id`, `page_number`, `page_count`, `filename`, `text`

Important errors:
- 404 document not found
- 400 page out of range

### `POST /api/explain`
Purpose: generate explanation for selected pages and question.

Request (`ExplainRequest`):
- `document_id: str`
- `pages: list[int]` (deduped/sorted by validator)
- `question: str`

Response (`ExplainResponse`):
- `answer: str`
- `pages_used: list[int]`
- `provider: str`
- `input_tokens: int | null` (provider-reported when available)
- `output_tokens: int | null` (provider-reported when available)
- `estimated_cost_usd: float | null` (provider-reported when available)

Important errors:
- 404/400 from PDF lookup/range validation
- 500 if provider inference/loading fails (e.g., model access/runtime errors)

### `POST /api/speech`
Purpose: synthesize speech from explanation text.

Request (`SpeechRequest`):
- `text: str`

Response (`SpeechResponse`):
- `audio_base64: str`
- `mime_type: str`
- `provider: str`

Current default path:
- Mock provider returns generated WAV tone (not semantic TTS).

### `GET /api/providers`
Purpose: return configured provider names/options.

Response (`ProviderConfigResponse`):
- `llm_provider`
- `gemma_model_id`
- `gemma_max_new_tokens`
- `tts_provider`
- `stt_provider`
- `available_*_providers`

### `GET /api/providers/status`
Purpose: return runtime provider status.

Response (`ProviderStatusResponse`):
- `llm` (`provider`, optional `model`, optional `device`, optional `loaded`)
- `tts` (`provider`)

---

## 9. Provider Diagnostics

Endpoint: `GET /api/providers/status` in [providers.py](../backend/app/api/providers.py), backed by [provider_factory.py](../backend/app/services/provider_factory.py).

Field meanings for `llm`:
- `provider`: active LLM implementation (`mock` or `gemma`)
- `model`: configured HF model ID (Gemma path)
- `device`: selected target device string (`mps`, `cuda`, or `cpu`)
- `loaded`: whether model/tokenizer are currently loaded in-process

Important distinction:
- **MPS available** means hardware/backend support exists (PyTorch capability).
- **`loaded: true` on status with `device: "mps"`** indicates the current provider instance has loaded the model and moved it to that selected device path.

---

## 10. Frontend Implementation

Main orchestration: [page.tsx](../frontend/app/page.tsx)

- PDF upload:
  - [PDFUploader.tsx](../frontend/components/PDFUploader.tsx) supports drag-and-drop and file picker.
  - Calls `uploadDocument` in [api.ts](../frontend/lib/api.ts).

- PDF rendering/navigation:
  - [PDFViewer.tsx](../frontend/components/PDFViewer.tsx) uses `react-pdf` (`Document`, `Page`) + zoom + prev/next.
  - Rendering uses local `File` object from browser.

- Page selection:
  - [PageSelector.tsx](../frontend/components/PageSelector.tsx) supports single pages and ranges (`2-4,7`) with validation.

- Tutor workflow:
  - [TutorPanel.tsx](../frontend/components/TutorPanel.tsx) manages question input and send action.
  - [ChatMessage.tsx](../frontend/components/ChatMessage.tsx) renders assistant responses with `react-markdown`.

- Provider config UI:
  - [ProviderConfigPanel.tsx](../frontend/components/ProviderConfigPanel.tsx) consumes `GET /api/providers`.

- Listen behavior:
  - Clicking Listen calls `POST /api/speech`.
  - Audio returned as base64 data URL and played in [AudioPlayer.tsx](../frontend/components/AudioPlayer.tsx).
  - This is currently backed by mock TTS unless TTS provider changes.

Placeholder/mock aspects:
- Microphone button in `TutorPanel` is UI placeholder (no STT flow).
- Speech generation defaults to mock tone output (not Qwen3 synthesis).

---

## 11. Configuration

Variables currently used by code:

| Variable | Default | Purpose |
|---|---|---|
| `CORS_ALLOW_ORIGINS` | `http://localhost:3000` | Comma-separated CORS allowlist in [main.py](../backend/app/main.py) |
| `PDF_UPLOAD_DIR` | `backend/uploads` | Backend local PDF storage directory in [main.py](../backend/app/main.py) |
| `DATABASE_URL` | `sqlite:///./evaluation.db` | SQLAlchemy/Alembic DB URL for evaluation tables in [database.py](../backend/app/evaluation/database.py) |
| `LLM_PROVIDER` | `mock` | Select LLM provider (`mock`, `gemma_local`, `gemma_remote`, `gemma`) in [provider_factory.py](../backend/app/services/provider_factory.py) |
| `GEMMA_MODEL_ID` | `""` | HF model ID for Gemma provider |
| `GEMMA_MAX_NEW_TOKENS` | `1000` | Max generation length for Gemma |
| `GEMMA_REMOTE_URL` | `""` | Base URL for remote Gemma service when `LLM_PROVIDER=gemma_remote` |
| `GEMMA_REMOTE_API_KEY` | `""` | API key sent as `X-API-Key` header for remote Gemma service |
| `GEMMA_REMOTE_TIMEOUT_SECONDS` | `120` | Timeout for remote inference requests |
| `TTS_PROVIDER` | `mock` | Select TTS provider (`mock` / `qwen3`) |
| `QWEN3_TTS_CHECKPOINT` | unset | Placeholder value passed to `Qwen3TTSProvider` constructor |
| `STT_PROVIDER` | `whisper` | Reported in provider config endpoint (STT not wired to endpoint) |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Frontend API base URL in [api.ts](../frontend/lib/api.ts) |
| `RUNPOD_API_KEY` | `""` | Required by [runpod_service/main.py](../runpod_service/app/main.py) to authorize remote requests |

---

## 12. Local Development

### Backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Apply evaluation DB migration:

```bash
cd backend
alembic upgrade head
```

### Frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

### Hugging Face authentication (Gemma)

```bash
huggingface-cli login
```

Optional access verification:

```bash
python -c "from huggingface_hub import hf_hub_download; print(hf_hub_download('google/gemma-3-4b-it','config.json'))"
```

### Run with MockLLMProvider

```bash
cd backend
LLM_PROVIDER=mock uvicorn app.main:app --reload --port 8000
```

### Run with GemmaProvider

```bash
cd backend
LLM_PROVIDER=gemma \
GEMMA_MODEL_ID=google/gemma-3-4b-it \
GEMMA_MAX_NEW_TOKENS=750 \
uvicorn app.main:app --reload --port 8000
```

### Run with Remote GemmaProvider (backend adapter)

```bash
cd backend
LLM_PROVIDER=gemma_remote \
GEMMA_MODEL_ID=google/gemma-3-4b-it \
GEMMA_REMOTE_URL=http://localhost:9000 \
GEMMA_REMOTE_API_KEY=change-me \
uvicorn app.main:app --reload --port 8000
```

### Evaluation runner workflow

```bash
cd backend
alembic upgrade head

cd ..
python evaluation/runner/run_evaluation.py --experiment e1a_gemma3_4b_text_m1_mps --new
python evaluation/runner/run_evaluation.py --experiment e1a_gemma3_4b_text_m1_mps --status
python evaluation/runner/run_evaluation.py --experiment e1a_gemma3_4b_text_m1_mps --resume --backend-url http://localhost:8000
python evaluation/runner/run_evaluation.py --experiment e1a_gemma3_4b_text_m1_mps --resume --backend-url http://localhost:8000 --input-cost-per-1m-usd 0.08 --output-cost-per-1m-usd 0.30
python evaluation/runner/run_evaluation.py --experiment e1a_gemma3_4b_text_m1_mps --backfill-cost --input-cost-per-1m-usd 0.08 --output-cost-per-1m-usd 0.30
python evaluation/runner/run_evaluation.py --experiment e1a_gemma3_4b_text_m1_mps --backfill-cost --overwrite-costs --input-cost-per-1m-usd 0.08 --output-cost-per-1m-usd 0.30
python evaluation/runner/run_evaluation.py --experiment e1a_gemma3_4b_text_m1_mps --import-e1
python evaluation/runner/run_evaluation.py --experiment e1a_gemma3_4b_text_m1_mps --compare-with e1b_gemma3_4b_text_runpod_cuda
```

---

## 13. Dependencies

Backend versions/ranges from [requirements.txt](../backend/requirements.txt):

- `fastapi==0.116.1` — HTTP API framework.
- `pydantic==2.11.7` — request/response/data validation.
- `pymupdf==1.26.4` — PDF parsing and text extraction.
- `python-multipart==0.0.20` — multipart upload handling.
- `sqlalchemy==2.0.36` — ORM and DB access for experiment/case persistence.
- `alembic==1.14.1` — DB migrations for evaluation schema.
- `psycopg[binary]==3.2.6` — PostgreSQL driver.
- `torch>=2.4,<2.7` — model execution backend (MPS/CUDA/CPU).
- `transformers>=4.52,<4.56` — tokenizer/model loading and generation.
- `tokenizers>=0.21,<0.22` — tokenizer runtime compatibility.
- `huggingface_hub>=0.33,<1.0` — model hub access/auth/download.
- `accelerate>=1.0,<1.11` — transformer loading/runtime dependency.
- `sentencepiece>=0.2,<0.3` — tokenizer dependency for many HF models.
- `requests==2.32.3` (transitive in env, used directly by runner) — backend API calls from evaluation runner.

Frontend versions from [package.json](../frontend/package.json):

- `next@15.0.3` — frontend framework.
- `react@18.3.1`, `react-dom@18.3.1` — UI runtime.
- `react-pdf@9.1.1` (PDF.js wrapper) — in-browser PDF render.
- `react-markdown@9.0.1` — markdown answer rendering.
- `tailwindcss@3.4.16` (+ postcss/autoprefixer) — styling.

---

## 14. Testing

Current test files:
- [test_api.py](../backend/tests/test_api.py)
  - document upload/page retrieval
  - explain path with mock provider
  - speech endpoint with mock provider
  - provider config/status endpoints
- [test_integration.py](../backend/tests/test_integration.py)
  - upload -> page read -> explain -> speech workflow
- [test_llm_configuration.py](../backend/tests/test_llm_configuration.py)
  - prompt section presence
  - page-grounding formatting
  - provider selection behavior
  - missing `GEMMA_MODEL_ID` validation
- [test_evaluation_storage.py](../backend/tests/test_evaluation_storage.py)
  - experiment/case idempotent creation
  - completed-case skipping and failed/interrupted-case retry logic
  - experiment config mismatch detection
  - progress accounting and idempotent E1 import
- [test_remote_gemma_provider.py](../backend/tests/test_remote_gemma_provider.py)
  - remote provider success/error handling
  - required auth/url/model validation
  - provider-factory no-fallback behavior for remote mode

Common commands:

```bash
cd backend && pytest -q
cd frontend && npm run lint
cd frontend && npm run typecheck
```

Note: test counts vary over time as tests are added/removed.

---

## 15. Current Performance Observations

The codebase does not yet contain a formal benchmark harness.

Point-in-time development-session observations (2026-10-03, local Mac, Gemma on MPS):

| Date | Model | Device | Observation |
|---|---|---|---|
| 2026-10-03 | `google/gemma-3-4b-it` | `mps` | First explain request ~143s (includes lazy model load), subsequent explain ~12s with model already loaded |
| 2026-10-03 (E1 baseline run) | `google/gemma-3-4b-it` | `mps` | Provider status transitioned `loaded: false -> true`; measured cold text-only inference 32.37s; warm inference samples: 9.31s, 9.90s, 193.40s, 110.23s, 253.85s, 196.34s, 234.13s, 335.21s, 53.90s (input size strongly affected latency) |
| 2026-10-04 (E1b baseline run) | `google/gemma-3-4b-it` | `runpod_cuda` | Real remote path (`RemoteGemmaProvider` -> Runpod RTX 4090/CUDA) completed 10/10 cases; sum per-case latency 321.55s vs E1a 1428.64s (4.44x speedup), with same 3/10 token-cap hits |

These are informal validation measurements, not controlled benchmarks.

E1 run notes (text-only):
- Configuration: `LLM_PROVIDER=gemma`, `GEMMA_MODEL_ID=google/gemma-3-4b-it`, `GEMMA_MAX_NEW_TOKENS=750`
- Synthetic insufficient-information case correctly returned that the document did not provide optimizer/schedule details.
- Real-world grounding check (early-page hallucination test) returned an insufficiency response instead of inventing the full later derivation.

---

## 16. Known Limitations

Currently supported by code constraints:

- Text-only document grounding in LLM path (no page image input to Gemma yet).
- No visual reasoning over figures/diagrams beyond extracted text.
- TTS endpoint defaults to mock audio generation; Qwen3 not implemented.
- STT is interface/placeholder only; no transcription endpoint.
- No RAG/vector retrieval or citation indexing.
- Uploaded PDFs are locally stored and not automatically cleaned.
- Document index is in-memory per process (not persistent across restart).
- Single-process app-level model serving; no inference queue/service isolation.
- Evaluation runner does not yet compute rubric scores; it stores run outputs/latencies and supports import/resume/compare.
- Remote inference path depends on external service availability/network; full E1b run has now been exercised with 10/10 completed cases on Runpod CUDA.
- No authentication/authorization.
- Local/dev-oriented deployment profile.

---

## 17. Planned Implementation Work

PLANNED work aligned with [pdf_explainer_design_doc.md](./pdf_explainer_design_doc.md):

- **Phase 1 / M3 (Implemented):** Multimodal Gemma execution path
  - Page rendering implemented in backend via PyMuPDF
  - Text + image provider interfaces implemented locally and remotely
  - E2 experiment execution intentionally not run yet

- **Phase 2 / M4 (Planned):** Qwen3-TTS
  - Replace mock speech synthesis with real model inference
  - Potential streaming audio

- **Phase 3 / M5 (Planned):** Whisper STT
  - Add microphone input flow and transcription endpoint

- **Phase 4 / M6+ (Partial + Planned):** Evaluation framework
  - Implemented: dataset case registry, persistent experiment storage, idempotent import/resume/status/compare runner actions.
  - Planned: rubric scoring pipeline, automated metric aggregation, and multimodal A/B reporting extensions.

All items in this section are planned unless explicitly implemented elsewhere in this document.

---

## 18. Design vs Implementation

- [pdf_explainer_design_doc.md](./pdf_explainer_design_doc.md) describes intended architecture, product direction, and research goals.
- `implementation_details.md` documents what the codebase currently does.

This implementation document should be updated whenever major implementation behavior changes.
