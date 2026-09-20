"""All tunable settings live here. Every value can be overridden with an environment variable,
so the same code runs on a laptop, a free Hugging Face Space, or an EC2 GPU box unchanged."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    model_id: str         # Hugging Face model repo (free, Apache-2.0 licensed)
    dtype: str            # "auto" | "float32" | "bfloat16" | "float16"
    max_files: int        # max images processed per batch
    max_image_side: int   # images are shrunk so the longest side is at most this many pixels
    min_pixels: int       # lower bound for the model's visual-token budget
    max_pixels: int       # upper bound for the visual-token budget (main speed/accuracy knob)
    max_new_tokens: int   # hard cap on generated tokens per card
    cache_size: int       # how many card results to remember (skip re-processing duplicates)


def load_settings() -> Settings:
    return Settings(
        model_id=os.getenv("MODEL_ID", "Qwen/Qwen2-VL-2B-Instruct"),
        dtype=os.getenv("DTYPE", "auto").strip().lower(),
        max_files=_int_env("MAX_FILES", 20),
        max_image_side=_int_env("MAX_IMAGE_SIDE", 1024),
        min_pixels=_int_env("MIN_PIXELS", 128 * 28 * 28),
        max_pixels=_int_env("MAX_PIXELS", 512 * 28 * 28),
        max_new_tokens=_int_env("MAX_NEW_TOKENS", 200),
        cache_size=_int_env("CACHE_SIZE", 200),
    )
