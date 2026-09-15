import os
import json

from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

SYSTEM_PROMPT = """You are given a YouTube video transcript with timestamps in [MM:SS] format.
Identify segments that are sponsor reads, ad reads, or self-promotion (e.g. "this video is sponsored by...", "use code...", "check out my merch...").
Do NOT flag the creator's own content, intros, or organic mentions of products unrelated to a paid deal.

Respond with ONLY a JSON array, no prose, no markdown fences. Each element:
{"start": <seconds:number>, "end": <seconds:number>, "label": "sponsor"}

If there are no sponsor segments, respond with [].
"""


def detect_sponsor_segments(transcript_text: str) -> list[dict]:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": transcript_text},
        ],
        temperature=0,
        response_format={"type": "json_object"} if False else None,  # llama3.3 on groq: plain JSON via prompt
    )
    raw = response.choices[0].message.content.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        segments = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return segments if isinstance(segments, list) else []
