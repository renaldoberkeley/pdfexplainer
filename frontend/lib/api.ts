export interface UploadDocumentResponse {
  document_id: string;
  filename: string;
  page_count: number;
}

export interface ExplainRequest {
  document_id: string;
  pages: number[];
  question: string;
}

export interface ExplainResponse {
  answer: string;
  pages_used: number[];
  provider: string;
}

export interface SpeechResponse {
  audio_base64: string;
  mime_type: string;
  provider: string;
}

export interface ProviderConfig {
  llm_provider: string;
  gemma_model_id: string;
  gemma_max_new_tokens: string;
  gemma_remote_url: string;
  tts_provider: string;
  stt_provider: string;
  available_llm_providers: string[];
  available_tts_providers: string[];
  available_stt_providers: string[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function parseResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : null;
  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String(payload.detail)
        : `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return payload as T;
}

export async function uploadDocument(file: File): Promise<UploadDocumentResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/documents`, {
    method: "POST",
    body: formData,
  });
  return parseResponse<UploadDocumentResponse>(response);
}

export async function requestExplanation(payload: ExplainRequest): Promise<ExplainResponse> {
  const response = await fetch(`${API_BASE_URL}/api/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse<ExplainResponse>(response);
}

export async function requestSpeech(text: string): Promise<SpeechResponse> {
  const response = await fetch(`${API_BASE_URL}/api/speech`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  return parseResponse<SpeechResponse>(response);
}

export async function getProviderConfig(): Promise<ProviderConfig> {
  const response = await fetch(`${API_BASE_URL}/api/providers`);
  return parseResponse<ProviderConfig>(response);
}
