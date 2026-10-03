from __future__ import annotations

import io
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def create_pdf_bytes() -> bytes:
    document = fitz.open()
    page_1 = document.new_page()
    page_1.insert_text((72, 72), "Transformer introduction and model overview.")
    page_2 = document.new_page()
    page_2.insert_text((72, 72), "Scaled dot-product attention equation and explanation.")
    return document.tobytes()


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.pdf_service.storage_dir = tmp_path
    return TestClient(app)


def test_full_upload_read_explain_and_speech_workflow(client: TestClient) -> None:
    pdf_bytes = create_pdf_bytes()

    upload_response = client.post(
        "/api/documents",
        files={"file": ("attention_is_all_you_need.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_response.status_code == 200
    upload_payload = upload_response.json()
    document_id = upload_payload["document_id"]
    assert upload_payload["page_count"] == 2

    page_response = client.get(f"/api/documents/{document_id}/pages/2")
    assert page_response.status_code == 200
    page_payload = page_response.json()
    assert page_payload["page_number"] == 2
    assert "Scaled dot-product attention equation" in page_payload["text"]

    explain_response = client.post(
        "/api/explain",
        json={
            "document_id": document_id,
            "pages": [2],
            "question": "Explain the scaled dot-product attention equation.",
        },
    )
    assert explain_response.status_code == 200
    explain_payload = explain_response.json()
    assert explain_payload["pages_used"] == [2]
    assert explain_payload["provider"] == "mock-llm"
    assert "scaled dot-product attention equation".lower() in explain_payload["answer"].lower()

    speech_response = client.post("/api/speech", json={"text": explain_payload["answer"]})
    assert speech_response.status_code == 200
    speech_payload = speech_response.json()
    assert speech_payload["provider"] == "mock-tts"
    assert speech_payload["mime_type"] == "audio/wav"
    assert len(speech_payload["audio_base64"]) > 100

