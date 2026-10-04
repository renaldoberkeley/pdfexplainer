from __future__ import annotations

from typing import Literal

from app.services.llm.base import LLMExplanation, LLMProvider, PageContext


class MockLLMProvider(LLMProvider):
    def status(self) -> dict[str, str | bool]:
        return {"provider": "mock", "loaded": True}

    async def explain(
        self,
        *,
        question: str,
        pages: list[PageContext],
        input_mode: Literal["text", "text_image"] = "text",
    ) -> LLMExplanation:
        snippets: list[str] = []
        image_count = 0
        for page in pages:
            text = page.text.strip()
            condensed = " ".join(text.split())
            if page.image is not None:
                image_count += 1
            snippets.append(
                f"Page {page.page_number}: {condensed[:350]}"
                + ("…" if len(condensed) > 350 else "")
            )

        answer = "\n\n".join(
            [
                "### Mock Tutor Explanation",
                f"**Question:** {question}",
                f"**Pages:** {', '.join(str(page.page_number) for page in pages)}",
                f"**Input mode:** {input_mode}",
                f"**Attached rendered page images:** {image_count}",
                "",
                "I am using the mock LLM provider for V1. Below is a grounded summary from the selected pages:",
                "",
                *snippets,
                "",
                "When Gemma is connected, this response will be replaced with model-generated pedagogy (intuition, step-by-step math, and examples).",
            ]
        )

        return LLMExplanation(
            answer=answer,
            pages_used=[page.page_number for page in pages],
            provider="mock-llm",
            image_count=image_count,
        )
