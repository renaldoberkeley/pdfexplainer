from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Hv1SessionStartRequest(BaseModel):
    prolific_pid: str | None = Field(default=None, max_length=128)
    study_id: str | None = Field(default=None, max_length=128)
    session_id: str | None = Field(default=None, max_length=128)
    local_participant_label: str | None = Field(default=None, max_length=128)


class Hv1RubricCriterion(BaseModel):
    name: str
    applies_to: str
    anchors: dict[str, str]


class Hv1RubricSummary(BaseModel):
    rubric_version: str
    abstention_policy: str
    criteria: list[Hv1RubricCriterion]


class Hv1CalibrationExample(BaseModel):
    calibration_id: str
    document_title: str
    pages: list[int]
    source_text: str
    question: str
    answer: str
    rubric_walkthrough: dict[str, int]
    notes: str


class Hv1PageSource(BaseModel):
    page_number: int
    image_base64: str
    image_mime_type: str
    extracted_text: str
    width: int
    height: int


class Hv1TaskPayload(BaseModel):
    hv1_response_id: str
    is_visual_case: bool
    question: str
    answer: str
    source_document: str
    source_pages: list[Hv1PageSource]


class Hv1Progress(BaseModel):
    completed: int
    total: int
    remaining: int
    completed_percent: float


class Hv1SessionStartResponse(BaseModel):
    participant_session_id: str
    provider: str
    progress: Hv1Progress
    next_task: Hv1TaskPayload | None
    rubric: Hv1RubricSummary
    calibration_example: Hv1CalibrationExample
    intro_notice: str


class Hv1ProgressResponse(BaseModel):
    participant_session_id: str
    progress: Hv1Progress


class Hv1TaskResponse(BaseModel):
    participant_session_id: str
    progress: Hv1Progress
    next_task: Hv1TaskPayload | None


class Hv1RatingSubmitRequest(BaseModel):
    hv1_response_id: str
    factual_correctness: int = Field(ge=0, le=4)
    document_grounding: int = Field(ge=0, le=4)
    completeness: int = Field(ge=0, le=4)
    teaching_clarity: int = Field(ge=0, le=4)
    visual_grounding: int | None = Field(default=None, ge=0, le=4)
    visual_detail_accuracy: int | None = Field(default=None, ge=0, le=4)
    comment: str | None = Field(default=None, max_length=4000)

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed if trimmed else None


class Hv1RatingSubmitResponse(BaseModel):
    participant_session_id: str
    saved: bool
    progress: Hv1Progress
    next_task: Hv1TaskPayload | None
