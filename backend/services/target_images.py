import random
from pathlib import Path

from backend.config import settings

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def scan_target_images() -> list[str]:
    d = settings.target_images_dir
    if not d.exists():
        d.mkdir(parents=True, exist_ok=True)
        return []
    return [
        f.name
        for f in d.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]


def pick_random_target(exclude: list[str] | None = None) -> str:
    images = scan_target_images()
    if not images:
        raise RuntimeError("No target images found in " + str(settings.target_images_dir))
    if exclude:
        candidates = [i for i in images if i not in exclude]
        if not candidates:
            candidates = images
    else:
        candidates = images
    return random.choice(candidates)


def target_image_path(filename: str) -> Path:
    return settings.target_images_dir / filename
