"""Parse WebVTT subtitle files into transcript entries."""

import re
from pathlib import Path

SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600

_CUE_TIMING_SEPARATOR = "-->"
_MARKUP_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")


def parse_vtt(vtt_file: Path) -> list[dict]:
    """Convert a VTT subtitle file into ``{"text", "start", "duration"}`` entries."""
    text = vtt_file.read_text(encoding="utf-8")

    entries = []
    for block in text.split("\n\n"):
        entry = _parse_cue(block)
        if entry is not None:
            entries.append(entry)
    return entries


def _parse_cue(block: str) -> dict | None:
    """Parse one VTT block, or return ``None`` if it is not a cue with text."""
    lines = block.strip().splitlines()

    timing_index = next(
        (i for i, line in enumerate(lines) if _CUE_TIMING_SEPARATOR in line), None
    )
    if timing_index is None:
        return None

    start_text, end_text = lines[timing_index].split(_CUE_TIMING_SEPARATOR)[:2]
    start = vtt_time_to_seconds(start_text.strip())
    end = vtt_time_to_seconds(end_text.strip())

    text = _clean_caption_text(" ".join(lines[timing_index + 1 :]))
    if not text:
        return None

    return {"text": text, "start": start, "duration": end - start}


def _clean_caption_text(text: str) -> str:
    """Drop markup tags such as ``<c>...</c>`` and collapse whitespace."""
    return _WHITESPACE.sub(" ", _MARKUP_TAG.sub("", text)).strip()


def vtt_time_to_seconds(timestamp: str) -> float:
    """Convert a VTT timestamp (``HH:MM:SS.mmm`` or ``MM:SS.mmm``) to seconds."""
    # Ignore cue settings after the time, and accept commas as the decimal mark.
    timestamp = timestamp.strip().split()[0].replace(",", ".")
    parts = timestamp.split(":")

    if len(parts) == 3:
        hours, minutes, seconds = parts
        return (
            float(hours) * SECONDS_PER_HOUR
            + float(minutes) * SECONDS_PER_MINUTE
            + float(seconds)
        )
    if len(parts) == 2:
        minutes, seconds = parts
        return float(minutes) * SECONDS_PER_MINUTE + float(seconds)

    raise ValueError(f"Invalid VTT timestamp: {timestamp}")
