from __future__ import annotations

import pytest

from app.services.llm.gemma import GemmaProvider
from app.services.llm.mock import MockLLMProvider
from app.services.llm.prompt_builder import build_prompt
from app.services.provider_factory import build_llm_provider


def test_prompt_construction_includes_sections_and_question() -> None:
    prompt = build_prompt(
        question="Explain attention",
        pages=[4],
        page_texts={4: "Scaled dot-product attention text."},
    )
    assert "INSTRUCTIONS:" in prompt
    assert "DOCUMENT CONTENT:" in prompt
    assert "USER QUESTION:" in prompt
    assert "Explain attention" in prompt


def test_prompt_construction_includes_page_grounding() -> None:
    prompt = build_prompt(
        question="Explain both pages",
        pages=[4, 5],
        page_texts={4: "Page four text", 5: "Page five text"},
    )
    assert "--- PAGE 4 ---" in prompt
    assert "Page four text" in prompt
    assert "--- PAGE 5 ---" in prompt
    assert "Page five text" in prompt


def test_provider_selection_returns_mock_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    provider = build_llm_provider()
    assert isinstance(provider, MockLLMProvider)


def test_provider_selection_returns_gemma(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemma")
    monkeypatch.setenv("GEMMA_MODEL_ID", "google/gemma-PLACEHOLDER")
    monkeypatch.setenv("GEMMA_MAX_NEW_TOKENS", "512")
    provider = build_llm_provider()
    assert isinstance(provider, GemmaProvider)
    assert provider.model_id == "google/gemma-PLACEHOLDER"
    assert provider.max_new_tokens == 512


def test_missing_gemma_model_id_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemma")
    monkeypatch.delenv("GEMMA_MODEL_ID", raising=False)
    monkeypatch.setenv("GEMMA_MAX_NEW_TOKENS", "512")
    with pytest.raises(ValueError, match="GEMMA_MODEL_ID"):
        build_llm_provider()

