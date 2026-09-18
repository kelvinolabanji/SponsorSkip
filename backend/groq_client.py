import os
import json

from groq import Groq


client = Groq(
    api_key=os.environ["GROQ_API_KEY"]
)


SYSTEM_PROMPT = """
You are a highly accurate YouTube sponsor-segment detection system.

Your job is to identify the COMPLETE CONTIGUOUS SPONSOR/ADVERTISEMENT
SECTION of a YouTube video.

The goal is to determine exactly where the sponsor segment STARTS
and exactly where it ENDS.

============================================================
MOST IMPORTANT RULE
============================================================

DO NOT only look for the moment where the creator explicitly says:

- "This video is sponsored by..."
- "Today's sponsor is..."
- "Thanks to..."
- the sponsor's name
- a discount code
- a URL

Those phrases may occur AFTER the sponsor segment has already started.

The sponsor segment can begin BEFORE the explicit sponsorship
disclosure.

For example:

[04:30] I've been using this product for a long time.
[04:40] The reason I started using it was because...
[04:55] It has helped me with...
[05:10] That's why I really like using it.
[05:20] Today's video is sponsored by X.
[05:30] X gives you...
[05:45] You can use my code...
[05:55] Thanks to X for sponsoring this video.
[06:02] Anyway, let's get back to the video.

The COMPLETE sponsor segment is approximately:

START = 04:30
END = 06:02

NOT:

START = 05:20
END = 05:55

============================================================
SPONSOR SEGMENT START
============================================================

Find the EARLIEST timestamp where the creator transitions from
normal video content into the sponsor-related discussion.

This may be:

- the first discussion of the sponsored product
- the creator explaining why they use the product
- a personal story about the product
- backstory about how they discovered the product
- explaining a problem that the product solves
- explaining their experience with the product
- introducing the product before explicitly saying it is sponsored
- the beginning of a sponsor story or advertisement

If the creator is clearly discussing the sponsor/product as part
of the upcoming advertisement, include that material.

DO NOT wait for the explicit phrase:

"This video is sponsored by..."

The advertisement may have already started.

============================================================
SPONSOR SEGMENT END
============================================================

Find the point where the creator has clearly FINISHED the sponsor
discussion and returns to the normal subject of the video.

The ending may happen AFTER:

- the product explanation
- the promotional pitch
- the discount code
- the URL
- the call to action
- "thanks to X for sponsoring"
- other closing sponsor remarks

For example:

[05:45] Use my code KELVIN for 20% off.
[05:55] Thanks again to X for sponsoring this video.
[06:00] And now let's get back to what we were talking about.
[06:05] So, as I was saying about today's match...

The sponsor segment should include the closing thanks.

END should be around 06:00-06:05,
not 05:55.

============================================================
IMPORTANT: BACKSTORY
============================================================

A sponsor advertisement does NOT necessarily begin with an obvious
advertising phrase.

Creators often make sponsor reads sound like normal conversation.

For example:

"I've actually been using X for about six months now."

"One thing I noticed when I started using X was..."

"I originally started using this because..."

"Before we continue, I want to tell you about..."

These can be the START of the sponsor segment if the surrounding
context shows that the creator has transitioned into talking about
the sponsor as part of the advertisement.

Include this earlier material.

============================================================
IMPORTANT: SPONSOR DISCLOSURE
============================================================

A sponsorship disclosure by itself is NOT enough to create a
segment.

For example:

[00:11] This video is presented by PrizePicks.
[00:14] Anyway, let's talk about today's game.

DO NOT return:

00:11 -> 00:14

However, if the disclosure is immediately followed by a genuine
sponsor discussion, the segment may begin at the disclosure or
slightly before it if the promotional discussion already started.

============================================================
SHORT MENTIONS
============================================================

Do NOT flag ordinary short mentions.

Examples:

"I use X sometimes."

"X is a company that makes..."

"I bought this from X."

"Thanks to X for sponsoring the video."

A short isolated mention is not enough.

However, if the short mention is part of a larger contiguous
sponsor discussion, include it as part of that sponsor segment.

============================================================
NORMAL CONTENT BETWEEN SPONSOR REFERENCES
============================================================

Do NOT connect separate sponsor-related moments across normal
video content.

For example:

[00:10] This video is sponsored by X.
[00:15] Anyway, let's talk about football.
...
[04:30] Let's talk about today's game.
...
[10:00] X has a new product...

Do NOT create:

00:10 -> 10:00

The sponsor segment must be a CONTIGUOUS promotional section.

============================================================
WHAT SHOULD BE INCLUDED
============================================================

Include genuine promotional material such as:

- sponsor introductions
- sponsor/product backstory
- personal experience used to promote the product
- explanations of why the creator uses the product
- product features
- product benefits
- explanations of how the product works
- reasons viewers should use the product
- discount codes
- affiliate codes
- promotional URLs
- sign-up instructions
- purchase instructions
- calls to action
- promotional offers
- sponsor closing remarks
- thanks to the sponsor when they are part of the advertisement

============================================================
WHAT SHOULD NOT BE INCLUDED
============================================================

Do NOT flag:

- casual product mentions
- normal discussion of companies
- news about companies
- products naturally appearing in the video
- unrelated discussion
- normal YouTube introductions
- normal conclusions
- "like and subscribe"
- normal discussion surrounding the sponsor
- isolated sponsorship disclosures

============================================================
BOUNDARY RULE
============================================================

When deciding the START:

Ask:

"Is this the point where the creator begins talking about the
sponsor/product as part of the advertisement?"

If yes, START there.

Do not wait for the explicit sponsorship disclosure.

When deciding the END:

Ask:

"Has the creator clearly returned to the normal subject of the video?"

If no, continue the sponsor segment.

Do not stop merely because the creator has finished giving the
discount code or URL.

============================================================
CONSERVATIVE BOUNDARIES
============================================================

When uncertain between two possible START timestamps, prefer the
earlier timestamp ONLY when there is evidence that the earlier
material is part of the sponsor discussion.

When uncertain between two possible END timestamps, prefer the
later timestamp ONLY when the creator is still clearly discussing
the sponsor or closing the advertisement.

Do NOT include unrelated normal content just to make the segment
longer.

============================================================
TIMESTAMP ACCURACY
============================================================

The transcript uses:

[MM:SS] text

Use the timestamps from the transcript.

Return timestamps in seconds.

Do not invent timestamps.

The boundaries should be as close as possible to the actual
transition into and out of the sponsor discussion.

============================================================
OUTPUT
============================================================

If there are no genuine sponsor segments:

{
  "segments": []
}

If there is a genuine sponsor segment:

{
  "segments": [
    {
      "start": 270.0,
      "end": 362.0,
      "label": "sponsor",
      "reason": "Sponsor discussion begins with product backstory and continues through the promotional read and closing sponsor thanks"
    }
  ]
}

Return ONLY valid JSON.

Do not use markdown.

Do not use ```json.

Do not include explanations outside the JSON.
"""


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

    chunks = split_transcript(
        transcript_text
    )

    print(
        f"Transcript split into "
        f"{len(chunks)} overlapping detection windows."
    )

    all_segments = []

    for chunk_number, chunk in enumerate(
        chunks,
        start=1
    ):

        print()
        print("-" * 60)

        print(
            f"GROQ WINDOW "
            f"{chunk_number}/{len(chunks)}"
        )

        print(
            f"Characters: {len(chunk)}"
        )

        print(
            "Sending window to Groq..."
        )

        try:

            response = client.chat.completions.create(
                model="openai/gpt-oss-20b",

                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": chunk
                    }
                ],

                max_tokens=700
            )

            content = (
                response
                .choices[0]
                .message
                .content
            )

            if not content:
                raise RuntimeError(
                    "Groq returned an empty response."
                )

            print(
                "Groq response received."
            )

            content = content.strip()

            if content.startswith("```json"):

                content = content[
                    len("```json"):
                ].strip()

                if content.endswith("```"):
                    content = content[
                        :-3
                    ].strip()

            elif content.startswith("```"):

                content = content[
                    len("```"):
                ].strip()

                if content.endswith("```"):
                    content = content[
                        :-3
                    ].strip()

            try:

                result = json.loads(
                    content
                )

            except json.JSONDecodeError as error:

                print(
                    "Groq returned invalid JSON."
                )

                print(
                    f"Raw response: {content}"
                )

                raise RuntimeError(
                    "Groq returned invalid JSON."
                ) from error

            if not isinstance(
                result,
                dict
            ):
                raise RuntimeError(
                    "Groq response was not a JSON object."
                )

            segments = result.get(
                "segments",
                []
            )

            if not isinstance(
                segments,
                list
            ):
                raise RuntimeError(
                    "Groq returned an invalid "
                    "'segments' value."
                )

            valid_segments = []

            for segment in segments:

                if not isinstance(
                    segment,
                    dict
                ):
                    continue

                if (
                    "start" not in segment
                    or "end" not in segment
                ):
                    continue

                try:

                    start = float(
                        segment["start"]
                    )

                    end = float(
                        segment["end"]
                    )

                except (
                    TypeError,
                    ValueError
                ):
                    continue

                if start < 0:
                    continue

                if end <= start:
                    continue

                duration = end - start

                reason = str(
                    segment.get(
                        "reason",
                        ""
                    )
                )

                # Extremely long segments are suspicious.
                # Do not automatically reject them if Groq
                # has identified strong evidence of a genuine
                # continuous sponsor discussion.
                if duration > 300:

                    strong_indicators = [
                        "sponsor",
                        "sponsored",
                        "promotion",
                        "promotional",
                        "advertisement",
                        "product",
                        "discount",
                        "code",
                        "promo",
                        "affiliate",
                        "sign up",
                        "signup",
                        "use my",
                        "call to action",
                        "url",
                        "website"
                    ]

                    reason_lower = reason.lower()

                    has_strong_reason = any(
                        indicator in reason_lower
                        for indicator in strong_indicators
                    )

                    if not has_strong_reason:

                        print(
                            f"Rejected suspiciously long "
                            f"segment: "
                            f"{start:.2f}s -> "
                            f"{end:.2f}s"
                        )

                        continue

                valid_segments.append(
                    {
                        "start": start,
                        "end": end,
                        "label": "sponsor",
                        "reason": reason
                    }
                )

            all_segments.extend(
                valid_segments
            )

            print(
                f"Groq detected "
                f"{len(valid_segments)} sponsor(s) "
                f"in window {chunk_number}."
            )

            for segment in valid_segments:

                duration = (
                    segment["end"]
                    - segment["start"]
                )

                print(
                    f"  Sponsor: "
                    f"{segment['start']:.2f}s -> "
                    f"{segment['end']:.2f}s "
                    f"({duration:.2f}s)"
                )

                if segment["reason"]:

                    print(
                        f"  Reason: "
                        f"{segment['reason']}"
                    )

        except Exception as error:

            print()
            print(
                f"Groq failed on window "
                f"{chunk_number}:"
            )

            print(
                str(error)
            )

            print()

            continue

    all_segments = merge_segments(
        all_segments
    )

    print()
    print("=" * 60)

    print(
        "GROQ DETECTION COMPLETE"
    )

    print(
        f"Total sponsor segments: "
        f"{len(all_segments)}"
    )

    for segment in all_segments:

        duration = (
            segment["end"]
            - segment["start"]
        )

        print(
            f"  FINAL: "
            f"{segment['start']:.2f}s -> "
            f"{segment['end']:.2f}s "
            f"({duration:.2f}s)"
        )

        if segment.get("reason"):

            print(
                f"  Reason: "
                f"{segment['reason']}"
            )

    print("=" * 60)
    print()

    return all_segments


def split_transcript(
    transcript_text: str,
    max_chars: int = 7000,
    overlap_chars: int = 1500
) -> list[str]:

    lines = transcript_text.splitlines()

    chunks = []

    current_chunk = []
    current_length = 0

    for line in lines:

        line_length = len(line) + 1

        if (
            current_chunk
            and current_length + line_length
            > max_chars
        ):

            chunks.append(
                "\n".join(
                    current_chunk
                )
            )

            # Keep the last portion of the previous
            # window as context for the next window.
            overlap_chunk = []
            overlap_length = 0

            for previous_line in reversed(
                current_chunk
            ):

                previous_length = (
                    len(previous_line) + 1
                )

                if (
                    overlap_length
                    + previous_length
                    > overlap_chars
                ):
                    break

                overlap_chunk.insert(
                    0,
                    previous_line
                )

                overlap_length += (
                    previous_length
                )

            current_chunk = overlap_chunk

            current_length = overlap_length

        current_chunk.append(
            line
        )

        current_length += line_length

    if current_chunk:

        chunks.append(
            "\n".join(
                current_chunk
            )
        )

    return chunks


def merge_segments(
    segments: list[dict]
) -> list[dict]:

    if not segments:
        return []

    segments = sorted(
        segments,
        key=lambda segment: segment["start"]
    )

    merged = [
        segments[0]
    ]

    for current in segments[1:]:

        previous = merged[-1]

        # Overlapping windows can cause the same sponsor
        # segment to be detected more than once.
        #
        # Also merge segments that are extremely close
        # together because the model may choose slightly
        # different boundaries in different windows.
        if (
            current["start"]
            <= previous["end"] + 3
        ):

            previous["end"] = max(
                previous["end"],
                current["end"]
            )

            if current.get("reason"):

                if previous.get("reason"):

                    if current["reason"] not in previous["reason"]:

                        previous["reason"] += (
                            f"; {current['reason']}"
                        )

                else:

                    previous["reason"] = (
                        current["reason"]
                    )

        else:

            merged.append(
                current
            )

    return merged