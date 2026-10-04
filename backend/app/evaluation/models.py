from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

JSONType = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    pass


class EvaluationExperiment(Base):
    __tablename__ = "evaluation_experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    input_mode: Mapped[str] = mapped_column(String(100), nullable=False)
    hardware_backend: Mapped[str] = mapped_column(String(100), nullable=False)
    execution_environment: Mapped[str] = mapped_column(String(100), nullable=False)
    device: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    max_new_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    total_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    cases: Mapped[list["EvaluationCase"]] = relationship(
        "EvaluationCase", back_populates="experiment", cascade="all, delete-orphan"
    )


class EvaluationCase(Base):
    __tablename__ = "evaluation_cases"
    __table_args__ = (UniqueConstraint("experiment_id", "case_id", name="uq_experiment_case_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("evaluation_experiments.id", ondelete="CASCADE"), nullable=False
    )
    case_id: Mapped[str] = mapped_column(String(50), nullable=False)
    document: Mapped[str] = mapped_column(String(255), nullable=False)
    pages: Mapped[list[int]] = mapped_column(JSONType, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    condition: Mapped[str | None] = mapped_column(String(40), nullable=True)
    case_input_mode: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    image_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    request_payload_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_preprocessing_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    server_generation_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    approximate_tokens_per_second: Mapped[float | None] = mapped_column(Float, nullable=True)
    performance_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    experiment: Mapped[EvaluationExperiment] = relationship(
        "EvaluationExperiment", back_populates="cases"
    )

    scores: Mapped[list["EvaluationScore"]] = relationship(
        "EvaluationScore", back_populates="evaluation_case", cascade="all, delete-orphan"
    )


class EvaluationScore(Base):
    __tablename__ = "evaluation_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("evaluation_experiments.id", ondelete="CASCADE"), nullable=False
    )
    evaluation_case_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("evaluation_cases.id", ondelete="CASCADE"), nullable=False
    )
    condition: Mapped[str] = mapped_column(String(40), nullable=False)
    rubric_version: Mapped[str] = mapped_column(String(80), nullable=False)
    scorer_type: Mapped[str] = mapped_column(String(40), nullable=False)
    scorer_identifier: Mapped[str | None] = mapped_column(String(120), nullable=True)
    factual_correctness: Mapped[int] = mapped_column(Integer, nullable=False)
    document_grounding: Mapped[int] = mapped_column(Integer, nullable=False)
    completeness: Mapped[int] = mapped_column(Integer, nullable=False)
    teaching_clarity: Mapped[int] = mapped_column(Integer, nullable=False)
    visual_grounding: Mapped[int | None] = mapped_column(Integer, nullable=True)
    visual_detail_accuracy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    evaluation_case: Mapped[EvaluationCase] = relationship("EvaluationCase", back_populates="scores")
