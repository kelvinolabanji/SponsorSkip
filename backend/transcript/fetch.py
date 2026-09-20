"""Download YouTube subtitles with yt-dlp."""

import subprocess
import tempfile
from pathlib import Path

from transcript.cleaning import clean_transcript
from transcript.errors import TranscriptUnavailable
from transcript.vtt import parse_vtt

SUBTITLE_LANGUAGE = "en"
YOUTUBE_WATCH_URL = "https://www.youtube.com/watch?v={video_id}"


def get_transcript(video_id: str) -> list[dict]:
    """Download, parse and clean the English subtitles of a YouTube video.

    Raises ``TranscriptUnavailable`` if yt-dlp is missing or fails, or if the
    video has no usable English captions.
    """
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            vtt_file = _download_subtitles(video_id, Path(temp_dir))
            transcript = clean_transcript(parse_vtt(vtt_file))
    except FileNotFoundError as error:
        raise TranscriptUnavailable(
            "yt-dlp is not installed or cannot be found."
        ) from error

    if not transcript:
        raise TranscriptUnavailable(
            "The English transcript was downloaded, "
            "but it contained no readable captions."
        )
    return transcript


def _download_subtitles(video_id: str, directory: Path) -> Path:
    """Run yt-dlp for ``video_id`` and return the VTT file it wrote."""
    command = [
        "yt-dlp",
        "--write-auto-subs",
        "--sub-langs",
        SUBTITLE_LANGUAGE,
        "--sub-format",
        "vtt",
        "--skip-download",
        "--output",
        str(directory / "%(id)s.%(ext)s"),
        YOUTUBE_WATCH_URL.format(video_id=video_id),
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise TranscriptUnavailable(result.stderr.strip())

    vtt_files = list(directory.glob(f"*.{SUBTITLE_LANGUAGE}.vtt"))
    if not vtt_files:
        raise TranscriptUnavailable(
            "YouTube subtitles were requested successfully, "
            "but no English VTT file was created."
        )
    return vtt_files[0]
