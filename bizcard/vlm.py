"""Thin wrapper around a Qwen vision-language model (free and open source, Apache-2.0).

The model is loaded ONCE (loading takes far longer than a single inference) and then reused
for every card. GPU is used automatically when available, otherwise CPU.
"""
from __future__ import annotations

import logging
import os

import torch
from PIL import Image
from transformers import AutoProcessor

try:  # name used by recent transformers versions
    from transformers import AutoModelForImageTextToText as _AutoVisionModel
except ImportError:  # older versions
    from transformers import AutoModelForVision2Seq as _AutoVisionModel

from .config import Settings
from .prompts import EXTRACTION_PROMPT

log = logging.getLogger(__name__)

_DTYPES = {
    "float32": torch.float32,
    "fp32": torch.float32,
    "bfloat16": torch.bfloat16,
    "bf16": torch.bfloat16,
    "float16": torch.float16,
    "fp16": torch.float16,
}


def _usable_cpu_threads() -> int:
    """CPU cores this process may really use (a container can see more cores than it owns)."""
    try:
        return len(os.sched_getaffinity(0))
    except AttributeError:  # Windows / macOS
        return os.cpu_count() or 2


def _pick_dtype(requested: str, use_cuda: bool) -> torch.dtype:
    if requested in _DTYPES:
        return _DTYPES[requested]
    # "auto": fp16 on GPU; bf16 on CPU (half the RAM of fp32, ~4.5 GB for the 2B model).
    return torch.float16 if use_cuda else torch.bfloat16


class QwenVLExtractor:
    """Image in, raw model text out. Parsing/validation is done elsewhere (parsing.py)."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._model = None
        self._processor = None

    def load(self) -> "QwenVLExtractor":
        if self._model is not None:
            return self
        s = self._settings
        use_cuda = torch.cuda.is_available()
        torch.set_num_threads(_usable_cpu_threads())
        dtype = _pick_dtype(s.dtype, use_cuda)
        log.info("Loading %s on %s (dtype=%s) ...", s.model_id, "GPU" if use_cuda else "CPU", dtype)

        self._model = _AutoVisionModel.from_pretrained(
            s.model_id,
            torch_dtype=dtype,
            device_map="auto" if use_cuda else "cpu",
        ).eval()
        # min/max_pixels control how many visual tokens an image becomes: fewer = faster.
        self._processor = AutoProcessor.from_pretrained(
            s.model_id, min_pixels=s.min_pixels, max_pixels=s.max_pixels
        )
        log.info("Model ready.")
        return self

    def generate(self, image: Image.Image) -> str:
        if self._model is None:
            self.load()
        messages = [
            {
                "role": "user",
                "content": [{"type": "image"}, {"type": "text", "text": EXTRACTION_PROMPT}],
            }
        ]
        prompt = self._processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._processor(text=[prompt], images=[image], return_tensors="pt")
        inputs = inputs.to(self._model.device)

        with torch.inference_mode():
            output = self._model.generate(
                **inputs,
                max_new_tokens=self._settings.max_new_tokens,
                do_sample=False,  # deterministic output
                temperature=None,  # silence "sampling params ignored" warnings
                top_p=None,
                top_k=None,
            )
        new_tokens = output[:, inputs["input_ids"].shape[1] :]  # drop the echoed prompt
        return self._processor.batch_decode(new_tokens, skip_special_tokens=True)[0]
