from __future__ import annotations

from io import BytesIO
from typing import Any, Literal

from PIL import Image

from app.services.llm.base import LLMExplanation, LLMProvider, PageContext
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
        self._processor: Any | None = None
        self._device = self._detect_device_preference()
        self._loaded = False
        self._torch: Any | None = None
        self._processor_supports_images = False

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
            from transformers import AutoModelForCausalLM, AutoModelForImageTextToText, AutoProcessor, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - dependency issue in runtime env
            raise RuntimeError(
                "Gemma dependencies are missing. Install torch, transformers, accelerate, and pillow."
            ) from exc

        self._torch = torch
        self._device = self._select_device(torch)
        tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        model = None
        try:
            model = AutoModelForImageTextToText.from_pretrained(
                self.model_id,
                low_cpu_mem_usage=True,
            )
        except Exception:  # pragma: no cover - model class fallback path
            model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                low_cpu_mem_usage=True,
            )

        model.to(self._device)
        model.eval()
        self._tokenizer = tokenizer
        self._model = model
        try:
            self._processor = AutoProcessor.from_pretrained(self.model_id)
            self._processor_supports_images = True
        except Exception:
            self._processor = None
            self._processor_supports_images = False
        self._loaded = True

    def status(self) -> dict[str, str | bool]:
        return {
            "provider": "gemma",
            "model": self.model_id,
            "device": self._device,
            "loaded": self._loaded,
        }

    def _render_pil_images(self, pages: list[PageContext]) -> list[Image.Image]:
        images: list[Image.Image] = []
        for page in pages:
            if page.image is None:
                continue
            try:
                image = Image.open(BytesIO(page.image.data))
                images.append(image.convert("RGB"))
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to parse rendered image for page {page.page_number}."
                ) from exc
        return images

    def _generate_text_only(self, prompt: str) -> tuple[str, int, int]:
        assert self._tokenizer is not None
        assert self._model is not None
        assert self._torch is not None
        tokenized = self._tokenizer(prompt, return_tensors="pt")
        tokenized = tokenized.to(self._device)

        with self._torch.inference_mode():
            output_ids = self._model.generate(
                **tokenized,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
            )

        prompt_token_count = int(tokenized["input_ids"].shape[1])
        generated_ids = output_ids[0][prompt_token_count:]
        answer = self._tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        return answer, prompt_token_count, int(generated_ids.shape[0])

    def _generate_multimodal(self, prompt: str, pil_images: list[Image.Image]) -> tuple[str, int, int]:
        if not pil_images:
            return self._generate_text_only(prompt)
        if not self._processor_supports_images or self._processor is None:
            raise RuntimeError("Configured Gemma runtime does not support multimodal processor inputs.")
        assert self._model is not None
        assert self._torch is not None

        content: list[dict[str, str]] = [{"type": "text", "text": prompt}]
        for _ in pil_images:
            content.append({"type": "image"})
        messages = [{"role": "user", "content": content}]

        chat_prompt = self._processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=False,
        )
        model_inputs = self._processor(
            text=chat_prompt,
            images=pil_images,
            return_tensors="pt",
        ).to(self._device)

        with self._torch.inference_mode():
            output_ids = self._model.generate(
                **model_inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
            )

        prompt_token_count = int(model_inputs["input_ids"].shape[1])
        generated_ids = output_ids[0][prompt_token_count:]
        answer = self._processor.decode(generated_ids, skip_special_tokens=True).strip()
        return answer, prompt_token_count, int(generated_ids.shape[0])

    async def explain(
        self,
        *,
        question: str,
        pages: list[PageContext],
        input_mode: Literal["text", "text_image"] = "text",
    ) -> LLMExplanation:
        self._ensure_loaded()
        prompt = build_prompt(
            question=question,
            pages=pages,
            include_image_markers=input_mode == "text_image",
        )
        pil_images = self._render_pil_images(pages) if input_mode == "text_image" else []

        if input_mode == "text_image":
            answer, input_tokens, output_tokens = self._generate_multimodal(prompt, pil_images)
        else:
            answer, input_tokens, output_tokens = self._generate_text_only(prompt)

        if not answer:
            answer = "I could not generate an explanation from the supplied pages."

        return LLMExplanation(
            answer=answer,
            pages_used=[page.page_number for page in pages],
            provider="gemma",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            image_count=len(pil_images),
        )


GemmaProvider = LocalGemmaProvider
