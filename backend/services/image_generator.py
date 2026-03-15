import asyncio
import io
import base64
from functools import partial

from PIL import Image

from backend.config import settings

_pipe = None
_gemini_client = None


def load_flux() -> None:
    """Load the image generation backend (local model or Gemini API)."""
    if settings.image_backend == "gemini":
        _load_gemini()
    else:
        _load_local()


def _load_gemini() -> None:
    global _gemini_client
    from google import genai

    _gemini_client = genai.Client(api_key=settings.gemini_api_key)
    print(f"Gemini API ready (model: {settings.gemini_model})")


def _load_local() -> None:
    global _pipe
    import torch
    model_name = settings.flux_model
    print(f"Loading model: {model_name}")

    if "flux" in model_name.lower():
        from diffusers import FluxPipeline
        _pipe = FluxPipeline.from_pretrained(
            model_name,
            torch_dtype=torch.bfloat16,
        )
        _pipe.enable_model_cpu_offload()
    else:
        from diffusers import AutoPipelineForText2Image
        _pipe = AutoPipelineForText2Image.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            variant="fp16" if "turbo" not in model_name.lower() else None,
        )
        _pipe.to("cuda")

    print(f"Model loaded: {model_name}")


def _apply_prefix(prompt: str) -> str:
    if settings.prompt_prefix:
        return f"{settings.prompt_prefix} {prompt}"
    return prompt


# ── Local generation ─────────────────────────────────────────

def _generate_local_sync(prompt: str, step_callback=None) -> Image.Image:
    assert _pipe is not None, "Model not loaded"

    prompt = _apply_prefix(prompt)

    callback = None
    if step_callback:
        def callback(pipe, step_index, timestep, callback_kwargs):
            step_callback(step_index + 1, settings.flux_steps)
            return callback_kwargs

    kwargs = dict(
        prompt=prompt,
        num_inference_steps=settings.flux_steps,
        guidance_scale=settings.flux_guidance_scale,
        width=settings.flux_width,
        height=settings.flux_height,
        callback_on_step_end=callback,
    )

    if settings.flux_guidance_scale == 0.0 and "flux" not in settings.flux_model.lower():
        kwargs.pop("guidance_scale")

    image = _pipe(**kwargs).images[0]
    return image


# ── Gemini generation ────────────────────────────────────────

def _generate_gemini_sync(prompt: str) -> Image.Image:
    assert _gemini_client is not None, "Gemini client not loaded"

    prompt = _apply_prefix(prompt)

    response = _gemini_client.models.generate_content(
        model=settings.gemini_model,
        contents=[prompt],
    )

    for part in response.parts:
        if part.inline_data is not None:
            img_bytes = part.inline_data.data
            return Image.open(io.BytesIO(img_bytes)).convert("RGB")

    # Fallback: if no image was returned, create a blank image
    print(f"Warning: Gemini returned no image for prompt: {prompt[:80]}")
    return Image.new("RGB", (1024, 1024), (30, 30, 30))


# ── Public API ───────────────────────────────────────────────

async def generate_image(prompt: str, step_callback=None) -> Image.Image:
    loop = asyncio.get_running_loop()

    if settings.image_backend == "gemini":
        # Gemini has no step callbacks, signal start/end
        if step_callback:
            step_callback(1, 2)
        image = await loop.run_in_executor(
            None, partial(_generate_gemini_sync, prompt)
        )
        if step_callback:
            step_callback(2, 2)
        return image
    else:
        return await loop.run_in_executor(
            None, partial(_generate_local_sync, prompt, step_callback)
        )


def image_to_base64(image: Image.Image, fmt: str = "WEBP") -> str:
    buf = io.BytesIO()
    image.save(buf, format=fmt, quality=85)
    return base64.b64encode(buf.getvalue()).decode()
