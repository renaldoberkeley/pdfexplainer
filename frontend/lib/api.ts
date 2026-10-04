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

export interface Hv1RubricCriterion {
  name: string;
  applies_to: string;
  anchors: Record<string, string>;
}

export interface Hv1RubricSummary {
  rubric_version: string;
  abstention_policy: string;
  criteria: Hv1RubricCriterion[];
}

export interface Hv1CalibrationExample {
  calibration_id: string;
  document_title: string;
  pages: number[];
  source_text: string;
  question: string;
  answer: string;
  rubric_walkthrough: Record<string, number>;
  notes: string;
}

export interface Hv1PageSource {
  page_number: number;
  image_base64: string;
  image_mime_type: string;
  extracted_text: string;
  width: number;
  height: number;
}

export interface Hv1TaskPayload {
  hv1_response_id: string;
  is_visual_case: boolean;
  question: string;
  answer: string;
  source_document: string;
  source_pages: Hv1PageSource[];
}

export interface Hv1Progress {
  completed: number;
  total: number;
  remaining: number;
  completed_percent: number;
}

export interface Hv1SessionStartRequest {
  prolific_pid?: string;
  study_id?: string;
  session_id?: string;
  local_participant_label?: string;
}

export interface Hv1SessionStartResponse {
  participant_session_id: string;
  provider: string;
  progress: Hv1Progress;
  next_task: Hv1TaskPayload | null;
  rubric: Hv1RubricSummary;
  calibration_example: Hv1CalibrationExample;
  intro_notice: string;
}

export interface Hv1TaskResponse {
  participant_session_id: string;
  progress: Hv1Progress;
  next_task: Hv1TaskPayload | null;
}

export interface Hv1RatingSubmitRequest {
  hv1_response_id: string;
  factual_correctness: number;
  document_grounding: number;
  completeness: number;
  teaching_clarity: number;
  visual_grounding?: number | null;
  visual_detail_accuracy?: number | null;
  comment?: string | null;
}

export interface Hv1RatingSubmitResponse {
  participant_session_id: string;
  saved: boolean;
  progress: Hv1Progress;
  next_task: Hv1TaskPayload | null;
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

export async function startHv1Session(
  payload: Hv1SessionStartRequest,
): Promise<Hv1SessionStartResponse> {
  const response = await fetch(`${API_BASE_URL}/api/research/hv1/session/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse<Hv1SessionStartResponse>(response);
}

export async function getHv1Task(participantSessionId: string): Promise<Hv1TaskResponse> {
  const response = await fetch(`${API_BASE_URL}/api/research/hv1/session/${participantSessionId}/task`);
  return parseResponse<Hv1TaskResponse>(response);
}

export async function submitHv1Rating(
  participantSessionId: string,
  payload: Hv1RatingSubmitRequest,
): Promise<Hv1RatingSubmitResponse> {
  const response = await fetch(`${API_BASE_URL}/api/research/hv1/session/${participantSessionId}/rating`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse<Hv1RatingSubmitResponse>(response);
}
