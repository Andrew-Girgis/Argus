import base64
import io
import logging
import os
from typing import Any

import httpx
from fastapi import FastAPI
from PIL import Image
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

app = FastAPI(title="Argus SAM 3.1 Service")

SAM_MODEL_ID = os.getenv("SAM_MODEL_ID", "facebook/sam3.1")
SAM_DEVICE = os.getenv("SAM_DEVICE", "auto")
SAM_CONFIDENCE_THRESHOLD = float(os.getenv("SAM_CONFIDENCE_THRESHOLD", "0.5"))
SAM_MAX_MASKS_PER_TARGET = int(os.getenv("SAM_MAX_MASKS_PER_TARGET", "3"))
_processor: Any | None = None
_device = "unknown"
_load_error: str | None = None


@app.on_event("startup")
async def load_model() -> None:
    """Load SAM 3.1 once at startup.

    Loading can fail on machines without CUDA/GPU memory or without gated HF access.
    Keep the service alive and expose the reason through /health and /segment.
    """
    global _device, _load_error, _processor
    try:
        import torch
        from sam3.model.sam3_image_processor import Sam3Processor
        from sam3.model_builder import build_sam3_image_model, download_ckpt_from_hf

        if SAM_DEVICE == "auto":
            _device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            _device = SAM_DEVICE

        logger.info("Loading %s on %s", SAM_MODEL_ID, _device)
        checkpoint_path = os.getenv("SAM_CHECKPOINT_PATH") or download_ckpt_from_hf(
            version="sam3.1"
        )
        model = build_sam3_image_model(
            device=_device,
            checkpoint_path=checkpoint_path,
            load_from_HF=False,
            eval_mode=True,
        )
        _processor = Sam3Processor(
            model,
            device=_device,
            confidence_threshold=SAM_CONFIDENCE_THRESHOLD,
        )
        _load_error = None
        logger.info("SAM 3.1 loaded from %s", checkpoint_path)
    except Exception as exc:
        _processor = None
        _load_error = f"{type(exc).__name__}: {exc}"
        logger.exception("SAM 3.1 model load failed")


class SegmentTarget(BaseModel):
    type: str
    prompt: str


class SegmentRequest(BaseModel):
    image_url: str
    image_type: str = "satellite"
    targets: list[SegmentTarget] = Field(default_factory=list)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model": SAM_MODEL_ID,
        "model_loaded": _processor is not None,
        "device": _device,
        "load_error": _load_error,
    }


@app.post("/segment")
async def segment(req: SegmentRequest) -> dict[str, Any]:
    """SAM 3.1 segmentation contract.

    The service is intentionally safe before checkpoint access is configured: it returns
    a structured unavailable response instead of failing the whole Argus pipeline.
    """
    if _processor is None:
        return {
            "status": "sam_unavailable",
            "model": SAM_MODEL_ID,
            "device": _device,
            "message": _load_error
            or "SAM 3.1 model is not loaded; configure gated HF checkpoint access and enable model loading.",
            "segments": [],
            "requested_targets": [target.model_dump() for target in req.targets],
        }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(req.image_url)
        response.raise_for_status()

    image = Image.open(io.BytesIO(response.content)).convert("RGB")
    inference_state = _processor.set_image(image)
    segments: list[dict[str, Any]] = []

    for target in req.targets:
        target_state = dict(inference_state)
        output = _processor.set_text_prompt(
            state=target_state,
            prompt=target.prompt,
        )
        segments.extend(_serialize_target_output(image, target, output))

    return {
        "status": "ok",
        "model": SAM_MODEL_ID,
        "device": _device,
        "segment_count": len(segments),
        "segments": segments,
        "requested_targets": [target.model_dump() for target in req.targets],
    }


def _serialize_target_output(
    image: Image.Image,
    target: SegmentTarget,
    output: dict[str, Any],
) -> list[dict[str, Any]]:
    masks = output.get("masks")
    boxes = output.get("boxes")
    scores = output.get("scores")
    if masks is None or boxes is None or scores is None:
        return []

    masks_cpu = masks.detach().cpu()
    boxes_cpu = boxes.detach().cpu()
    scores_cpu = scores.detach().cpu()
    count = min(len(scores_cpu), SAM_MAX_MASKS_PER_TARGET)

    serialized = []
    for index in range(count):
        mask = masks_cpu[index]
        if mask.ndim == 3:
            mask = mask.squeeze(0)
        mask_bool = mask.bool().numpy()
        box = [round(float(value), 2) for value in boxes_cpu[index].tolist()]
        score = float(scores_cpu[index].item())
        serialized.append(
            {
                "type": target.type,
                "prompt": target.prompt,
                "index": index,
                "score": score,
                "bbox": box,
                "mask_area_px": int(mask_bool.sum()),
                "mask_png": _mask_data_url(mask_bool),
                "overlay_png": _overlay_data_url(image, mask_bool),
            }
        )
    return serialized


def _mask_data_url(mask_bool: Any) -> str:
    mask_image = Image.fromarray((mask_bool.astype("uint8") * 255), mode="L")
    buffer = io.BytesIO()
    mask_image.save(buffer, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode('ascii')}"


def _overlay_data_url(image: Image.Image, mask_bool: Any) -> str:
    overlay = image.convert("RGBA")
    mask = Image.fromarray((mask_bool.astype("uint8") * 120), mode="L")
    color = Image.new("RGBA", image.size, (255, 0, 80, 0))
    color.putalpha(mask)
    composed = Image.alpha_composite(overlay, color)
    buffer = io.BytesIO()
    composed.save(buffer, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode('ascii')}"
