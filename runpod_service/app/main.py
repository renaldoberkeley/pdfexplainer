from __future__ import annotations

import json
import os
import time
from io import BytesIO
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, ValidationError


class GenerateRequest(BaseModel):
    model: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    max_new_tokens: int = Field(default=750, ge=1, le=4096)
    input_mode: str = Field(default="text")


class PageImageMeta(BaseModel):
    page_number: int = Field(ge=1)
    image_format: str = Field(min_length=1)
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    rendered_dpi: int = Field(ge=72, le=400)


class GenerateResponse(BaseModel):
    text: str
    model: str
    device: str
    input_tokens: int
    output_tokens: int
    generation_seconds: float
    loaded: bool
    image_count: int = 0
    image_preprocessing_seconds: float | None = None


class ModelStatus(BaseModel):
    model: str
    device: str
    loaded: bool
    cuda_available: bool
    gpu_name: str | None = None


class GemmaRuntime:
    def __init__(self) -> None:
        self._model: Any | None = None
        self._tokenizer: Any | None = None
        self._processor: Any | None = None
        self._torch: Any | None = None
        self._model_id = os.getenv("GEMMA_MODEL_ID", "").strip()
        if not self._model_id:
            raise ValueError("GEMMA_MODEL_ID is required for runpod inference service.")
        self._device = "cpu"
        self._loaded = False

    def _select_device(self, torch_module: Any) -> str:
        if torch_module.cuda.is_available():
            return "cuda"
        if hasattr(torch_module.backends, "mps") and torch_module.backends.mps.is_available():
            return "mps"
        return "cpu"

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoModelForImageTextToText, AutoProcessor, AutoTokenizer

        self._torch = torch
        self._device = self._select_device(torch)
        self._tokenizer = AutoTokenizer.from_pretrained(self._model_id)
        try:
            self._model = AutoModelForImageTextToText.from_pretrained(
                self._model_id,
                low_cpu_mem_usage=True,
            )
        except Exception:  # pragma: no cover - fallback for text-only checkpoints
            self._model = AutoModelForCausalLM.from_pretrained(
                self._model_id,
                low_cpu_mem_usage=True,
            )
        self._model.to(self._device)
        self._model.eval()
        try:
            self._processor = AutoProcessor.from_pretrained(self._model_id)
        except Exception:
            self._processor = None
        self._loaded = True

    def _generate_text_only(self, prompt: str, max_new_tokens: int) -> GenerateResponse:
        assert self._tokenizer is not None
        assert self._model is not None
        assert self._torch is not None
        start = time.monotonic()
        tokens = self._tokenizer(prompt, return_tensors="pt").to(self._device)
        with self._torch.inference_mode():
            output_ids = self._model.generate(
                **tokens,
                max_new_tokens=max_new_tokens,
                do_sample=False,
            )
        prompt_token_count = int(tokens["input_ids"].shape[1])
        generated = output_ids[0][prompt_token_count:]
        text = self._tokenizer.decode(generated, skip_special_tokens=True).strip()
        generation_seconds = round(time.monotonic() - start, 2)
        return GenerateResponse(
            text=text,
            model=self._model_id,
            device=self._device,
            input_tokens=prompt_token_count,
            output_tokens=int(generated.shape[0]),
            generation_seconds=generation_seconds,
            loaded=self._loaded,
        )

    def _generate_multimodal(
        self,
        *,
        prompt: str,
        max_new_tokens: int,
        images: list[Image.Image],
        preprocessing_seconds: float,
    ) -> GenerateResponse:
        if not images:
            return self._generate_text_only(prompt, max_new_tokens)
        if self._processor is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Configured model runtime does not support multimodal processing.",
            )

        assert self._torch is not None
        assert self._model is not None

        content: list[dict[str, str]] = [{"type": "text", "text": prompt}]
        for _ in images:
            content.append({"type": "image"})
        messages = [{"role": "user", "content": content}]
        chat_prompt = self._processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=False,
        )

        start = time.monotonic()
        model_inputs = self._processor(text=chat_prompt, images=images, return_tensors="pt").to(self._device)
        with self._torch.inference_mode():
            output_ids = self._model.generate(
                **model_inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
            )
        prompt_token_count = int(model_inputs["input_ids"].shape[1])
        generated = output_ids[0][prompt_token_count:]
        tokenizer = getattr(self._processor, "tokenizer", None) or self._tokenizer
        text = tokenizer.decode(generated, skip_special_tokens=True).strip()
        generation_seconds = round(time.monotonic() - start, 2)
        return GenerateResponse(
            text=text,
            model=self._model_id,
            device=self._device,
            input_tokens=prompt_token_count,
            output_tokens=int(generated.shape[0]),
            generation_seconds=generation_seconds,
            loaded=self._loaded,
            image_count=len(images),
            image_preprocessing_seconds=round(preprocessing_seconds, 4),
        )

    def generate(
        self,
        *,
        prompt: str,
        max_new_tokens: int,
        input_mode: str = "text",
        images: list[Image.Image] | None = None,
        image_preprocessing_seconds: float = 0.0,
    ) -> GenerateResponse:
        self.ensure_loaded()
        if input_mode == "text_image":
            return self._generate_multimodal(
                prompt=prompt,
                max_new_tokens=max_new_tokens,
                images=images or [],
                preprocessing_seconds=image_preprocessing_seconds,
            )
        return self._generate_text_only(prompt, max_new_tokens)

    def status(self) -> ModelStatus:
        cuda_available = False
        gpu_name = None
        if self._torch is not None:
            cuda_available = bool(self._torch.cuda.is_available())
            if cuda_available:
                gpu_name = str(self._torch.cuda.get_device_name(0))
        return ModelStatus(
            model=self._model_id,
            device=self._device,
            loaded=self._loaded,
            cuda_available=cuda_available,
            gpu_name=gpu_name,
        )


app = FastAPI(title="RunPod Gemma Inference Service", version="0.2.0")
runtime = GemmaRuntime()


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("RUNPOD_API_KEY", "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RUNPOD_API_KEY is not configured.",
        )
    if x_api_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def _load_images_from_form(raw_files: list[Any], images_meta: list[PageImageMeta]) -> tuple[list[Image.Image], float]:
    if len(raw_files) != len(images_meta):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="images and images_meta length mismatch.",
        )
    preprocessing_start = time.monotonic()
    images: list[Image.Image] = []
    for file in raw_files:
        try:
            image = Image.open(BytesIO(file.file.read())).convert("RGB")
        except UnidentifiedImageError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Malformed image payload: {file.filename}",
            ) from exc
        images.append(image)
    return images, time.monotonic() - preprocessing_start


async def _parse_request(request: Request) -> tuple[GenerateRequest, list[PageImageMeta], list[Image.Image], float]:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        images_meta_raw = form.get("images_meta")
        try:
            images_meta_json = json.loads(images_meta_raw) if images_meta_raw else []
            images_meta = [PageImageMeta.model_validate(item) for item in images_meta_json]
        except (ValidationError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="images_meta is malformed.",
            ) from exc
        payload = GenerateRequest(
            model=str(form.get("model", "")),
            prompt=str(form.get("prompt", "")),
            max_new_tokens=int(form.get("max_new_tokens", 750)),
            input_mode=str(form.get("input_mode", "text")),
        )
        raw_files = form.getlist("images")
        if payload.input_mode == "text_image" and not raw_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="text_image input_mode requires at least one image.",
            )
        images, preprocessing_seconds = _load_images_from_form(raw_files, images_meta)
        return payload, images_meta, images, preprocessing_seconds

    payload_json = await request.json()
    payload = GenerateRequest.model_validate(payload_json)
    return payload, [], [], 0.0


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/model/status", response_model=ModelStatus, dependencies=[Depends(verify_api_key)])
async def model_status() -> ModelStatus:
    return runtime.status()


@app.post("/generate", response_model=GenerateResponse, dependencies=[Depends(verify_api_key)])
async def generate(request: Request) -> GenerateResponse:
    payload, images_meta, images, preprocessing_seconds = await _parse_request(request)
    if payload.model.strip() != runtime.status().model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configured model is {runtime.status().model}; got {payload.model}.",
        )
    if payload.input_mode not in {"text", "text_image"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="input_mode must be text or text_image.",
        )
    if payload.input_mode == "text_image" and not images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="text_image input_mode requires at least one image.",
        )
    if payload.input_mode == "text_image" and len(images_meta) != len(images):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image metadata does not match provided images.",
        )
    return runtime.generate(
        prompt=payload.prompt,
        max_new_tokens=payload.max_new_tokens,
        input_mode=payload.input_mode,
        images=images,
        image_preprocessing_seconds=preprocessing_seconds,
    )
