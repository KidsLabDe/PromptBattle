from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    target_images_dir: Path = Path(__file__).resolve().parent.parent / "target_images"
    generated_images_dir: Path = Path(__file__).resolve().parent / "generated"
    history_dir: Path = Path(__file__).resolve().parent.parent / "generated_history"
    static_dir: Path = Path(__file__).resolve().parent.parent / "frontend" / "build"

    # Image generation backend: "local" (diffusers) or "gemini" (Google API)
    image_backend: str = "local"

    # Local model settings (used when image_backend=local)
    flux_model: str = "black-forest-labs/FLUX.1-schnell"
    flux_steps: int = 4
    flux_guidance_scale: float = 0.0
    flux_width: int = 1024
    flux_height: int = 1024

    # Gemini API settings (used when image_backend=gemini)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-image-preview"

    # Prompt-Prefix: wird vor jeden Spieler-Prompt gesetzt.
    prompt_prefix: str = ""

    clip_model: str = "openai/clip-vit-large-patch14"
    clip_raw_min: float = 0.4
    clip_raw_max: float = 0.9

    round_time_seconds: int = 60
    base_threshold: int = 25
    threshold_step: int = 5
    max_threshold: int = 75

    # Multiplayer auto-flow settings
    multi_result_display_seconds: int = 10
    multi_restart_delay_seconds: int = 5

    model_config = {"env_prefix": "PB_", "env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
