import asyncio
import io
import json
import logging
import re
from functools import partial
from PIL import Image

from backend.config import settings

logger = logging.getLogger(__name__)

# ── CLIP (local) ─────────────────────────────────────────────
_model = None
_processor = None
_device: str = "cpu"


def _get_device() -> str:
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_clip() -> None:
    if settings.similarity_backend == "gemini":
        print("Similarity backend: Gemini (no CLIP loading needed)")
        return
    global _model, _processor, _device
    import torch
    from transformers import CLIPModel, CLIPProcessor
    _device = _get_device()
    print(f"Loading CLIP model: {settings.clip_model} on {_device}")
    _processor = CLIPProcessor.from_pretrained(settings.clip_model)
    _model = CLIPModel.from_pretrained(settings.clip_model).to(_device).eval()
    print("CLIP model loaded.")


def _compute_clip(image_a: Image.Image, image_b: Image.Image) -> tuple[float, str]:
    import torch
    assert _model is not None and _processor is not None, "CLIP not loaded"

    inputs = _processor(images=[image_a, image_b], return_tensors="pt", padding=True)
    inputs = {k: v.to(_device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = _model.get_image_features(**inputs)
        features = outputs if isinstance(outputs, torch.Tensor) else outputs.pooler_output

    features = features / features.norm(dim=-1, keepdim=True)
    raw_sim = (features[0] @ features[1]).item()

    score = (raw_sim - settings.clip_raw_min) / (settings.clip_raw_max - settings.clip_raw_min)
    return max(0.0, min(100.0, score * 100.0)), ""


# ── Gemini (API) ─────────────────────────────────────────────
_gemini_client = None


def _load_gemini_similarity() -> None:
    global _gemini_client
    from google import genai
    _gemini_client = genai.Client(api_key=settings.gemini_api_key)
    print(f"Gemini similarity ready (model: {settings.similarity_gemini_model})")


def _image_to_bytes(img: Image.Image) -> bytes:
    # Resize for similarity: 512px max is enough for comparison, saves tokens
    if max(img.size) > 512:
        img = img.copy()
        img.thumbnail((512, 512), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def _compute_gemini_sync(image_a: Image.Image, image_b: Image.Image) -> tuple[float, str]:
    if _gemini_client is None:
        _load_gemini_similarity()

    from google.genai import types

    prompt = """Du bist ein Bildvergleichs-Experte. Vergleiche die beiden Bilder und bewerte ihre visuelle Ähnlichkeit.

Bewerte auf einer Skala von 0 bis 100:
- 0 = komplett unterschiedlich (andere Objekte, Szene, Farben)
- 25 = leichte Ähnlichkeit (gleiche Kategorie, aber sehr verschieden)
- 50 = moderate Ähnlichkeit (ähnliche Szene/Objekte, aber deutliche Unterschiede)
- 75 = hohe Ähnlichkeit (gleiche Szene, ähnliche Komposition, kleine Unterschiede)
- 100 = identisch

Antworte NUR mit einem JSON-Objekt in diesem Format:
{"score": <zahl>, "reason": "<kurze begründung auf deutsch>"}"""

    img_a_bytes = _image_to_bytes(image_a)
    img_b_bytes = _image_to_bytes(image_b)

    response = _gemini_client.models.generate_content(
        model=settings.similarity_gemini_model,
        contents=[
            prompt,
            types.Part.from_bytes(data=img_a_bytes, mime_type="image/jpeg"),
            types.Part.from_bytes(data=img_b_bytes, mime_type="image/jpeg"),
        ],
    )

    try:
        usage = getattr(response, "usage_metadata", None)
        if usage:
            logger.info(
                "Gemini usage [similarity] model=%s prompt_tokens=%s candidates_tokens=%s total_tokens=%s",
                settings.similarity_gemini_model,
                getattr(usage, "prompt_token_count", "?"),
                getattr(usage, "candidates_token_count", "?"),
                getattr(usage, "total_token_count", "?"),
            )
    except Exception:
        pass

    text = response.text.strip()
    # Extract JSON from response (may be wrapped in markdown code block)
    json_match = re.search(r'\{[^}]+\}', text)
    if json_match:
        data = json.loads(json_match.group())
        score = float(data.get("score", 0))
        reason = data.get("reason", "")
        print(f"Gemini similarity: {score}% - {reason}")
        return max(0.0, min(100.0, score)), reason

    print(f"Warning: Could not parse Gemini similarity response: {text}")
    return 50.0, ""


# ── Public API ───────────────────────────────────────────────

async def compute_similarity(image_a: Image.Image, image_b: Image.Image) -> tuple[float, str]:
    """Returns (score, reason) tuple."""
    if settings.similarity_backend == "gemini":
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, partial(_compute_gemini_sync, image_a, image_b)
        )
    else:
        return _compute_clip(image_a, image_b)
