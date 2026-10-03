from __future__ import annotations

import argparse
import io
import json
import os
import sys
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz
import requests
from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.evaluation.database import create_session_factory
from app.evaluation.models import EvaluationCase, EvaluationExperiment
from evaluation.runner.cases import E1_CASES, EXPERIMENT_DEFS
from evaluation.runner.storage import (
    ensure_experiment,
    get_progress,
    list_cases_for_resume,
    mark_case_completed,
    mark_case_failed,
    mark_case_running,
    update_experiment_aggregate,
)


@dataclass(slots=True)
class ExplainResult:
    answer: str
    provider: str | None
    pages_used: list[int] | None
    latency_seconds: float
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: float | None


class EvaluationApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def upload_document(self, file_name: str, file_bytes: bytes) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/api/documents",
            files={"file": (file_name, io.BytesIO(file_bytes), "application/pdf")},
            timeout=120,
        )
        response.raise_for_status()
        return response.json()

    def explain(self, document_id: str, pages: list[int], question: str) -> ExplainResult:
        start = time.monotonic()
        response = requests.post(
            f"{self.base_url}/api/explain",
            json={"document_id": document_id, "pages": pages, "question": question},
            timeout=7200,
        )
        latency = round(time.monotonic() - start, 2)
        response.raise_for_status()
        payload = response.json()
        answer = str(payload["answer"])
        return ExplainResult(
            answer=answer,
            provider=payload.get("provider"),
            pages_used=payload.get("pages_used"),
            latency_seconds=latency,
            input_tokens=payload.get("input_tokens"),
            output_tokens=payload.get("output_tokens"),
            estimated_cost_usd=payload.get("estimated_cost_usd"),
        )


class EvaluationRunner:
    def __init__(self, api_client: EvaluationApiClient) -> None:
        self._api = api_client

    def run_case(self, case: EvaluationCase) -> ExplainResult:
        if case.document == "synthetic_e1_smoke.pdf":
            pdf_bytes = self._create_synthetic_pdf()
        else:
            file_path = PROJECT_ROOT / "evaluation" / "documents" / case.document
            pdf_bytes = file_path.read_bytes()

        uploaded = self._api.upload_document(case.document, pdf_bytes)
        return self._api.explain(uploaded["document_id"], case.pages, case.question)

    @staticmethod
    def _create_synthetic_pdf() -> bytes:
        document = fitz.open()
        page = document.new_page()
        text = (
            "Neural networks learn patterns by adjusting numerical parameters called weights. "
            "Training uses examples to progressively update these weights."
        )
        page.insert_text((72, 72), textwrap.fill(text, 70))
        return document.tobytes()


def _resolve_results_file_path(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()

    candidates = [
        Path.home()
        / ".copilot"
        / "session-state"
        / "3ee9ca63-e860-43c9-81bf-0f218e46425b"
        / "files"
        / "e1_baseline_results.json",
        PROJECT_ROOT / "evaluation" / "e1_baseline_results.json",
    ]
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Could not locate e1_baseline_results.json. Pass --results-file explicitly."
    )


def _print_status(experiment: EvaluationExperiment, progress: Any) -> None:
    print(
        json.dumps(
            {
                "experiment_key": experiment.experiment_key,
                "name": experiment.name,
                "status": experiment.status,
                "total_cases": progress.total,
                "completed_cases": progress.completed,
                "failed_cases": progress.failed,
                "running_cases": progress.running,
                "pending_cases": progress.pending,
                "total_estimated_cost_usd": experiment.total_estimated_cost_usd,
                "provider": experiment.provider,
                "model_id": experiment.model_id,
                "hardware_backend": experiment.hardware_backend,
                "execution_environment": experiment.execution_environment,
                "device": experiment.device,
            },
            indent=2,
        )
    )


def _estimate_cost_usd(
    *,
    input_tokens: int | None,
    output_tokens: int | None,
    input_cost_per_1m_usd: float | None,
    output_cost_per_1m_usd: float | None,
) -> float | None:
    if input_cost_per_1m_usd is None and output_cost_per_1m_usd is None:
        return None
    total = 0.0
    had_component = False
    if input_cost_per_1m_usd is not None and input_tokens is not None:
        total += (input_tokens / 1_000_000) * input_cost_per_1m_usd
        had_component = True
    if output_cost_per_1m_usd is not None and output_tokens is not None:
        total += (output_tokens / 1_000_000) * output_cost_per_1m_usd
        had_component = True
    if not had_component:
        return None
    return round(total, 8)


def _import_existing_e1(
    session_factory: Any, experiment_key: str, definition: dict[str, Any], results_file: Path
) -> None:
    data = json.loads(results_file.read_text(encoding="utf-8"))
    legacy_case_id_map = {
        "S1_basic": "S1",
        "S2_technical": "S2",
        "S3_insufficient": "S3",
    }
    with session_factory() as session:
        experiment = ensure_experiment(
            session,
            experiment_key=experiment_key,
            definition=definition,
            cases=E1_CASES,
            create_if_missing=True,
        )
        rows = session.execute(
            select(EvaluationCase).where(EvaluationCase.experiment_id == experiment.id)
        ).scalars()
        by_case_id = {row.case_id: row for row in rows}

        def upsert(case_id: str, case_payload: dict[str, Any]) -> None:
            case_id = legacy_case_id_map.get(case_id, case_id)
            if case_id not in by_case_id:
                raise KeyError(f"Unknown case id in import payload: {case_id}")
            row = by_case_id[case_id]
            row.status = "completed"
            row.answer = case_payload["answer"]
            row.latency_seconds = float(case_payload["latency_seconds"])
            row.input_tokens = case_payload.get("input_tokens_estimate")
            row.output_tokens = case_payload.get("output_tokens_estimate")
            row.estimated_cost_usd = case_payload.get("estimated_cost_usd")
            row.error = None

        for section in ("synthetic_smoke", "notebook_e1", "slides_e1"):
            for case_payload in data.get(section, {}).get("cases", []):
                upsert(case_payload["id"], case_payload)

        hallucination = data["hallucination_test"] | {"id": "H1"}
        upsert("H1", hallucination)
        session.commit()
        progress = update_experiment_aggregate(session, experiment)
        _print_status(experiment, progress)


def _resume_experiment(
    session_factory: Any,
    *,
    experiment_key: str,
    definition: dict[str, Any],
    backend_url: str,
    stale_running_minutes: int,
    input_cost_per_1m_usd: float | None,
    output_cost_per_1m_usd: float | None,
) -> None:
    runner = EvaluationRunner(EvaluationApiClient(backend_url))
    with session_factory() as session:
        experiment = ensure_experiment(
            session,
            experiment_key=experiment_key,
            definition=definition,
            cases=E1_CASES,
            create_if_missing=False,
        )
        runnable = list_cases_for_resume(
            session, experiment, stale_running_minutes=stale_running_minutes
        )

        if not runnable:
            progress = update_experiment_aggregate(session, experiment)
            _print_status(experiment, progress)
            return

        for case in runnable:
            mark_case_running(session, case)
            print(f"{case.case_id} → running")
            try:
                result = runner.run_case(case)
                estimated_cost_usd = result.estimated_cost_usd
                if estimated_cost_usd is None:
                    estimated_cost_usd = _estimate_cost_usd(
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        input_cost_per_1m_usd=input_cost_per_1m_usd,
                        output_cost_per_1m_usd=output_cost_per_1m_usd,
                    )
                mark_case_completed(
                    session,
                    case,
                    answer=result.answer,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    estimated_cost_usd=estimated_cost_usd,
                    latency_seconds=result.latency_seconds,
                )
                print(f"{case.case_id} ✓ completed ({result.latency_seconds:.2f}s)")
            except Exception as exc:
                mark_case_failed(session, case, error=str(exc))
                print(f"{case.case_id} ✗ failed ({exc})")
            progress = update_experiment_aggregate(session, experiment)
            print(f"[{progress.completed}/{progress.total}] completed")


def _backfill_costs(
    session_factory: Any,
    *,
    experiment_key: str,
    definition: dict[str, Any],
    input_cost_per_1m_usd: float | None,
    output_cost_per_1m_usd: float | None,
    overwrite_existing: bool,
) -> None:
    if input_cost_per_1m_usd is None and output_cost_per_1m_usd is None:
        raise ValueError(
            "Backfill requires --input-cost-per-1m-usd and/or --output-cost-per-1m-usd."
        )

    with session_factory() as session:
        experiment = ensure_experiment(
            session,
            experiment_key=experiment_key,
            definition=definition,
            cases=E1_CASES,
            create_if_missing=False,
        )
        rows = list(
            session.execute(
                select(EvaluationCase).where(EvaluationCase.experiment_id == experiment.id)
            ).scalars()
        )
        updated = 0
        skipped = 0
        for row in rows:
            if row.status != "completed":
                skipped += 1
                continue
            if row.estimated_cost_usd is not None and not overwrite_existing:
                skipped += 1
                continue
            estimate = _estimate_cost_usd(
                input_tokens=row.input_tokens,
                output_tokens=row.output_tokens,
                input_cost_per_1m_usd=input_cost_per_1m_usd,
                output_cost_per_1m_usd=output_cost_per_1m_usd,
            )
            if estimate is None:
                skipped += 1
                continue
            row.estimated_cost_usd = estimate
            updated += 1

        session.commit()
        progress = update_experiment_aggregate(session, experiment)
        print(
            f"Backfill complete: updated={updated}, skipped={skipped}, "
            f"total_estimated_cost_usd={experiment.total_estimated_cost_usd:.8f}"
        )
        _print_status(experiment, progress)


def _compare_experiments(session_factory: Any, left_key: str, right_key: str) -> None:
    with session_factory() as session:
        left = session.execute(
            select(EvaluationExperiment).where(EvaluationExperiment.experiment_key == left_key)
        ).scalar_one_or_none()
        right = session.execute(
            select(EvaluationExperiment).where(EvaluationExperiment.experiment_key == right_key)
        ).scalar_one_or_none()
        if left is None:
            raise ValueError(f"Experiment not found: {left_key}")
        if right is None:
            raise ValueError(f"Experiment not found: {right_key}")

        left_cases = {
            row.case_id: row
            for row in session.execute(
                select(EvaluationCase).where(EvaluationCase.experiment_id == left.id)
            ).scalars()
        }
        right_cases = {
            row.case_id: row
            for row in session.execute(
                select(EvaluationCase).where(EvaluationCase.experiment_id == right.id)
            ).scalars()
        }

        print(
            f"Total estimated cost USD: left={left.total_estimated_cost_usd:.8f} "
            f"right={right.total_estimated_cost_usd:.8f}"
        )

        print("| Case | M1 MPS | RunPod CUDA | Speedup |")
        print("|---|---:|---:|---:|")
        for case in E1_CASES:
            left_latency = left_cases.get(case.case_id).latency_seconds if case.case_id in left_cases else None
            right_latency = right_cases.get(case.case_id).latency_seconds if case.case_id in right_cases else None
            left_str = f"{left_latency:.2f}" if left_latency is not None else "unavailable"
            right_str = f"{right_latency:.2f}" if right_latency is not None else "unavailable"
            if left_latency and right_latency and right_latency > 0:
                speedup = f"{left_latency / right_latency:.2f}x"
            else:
                speedup = "unavailable"
            print(f"| {case.case_id} | {left_str} | {right_str} | {speedup} |")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluation experiment runner")
    parser.add_argument("--experiment", required=True, help="Experiment key")
    parser.add_argument("--backend-url", default="http://localhost:8000")
    parser.add_argument("--new", action="store_true", help="Create a new experiment shell")
    parser.add_argument("--resume", action="store_true", help="Resume runnable cases")
    parser.add_argument("--status", action="store_true", help="Print experiment status only")
    parser.add_argument("--backfill-cost", action="store_true", help="Backfill estimated costs")
    parser.add_argument(
        "--overwrite-costs",
        action="store_true",
        help="Recompute existing case cost estimates during --backfill-cost.",
    )
    parser.add_argument("--import-e1", action="store_true", help="Import existing E1 JSON results")
    parser.add_argument("--results-file", help="Path to e1_baseline_results.json")
    parser.add_argument("--compare-with", help="Compare with another experiment key")
    parser.add_argument("--stale-running-minutes", type=int, default=10)
    parser.add_argument(
        "--input-cost-per-1m-usd",
        type=float,
        default=None,
        help="Optional input token pricing used for estimated cost tracking.",
    )
    parser.add_argument(
        "--output-cost-per-1m-usd",
        type=float,
        default=None,
        help="Optional output token pricing used for estimated cost tracking.",
    )
    args = parser.parse_args()

    selected_actions = [
        args.new,
        args.resume,
        args.status,
        args.backfill_cost,
        args.import_e1,
        bool(args.compare_with),
    ]
    if sum(1 for item in selected_actions if item) != 1:
        raise SystemExit(
            "Choose exactly one action: --new, --resume, --status, --backfill-cost, --import-e1, or --compare-with."
        )

    if args.experiment not in EXPERIMENT_DEFS:
        raise SystemExit(f"Unknown experiment key: {args.experiment}")

    session_factory = create_session_factory(os.getenv("DATABASE_URL"))
    definition = EXPERIMENT_DEFS[args.experiment]

    if args.new:
        with session_factory() as session:
            experiment = ensure_experiment(
                session,
                experiment_key=args.experiment,
                definition=definition,
                cases=E1_CASES,
                create_if_missing=True,
            )
            progress = get_progress(session, experiment)
            _print_status(experiment, progress)
        return

    if args.status:
        with session_factory() as session:
            experiment = ensure_experiment(
                session,
                experiment_key=args.experiment,
                definition=definition,
                cases=E1_CASES,
                create_if_missing=False,
            )
            progress = get_progress(session, experiment)
            _print_status(experiment, progress)
        return

    if args.import_e1:
        results_path = _resolve_results_file_path(args.results_file)
        _import_existing_e1(session_factory, args.experiment, definition, results_path)
        return

    if args.backfill_cost:
        _backfill_costs(
            session_factory,
            experiment_key=args.experiment,
            definition=definition,
            input_cost_per_1m_usd=args.input_cost_per_1m_usd,
            output_cost_per_1m_usd=args.output_cost_per_1m_usd,
            overwrite_existing=args.overwrite_costs,
        )
        return

    if args.compare_with:
        _compare_experiments(session_factory, args.experiment, args.compare_with)
        return

    if args.resume:
        _resume_experiment(
            session_factory,
            experiment_key=args.experiment,
            definition=definition,
            backend_url=args.backend_url,
            stale_running_minutes=args.stale_running_minutes,
            input_cost_per_1m_usd=args.input_cost_per_1m_usd,
            output_cost_per_1m_usd=args.output_cost_per_1m_usd,
        )
        return


if __name__ == "__main__":
    main()
