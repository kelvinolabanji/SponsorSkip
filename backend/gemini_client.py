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

    response = client.interactions.create(
        model="gemini-3.6-flash",
        system_instruction=SYSTEM_PROMPT,
        input=transcript_text,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": SponsorResult.model_json_schema()
        }
    )

    result = SponsorResult.model_validate_json(
        response.output_text
    )

    return [
        segment.model_dump()
        for segment in result.segments
    ]