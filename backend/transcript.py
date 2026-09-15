from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound


class TranscriptUnavailable(Exception):
    pass


def get_transcript(video_id: str) -> list[dict]:
    """Returns list of {"text": str, "start": float, "duration": float}."""
    try:
        return YouTubeTranscriptApi.get_transcript(video_id)
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        raise TranscriptUnavailable(str(e))


def format_for_prompt(transcript: list[dict]) -> str:
    """Compact timestamped text block for the LLM prompt."""
    lines = []
    for entry in transcript:
        start = entry["start"]
        mm, ss = divmod(int(start), 60)
        lines.append(f"[{mm:02d}:{ss:02d}] {entry['text']}")
    return "\n".join(lines)
