from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True)
class LLMExplanation:
    answer: str
    pages_used: list[int]
    provider: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    image_count: int = 0
    request_payload_bytes: int | None = None
    image_preprocessing_seconds: float | None = None
    server_generation_seconds: float | None = None
    approximate_tokens_per_second: float | None = None


@dataclass(slots=True)
class PageImage:
    data: bytes
    image_format: str
    width: int
    height: int
    rendered_dpi: int


@dataclass(slots=True)
class PageContext:
    page_number: int
    text: str
    image: PageImage | None = None


class LLMProvider(ABC):
    @abstractmethod
    async def explain(
        self,
        *,
        question: str,
        pages: list[PageContext],
        input_mode: Literal["text", "text_image"] = "text",
    ) -> LLMExplanation:
        raise NotImplementedError
