from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.evaluation.models import EvaluationCase, EvaluationExperiment
from evaluation.runner.cases import EvaluationCaseDef


@dataclass(slots=True)
class ProgressStats:
    total: int
    completed: int
    failed: int
    running: int
    pending: int


def _config_shape(defn: dict[str, Any]) -> dict[str, Any]:
    return {
        "model_id": defn["model_id"],
        "provider": defn["provider"],
        "input_mode": defn["input_mode"],
        "hardware_backend": defn["hardware_backend"],
        "execution_environment": defn["execution_environment"],
        "device": defn["device"],
        "prompt_version": defn["prompt_version"],
        "max_new_tokens": int(defn["max_new_tokens"]),
    }


def ensure_experiment(
    session: Session,
    *,
    experiment_key: str,
    definition: dict[str, Any],
    cases: list[EvaluationCaseDef],
    create_if_missing: bool,
) -> EvaluationExperiment:
    existing = session.execute(
        select(EvaluationExperiment).where(EvaluationExperiment.experiment_key == experiment_key)
    ).scalar_one_or_none()

    if existing is None:
        if not create_if_missing:
            raise ValueError(f"Experiment {experiment_key} not found. Use --new first.")
        cfg = _config_shape(definition)
        experiment = EvaluationExperiment(
            experiment_key=experiment_key,
            name=str(definition["name"]),
            model_id=str(definition["model_id"]),
            provider=str(definition["provider"]),
            input_mode=str(definition["input_mode"]),
            hardware_backend=str(definition["hardware_backend"]),
            execution_environment=str(definition["execution_environment"]),
            device=str(definition["device"]),
            prompt_version=str(definition["prompt_version"]),
            max_new_tokens=int(definition["max_new_tokens"]),
            status="pending",
            total_cases=len(cases),
            completed_cases=0,
            total_estimated_cost_usd=0.0,
            configuration=cfg,
        )
        session.add(experiment)
        session.flush()
        for case in cases:
            session.add(
                EvaluationCase(
                    experiment_id=experiment.id,
                    case_id=case.case_id,
                    document=case.document,
                    pages=case.pages,
                    question=case.question,
                    case_input_mode=experiment.input_mode,
                    status="pending",
                )
            )
        session.commit()
        return experiment

    expected = _config_shape(definition)
    observed = {
        "model_id": existing.model_id,
        "provider": existing.provider,
        "input_mode": existing.input_mode,
        "hardware_backend": existing.hardware_backend,
        "execution_environment": existing.execution_environment,
        "device": existing.device,
        "prompt_version": existing.prompt_version,
        "max_new_tokens": existing.max_new_tokens,
    }
    if observed != expected:
        raise ValueError(
            f"Experiment configuration mismatch for {experiment_key}. "
            f"Existing={observed} Expected={expected}"
        )

    existing.total_cases = len(cases)
    _sync_cases(session, existing, cases)
    session.commit()
    return existing


def _sync_cases(session: Session, experiment: EvaluationExperiment, cases: list[EvaluationCaseDef]) -> None:
    existing_rows = session.execute(
        select(EvaluationCase).where(EvaluationCase.experiment_id == experiment.id)
    ).scalars()
    by_id = {row.case_id: row for row in existing_rows}
    for case in cases:
        if case.case_id not in by_id:
            session.add(
                EvaluationCase(
                    experiment_id=experiment.id,
                    case_id=case.case_id,
                    document=case.document,
                    pages=case.pages,
                    question=case.question,
                    case_input_mode=experiment.input_mode,
                    status="pending",
                )
            )


def get_progress(session: Session, experiment: EvaluationExperiment) -> ProgressStats:
    rows = session.execute(
        select(EvaluationCase.status).where(EvaluationCase.experiment_id == experiment.id)
    ).scalars()
    counts = {"completed": 0, "failed": 0, "running": 0, "pending": 0}
    total = 0
    for status in rows:
        total += 1
        counts[status] = counts.get(status, 0) + 1
    return ProgressStats(
        total=total,
        completed=counts.get("completed", 0),
        failed=counts.get("failed", 0),
        running=counts.get("running", 0),
        pending=counts.get("pending", 0),
    )


def list_cases_for_resume(
    session: Session,
    experiment: EvaluationExperiment,
    *,
    stale_running_minutes: int,
) -> list[EvaluationCase]:
    stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_running_minutes)
    rows = session.execute(
        select(EvaluationCase)
        .where(EvaluationCase.experiment_id == experiment.id)
        .order_by(EvaluationCase.id.asc())
    ).scalars()
    runnable: list[EvaluationCase] = []
    for row in rows:
        if row.status == "completed":
            continue
        if row.status == "pending" or row.status == "failed":
            runnable.append(row)
            continue
        if row.status == "running" and (row.started_at is None or row.started_at <= stale_cutoff):
            runnable.append(row)
    return runnable


def mark_case_running(session: Session, case: EvaluationCase) -> None:
    case.status = "running"
    case.error = None
    case.started_at = datetime.now(timezone.utc)
    case.completed_at = None
    session.commit()


def mark_case_completed(
    session: Session,
    case: EvaluationCase,
    *,
    answer: str,
    input_tokens: int | None,
    output_tokens: int | None,
    estimated_cost_usd: float | None,
    latency_seconds: float,
    image_count: int | None = None,
    image_metadata: dict[str, Any] | None = None,
    request_payload_bytes: int | None = None,
    image_preprocessing_seconds: float | None = None,
    server_generation_seconds: float | None = None,
    approximate_tokens_per_second: float | None = None,
    performance_metadata: dict[str, Any] | None = None,
) -> None:
    case.status = "completed"
    case.answer = answer
    case.input_tokens = input_tokens
    case.output_tokens = output_tokens
    case.estimated_cost_usd = estimated_cost_usd
    case.latency_seconds = latency_seconds
    case.image_count = image_count
    case.image_metadata = image_metadata
    case.request_payload_bytes = request_payload_bytes
    case.image_preprocessing_seconds = image_preprocessing_seconds
    case.server_generation_seconds = server_generation_seconds
    case.approximate_tokens_per_second = approximate_tokens_per_second
    case.performance_metadata = performance_metadata
    case.completed_at = datetime.now(timezone.utc)
    case.error = None
    session.commit()


def mark_case_failed(session: Session, case: EvaluationCase, *, error: str) -> None:
    case.status = "failed"
    case.error = error
    case.completed_at = datetime.now(timezone.utc)
    session.commit()


def update_experiment_aggregate(session: Session, experiment: EvaluationExperiment) -> ProgressStats:
    progress = get_progress(session, experiment)
    experiment.completed_cases = progress.completed
    rows = session.execute(
        select(EvaluationCase.estimated_cost_usd).where(
            EvaluationCase.experiment_id == experiment.id
        )
    ).scalars()
    experiment.total_estimated_cost_usd = round(
        sum(cost for cost in rows if cost is not None), 8
    )
    if progress.completed == progress.total and progress.total > 0:
        experiment.status = "completed"
        experiment.completed_at = datetime.now(timezone.utc)
    elif progress.running > 0:
        experiment.status = "running"
    elif progress.failed > 0 and progress.completed < progress.total:
        experiment.status = "running"
    else:
        experiment.status = "pending"
    if experiment.started_at is None:
        experiment.started_at = datetime.now(timezone.utc)
    session.commit()
    return progress
