import json
import re
import time

from groq import Groq
from dotenv import load_dotenv
import os


load_dotenv()


client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


MODEL = "openai/gpt-oss-20b"

WINDOW_SIZE = 5500
OVERLAP_SIZE = 1000

MAX_RETRIES = 4

RATE_LIMIT_WAIT = 3

MAX_REASON_LENGTH = 250


SYSTEM_PROMPT = """
You are a precise YouTube sponsor-segment detector.

Your job is to identify CONTIGUOUS sections of a YouTube transcript that are actual sponsor advertisements.

A sponsor segment may begin BEFORE the creator explicitly says:
- "sponsored by"
- "this video is sponsored by"
- "thanks to our sponsor"

If the transcript shows the creator transitioning into a sponsor discussion, giving personal experience with the product, explaining the product, recommending it, giving a discount code/link, or otherwise delivering the promotional message, include that entire contiguous promotional section.

The sponsor segment should end only when the creator clearly returns to their normal video content.

IMPORTANT:

1. Do NOT mark an isolated sponsorship disclosure as a sponsor segment.
2. Do NOT mark ordinary discussion of a company/product as sponsorship unless it is clearly promotional.
3. Do NOT mark unrelated mentions of products.
4. Do NOT combine separate sponsor segments.
5. Start the segment early enough to include the sponsor introduction, setup, personal story, or transition if those are clearly part of the advertisement.
6. End the segment after the sponsor's closing message, thanks, discount code, or final promotional statement when the creator then returns to normal content.
7. Use the timestamps from the transcript.
8. Only return segments that are supported by the transcript.
9. Be conservative when evidence is unclear.
10. Output ONLY valid JSON.

Return exactly this structure:

{
  "segments": [
    {
      "start": 321.0,
      "end": 377.0,
      "label": "sponsor",
      "reason": "Short explanation"
    }
  ]
}

If there are no sponsors:

{
  "segments": []
}

Keep the reason SHORT.

Do not include markdown.
Do not include ```json.
Do not include any text outside the JSON object.
"""


def extract_json(text: str) -> dict:
    """
    Attempts to extract a JSON object from the model response.

    Handles:
    - normal JSON
    - accidental markdown fences
    - extra text surrounding JSON
    """

    if not text:
        raise ValueError("Groq returned an empty response.")

    text = text.strip()

    # Remove markdown fences if the model accidentally adds them.
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    text = text.strip()

    # First attempt: entire response.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Second attempt: find the JSON object.
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError(
        "Groq returned invalid or incomplete JSON."
    )


def validate_segments(data: dict) -> list[dict]:
    """
    Validate and normalize Groq's detected sponsor segments.
    """

    if not isinstance(data, dict):
        raise ValueError(
            "Groq response is not a JSON object."
        )

    raw_segments = data.get("segments", [])

    if not isinstance(raw_segments, list):
        raise ValueError(
            "Groq 'segments' field is not a list."
        )

    segments = []

    for segment in raw_segments:

        if not isinstance(segment, dict):
            continue

        try:
            start = float(segment["start"])
            end = float(segment["end"])
        except (
            KeyError,
            TypeError,
            ValueError
        ):
            continue

        if start < 0:
            continue

        if end <= start:
            continue

        duration = end - start

        # A single sponsor read this long is suspicious.
        # This protects against a model accidentally selecting
        # almost the entire video.
        if duration > 600:
            print(
                f"Ignoring suspiciously long segment: "
                f"{start:.2f} -> {end:.2f}"
            )
            continue

        reason = str(
            segment.get(
                "reason",
                "Sponsor segment detected."
            )
        ).strip()

        if len(reason) > MAX_REASON_LENGTH:
            reason = reason[:MAX_REASON_LENGTH].rstrip() + "..."

        segments.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "label": "sponsor",
            "reason": reason
        })

    return segments


def call_groq(transcript_window: str) -> list[dict]:
    """
    Send one transcript window to Groq.

    Includes retry handling for:
    - invalid JSON
    - truncated responses
    - rate limits
    - temporary API failures
    """

    for attempt in range(1, MAX_RETRIES + 1):

        print(
            f"Sending window to Groq "
            f"(attempt {attempt}/{MAX_RETRIES})..."
        )

        try:

            response = client.chat.completions.create(
                model=MODEL,

                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": (
                            "Analyze this transcript window "
                            "for sponsor segments.\n\n"
                            + transcript_window
                        )
                    }
                ],

                temperature=0,

                # Keep the response intentionally small.
                max_tokens=700
            )

            content = response.choices[0].message.content

            if not content:
                raise ValueError(
                    "Groq returned an empty response."
                )

            print("Groq response received.")

            try:

                data = extract_json(content)

                segments = validate_segments(data)

                print(
                    f"Groq detected "
                    f"{len(segments)} sponsor(s) "
                    f"in this window."
                )

                return segments

            except ValueError as json_error:

                print(
                    "Groq returned invalid JSON."
                )

                print(
                    f"Raw response: {content}"
                )

                print(
                    f"JSON error: {json_error}"
                )

                if attempt < MAX_RETRIES:

                    wait_time = 1.5 * attempt

                    print(
                        f"Retrying malformed response "
                        f"in {wait_time:.1f}s..."
                    )

                    time.sleep(wait_time)

                    continue

                print(
                    "Maximum JSON retries reached."
                )

                return []

        except Exception as error:

            error_text = str(error)

            # -------------------------------------------------
            # GROQ RATE LIMIT
            # -------------------------------------------------

            if (
                "429" in error_text
                or "rate_limit_exceeded" in error_text
                or "Rate limit" in error_text
            ):

                # Groq normally tells us how long to wait.
                wait_time = RATE_LIMIT_WAIT

                match = re.search(
                    r"Please try again in ([0-9.]+)s",
                    error_text
                )

                if match:

                    try:
                        wait_time = float(
                            match.group(1)
                        )
                    except ValueError:
                        pass

                # Add a small safety margin.
                wait_time += 0.5

                print()
                print(
                    "Groq rate limit reached."
                )

                print(
                    f"Waiting {wait_time:.1f}s "
                    f"before retrying..."
                )

                if attempt < MAX_RETRIES:

                    time.sleep(wait_time)

                    continue

                print(
                    "Maximum rate-limit retries reached."
                )

                return []

            # -------------------------------------------------
            # OTHER TEMPORARY API ERRORS
            # -------------------------------------------------

            print(
                f"Groq request failed: {error}"
            )

            if attempt < MAX_RETRIES:

                wait_time = 2 * attempt

                print(
                    f"Retrying in "
                    f"{wait_time}s..."
                )

                time.sleep(wait_time)

                continue

            print(
                "Maximum retries reached."
            )

            return []

    return []


def merge_segments(
    segments: list[dict]
) -> list[dict]:
    """
    Merge overlapping or very close sponsor detections.

    Overlapping transcript windows can cause the same sponsor
    to be detected more than once.
    """

    if not segments:
        return []

    segments = sorted(
        segments,
        key=lambda segment: segment["start"]
    )

    merged = []

    current = segments[0].copy()

    for next_segment in segments[1:]:

        # Allow a small gap because overlapping windows may
        # produce slightly different boundaries.
        gap = (
            next_segment["start"]
            - current["end"]
        )

        if gap <= 8:

            current["end"] = max(
                current["end"],
                next_segment["end"]
            )

            current_reason = current.get(
                "reason",
                ""
            )

            next_reason = next_segment.get(
                "reason",
                ""
            )

            if (
                next_reason
                and next_reason not in current_reason
            ):

                combined_reason = (
                    current_reason
                    + " "
                    + next_reason
                )

                current["reason"] = (
                    combined_reason[
                        :MAX_REASON_LENGTH
                    ]
                )

        else:

            merged.append(current)

            current = next_segment.copy()

    merged.append(current)

    return merged


def split_transcript(
    transcript_text: str
) -> list[str]:
    """
    Split transcript into overlapping windows.

    Windows are kept smaller than before to reduce TPM usage
    and make truncated model responses less likely.
    """

    windows = []

    start = 0
    transcript_length = len(
        transcript_text
    )

    while start < transcript_length:

        end = min(
            start + WINDOW_SIZE,
            transcript_length
        )

        window = transcript_text[
            start:end
        ]

        windows.append(window)

        if end >= transcript_length:
            break

        start = end - OVERLAP_SIZE

    return windows


def detect_sponsor_segments(
    transcript_text: str
) -> list[dict]:

    print()
    print("=" * 60)
    print("GROQ SPONSOR DETECTION")
    print("=" * 60)

    print(
        f"Total transcript characters: "
        f"{len(transcript_text)}"
    )

    windows = split_transcript(
        transcript_text
    )

    print(
        f"Transcript split into "
        f"{len(windows)} overlapping "
        f"detection windows."
    )

    all_segments = []

    for index, window in enumerate(
        windows,
        start=1
    ):

        print()
        print("-" * 60)
        print(
            f"GROQ WINDOW "
            f"{index}/{len(windows)}"
        )

        print(
            f"Characters: "
            f"{len(window)}"
        )

        segments = call_groq(
            window
        )

        if segments:

            print(
                f"Window {index} produced "
                f"{len(segments)} sponsor segment(s)."
            )

            for segment in segments:

                print(
                    f"  "
                    f"{segment['start']}s -> "
                    f"{segment['end']}s"
                )

                print(
                    f"  Reason: "
                    f"{segment['reason']}"
                )

            all_segments.extend(
                segments
            )

        else:

            print(
                f"Window {index} produced "
                f"no sponsor segments."
            )

        # Small pause between successful requests.
        # This reduces the chance of immediately hitting
        # the rolling TPM limit.
        if index < len(windows):

            print(
                "Waiting briefly before "
                "next Groq window..."
            )

            time.sleep(1.0)

    print()
    print("-" * 60)

    print(
        f"Raw detected segments: "
        f"{len(all_segments)}"
    )

    merged_segments = merge_segments(
        all_segments
    )

    print()
    print("=" * 60)
    print("GROQ DETECTION COMPLETE")
    print("=" * 60)

    print(
        f"Total sponsor segments: "
        f"{len(merged_segments)}"
    )

    for segment in merged_segments:

        print(
            f"  "
            f"{segment['start']}s -> "
            f"{segment['end']}s"
        )

        print(
            f"  {segment['reason']}"
        )

    print("=" * 60)
    print()

    return merged_segments