import os
from google import genai
from pydantic import BaseModel


client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)


SYSTEM_PROMPT = """
You are analyzing a YouTube video transcript to identify sponsored segments.

Identify segments that contain:
- sponsor reads
- paid advertisements
- explicit sponsorship messages
- creator self-promotion
- merch promotions
- Patreon or membership promotions
- products or services the creator is promoting

Do NOT flag:
- normal discussion of products
- organic recommendations
- normal video content
- intros
- outros unless they contain promotional content

For each sponsored segment provide:
- start: timestamp in seconds
- end: timestamp in seconds
- label: "sponsor"

If there are no sponsored segments, return an empty segments array.
"""


class SponsorSegment(BaseModel):
    start: float
    end: float
    label: str


class SponsorResult(BaseModel):
    segments: list[SponsorSegment]


def detect_sponsor_segments(transcript_text: str) -> list[dict]:
    chunks = split_transcript(transcript_text)

    all_segments = []

    for chunk in chunks:
        response = client.interactions.create(
            model="gemini-3.6-flash",
            system_instruction=SYSTEM_PROMPT,
            input=chunk,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": SponsorResult.model_json_schema()
            }
        )

        result = SponsorResult.model_validate_json(
            response.output_text
        )

        all_segments.extend(
            segment.model_dump()
            for segment in result.segments
        )

    return all_segments

def split_transcript(
    transcript_text: str,
    max_chars: int = 12000
) -> list[str]:

    lines = transcript_text.splitlines()

    chunks = []
    current_chunk = []
    current_length = 0

    for line in lines:

        line_length = len(line)

        if current_chunk and current_length + line_length > max_chars:
            chunks.append("\n".join(current_chunk))

            current_chunk = []
            current_length = 0

        current_chunk.append(line)
        current_length += line_length

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks