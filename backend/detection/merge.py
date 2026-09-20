"""Merge sponsor segments detected in overlapping transcript windows."""

from detection.settings import MAX_REASON_LENGTH, MERGE_GAP_SECONDS


def merge_segments(segments: list[dict]) -> list[dict]:
    """Merge overlapping or nearly adjacent detections of the same sponsor.

    Overlapping windows can detect the same sponsor twice with slightly
    different boundaries. The input is not modified.
    """
    if not segments:
        return []

    ordered = sorted(segments, key=lambda segment: segment["start"])
    merged = []
    current = ordered[0].copy()

    for following in ordered[1:]:
        gap = following["start"] - current["end"]
        if gap <= MERGE_GAP_SECONDS:
            _absorb(current, following)
        else:
            merged.append(current)
            current = following.copy()

    merged.append(current)
    return merged


def _absorb(current: dict, other: dict) -> None:
    """Extend ``current`` (in place) to also cover ``other``."""
    current["end"] = max(current["end"], other["end"])

    current_reason = current.get("reason", "")
    other_reason = other.get("reason", "")
    if other_reason and other_reason not in current_reason:
        combined = f"{current_reason} {other_reason}"
        current["reason"] = combined[:MAX_REASON_LENGTH]
