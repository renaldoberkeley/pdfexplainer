from __future__ import annotations

import pytest

from app.services.llm.gemma import GemmaProvider
from app.services.llm.base import PageContext, PageImage
from app.services.llm.mock import MockLLMProvider
from app.services.llm.prompt_builder import build_prompt
from app.services.provider_factory import build_llm_provider


def test_prompt_construction_includes_sections_and_question() -> None:
    prompt = build_prompt(
        question="Explain attention",
        pages=[PageContext(page_number=4, text="Scaled dot-product attention text.")],
    )
    assert "INSTRUCTIONS:" in prompt
    assert "DOCUMENT CONTENT:" in prompt
    assert "USER QUESTION:" in prompt
    assert "Explain attention" in prompt


def test_prompt_construction_includes_page_grounding() -> None:
    prompt = build_prompt(
        question="Explain both pages",
        pages=[
            PageContext(page_number=4, text="Page four text"),
            PageContext(page_number=5, text="Page five text"),
        ],
    )
    assert "--- PAGE 4 ---" in prompt
    assert "Page four text" in prompt
    assert "--- PAGE 5 ---" in prompt
    assert "Page five text" in prompt


def test_prompt_construction_does_not_leak_design_metadata() -> None:
    prompt = build_prompt(
        question="Explain visual relation",
        pages=[
            PageContext(
                page_number=2,
                text="A simple synthetic visual setup.",
                image=PageImage(
                    data=b"img",
                    image_format="png",
                    width=100,
                    height=100,
                    rendered_dpi=200,
                ),
            )
        ],
        include_image_markers=True,
    )
    assert "expected_text_only_limitation" not in prompt
    assert "experiment hypothesis" not in prompt.lower()
    assert "[Rendered page image for this page is attached.]" in prompt


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
