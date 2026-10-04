from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import create_app


@pytest.fixture
def hv1_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    project_root = Path(__file__).resolve().parents[2]
    db_path = tmp_path / "hv1.sqlite"
    db_url = f"sqlite:///{db_path}"

    monkeypatch.setenv("DATABASE_URL", db_url)

    engine = create_engine(db_url, future=True)
    ddl = (project_root / "backend/tests/sql/hv1_sqlite_schema.sql").read_text(encoding="utf-8")
    with engine.begin() as conn:
        for stmt in [chunk.strip() for chunk in ddl.split(";") if chunk.strip()]:
            conn.execute(text(stmt))

    app = create_app()
    app.state.hv1_service._session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    client = TestClient(app)
    try:
        yield client
    finally:
        client.close()


def test_hv1_session_starts_and_returns_blinded_task(hv1_client: TestClient) -> None:
    response = hv1_client.post("/api/research/hv1/session/start", json={"local_participant_label": "dev-r1"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "development"
    assert payload["progress"]["total"] == 12
    assert payload["next_task"]["hv1_response_id"].startswith("HV1-R")
    assert "condition" not in payload["next_task"]
    assert payload["rubric"]["rubric_version"] == "human_e2_rubric_v1"


def test_hv1_submit_requires_visual_fields_for_visual_case(hv1_client: TestClient) -> None:
    session = hv1_client.post("/api/research/hv1/session/start", json={"local_participant_label": "dev-r2"})
    payload = session.json()
    participant_session_id = payload["participant_session_id"]
    task = payload["next_task"]

    # advance until we find a visual task
    while task and not task["is_visual_case"]:
        submit = hv1_client.post(
            f"/api/research/hv1/session/{participant_session_id}/rating",
            json={
                "hv1_response_id": task["hv1_response_id"],
                "factual_correctness": 3,
                "document_grounding": 3,
                "completeness": 3,
                "teaching_clarity": 3,
            },
        )
        assert submit.status_code == 200
        task = submit.json()["next_task"]

    assert task is not None and task["is_visual_case"]
    bad_submit = hv1_client.post(
        f"/api/research/hv1/session/{participant_session_id}/rating",
        json={
            "hv1_response_id": task["hv1_response_id"],
            "factual_correctness": 3,
            "document_grounding": 3,
            "completeness": 3,
            "teaching_clarity": 3,
        },
    )
    assert bad_submit.status_code == 422


def test_hv1_prevents_duplicate_submission(hv1_client: TestClient) -> None:
    session = hv1_client.post("/api/research/hv1/session/start", json={"local_participant_label": "dev-r3"})
    payload = session.json()
    participant_session_id = payload["participant_session_id"]
    task = payload["next_task"]
    assert task is not None

    submit_payload = {
        "hv1_response_id": task["hv1_response_id"],
        "factual_correctness": 3,
        "document_grounding": 3,
        "completeness": 3,
        "teaching_clarity": 3,
    }
    if task["is_visual_case"]:
        submit_payload["visual_grounding"] = 3
        submit_payload["visual_detail_accuracy"] = 3

    first = hv1_client.post(
        f"/api/research/hv1/session/{participant_session_id}/rating", json=submit_payload
    )
    assert first.status_code == 200
    second = hv1_client.post(
        f"/api/research/hv1/session/{participant_session_id}/rating", json=submit_payload
    )
    assert second.status_code == 409
