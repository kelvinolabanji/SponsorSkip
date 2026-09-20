"""Format transcripts for the sponsor-detection prompt."""

from transcript.vtt import SECONDS_PER_MINUTE


def format_for_prompt(transcript: list[dict]) -> str:
    """Render entries as ``[MM:SS] text`` lines for the detection model."""
    lines = []
    for entry in transcript:
        minutes, seconds = divmod(int(entry["start"]), SECONDS_PER_MINUTE)
        lines.append(f"[{minutes:02d}:{seconds:02d}] {entry['text']}")
    return "\n".join(lines)
