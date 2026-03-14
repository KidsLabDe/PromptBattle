import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from backend.config import settings

_model: CLIPModel | None = None
_processor: CLIPProcessor | None = None


def load_clip() -> None:
    global _model, _processor
    print(f"Loading CLIP model: {settings.clip_model}")
    _processor = CLIPProcessor.from_pretrained(settings.clip_model)
    _model = CLIPModel.from_pretrained(settings.clip_model).to("cuda").eval()
    print("CLIP model loaded.")


def compute_similarity(image_a: Image.Image, image_b: Image.Image) -> float:
    assert _model is not None and _processor is not None, "CLIP not loaded"

    inputs = _processor(images=[image_a, image_b], return_tensors="pt", padding=True)
    inputs = {k: v.to("cuda") for k, v in inputs.items()}

    with torch.no_grad():
        outputs = _model.get_image_features(**inputs)
        # Handle both raw tensor and BaseModelOutputWithPooling
        features = outputs if isinstance(outputs, torch.Tensor) else outputs.pooler_output

    features = features / features.norm(dim=-1, keepdim=True)
    raw_sim = (features[0] @ features[1]).item()

    # remap from [clip_raw_min, clip_raw_max] to [0, 100]
    score = (raw_sim - settings.clip_raw_min) / (settings.clip_raw_max - settings.clip_raw_min)
    return max(0.0, min(100.0, score * 100.0))
