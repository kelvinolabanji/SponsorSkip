"""Parse and validate the model's JSON reply."""

import json
import logging
import re

from detection.settings import (
    DEFAULT_REASON,
    MAX_REASON_LENGTH,
    MAX_SEGMENT_SECONDS,
    SEGMENT_LABEL,
)

logger = logging.getLogger(__name__)

_OPENING_FENCE = re.compile(r"^```(?:json)?\s*", re.IGNORECASE)
_CLOSING_FENCE = re.compile(r"\s*```$")


def extract_json(text: str) -> dict:
    """Extract a JSON object from a model reply.

    Handles plain JSON, accidental markdown fences and extra text around the
    object. Raises ``ValueError`` if nothing parseable is found.
    """
    if not text:
        raise ValueError("Groq returned an empty response.")

    text = _strip_code_fences(text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError("Groq returned invalid or incomplete JSON.")


def _strip_code_fences(text: str) -> str:
    text = _OPENING_FENCE.sub("", text.strip())
    return _CLOSING_FENCE.sub("", text).strip()


def validate_segments(data: dict) -> list[dict]:
    """Validate and normalize the segments in a parsed model reply.

    Malformed individual segments are skipped; a malformed payload raises
    ``ValueError``.
    """
    if not isinstance(data, dict):
        raise ValueError("Groq response is not a JSON object.")

    raw_segments = data.get("segments", [])
    if not isinstance(raw_segments, list):
        raise ValueError("Groq 'segments' field is not a list.")

    normalized = (_normalize_segment(raw) for raw in raw_segments)
    return [segment for segment in normalized if segment is not None]


def _normalize_segment(raw: object) -> dict | None:
    """Return a clean segment dict, or ``None`` if ``raw`` is unusable."""
    if not isinstance(raw, dict):
        return None

    try:
        start = float(raw["start"])
        end = float(raw["end"])
    except (KeyError, TypeError, ValueError):
        return None

    if start < 0 or end <= start:
        return None

    # A single sponsor read this long is suspicious: it usually means the model
    # selected almost the entire video.
    if end - start > MAX_SEGMENT_SECONDS:
        logger.warning("Ignoring suspiciously long segment: %.2f -> %.2f", start, end)
        return None

    reason = str(raw.get("reason", DEFAULT_REASON)).strip()
    if len(reason) > MAX_REASON_LENGTH:
        reason = reason[:MAX_REASON_LENGTH].rstrip() + "..."

    return {
        "start": round(start, 2),
        "end": round(end, 2),
        "label": SEGMENT_LABEL,
        "reason": reason,
    }
