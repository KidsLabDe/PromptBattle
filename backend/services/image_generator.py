import asyncio
import io
import base64
from functools import partial

import torch
from diffusers import FluxPipeline
from PIL import Image

from backend.config import settings

_pipe: FluxPipeline | None = None


def load_flux() -> None:
    global _pipe
    print(f"Loading FLUX model: {settings.flux_model}")
    _pipe = FluxPipeline.from_pretrained(
        settings.flux_model,
        torch_dtype=torch.bfloat16,
    )
    _pipe.enable_model_cpu_offload()
    print("FLUX model loaded.")


def _generate_sync(prompt: str, step_callback=None) -> Image.Image:
    assert _pipe is not None, "FLUX not loaded"

    callback = None
    if step_callback:
        def callback(pipe, step_index, timestep, callback_kwargs):
            step_callback(step_index + 1, settings.flux_steps)
            return callback_kwargs

    image = _pipe(
        prompt=prompt,
        num_inference_steps=settings.flux_steps,
        guidance_scale=settings.flux_guidance_scale,
        width=settings.flux_width,
        height=settings.flux_height,
        callback_on_step_end=callback,
    ).images[0]
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
