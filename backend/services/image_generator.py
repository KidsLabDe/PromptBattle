import asyncio
import io
import base64
from functools import partial

import torch
from PIL import Image

from backend.config import settings

_pipe = None


def load_flux() -> None:
    global _pipe
    model_name = settings.flux_model
    print(f"Loading model: {model_name}")

    # Detect pipeline type based on model name
    if "flux" in model_name.lower():
        from diffusers import FluxPipeline
        _pipe = FluxPipeline.from_pretrained(
            model_name,
            torch_dtype=torch.bfloat16,
        )
        _pipe.enable_model_cpu_offload()
    else:
        # Stable Diffusion / SDXL / SDXL-Turbo
        from diffusers import AutoPipelineForText2Image
        _pipe = AutoPipelineForText2Image.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            variant="fp16" if "turbo" not in model_name.lower() else None,
        )
        _pipe.to("cuda")

    print(f"Model loaded: {model_name}")


def _generate_sync(prompt: str, step_callback=None) -> Image.Image:
    assert _pipe is not None, "Model not loaded"

    # Prompt-Prefix anwenden (z.B. für deutsche Prompts)
    if settings.prompt_prefix:
        prompt = f"{settings.prompt_prefix} {prompt}"

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

    # Some turbo models don't support guidance_scale=0
    if settings.flux_guidance_scale == 0.0 and "flux" not in settings.flux_model.lower():
        kwargs.pop("guidance_scale")

    image = _pipe(**kwargs).images[0]
    return image


async def generate_image(prompt: str, step_callback=None) -> Image.Image:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, partial(_generate_sync, prompt, step_callback)
    )


def image_to_base64(image: Image.Image, fmt: str = "WEBP") -> str:
    buf = io.BytesIO()
    image.save(buf, format=fmt, quality=85)
    return base64.b64encode(buf.getvalue()).decode()
