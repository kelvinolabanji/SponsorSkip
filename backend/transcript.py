import subprocess
import tempfile
from pathlib import Path
import re


class TranscriptUnavailable(Exception):
    pass


def parse_vtt(vtt_file: Path) -> list[dict]:
    """Convert a VTT subtitle file into our normal transcript format."""

    text = vtt_file.read_text(encoding="utf-8")

    entries = []

    blocks = text.split("\n\n")

    for block in blocks:
        lines = block.strip().splitlines()

        # Find the timestamp line
        timestamp_index = None

        for i, line in enumerate(lines):
            if "-->" in line:
                timestamp_index = i
                break

        if timestamp_index is None:
            continue

        timestamp_line = lines[timestamp_index]

        start_time, end_time = timestamp_line.split("-->")[:2]

        start = vtt_time_to_seconds(start_time.strip())
        end = vtt_time_to_seconds(end_time.strip())

        # Everything after the timestamp is subtitle text
        subtitle_lines = lines[timestamp_index + 1:]

        subtitle_text = " ".join(subtitle_lines)

        # Remove HTML tags like <c>...</c>
        subtitle_text = re.sub(r"<[^>]+>", "", subtitle_text)

        # Remove duplicate whitespace
        subtitle_text = re.sub(r"\s+", " ", subtitle_text).strip()

        if subtitle_text:
            entries.append({
                "text": subtitle_text,
                "start": start,
                "duration": end - start
            })

    return entries


def vtt_time_to_seconds(timestamp: str) -> float:
    """Convert a VTT timestamp to seconds."""

    timestamp = timestamp.strip().split()[0]
    timestamp = timestamp.replace(",", ".")

    parts = timestamp.split(":")

    if len(parts) == 3:
        hours, minutes, seconds = parts

        return (
            float(hours) * 3600
            + float(minutes) * 60
            + float(seconds)
        )

    elif len(parts) == 2:
        minutes, seconds = parts

        return (
            float(minutes) * 60
            + float(seconds)
        )

    else:
        raise ValueError(f"Invalid VTT timestamp: {timestamp}")

def get_transcript(video_id: str) -> list[dict]:
    """Download and return YouTube subtitles."""

    try:
        with tempfile.TemporaryDirectory() as temp_dir:

            output_template = str(
                Path(temp_dir) / "%(id)s.%(ext)s"
            )

            command = [
                "yt-dlp",
                "--write-auto-subs",
                "--sub-langs", "en",
                "--sub-format", "vtt",
                "--skip-download",
                "--output", output_template,
                f"https://www.youtube.com/watch?v={video_id}"
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise TranscriptUnavailable(
                    result.stderr
                )

            vtt_file = Path(temp_dir) / f"{video_id}.en.vtt"

            if not vtt_file.exists():
                raise TranscriptUnavailable(
                    "No English transcript found for this video."
                )

            return parse_vtt(vtt_file)

    except FileNotFoundError:
        raise TranscriptUnavailable(
            "yt-dlp is not installed or cannot be found."
        )


def format_for_prompt(transcript: list[dict]) -> str:
    """Compact timestamped text block for the LLM prompt."""

    lines = []

    for entry in transcript:

        start = entry["start"]

        mm, ss = divmod(int(start), 60)

        lines.append(
            f"[{mm:02d}:{ss:02d}] {entry['text']}"
        )

    return "\n".join(lines)