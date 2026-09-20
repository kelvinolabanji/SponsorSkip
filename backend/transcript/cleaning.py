"""Remove duplicated caption text from transcripts."""

# Captions repeating fewer words than this are kept as they are.
MIN_OVERLAP_WORDS = 3


def clean_transcript(entries: list[dict]) -> list[dict]:
    """Remove duplicated or overlapping caption text.

    YouTube auto-generated captions often repeat the end of the previous
    caption at the start of the next one.
    """
    cleaned = []

    for entry in entries:
        text = entry["text"].strip()
        if not text:
            continue

        if cleaned:
            previous_text = cleaned[-1]["text"]
            if text.lower() == previous_text.lower():
                continue
            text = _remove_repeated_prefix(previous_text, text)
            if not text:
                continue

        cleaned.append(
            {"text": text, "start": entry["start"], "duration": entry["duration"]}
        )

    return cleaned


def _remove_repeated_prefix(previous_text: str, text: str) -> str:
    """Drop the start of ``text`` that repeats the end of ``previous_text``.

    Matching ignores case; the remaining words keep their original case.
    Returns an empty string if the whole caption was already present.
    """
    words = text.split()
    if len(words) < MIN_OVERLAP_WORDS:
        return text

    lowered_words = text.lower().split()
    previous_words = previous_text.lower().split()

    longest_overlap = min(len(previous_words), len(words))
    for size in range(longest_overlap, MIN_OVERLAP_WORDS - 1, -1):
        if previous_words[-size:] == lowered_words[:size]:
            return " ".join(words[size:])

    return text
