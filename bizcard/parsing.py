"""Turn the model's raw text into a clean, validated Lead.

Small models sometimes wrap JSON in markdown, add trailing commas, write "N/A" or invent
malformed emails. Everything here is deliberately forgiving on input and strict on output.
"""
from __future__ import annotations

import json
import re

from .schema import Lead

_CODE_FENCE = re.compile(r"```(?:json)?", re.IGNORECASE)
_TRAILING_COMMA = re.compile(r",\s*([}\]])")
_EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$")
_HONORIFIC = re.compile(r"^(dr|mr|mrs|ms|miss|prof|er|ca|cs)\.?\s+", re.IGNORECASE)
_NULLISH = {"", "null", "none", "n/a", "na", "nil", "-", "--", "unknown", "not visible"}


def extract_json(raw: str) -> dict:
    """Pull the first JSON object out of the model output. Raises ValueError if impossible."""
    text = _CODE_FENCE.sub("", raw)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found in model output")
    snippet = _TRAILING_COMMA.sub(r"\1", text[start : end + 1])
    try:
        data = json.loads(snippet)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON from model: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("model output is not a JSON object")
    return data


def clean_text(value) -> str:
    """Any model value -> tidy single-line string ('' for null-like values)."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(v) for v in value if v)
    text = re.sub(r"\s+", " ", str(value)).strip()
    return "" if text.lower() in _NULLISH else text


def clean_email(value) -> str:
    """Return the first syntactically valid email, else ''. Rejects hallucinated junk."""
    text = clean_text(value).lower().replace("mailto:", "")
    for candidate in re.split(r"[,;/\s]+", text):
        if _EMAIL.match(candidate):
            return candidate
    return ""


def clean_phone(value) -> str:
    """Keep digits and common phone punctuation; drop labels like 'Tel:'; validate length."""
    text = clean_text(value)
    numbers = []
    for part in re.split(r"[,;/|]", text):
        part = re.sub(r"[^\d+()\-.\s]", "", part)
        part = re.sub(r"\s+", " ", part).strip()
        if 7 <= sum(ch.isdigit() for ch in part) <= 15:
            numbers.append(part)
    return ", ".join(numbers)


def _fix_case(name: str) -> str:
    """'RAHUL' / 'rahul' -> 'Rahul'; mixed case is assumed to be intentional."""
    return name.title() if name.isupper() or name.islower() else name


def _clean_names(first: str, last: str) -> tuple[str, str]:
    first = _HONORIFIC.sub("", first)
    # The model sometimes puts the full name in first_name: split off the last word.
    if first and not last and " " in first:
        first, last = first.rsplit(" ", 1)
    return _fix_case(first), _fix_case(last)


def build_lead(data: dict, source_file: str) -> Lead:
    """Validate and normalise the model's dict into a Lead."""
    first, last = _clean_names(clean_text(data.get("first_name")), clean_text(data.get("last_name")))
    return Lead(
        first_name=first,
        last_name=last,
        position=clean_text(data.get("position")),
        company=clean_text(data.get("company")),
        location=clean_text(data.get("location")),
        phone=clean_phone(data.get("phone")),
        email=clean_email(data.get("email")),
        source_file=source_file,
    )
