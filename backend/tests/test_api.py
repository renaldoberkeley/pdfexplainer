from __future__ import annotations

import io
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def make_pdf_bytes(pages: list[str]) -> bytes:
    document = fitz.open()
    for content in pages:
        page = document.new_page()
        page.insert_text((72, 72), content)
    return document.tobytes()


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.pdf_service.storage_dir = tmp_path
    return TestClient(app)


def test_upload_and_get_page(client: TestClient) -> None:
    content = make_pdf_bytes(["Hello page one", "Second page text"])
    response = client.post(
        "/api/documents",
        files={"file": ("test.pdf", io.BytesIO(content), "application/pdf")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["page_count"] == 2

    page_response = client.get(f"/api/documents/{payload['document_id']}/pages/1")
    assert page_response.status_code == 200
    page_payload = page_response.json()
    assert page_payload["page_number"] == 1
    assert "Hello page one" in page_payload["text"]


def test_explain_with_mock_provider(client: TestClient) -> None:
    content = make_pdf_bytes(["Attention equation details"])
    upload_response = client.post(
        "/api/documents",
        files={"file": ("attention.pdf", io.BytesIO(content), "application/pdf")},
    )
    document_id = upload_response.json()["document_id"]

    explain_response = client.post(
        "/api/explain",
        json={
            "document_id": document_id,
            "pages": [1],
            "question": "Explain the equation",
        },
    )
    assert explain_response.status_code == 200
    payload = explain_response.json()
    assert payload["pages_used"] == [1]
    assert payload["provider"] == "mock-llm"
    assert "Explain the equation" in payload["answer"]


def test_speech_mock_returns_audio(client: TestClient) -> None:
    response = client.post("/api/speech", json={"text": "hello world"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "mock-tts"
    assert payload["mime_type"] == "audio/wav"
    assert len(payload["audio_base64"]) > 10


def test_provider_configuration_endpoint(client: TestClient) -> None:
    response = client.get("/api/providers")
    assert response.status_code == 200
    payload = response.json()
    assert payload["llm_provider"] == "mock"
    assert payload["gemma_model_id"] == ""
    assert payload["gemma_max_new_tokens"] == "1000"
    assert payload["gemma_remote_url"] == ""
    assert payload["tts_provider"] == "mock"
    assert payload["stt_provider"] == "whisper"
    assert "gemma" in payload["available_llm_providers"]


def test_provider_status_endpoint(client: TestClient) -> None:
    response = client.get("/api/providers/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["llm"]["provider"] == "mock"
    assert payload["llm"]["loaded"] is True
    assert payload["tts"]["provider"] == "mock"
