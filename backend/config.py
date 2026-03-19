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
    gemini_model: str = "imagen-4.0-fast-generate-001"
    gemini_image_size: int = 512  # Resize generated images to this size (0 = no resize)

    # Prompt-Prefix: wird vor jeden Spieler-Prompt gesetzt.
    prompt_prefix: str = ""

    # Similarity backend: "clip" (local CLIP model) or "gemini" (Google API)
    similarity_backend: str = "clip"
    # Gemini model for similarity scoring (when similarity_backend=gemini)
    similarity_gemini_model: str = "gemini-2.5-flash"

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

    # Frontend animation timings (seconds)
    image_display_seconds: float = 3.0    # Pause to show generated images before comparing
    compare_bar_seconds: float = 3.0      # "Bilder werden verglichen" bar duration
    score_reveal_seconds: float = 2.5     # Score bars animation duration
    result_display_seconds: float = 8.0   # How long the winner overlay shows
    gameover_restart_seconds: float = 5.0 # How long gameover screen shows before auto-restart

    model_config = {"env_prefix": "PB_", "env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
