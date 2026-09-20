"""Split long transcripts into overlapping windows."""

from detection.settings import OVERLAP_SIZE, WINDOW_SIZE


def split_transcript(transcript_text: str) -> list[str]:
    """Split ``transcript_text`` into windows of ``WINDOW_SIZE`` characters.

    Consecutive windows overlap by ``OVERLAP_SIZE`` characters so a sponsor
    read on a boundary is seen whole by at least one window. Windows are kept
    small to limit token usage and reduce truncated model replies.
    """
    windows = []
    start = 0
    length = len(transcript_text)

    while start < length:
        end = min(start + WINDOW_SIZE, length)
        windows.append(transcript_text[start:end])
        if end >= length:
            break
        start = end - OVERLAP_SIZE

    return windows
