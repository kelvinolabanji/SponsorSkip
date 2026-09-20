"""Run sponsor detection over a whole transcript."""

import logging
import time

from detection.groq_api import call_groq
from detection.merge import merge_segments
from detection.settings import WINDOW_PAUSE_SECONDS
from detection.windows import split_transcript

logger = logging.getLogger(__name__)


def detect_sponsor_segments(transcript_text: str) -> list[dict]:
    """Return merged sponsor segments found anywhere in ``transcript_text``.

    The transcript is split into overlapping windows, each window is analysed
    separately, and the results are merged.
    """
    windows = split_transcript(transcript_text)
    logger.info(
        "Sponsor detection: %d characters in %d window(s)",
        len(transcript_text),
        len(windows),
    )

    all_segments = []
    for index, window in enumerate(windows, start=1):
        segments = call_groq(window)
        logger.info(
            "Window %d/%d (%d characters): %d sponsor segment(s)",
            index,
            len(windows),
            len(window),
            len(segments),
        )
        all_segments.extend(segments)

        # Pause between requests to avoid the rolling tokens-per-minute limit.
        if index < len(windows):
            time.sleep(WINDOW_PAUSE_SECONDS)

    merged = merge_segments(all_segments)
    logger.info("Sponsor detection complete: %d segment(s)", len(merged))
    for segment in merged:
        logger.info(
            "  %ss -> %ss: %s", segment["start"], segment["end"], segment["reason"]
        )
    return merged
