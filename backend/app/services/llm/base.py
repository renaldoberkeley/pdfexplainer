from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class LLMExplanation:
    answer: str
    pages_used: list[int]
    provider: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None


class LLMProvider(ABC):
    @abstractmethod
    async def explain(
        self,
        *,
        question: str,
        pages: list[int],
        page_texts: dict[int, str],
        page_images: dict[int, bytes] | None = None,
    ) -> LLMExplanation:
        raise NotImplementedError
