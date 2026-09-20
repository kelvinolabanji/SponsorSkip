"""Backward-compatible import path; the code now lives in ``detection``."""

from detection.groq_api import call_groq, client
from detection.merge import merge_segments
from detection.parsing import extract_json, validate_segments
from detection.pipeline import detect_sponsor_segments
from detection.prompt import SYSTEM_PROMPT
from detection.settings import (
    MAX_REASON_LENGTH,
    MAX_RETRIES,
    MODEL,
    OVERLAP_SIZE,
    RATE_LIMIT_WAIT,
    WINDOW_SIZE,
)
from detection.windows import split_transcript

__all__ = [
    "MAX_REASON_LENGTH",
    "MAX_RETRIES",
    "MODEL",
    "OVERLAP_SIZE",
    "RATE_LIMIT_WAIT",
    "SYSTEM_PROMPT",
    "WINDOW_SIZE",
    "call_groq",
    "client",
    "detect_sponsor_segments",
    "extract_json",
    "merge_segments",
    "split_transcript",
    "validate_segments",
]
