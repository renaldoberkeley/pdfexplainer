from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from app.services.llm.base import LLMExplanation, LLMProvider, PageContext
from app.services.llm.prompt_builder import build_prompt


@dataclass(slots=True)
class RemoteGemmaTransport:
    async def generate(
        self,
        *,
        url: str,
        api_key: str,
        payload: dict[str, Any],
        timeout_seconds: float,
        files: list[tuple[str, tuple[str, bytes, str]]] | None = None,
    ) -> dict[str, Any]:
        headers = {"X-API-Key": api_key} if api_key else {}
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            if files:
                response = await client.post(
                    f"{url.rstrip('/')}/generate",
                    data=payload,
                    files=files,
                    headers=headers,
                )
            else:
                response = await client.post(
                    f"{url.rstrip('/')}/generate",
                    json=payload,
                    headers=headers,
                )
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

    @staticmethod
    def _build_multipart_payload(
        pages: list[PageContext],
        *,
        model_id: str,
        prompt: str,
        max_new_tokens: int,
    ) -> tuple[dict[str, str], list[tuple[str, tuple[str, bytes, str]]]]:
        image_entries: list[dict[str, Any]] = []
        files: list[tuple[str, tuple[str, bytes, str]]] = []
        for idx, page in enumerate(pages):
            if page.image is None:
                continue
            ext = page.image.image_format.lower().replace("jpg", "jpeg")
            mime = f"image/{ext}"
            filename = f"page-{page.page_number}-{idx}.{ext}"
            image_entries.append(
                {
                    "page_number": page.page_number,
                    "image_format": ext,
                    "width": page.image.width,
                    "height": page.image.height,
                    "rendered_dpi": page.image.rendered_dpi,
                }
            )
            files.append(("images", (filename, page.image.data, mime)))

        payload = {
            "model": model_id,
            "prompt": prompt,
            "max_new_tokens": str(max_new_tokens),
            "input_mode": "text_image",
            "images_meta": json.dumps(image_entries),
        }
        return payload, files

    async def explain(
        self,
        *,
        question: str,
        pages: list[PageContext],
        input_mode: Literal["text", "text_image"] = "text",
    ) -> LLMExplanation:
        prompt = build_prompt(
            question=question,
            pages=pages,
            include_image_markers=input_mode == "text_image",
        )
        transport_payload: dict[str, Any] = {
            "model": self.model_id,
            "prompt": prompt,
            "max_new_tokens": self.max_new_tokens,
            "input_mode": input_mode,
        }
        files: list[tuple[str, tuple[str, bytes, str]]] | None = None
        image_count = 0
        request_payload_bytes = len(prompt.encode("utf-8"))
        if input_mode == "text_image":
            transport_payload, files = self._build_multipart_payload(
                pages,
                model_id=self.model_id,
                prompt=prompt,
                max_new_tokens=self.max_new_tokens,
            )
            image_count = len(files)
            request_payload_bytes += sum(len(item[1][1]) for item in files)

        try:
            start = time.monotonic()
            data = await self.transport.generate(
                url=self.base_url,
                api_key=self.api_key,
                payload=transport_payload,
                files=files,
                timeout_seconds=self.timeout_seconds,
            )
            total_latency = time.monotonic() - start
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
        generation_seconds_raw = data.get("generation_seconds")
        image_preprocessing_seconds_raw = data.get("image_preprocessing_seconds")
        input_tokens = int(input_tokens_raw) if isinstance(input_tokens_raw, (int, float)) else None
        output_tokens = int(output_tokens_raw) if isinstance(output_tokens_raw, (int, float)) else None
        estimated_cost_usd = (
            float(estimated_cost_raw)
            if isinstance(estimated_cost_raw, (int, float))
            else None
        )
        server_generation_seconds = (
            float(generation_seconds_raw)
            if isinstance(generation_seconds_raw, (int, float))
            else None
        )
        image_preprocessing_seconds = (
            float(image_preprocessing_seconds_raw)
            if isinstance(image_preprocessing_seconds_raw, (int, float))
            else None
        )
        approx_tps = None
        if output_tokens is not None and server_generation_seconds and server_generation_seconds > 0:
            approx_tps = round(output_tokens / server_generation_seconds, 4)
        return LLMExplanation(
            answer=answer,
            pages_used=[page.page_number for page in pages],
            provider="gemma-remote",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost_usd,
            image_count=image_count,
            request_payload_bytes=request_payload_bytes,
            image_preprocessing_seconds=image_preprocessing_seconds,
            server_generation_seconds=server_generation_seconds,
            approximate_tokens_per_second=approx_tps,
        )
