# AI PDF Tutor — Design Document

## 1. Overview

AI PDF Tutor is a web application that allows users to upload a PDF,
select specific pages, and have an open-weight AI model explain the
content conversationally.

The system is designed especially for technical documents such as
research papers, where understanding may require reasoning over:

- Text
- Mathematical equations
- Figures
- Tables
- Architecture diagrams

Users can ask follow-up questions and listen to explanations through
text-to-speech.

---

## 2. Goals

### Primary Goals

- Upload and view PDFs in the browser.
- Ask questions about specific pages.
- Ground AI responses in selected PDF pages.
- Understand both textual and visual page content.
- Generate clear educational explanations.
- Read explanations aloud using an open-weight TTS model.
- Run the core AI models locally or on self-hosted GPU infrastructure.

### ML / Research Goals

- Support experimentation with different open-weight LLMs.
- Measure answer quality and document grounding.
- Compare text-only vs multimodal document understanding.
- Evaluate model size, latency, memory usage, and answer quality.
- Support future fine-tuning / LoRA experiments.

---

## 3. Non-Goals — V1

V1 will not include:

- Authentication
- Multi-user document storage
- Vector database / RAG
- Cloud persistence
- Fine-tuning
- Real-time voice conversations
- Large-scale production deployment

---

## 4. User Experience

Example workflow:

1. User uploads `attention_is_all_you_need.pdf`.
2. PDF appears in the document viewer.
3. User navigates to page 4.
4. User asks:

   "Explain the scaled dot-product attention equation."

5. The application provides Gemma with:
   - Page number
   - Extracted page text
   - Rendered page image
   - User's question

6. Gemma generates an explanation.

7. The explanation appears in the AI Tutor panel.

8. User presses "Listen."

9. Qwen3-TTS converts the explanation to speech.

10. User asks a follow-up question.

---

## 5. System Architecture

                         Browser

          ┌───────────────────────────────┐
          │                               │
          │ PDF Viewer     AI Tutor       │
          │                               │
          │ Page 4         Conversation   │
          │                🔊 Listen      │
          └───────────────┬───────────────┘
                          │
                          ▼
                       FastAPI
                          │
               ┌──────────┴──────────┐
               │                     │
               ▼                     ▼
          PDF Service          AI Services
               │                     │
        ┌──────┴──────┐       ┌─────┴─────┐
        │             │       │           │
       Text         Image   Gemma       Qwen TTS
        │             │       │           │
        └──────┬──────┘       │           │
               └──────────────►           │
                               │           │
                               ▼           ▼
                          Explanation    Audio

---

## 6. Frontend Architecture

Technology:

- Next.js
- React
- TypeScript
- PDF.js / react-pdf
- Tailwind CSS

Major components:

PDFUploader
PDFViewer
PageSelector
TutorPanel
ChatMessage
AudioPlayer
ProviderConfigPanel

The frontend contains no model-specific inference logic.

---

## 7. Backend Architecture

Technology:

- Python
- FastAPI
- PyMuPDF
- PyTorch
- Hugging Face Transformers

Primary endpoints:

POST /api/documents
GET  /api/documents/{id}/pages/{page}
POST /api/explain
POST /api/speech
GET  /api/providers/status

---

## 8. PDF Processing

For every selected page, the PDF service produces:

PageContent:
    page_number
    extracted_text
    rendered_image
    metadata

PyMuPDF performs text extraction and page rendering.

The rendered page is important because text extraction alone may lose:

- Equation formatting
- Charts
- Figures
- Diagrams
- Spatial relationships

---

## 9. LLM Architecture

Models are accessed through a provider abstraction:

LLMProvider
    |
    +-- MockLLMProvider
    |
    +-- GemmaProvider
    |
    +-- FutureProvider

The application should not depend directly on Gemma.

Configuration:

LLM_PROVIDER=gemma
GEMMA_MODEL_ID=...
GEMMA_MAX_NEW_TOKENS=750

---

## 10. Gemma Inference

Initial development model:

google/gemma-3-4b-it

Inference pipeline:

Selected PDF Pages
       |
       +---- extracted text
       |
       +---- page images
       |
       +---- question
       |
       v
    Prompt / Processor
       |
       v
      Gemma
       |
       v
  Explanation

Device preference:

Apple MPS -> CUDA -> CPU

The model should be loaded lazily and reused across requests.

---

## 11. Grounding Strategy

Each page is explicitly identified:

--- PAGE 4 ---
<page content>

--- PAGE 5 ---
<page content>

The model is instructed to:

- Base answers on supplied pages.
- Distinguish document content from general knowledge.
- State when the selected pages do not contain enough information.
- Reference relevant page numbers when appropriate.

---

## 12. Explanation Strategy

For technical material, responses should follow:

### Intuition
What is the author trying to accomplish?

### Technical Explanation
How does the mechanism work?

### Mathematics
For equations:
1. Purpose
2. Variables
3. Operations
4. Intuition

### Figures
Explain:
1. What the figure represents
2. Major components
3. Relationships
4. Why the figure matters

---

## 13. Speech Architecture

TTSProvider
    |
    +-- MockTTSProvider
    |
    +-- Qwen3TTSProvider

Pipeline:

Gemma explanation
       |
       v
   Qwen3-TTS
       |
       v
     Audio
       |
       v
 Browser player

---

## 14. Future Speech Input

STTProvider
    |
    +-- WhisperProvider

This enables:

User microphone
      |
      v
    Whisper
      |
      v
     Text
      |
      v
    Gemma
      |
      v
  Qwen3-TTS
      |
      v
 Spoken response

This creates a conversational document tutor.

---

## 15. Model Evaluation

The system should eventually maintain an evaluation dataset containing:

- PDF page
- Question
- Expected concepts
- Model response

Metrics:

### Document Grounding
Does the answer accurately reflect the selected pages?

### Factual Accuracy
Are claims correct?

### Equation Understanding
Does the model correctly explain mathematical expressions?

### Figure Understanding
Does the explanation correspond to the actual figure?

### Teaching Quality
Is the explanation understandable?

### Hallucination Rate
Does the model invent content not present in the document?

### Performance
- Time to first token
- Total generation time
- Tokens/sec
- GPU memory
- Model load time

---

## 16. Experiment Framework

Experiments should make it possible to compare:

Text only
vs
Text + page image

Small Gemma
vs
Larger Gemma

FP16/BF16
vs
Quantized inference

Prompt A
vs
Prompt B

Base model
vs
LoRA fine-tuned model

Each experiment should use the same evaluation dataset.

---

## 17. Observability

Capture:

- model ID
- inference device
- input token count
- output token count
- model load time
- generation latency
- pages used
- errors

Do not log uploaded document contents by default.

---

## 18. Security / Privacy

Uploaded documents may contain sensitive information.

V1:

- Temporary local storage
- No external model API required
- No permanent document persistence
- Files deleted after expiration/application cleanup

Future versions should define explicit retention policies.

---

## 19. Deployment Evolution

### Phase 1
Local Mac development

Gemma -> Apple MPS

### Phase 2
Remote GPU

Gemma -> RunPod / GPU server

### Phase 3
Optimized model serving

FastAPI
   |
   v
Inference Server
   |
   v
GPU

Potential serving technologies:

- vLLM
- Hugging Face TGI
- llama.cpp / MLX where appropriate

---

## 20. Milestones

### M1 — Application Shell
[x] PDF upload
[x] PDF viewer
[x] Page extraction
[x] Tutor UI
[x] Provider abstraction

### M2 — Local LLM
[x] Gemma provider
[x] MPS detection
[ ] Real Gemma inference

### M3 — Multimodal Understanding
[ ] Render pages
[ ] Send page images to Gemma
[ ] Explain figures/equations

### M4 — Voice Output
[ ] Qwen3-TTS
[ ] Streaming audio
[ ] Audio controls

### M5 — Voice Input
[ ] Whisper
[ ] Microphone input
[ ] Conversational interaction

### M6 — Evaluation
[ ] Evaluation dataset
[ ] Automated model evaluation
[ ] Model comparison dashboard

### M7 — ML Research
[ ] LoRA fine-tuning
[ ] Quantization experiments
[ ] Model comparison
[ ] Latency/quality benchmarking

---

## 21. Open Questions

- Which Gemma checkpoint provides the best quality/latency tradeoff?
- Should page images always be provided or only when visual content exists?
- How should very large documents be handled?
- When does RAG become necessary?
- Should explanations cite page regions in addition to page numbers?
- Can TTS begin streaming before Gemma finishes the complete answer?
- What evaluation methodology best measures teaching quality?