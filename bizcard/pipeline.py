"""Batch pipeline: read image -> (cache) -> model -> parse -> lead table.

Deliberately independent from the UI and from torch, so it can be unit-tested with a fake
extractor (see tests/).
"""
from __future__ import annotations

import hashlib
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, Iterator, NamedTuple, Protocol

import pandas as pd
from PIL import Image, ImageOps

from .config import Settings
from .parsing import build_lead, extract_json
from .schema import LEAD_COLUMNS, Lead

log = logging.getLogger(__name__)


class Extractor(Protocol):
    """Anything that turns a card image into the model's raw text answer."""

    def generate(self, image: Image.Image) -> str: ...


@dataclass
class CardResult:
    source_file: str
    lead: Lead | None = None
    error: str | None = None


@dataclass
class Progress:
    done: int
    total: int
    results: list[CardResult]
    eta_seconds: float | None  # None until at least one card has gone through the model


class LeadTable(NamedTuple):
    frame: pd.DataFrame
    problems: list[str]  # files that failed or contained no contact details
    duplicates: int      # cards skipped because their email was already seen


def prepare_image(path: str | Path, max_side: int) -> Image.Image:
    """Open, fix phone-camera rotation, convert to RGB and shrink (less pixels = faster model)."""
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((max_side, max_side))
    return img


class LeadPipeline:
    def __init__(self, extractor: Extractor, settings: Settings):
        self._extractor = extractor
        self._settings = settings
        # Same card uploaded twice -> answer instantly instead of re-running the model.
        self._cache: OrderedDict[str, Lead] = OrderedDict()

    # ------------------------------------------------------------------ public API
    def iter_process(self, paths: Iterable[str | Path]) -> Iterator[Progress]:
        """Yield a Progress after every card so the UI can stream partial results."""
        paths = list(paths)[: self._settings.max_files]
        results: list[CardResult] = []
        model_seconds, model_runs = 0.0, 0

        for done, path in enumerate(paths, start=1):
            started = time.perf_counter()
            result, used_model = self._process_one(path)
            if used_model:
                model_seconds += time.perf_counter() - started
                model_runs += 1
            results.append(result)

            eta = (model_seconds / model_runs) * (len(paths) - done) if model_runs else None
            yield Progress(done, len(paths), list(results), eta)

    # ------------------------------------------------------------------ internals
    def _process_one(self, path: str | Path) -> tuple[CardResult, bool]:
        """Returns (result, whether the model actually ran). Never raises: one bad card must
        not stop the rest of the batch."""
        name = Path(path).name
        try:
            key = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            cached = self._cache.get(key)
            if cached is not None:
                self._cache.move_to_end(key)
                return CardResult(name, replace(cached, source_file=name)), False

            image = prepare_image(path, self._settings.max_image_side)
            raw = self._extractor.generate(image)
            lead = build_lead(extract_json(raw), name)

            self._cache[key] = lead
            while len(self._cache) > self._settings.cache_size:
                self._cache.popitem(last=False)  # evict least recently used
            return CardResult(name, lead), True
        except Exception as exc:  # noqa: BLE001 - intentionally broad, see docstring
            log.warning("Failed on %s: %s", name, exc)
            return CardResult(name, error=str(exc) or type(exc).__name__), False


def build_lead_table(results: Iterable[CardResult]) -> LeadTable:
    """Collect successful, non-empty leads into a DataFrame; drop duplicates by email."""
    rows, problems, seen_emails, duplicates = [], [], set(), 0
    for r in results:
        if r.error:
            problems.append(f"{r.source_file} ({r.error})")
        elif not r.lead.has_contact_info():
            problems.append(f"{r.source_file} (no contact details found)")
        elif r.lead.email and r.lead.email in seen_emails:
            duplicates += 1
        else:
            if r.lead.email:
                seen_emails.add(r.lead.email)
            rows.append(r.lead.as_row())
    return LeadTable(pd.DataFrame(rows, columns=LEAD_COLUMNS), problems, duplicates)
