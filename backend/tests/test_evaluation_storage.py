from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.models import Base, EvaluationCase, EvaluationExperiment
from evaluation.runner.cases import E1_CASES, EXPERIMENT_DEFS
from evaluation.runner.run_evaluation import _backfill_costs, _import_existing_e1
from evaluation.runner.storage import (
    ensure_experiment,
    get_progress,
    list_cases_for_resume,
    mark_case_completed,
    mark_case_running,
    update_experiment_aggregate,
)


@pytest.fixture
def session_factory(tmp_path: Path):
    db_path = tmp_path / "eval.sqlite"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_experiment_and_case_creation(session_factory) -> None:
    with session_factory() as session:
        experiment = ensure_experiment(
            session,
            experiment_key="e1a_gemma3_4b_text_m1_mps",
            definition=EXPERIMENT_DEFS["e1a_gemma3_4b_text_m1_mps"],
            cases=E1_CASES,
            create_if_missing=True,
        )
        assert experiment.total_cases == 10
        total_cases = session.execute(
            select(EvaluationCase).where(EvaluationCase.experiment_id == experiment.id)
        ).scalars()
        assert len(list(total_cases)) == 10


def test_experiment_creation_is_unique(session_factory) -> None:
    with session_factory() as session:
        ensure_experiment(
            session,
            experiment_key="e1a_gemma3_4b_text_m1_mps",
            definition=EXPERIMENT_DEFS["e1a_gemma3_4b_text_m1_mps"],
            cases=E1_CASES,
            create_if_missing=True,
        )
        ensure_experiment(
            session,
            experiment_key="e1a_gemma3_4b_text_m1_mps",
            definition=EXPERIMENT_DEFS["e1a_gemma3_4b_text_m1_mps"],
            cases=E1_CASES,
            create_if_missing=True,
        )
        experiments = session.execute(select(EvaluationExperiment)).scalars()
        cases = session.execute(select(EvaluationCase)).scalars()
        assert len(list(experiments)) == 1
        assert len(list(cases)) == 10


def test_completed_case_is_skipped(session_factory) -> None:
    with session_factory() as session:
        experiment = ensure_experiment(
            session,
            experiment_key="e1a_gemma3_4b_text_m1_mps",
            definition=EXPERIMENT_DEFS["e1a_gemma3_4b_text_m1_mps"],
            cases=E1_CASES,
            create_if_missing=True,
        )
        case = session.execute(
            select(EvaluationCase).where(
                EvaluationCase.experiment_id == experiment.id, EvaluationCase.case_id == "S1"
            )
        ).scalar_one()
        mark_case_running(session, case)
        mark_case_completed(
            session,
            case,
            answer="ok",
            input_tokens=1,
            output_tokens=1,
            estimated_cost_usd=0.000123,
            latency_seconds=1.0,
        )
        runnable = list_cases_for_resume(session, experiment, stale_running_minutes=10)
        assert all(item.case_id != "S1" for item in runnable)


def test_failed_case_is_retried(session_factory) -> None:
    with session_factory() as session:
        experiment = ensure_experiment(
            session,
            experiment_key="e1a_gemma3_4b_text_m1_mps",
            definition=EXPERIMENT_DEFS["e1a_gemma3_4b_text_m1_mps"],
            cases=E1_CASES,
            create_if_missing=True,
        )
        case = session.execute(
            select(EvaluationCase).where(
                EvaluationCase.experiment_id == experiment.id, EvaluationCase.case_id == "S2"
            )
        ).scalar_one()
        case.status = "failed"
        session.commit()
        runnable = list_cases_for_resume(session, experiment, stale_running_minutes=10)
        assert any(item.case_id == "S2" for item in runnable)


def test_interrupted_running_case_is_retried(session_factory) -> None:
    with session_factory() as session:
        experiment = ensure_experiment(
            session,
            experiment_key="e1a_gemma3_4b_text_m1_mps",
            definition=EXPERIMENT_DEFS["e1a_gemma3_4b_text_m1_mps"],
            cases=E1_CASES,
            create_if_missing=True,
        )
        case = session.execute(
            select(EvaluationCase).where(
                EvaluationCase.experiment_id == experiment.id, EvaluationCase.case_id == "S3"
            )
        ).scalar_one()
        case.status = "running"
        case.started_at = None
        session.commit()
        runnable = list_cases_for_resume(session, experiment, stale_running_minutes=10)
        assert any(item.case_id == "S3" for item in runnable)


def test_configuration_mismatch_detection(session_factory) -> None:
    with session_factory() as session:
        ensure_experiment(
            session,
            experiment_key="e1a_gemma3_4b_text_m1_mps",
            definition=EXPERIMENT_DEFS["e1a_gemma3_4b_text_m1_mps"],
            cases=E1_CASES,
            create_if_missing=True,
        )
        mismatched = dict(EXPERIMENT_DEFS["e1a_gemma3_4b_text_m1_mps"])
        mismatched["max_new_tokens"] = 900
        with pytest.raises(ValueError, match="configuration mismatch"):
            ensure_experiment(
                session,
                experiment_key="e1a_gemma3_4b_text_m1_mps",
                definition=mismatched,
                cases=E1_CASES,
                create_if_missing=True,
            )


def test_progress_calculation(session_factory) -> None:
    with session_factory() as session:
        experiment = ensure_experiment(
            session,
            experiment_key="e1a_gemma3_4b_text_m1_mps",
            definition=EXPERIMENT_DEFS["e1a_gemma3_4b_text_m1_mps"],
            cases=E1_CASES,
            create_if_missing=True,
        )
        rows = session.execute(
            select(EvaluationCase).where(EvaluationCase.experiment_id == experiment.id)
        ).scalars()
        rows = list(rows)
        rows[0].status = "completed"
        rows[1].status = "failed"
        rows[2].status = "running"
        session.commit()
        progress = get_progress(session, experiment)
        assert progress.total == 10
        assert progress.completed == 1
        assert progress.failed == 1
        assert progress.running == 1
        assert progress.pending == 7


def test_e1_json_import_is_idempotent(session_factory, tmp_path: Path) -> None:
    payload = {
        "synthetic_smoke": {
            "cases": [
                {
                    "id": "S1",
                    "answer": "ans1",
                    "latency_seconds": 1.0,
                    "input_tokens_estimate": 10,
                    "output_tokens_estimate": 20,
                }
            ]
        },
        "notebook_e1": {"cases": []},
        "slides_e1": {"cases": []},
        "hallucination_test": {
            "answer": "h1",
            "latency_seconds": 2.0,
            "input_tokens_estimate": 11,
            "output_tokens_estimate": 21,
        },
    }
    results_file = tmp_path / "e1.json"
    results_file.write_text(json.dumps(payload), encoding="utf-8")

    _import_existing_e1(
        session_factory,
        "e1a_gemma3_4b_text_m1_mps",
        EXPERIMENT_DEFS["e1a_gemma3_4b_text_m1_mps"],
        results_file,
    )
    _import_existing_e1(
        session_factory,
        "e1a_gemma3_4b_text_m1_mps",
        EXPERIMENT_DEFS["e1a_gemma3_4b_text_m1_mps"],
        results_file,
    )

    with session_factory() as session:
        cases = list(session.execute(select(EvaluationCase)).scalars())
        assert len(cases) == 10
        s1 = next(case for case in cases if case.case_id == "S1")
        h1 = next(case for case in cases if case.case_id == "H1")
        assert s1.status == "completed"
        assert h1.status == "completed"


def test_experiment_aggregate_tracks_total_cost(session_factory) -> None:
    with session_factory() as session:
        experiment = ensure_experiment(
            session,
            experiment_key="e1a_gemma3_4b_text_m1_mps",
            definition=EXPERIMENT_DEFS["e1a_gemma3_4b_text_m1_mps"],
            cases=E1_CASES,
            create_if_missing=True,
        )
        rows = list(
            session.execute(
                select(EvaluationCase).where(EvaluationCase.experiment_id == experiment.id)
            ).scalars()
        )
        rows[0].status = "completed"
        rows[0].estimated_cost_usd = 0.01000000
        rows[1].status = "completed"
        rows[1].estimated_cost_usd = 0.02000000
        session.commit()

        update_experiment_aggregate(session, experiment)
        refreshed = session.execute(
            select(EvaluationExperiment).where(EvaluationExperiment.id == experiment.id)
        ).scalar_one()
        assert refreshed.total_estimated_cost_usd == 0.03


def test_backfill_costs_from_token_counts(session_factory) -> None:
    with session_factory() as session:
        experiment = ensure_experiment(
            session,
            experiment_key="e1a_gemma3_4b_text_m1_mps",
            definition=EXPERIMENT_DEFS["e1a_gemma3_4b_text_m1_mps"],
            cases=E1_CASES,
            create_if_missing=True,
        )
        row = session.execute(
            select(EvaluationCase).where(
                EvaluationCase.experiment_id == experiment.id, EvaluationCase.case_id == "S1"
            )
        ).scalar_one()
        row.status = "completed"
        row.input_tokens = 100_000
        row.output_tokens = 50_000
        session.commit()

    _backfill_costs(
        session_factory,
        experiment_key="e1a_gemma3_4b_text_m1_mps",
        definition=EXPERIMENT_DEFS["e1a_gemma3_4b_text_m1_mps"],
        input_cost_per_1m_usd=0.08,
        output_cost_per_1m_usd=0.30,
        overwrite_existing=False,
    )

    with session_factory() as session:
        experiment = session.execute(select(EvaluationExperiment)).scalar_one()
        row = session.execute(
            select(EvaluationCase).where(EvaluationCase.case_id == "S1")
        ).scalar_one()
        assert row.estimated_cost_usd == 0.023
        assert experiment.total_estimated_cost_usd == 0.023


def test_backfill_costs_requires_pricing(session_factory) -> None:
    with session_factory() as session:
        ensure_experiment(
            session,
            experiment_key="e1a_gemma3_4b_text_m1_mps",
            definition=EXPERIMENT_DEFS["e1a_gemma3_4b_text_m1_mps"],
            cases=E1_CASES,
            create_if_missing=True,
        )
    with pytest.raises(ValueError, match="Backfill requires"):
        _backfill_costs(
            session_factory,
            experiment_key="e1a_gemma3_4b_text_m1_mps",
            definition=EXPERIMENT_DEFS["e1a_gemma3_4b_text_m1_mps"],
            input_cost_per_1m_usd=None,
            output_cost_per_1m_usd=None,
            overwrite_existing=False,
        )
