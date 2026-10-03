# Open-Source AI PDF Tutor (V1)

V1 includes a complete local workflow:

1. Upload a PDF
2. View and navigate it in the browser
3. Select page(s)
4. Ask the AI Tutor questions
5. Get a Markdown explanation from a mock LLM provider
6. Click **Listen** to synthesize mock audio via a mock TTS provider
7. View active provider status in the Provider Configuration panel

No paid APIs, no auth, and no database are required.

---

## Tech Stack

### Frontend
- Next.js (App Router)
- TypeScript
- React
- Tailwind CSS
- react-pdf (PDF.js)

### Backend
- Python 3.11+
- FastAPI
- Pydantic
- PyMuPDF

### AI / Speech Architecture
- `LLMProvider` abstraction
  - `MockLLMProvider` (active in V1)
  - `GemmaProvider` placeholder
- `TTSProvider` abstraction
  - `MockTTSProvider` (active in V1)
  - `Qwen3TTSProvider` placeholder
- `STTProvider` abstraction
  - `WhisperSTTProvider` placeholder

---

## Project Structure

```text
pdf_explainer/
  frontend/
  backend/
  README.md
  docker-compose.yml
  .gitignore
```

### Backend layout

```text
backend/
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
    services/
      pdf_service.py
      provider_factory.py
      llm/
        base.py
        mock.py
        gemma.py
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
  requirements.txt
```

### Frontend layout

```text
frontend/
  app/
    layout.tsx
    page.tsx
    globals.css
  components/
    ProviderConfigPanel.tsx
    PDFViewer.tsx
    PDFUploader.tsx
    TutorPanel.tsx
    ChatMessage.tsx
    PageSelector.tsx
    AudioPlayer.tsx
  lib/
    api.ts
```

---

## API Endpoints

### `POST /api/documents`
Upload a PDF file.

Response:
```json
{
  "document_id": "uuid",
  "filename": "attention_is_all_you_need.pdf",
  "page_count": 15
}
```

### `GET /api/documents/{document_id}/pages/{page_number}`
Get extracted text and metadata for a page.

### `POST /api/explain`
Request explanation for selected pages.

Request:
```json
{
  "document_id": "uuid",
  "pages": [4],
  "question": "Explain this page"
}
```

Response:
```json
{
  "answer": "...",
  "pages_used": [4],
  "provider": "mock-llm"
}
```

### `POST /api/speech`
Generate speech (mock in V1).

Request:
```json
{
  "text": "Explanation text"
}
```

Response:
```json
{
  "audio_base64": "...",
  "mime_type": "audio/wav",
  "provider": "mock-tts"
}
```

### `GET /api/providers`
Read the active/available provider configuration used by the backend.

Response:
```json
{
  "llm_provider": "mock",
  "tts_provider": "mock",
  "stt_provider": "whisper",
  "available_llm_providers": ["mock", "gemma"],
  "available_tts_providers": ["mock", "qwen3"],
  "available_stt_providers": ["whisper"]
}
```

### `GET /api/providers/status`
Read runtime provider status (no secrets).

Response:
```json
{
  "llm": {
    "provider": "gemma",
    "model": "your-hf-model-id",
    "device": "mps",
    "loaded": false
  },
  "tts": {
    "provider": "mock"
  }
}
```

---

## Local Setup (without Docker)

## 1) Start Backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`.

## 2) Start Frontend

In a second terminal:

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

Frontend runs at `http://localhost:3000`.

---

## Docker Compose

```bash
docker compose up --build
```

---

## Provider Switching

Backend provider selection is env-driven:

- `LLM_PROVIDER=mock` (default)
- `LLM_PROVIDER=gemma`
- `TTS_PROVIDER=mock` (default)
- `TTS_PROVIDER=qwen3` (placeholder class, not wired to inference yet)

Gemma settings:

- `GEMMA_MODEL_ID=` (required when `LLM_PROVIDER=gemma`)
- `GEMMA_MAX_NEW_TOKENS=1000` (optional, default shown)

---

## Running Gemma locally

1. Ensure your Hugging Face account has access to the Gemma model you plan to use.
2. Set `GEMMA_MODEL_ID` to the **exact model ID** you selected from Hugging Face.
3. Switch provider:

```bash
export LLM_PROVIDER=gemma
export GEMMA_MODEL_ID="<PUT_EXACT_GEMMA_HF_MODEL_ID_HERE>"
export GEMMA_MAX_NEW_TOKENS=1000
uvicorn app.main:app --reload --port 8000
```

### Device behavior

The backend chooses device in this order:

1. Apple Silicon MPS
2. CUDA
3. CPU

### Practical limitations on Mac

- Large Gemma checkpoints may be slow on consumer Macs.
- Memory pressure can be high for larger parameter counts.
- First request can take noticeably longer because the model is loaded lazily on first use.

### Switch back to mock quickly

```bash
export LLM_PROVIDER=mock
unset GEMMA_MODEL_ID
uvicorn app.main:app --reload --port 8000
```

---

## Notes for Future Work

- Wire `Qwen3TTSProvider` to Qwen3-TTS inference.
- Add STT endpoint using `WhisperSTTProvider`.
- Consider persistent document storage and async job queueing for large files.
