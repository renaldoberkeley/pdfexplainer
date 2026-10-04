from __future__ import annotations

import asyncio

import pytest

from app.services.llm.base import PageContext, PageImage
from app.services.llm.remote_gemma import RemoteGemmaProvider, RemoteGemmaTransport
from app.services.provider_factory import build_llm_provider
from evaluation.runner.cases import EXPERIMENT_DEFS


class FakeTransport(RemoteGemmaTransport):
    def __init__(self, payload=None, error: Exception | None = None):
        self.payload = payload
        self.error = error
        self.last_payload = None
        self.last_files = None

    async def generate(self, *, url, api_key, payload, timeout_seconds, files=None):  # type: ignore[override]
        if self.error:
            raise self.error
        self.last_payload = payload
        self.last_files = files
        return self.payload


def test_remote_inference_success() -> None:
    provider = RemoteGemmaProvider(
        model_id="google/gemma-3-4b-it",
        base_url="https://example.com",
        api_key="secret",
        transport=FakeTransport(
            payload={
                "text": "answer",
                "model": "google/gemma-3-4b-it",
                "device": "cuda",
                "loaded": True,
                "input_tokens": 123,
                "output_tokens": 45,
                "estimated_cost_usd": 0.00123,
            }
        ),
    )
    result = asyncio.run(
        provider.explain(question="q", pages=[PageContext(page_number=1, text="text")])
    )
    assert result.answer == "answer"
    assert result.input_tokens == 123
    assert result.output_tokens == 45
    assert result.estimated_cost_usd == 0.00123
    assert provider.status()["device"] == "cuda"
    assert provider.status()["loaded"] is True


def test_remote_timeout_error() -> None:
    import httpx

    provider = RemoteGemmaProvider(
        model_id="google/gemma-3-4b-it",
        base_url="https://example.com",
        api_key="secret",
        transport=FakeTransport(error=httpx.TimeoutException("timeout")),
    )
    with pytest.raises(RuntimeError, match="timed out"):
        asyncio.run(provider.explain(question="q", pages=[PageContext(page_number=1, text="text")]))


def test_remote_http_error() -> None:
    import httpx

    provider = RemoteGemmaProvider(
        model_id="google/gemma-3-4b-it",
        base_url="https://example.com",
        api_key="secret",
        transport=FakeTransport(error=httpx.HTTPError("bad gateway")),
    )
    with pytest.raises(RuntimeError, match="connection error"):
        asyncio.run(provider.explain(question="q", pages=[PageContext(page_number=1, text="text")]))


def test_remote_malformed_response() -> None:
    provider = RemoteGemmaProvider(
        model_id="google/gemma-3-4b-it",
        base_url="https://example.com",
        api_key="secret",
        transport=FakeTransport(payload={"device": "cuda"}),
    )
    with pytest.raises(RuntimeError, match="malformed"):
        asyncio.run(provider.explain(question="q", pages=[PageContext(page_number=1, text="text")]))


def test_remote_multimodal_payload_serialization() -> None:
    transport = FakeTransport(
        payload={
            "text": "answer",
            "model": "google/gemma-3-4b-it",
            "device": "cuda",
            "loaded": True,
            "input_tokens": 20,
            "output_tokens": 10,
            "generation_seconds": 1.5,
            "image_preprocessing_seconds": 0.02,
        }
    )
    provider = RemoteGemmaProvider(
        model_id="google/gemma-3-4b-it",
        base_url="https://example.com",
        api_key="secret",
        transport=transport,
    )
    pages = [
        PageContext(
            page_number=7,
            text="content",
            image=PageImage(
                data=b"fakepng",
                image_format="png",
                width=120,
                height=90,
                rendered_dpi=200,
            ),
        )
    ]
    result = asyncio.run(provider.explain(question="q", pages=pages, input_mode="text_image"))
    assert result.image_count == 1
    assert result.server_generation_seconds == 1.5
    assert transport.last_payload is not None
    assert transport.last_payload["input_mode"] == "text_image"
    assert transport.last_files is not None
    assert len(transport.last_files) == 1


def test_remote_auth_required() -> None:
    with pytest.raises(ValueError, match="GEMMA_REMOTE_API_KEY"):
        RemoteGemmaProvider(
            model_id="google/gemma-3-4b-it",
            base_url="https://example.com",
            api_key="",
        )


def test_provider_selection_remote_no_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemma_remote")
    monkeypatch.setenv("GEMMA_MODEL_ID", "google/gemma-3-4b-it")
    monkeypatch.setenv("GEMMA_REMOTE_URL", "https://example.com")
    monkeypatch.delenv("GEMMA_REMOTE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMMA_REMOTE_API_KEY"):
        build_llm_provider()


def test_e1b_hardware_backend_definition() -> None:
    definition = EXPERIMENT_DEFS["e1b_gemma3_4b_text_runpod_cuda"]
    assert definition["hardware_backend"] == "runpod_cuda"
    assert definition["execution_environment"] == "runpod"
    assert definition["provider"] == "gemma_remote"
