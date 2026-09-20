"""Business logic for ``/segments``: cache lookup, transcript and detection."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from db import VideoSegments
from detection.pipeline import detect_sponsor_segments
from transcript import format_for_prompt, get_transcript

logger = logging.getLogger(__name__)


class SegmentDetectionFailed(Exception):
    """Sponsor detection raised an unexpected error."""


async def get_or_detect_segments(
    video_id: str, session: AsyncSession
) -> tuple[list[dict], bool]:
    """Return ``(segments, was_cached)`` for a video.

    Uses the database cache when possible; otherwise fetches the transcript,
    runs sponsor detection and stores the result.

    Raises ``TranscriptUnavailable`` if no transcript can be obtained and
    ``SegmentDetectionFailed`` if detection crashes.
    """
    cached = await session.get(VideoSegments, video_id)
    if cached:
        logger.info("Using cached sponsor segments for %s", video_id)
        return cached.segments, True

    transcript = get_transcript(video_id)
    transcript_text = format_for_prompt(transcript)
    logger.info(
        "Transcript retrieved for %s: %d entries, %d characters",
        video_id,
        len(transcript),
        len(transcript_text),
    )

    try:
        segments = detect_sponsor_segments(transcript_text)
    except Exception as error:
        logger.exception("Sponsor detection failed for %s", video_id)
        raise SegmentDetectionFailed(video_id) from error

    session.add(VideoSegments(video_id=video_id, segments=segments))
    await session.commit()
    return segments, False
