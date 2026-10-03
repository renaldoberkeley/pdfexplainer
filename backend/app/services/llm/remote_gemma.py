from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.services.llm.base import LLMExplanation, LLMProvider
from app.services.llm.prompt_builder import build_prompt


@dataclass(slots=True)
class RemoteGemmaTransport:
    async def generate(
        self, *, url: str, api_key: str, payload: dict[str, Any], timeout_seconds: float
    ) -> dict[str, Any]:
        headers = {"X-API-Key": api_key} if api_key else {}
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(f"{url.rstrip('/')}/generate", json=payload, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(f"Remote inference failed with {response.status_code}: {response.text}")
        data = response.json()
        if not isinstance(data, dict) or "text" not in data:
            raise RuntimeError("Remote inference response is malformed: missing `text`.")
        return data


class RemoteGemmaProvider(LLMProvider):
    def __init__(
        self,
        *,
        model_id: str,
        base_url: str,
        api_key: str,
        max_new_tokens: int = 1000,
        timeout_seconds: float = 120.0,
        transport: RemoteGemmaTransport | None = None,
    ) -> None:
        self.model_id = model_id.strip()
        self.base_url = base_url.strip()
        self.api_key = api_key
        self.max_new_tokens = max_new_tokens
        self.timeout_seconds = timeout_seconds
        self.transport = transport or RemoteGemmaTransport()
        self._device = "unknown"
        self._loaded = False

        if not self.model_id:
            raise ValueError("GEMMA_MODEL_ID must be set when LLM_PROVIDER=gemma_remote.")
        if not self.base_url:
            raise ValueError("GEMMA_REMOTE_URL must be set when LLM_PROVIDER=gemma_remote.")
        if not self.api_key:
            raise ValueError("GEMMA_REMOTE_API_KEY must be set when LLM_PROVIDER=gemma_remote.")

    def status(self) -> dict[str, str | bool]:
        return {
            "provider": "gemma_remote",
            "model": self.model_id,
            "device": self._device,
            "loaded": self._loaded,
        }

    async def explain(
        self,
        *,
        question: str,
        pages: list[int],
        page_texts: dict[int, str],
        page_images: dict[int, bytes] | None = None,
    ) -> LLMExplanation:
        prompt = build_prompt(question=question, pages=pages, page_texts=page_texts)
        payload = {
            "model": self.model_id,
            "prompt": prompt,
            "max_new_tokens": self.max_new_tokens,
        }
        try:
            data = await self.transport.generate(
                url=self.base_url,
                api_key=self.api_key,
                payload=payload,
                timeout_seconds=self.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise RuntimeError("Remote inference request timed out.") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Remote inference connection error: {exc}") from exc

        if "text" not in data:
            raise RuntimeError("Remote inference response is malformed: missing `text`.")
        self._device = str(data.get("device") or "unknown")
        self._loaded = bool(data.get("loaded", True))
        answer = str(data["text"]).strip()
        if not answer:
            answer = "I could not generate an explanation from the supplied pages."
        input_tokens_raw = data.get("input_tokens")
        output_tokens_raw = data.get("output_tokens")
        estimated_cost_raw = data.get("estimated_cost_usd")
        input_tokens = int(input_tokens_raw) if isinstance(input_tokens_raw, (int, float)) else None
        output_tokens = int(output_tokens_raw) if isinstance(output_tokens_raw, (int, float)) else None
        estimated_cost_usd = (
            float(estimated_cost_raw)
            if isinstance(estimated_cost_raw, (int, float))
            else None
        )
        return LLMExplanation(
            answer=answer,
            pages_used=pages,
            provider="gemma-remote",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost_usd,
        )
