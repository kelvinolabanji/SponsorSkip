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
        subtitle_text = re.sub(
            r"<[^>]+>",
            "",
            subtitle_text
        )

        # Remove duplicate whitespace
        subtitle_text = re.sub(
            r"\s+",
            " ",
            subtitle_text
        ).strip()

        if subtitle_text:
            entries.append({
                "text": subtitle_text,
                "start": start,
                "duration": end - start
            })

    return entries


def clean_transcript(entries: list[dict]) -> list[dict]:
    """
    Remove duplicated/overlapping caption text.

    YouTube auto-generated captions often repeat portions
    of the previous caption.
    """

    cleaned = []

    for entry in entries:

        text = entry["text"].strip()

        if not text:
            continue

        # Exact duplicate
        if (
            cleaned
            and text.lower() == cleaned[-1]["text"].lower()
        ):
            continue

        # Check whether this caption is mostly already
        # present in the previous caption.
        if cleaned:

            previous = cleaned[-1]["text"]

            previous_words = previous.lower().split()
            current_words = text.lower().split()

            if len(current_words) >= 3:

                max_overlap = min(
                    len(previous_words),
                    len(current_words)
                )

                for overlap_size in range(
                    max_overlap,
                    2,
                    -1
                ):

                    previous_end = (
                        previous_words[-overlap_size:]
                    )

                    current_start = (
                        current_words[:overlap_size]
                    )

                    if previous_end == current_start:

                        # Remove repeated beginning
                        # from this caption.
                        text = " ".join(
                            current_words[overlap_size:]
                        )

                        if not text:
                            break

                        # Preserve original capitalization
                        # where possible.
                        original_words = (
                            entry["text"]
                            .strip()
                            .split()
                        )

                        if len(original_words) > overlap_size:
                            text = " ".join(
                                original_words[overlap_size:]
                            )

                        break

        if not text:
            continue

        cleaned.append({
            "text": text,
            "start": entry["start"],
            "duration": entry["duration"]
        })

    return cleaned


def vtt_time_to_seconds(timestamp: str) -> float:
    """Convert a VTT timestamp to seconds."""

    timestamp = timestamp.strip().split()[0]

    # VTT can use commas for milliseconds
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
        raise ValueError(
            f"Invalid VTT timestamp: {timestamp}"
        )


def get_transcript(video_id: str) -> list[dict]:
    """Download and return YouTube English subtitles."""

    try:

        with tempfile.TemporaryDirectory() as temp_dir:

            output_template = str(
                Path(temp_dir) / "%(id)s.%(ext)s"
            )

            command = [
                "yt-dlp",

                "--write-auto-subs",

                "--sub-langs",
                "en",

                "--sub-format",
                "vtt",

                "--skip-download",

                "--output",
                output_template,

                f"https://www.youtube.com/watch?v={video_id}"
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True
            )

            # yt-dlp failed
            if result.returncode != 0:

                raise TranscriptUnavailable(
                    result.stderr.strip()
                )

            # Find the English VTT file that yt-dlp
            # actually created.
            vtt_files = list(
                Path(temp_dir).glob("*.en.vtt")
            )

            if not vtt_files:

                raise TranscriptUnavailable(
                    "YouTube subtitles were requested "
                    "successfully, but no English VTT "
                    "file was created."
                )

            # Use the downloaded English subtitle file.
            vtt_file = vtt_files[0]

            # Parse VTT
            transcript = parse_vtt(vtt_file)

            # Remove overlapping/duplicate captions
            transcript = clean_transcript(transcript)

            if not transcript:

                raise TranscriptUnavailable(
                    "The English transcript was downloaded, "
                    "but it contained no readable captions."
                )

            return transcript

    except FileNotFoundError:

        raise TranscriptUnavailable(
            "yt-dlp is not installed or cannot be found."
        )


def format_for_prompt(transcript: list[dict]) -> str:
    """Convert transcript into timestamped text for Gemini."""

    lines = []

    for entry in transcript:

        start = entry["start"]

        mm, ss = divmod(
            int(start),
            60
        )

        lines.append(
            f"[{mm:02d}:{ss:02d}] {entry['text']}"
        )

    return "\n".join(lines)