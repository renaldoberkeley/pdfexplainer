from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

os.environ.setdefault("GEMMA_MODEL_ID", "google/gemma-3-4b-it")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app.main as main_module


def _png_bytes(color: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", (16, 16), color)
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def _auth_header() -> dict[str, str]:
    return {"X-API-Key": "test-key"}


def _client(monkeypatch):
    monkeypatch.setenv("RUNPOD_API_KEY", "test-key")

    def fake_generate(*, prompt, max_new_tokens, input_mode="text", images=None, image_preprocessing_seconds=0.0):
        return main_module.GenerateResponse(
            text=f"mode={input_mode}",
            model=main_module.runtime.status().model,
            device="cuda",
            input_tokens=10,
            output_tokens=5,
            generation_seconds=1.0,
            loaded=True,
            image_count=len(images or []),
            image_preprocessing_seconds=image_preprocessing_seconds if images else None,
        )

    monkeypatch.setattr(main_module.runtime, "generate", fake_generate)
    monkeypatch.setattr(main_module.runtime, "status", lambda: main_module.ModelStatus(
        model=main_module.runtime._model_id,  # noqa: SLF001
        device="cuda",
        loaded=True,
        cuda_available=True,
        gpu_name="NVIDIA GeForce RTX 4090",
    ))
    return TestClient(main_module.app)


def test_text_only_json_contract(monkeypatch) -> None:
    client = _client(monkeypatch)
    response = client.post(
        "/generate",
        headers=_auth_header(),
        json={
            "model": main_module.runtime._model_id,  # noqa: SLF001
            "prompt": "hello",
            "max_new_tokens": 64,
            "input_mode": "text",
        },
    )
    assert response.status_code == 200
    assert response.json()["text"] == "mode=text"


def test_multimodal_missing_image_rejected(monkeypatch) -> None:
    client = _client(monkeypatch)
    response = client.post(
        "/generate",
        headers=_auth_header(),
        json={
            "model": main_module.runtime._model_id,  # noqa: SLF001
            "prompt": "hello",
            "max_new_tokens": 64,
            "input_mode": "text_image",
        },
    )
    assert response.status_code == 400


def test_multimodal_malformed_image_rejected(monkeypatch) -> None:
    client = _client(monkeypatch)
    response = client.post(
        "/generate",
        headers=_auth_header(),
        data={
            "model": main_module.runtime._model_id,  # noqa: SLF001
            "prompt": "hello",
            "max_new_tokens": "64",
            "input_mode": "text_image",
            "images_meta": json.dumps(
                [{"page_number": 1, "image_format": "png", "width": 16, "height": 16, "rendered_dpi": 200}]
            ),
        },
        files={"images": ("bad.png", b"not-an-image", "image/png")},
    )
    assert response.status_code == 400


def test_multimodal_multiple_images_and_order(monkeypatch) -> None:
    client = _client(monkeypatch)
    files = [
        ("images", ("p1.png", _png_bytes((255, 0, 0)), "image/png")),
        ("images", ("p2.png", _png_bytes((0, 0, 255)), "image/png")),
    ]
    response = client.post(
        "/generate",
        headers=_auth_header(),
        data={
            "model": main_module.runtime._model_id,  # noqa: SLF001
            "prompt": "hello",
            "max_new_tokens": "64",
            "input_mode": "text_image",
            "images_meta": json.dumps(
                [
                    {"page_number": 1, "image_format": "png", "width": 16, "height": 16, "rendered_dpi": 200},
                    {"page_number": 2, "image_format": "png", "width": 16, "height": 16, "rendered_dpi": 200},
                ]
            ),
        },
        files=files,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["text"] == "mode=text_image"
    assert payload["image_count"] == 2


def test_multimodal_ten_images_supported(monkeypatch) -> None:
    client = _client(monkeypatch)
    files = []
    meta = []
    for idx in range(10):
        files.append(("images", (f"p{idx+1}.png", _png_bytes((idx * 20 % 255, 0, 100)), "image/png")))
        meta.append(
            {"page_number": idx + 1, "image_format": "png", "width": 16, "height": 16, "rendered_dpi": 200}
        )
    response = client.post(
        "/generate",
        headers=_auth_header(),
        data={
            "model": main_module.runtime._model_id,  # noqa: SLF001
            "prompt": "hello",
            "max_new_tokens": "64",
            "input_mode": "text_image",
            "images_meta": json.dumps(meta),
        },
        files=files,
    )
    assert response.status_code == 200
    assert response.json()["image_count"] == 10


def test_authentication_required(monkeypatch) -> None:
    client = _client(monkeypatch)
    response = client.post(
        "/generate",
        json={
            "model": main_module.runtime._model_id,  # noqa: SLF001
            "prompt": "hello",
            "max_new_tokens": 64,
            "input_mode": "text",
        },
    )
    assert response.status_code == 401
