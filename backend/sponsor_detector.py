from groq_client import (
    detect_sponsor_segments as detect_with_groq
)


def detect_sponsor_segments(
    transcript_text: str
) -> list[dict]:

    return detect_with_groq(
        transcript_text
    )
    