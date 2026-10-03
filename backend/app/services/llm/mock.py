from __future__ import annotations

from app.services.llm.base import LLMExplanation, LLMProvider


class MockLLMProvider(LLMProvider):
    def status(self) -> dict[str, str | bool]:
        return {"provider": "mock", "loaded": True}

    async def explain(
        self,
        *,
        question: str,
        pages: list[int],
        page_texts: dict[int, str],
        page_images: dict[int, bytes] | None = None,
    ) -> LLMExplanation:
        snippets: list[str] = []
        for page in pages:
            text = page_texts.get(page, "").strip()
            condensed = " ".join(text.split())
            snippets.append(
                f"Page {page}: {condensed[:350]}" + ("…" if len(condensed) > 350 else "")
            )

        answer = "\n\n".join(
            [
                "### Mock Tutor Explanation",
                f"**Question:** {question}",
                f"**Pages:** {', '.join(str(page) for page in pages)}",
                "",
                "I am using the mock LLM provider for V1. Below is a grounded summary from the selected pages:",
                "",
                *snippets,
                "",
                "When Gemma is connected, this response will be replaced with model-generated pedagogy (intuition, step-by-step math, and examples).",
            ]
        )

        return LLMExplanation(answer=answer, pages_used=pages, provider="mock-llm")
