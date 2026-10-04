from __future__ import annotations

import io
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.pdf_service import DEFAULT_RENDER_DPI


def create_shape_fixture_pdf_bytes() -> bytes:
    doc = fitz.open()

    page1 = doc.new_page(width=500, height=300)
    page1.insert_text((40, 40), "RED CIRCLE ---> BLUE SQUARE", fontsize=16)
    page1.draw_circle((120, 160), 35, color=(1, 0, 0), fill=(1, 0.7, 0.7))
    page1.draw_rect(fitz.Rect(320, 125, 390, 195), color=(0, 0, 1), fill=(0.7, 0.8, 1))
    page1.draw_line((165, 160), (315, 160), color=(0, 0, 0), width=2)
    page1.draw_line((315, 160), (300, 150), color=(0, 0, 0), width=2)
    page1.draw_line((315, 160), (300, 170), color=(0, 0, 0), width=2)

    page2 = doc.new_page(width=500, height=300)
    page2.insert_text((40, 40), "A=10  B=20  C=30", fontsize=16)
    page2.draw_rect(fitz.Rect(70, 90, 430, 240), color=(0, 0, 0), width=1)
    page2.insert_text((100, 135), "A", fontsize=14)
    page2.insert_text((220, 165), "B", fontsize=14)
    page2.insert_text((340, 195), "C", fontsize=14)

    return doc.tobytes()


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.pdf_service.storage_dir = tmp_path
    return TestClient(app)


def test_pdf_service_renders_single_page_image(client: TestClient) -> None:
    pdf_bytes = create_shape_fixture_pdf_bytes()
    upload = client.post(
        "/api/documents",
        files={"file": ("synthetic_multimodal_fixture.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload.status_code == 200
    document_id = upload.json()["document_id"]

    rendered = client.app.state.pdf_service.render_page_image(document_id, 1)
    assert rendered.page_number == 1
    assert rendered.image_format == "png"
    assert rendered.rendered_dpi == DEFAULT_RENDER_DPI
    assert rendered.width > 0
    assert rendered.height > 0
    assert len(rendered.image_bytes) > 100


def test_pdf_service_multimodal_page_context_order_and_association(client: TestClient) -> None:
    pdf_bytes = create_shape_fixture_pdf_bytes()
    upload = client.post(
        "/api/documents",
        files={"file": ("synthetic_multimodal_fixture.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    document_id = upload.json()["document_id"]

    contexts = client.app.state.pdf_service.get_page_contexts(
        document_id,
        [1, 2],
        include_images=True,
    )
    assert [c.page_number for c in contexts] == [1, 2]
    assert all(c.image is not None for c in contexts)
    assert contexts[0].text != contexts[1].text
    assert contexts[0].image is not None and contexts[0].image.width > 0
    assert contexts[1].image is not None and contexts[1].image.height > 0


def test_multimodal_explain_endpoint_with_mock_provider(client: TestClient) -> None:
    pdf_bytes = create_shape_fixture_pdf_bytes()
    upload = client.post(
        "/api/documents",
        files={"file": ("synthetic_multimodal_fixture.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    document_id = upload.json()["document_id"]

    response = client.post(
        "/api/explain",
        json={
            "document_id": document_id,
            "pages": [1, 2],
            "question": "What does the arrow point toward?",
            "input_mode": "text_image",
            "rendered_dpi": 200,
            "image_format": "png",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "mock-llm"
    assert payload["input_mode"] == "text_image"
    assert payload["image_count"] == 2


def test_ten_page_rendering_and_order_without_benchmark_prompts(client: TestClient) -> None:
    doc = fitz.open()
    for idx in range(10):
        p = doc.new_page()
        p.insert_text((72, 72), f"Development fixture page {idx + 1}")
    pdf_bytes = doc.tobytes()
    upload = client.post(
        "/api/documents",
        files={"file": ("ten_pages_dev_fixture.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    document_id = upload.json()["document_id"]
    pages = list(range(1, 11))
    contexts = client.app.state.pdf_service.get_page_contexts(document_id, pages, include_images=True)
    assert [c.page_number for c in contexts] == pages
    assert all(c.image is not None for c in contexts)
    assert all(len(c.image.data) > 0 for c in contexts if c.image is not None)
