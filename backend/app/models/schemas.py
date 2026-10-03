from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    page_count: int


class PageResponse(BaseModel):
    document_id: str
    page_number: int
    page_count: int
    filename: str
    text: str


class ExplainRequest(BaseModel):
    document_id: str = Field(min_length=1)
    pages: list[int] = Field(min_length=1)
    question: str = Field(min_length=1)

    @field_validator("pages")
    @classmethod
    def ensure_pages_are_unique(cls, value: list[int]) -> list[int]:
        normalized = sorted(set(value))
        if not normalized:
            raise ValueError("At least one page must be selected.")
        return normalized


class ExplainResponse(BaseModel):
    answer: str
    pages_used: list[int]
    provider: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1)


class SpeechResponse(BaseModel):
    audio_base64: str
    mime_type: str
    provider: str


class ProviderConfigResponse(BaseModel):
    llm_provider: str
    gemma_model_id: str
    gemma_max_new_tokens: str
    gemma_remote_url: str
    tts_provider: str
    stt_provider: str
    available_llm_providers: list[str]
    available_tts_providers: list[str]
    available_stt_providers: list[str]


class LLMProviderStatus(BaseModel):
    provider: str
    model: str | None = None
    device: str | None = None
    loaded: bool | None = None


class TTSProviderStatus(BaseModel):
    provider: str


class ProviderStatusResponse(BaseModel):
    llm: LLMProviderStatus
    tts: TTSProviderStatus
