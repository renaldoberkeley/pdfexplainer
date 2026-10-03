from __future__ import annotations

from typing import Any

from app.services.llm.base import LLMExplanation, LLMProvider
from app.services.llm.prompt_builder import build_prompt


class LocalGemmaProvider(LLMProvider):
    def __init__(self, model_id: str, max_new_tokens: int = 1000) -> None:
        normalized_model_id = model_id.strip()
        if not normalized_model_id:
            raise ValueError("GEMMA_MODEL_ID must be set when LLM_PROVIDER=gemma.")

        self.model_id = normalized_model_id
        self.max_new_tokens = max_new_tokens
        self._model: Any | None = None
        self._tokenizer: Any | None = None
        self._device = self._detect_device_preference()
        self._loaded = False
        self._torch: Any | None = None

    def _detect_device_preference(self) -> str:
        try:
            import torch
        except ImportError:
            return "cpu"
        return self._select_device(torch)

    def _select_device(self, torch_module: Any) -> str:
        if hasattr(torch_module.backends, "mps") and torch_module.backends.mps.is_available():
            return "mps"
        if torch_module.cuda.is_available():
            return "cuda"
        return "cpu"

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        try:
            import accelerate  # noqa: F401
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - dependency issue in runtime env
            raise RuntimeError(
                "Gemma dependencies are missing. Install torch, transformers, and accelerate."
            ) from exc

        self._torch = torch
        self._device = self._select_device(torch)
        tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            low_cpu_mem_usage=True,
        )
        model.to(self._device)
        model.eval()
        self._tokenizer = tokenizer
        self._model = model
        self._loaded = True

    def status(self) -> dict[str, str | bool]:
        return {
            "provider": "gemma",
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
        self._ensure_loaded()
        assert self._tokenizer is not None
        assert self._model is not None
        assert self._torch is not None

        prompt = build_prompt(question=question, pages=pages, page_texts=page_texts)
        tokenized = self._tokenizer(prompt, return_tensors="pt")
        tokenized = tokenized.to(self._device)

        with self._torch.inference_mode():
            output_ids = self._model.generate(
                **tokenized,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
            )

        prompt_token_count = tokenized["input_ids"].shape[1]
        generated_ids = output_ids[0][prompt_token_count:]
        answer = self._tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        if not answer:
            answer = "I could not generate an explanation from the supplied pages."

        return LLMExplanation(
            answer=answer,
            pages_used=pages,
            provider="gemma",
            input_tokens=int(prompt_token_count),
            output_tokens=int(generated_ids.shape[0]),
        )


GemmaProvider = LocalGemmaProvider
