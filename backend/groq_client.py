import os
import json

from groq import Groq


# --------------------------------------------------
# Groq client
# --------------------------------------------------

client = Groq(
    api_key=os.environ["GROQ_API_KEY"]
)


# --------------------------------------------------
# Sponsor detection prompt
# --------------------------------------------------

SYSTEM_PROMPT = """
You are a highly accurate YouTube sponsor-segment detection system.

Your job is NOT simply to find mentions of companies or sponsors.

Your job is to identify the ACTUAL CONTIGUOUS PROMOTIONAL SEGMENT
that a viewer would reasonably want to skip.

============================================================
IMPORTANT DISTINCTION
============================================================

There are THREE different things you may encounter:

1. SPONSOR MENTION

A casual mention of a company, product, or service.

Example:
"I use PrizePicks sometimes."

This is NOT a sponsor segment.

------------------------------------------------------------

2. SPONSOR DISCLOSURE

A short disclosure telling the viewer that the video has a sponsor.

Examples:

"This video is sponsored by PrizePicks."

"This video is presented by PrizePicks."

"Thanks to PrizePicks for sponsoring today's video."

A disclosure by itself is NOT the sponsor segment.

DO NOT start a sponsor segment at the disclosure timestamp
unless the actual promotional content begins there and continues
as a genuine advertisement.

For example:

[00:11] This video is presented by PrizePicks.
[00:14] Anyway, let's get into today's video.
[00:20] Today we're talking about...

DO NOT return:

start = 11

------------------------------------------------------------

3. ACTUAL SPONSOR SEGMENT

This is a contiguous portion of the video where the creator
actively promotes the sponsor.

Examples include:

- explaining the sponsor's product or service
- explaining how the product works
- explaining why viewers should use it
- giving a discount code
- giving an affiliate code
- directing viewers to a sponsor URL
- giving a promotional call to action
- describing sponsor features or benefits
- encouraging viewers to sign up, download, purchase, or use
  the sponsor's service

Example:

[05:01] Now let's talk about today's sponsor, PrizePicks.
[05:08] PrizePicks is a daily fantasy sports platform...
[05:20] You can pick players...
[05:35] Use my code KELVIN...
[05:48] Go to prizepicks.com...
[06:02] Anyway, let's get back to the video.

This IS an actual sponsor segment.

The correct result would be approximately:

start = 301
end = 362

NOT:

start = 11
end = 362

============================================================
CORE RULE
============================================================

ONLY return a segment when there is a genuine CONTIGUOUS
PROMOTIONAL BLOCK.

Do not turn isolated sponsor mentions into sponsor segments.

Do not connect a sponsor disclosure to a later sponsor segment
just because they mention the same company.

============================================================
START TIMESTAMP
============================================================

The START must be the timestamp where the ACTUAL PROMOTIONAL
CONTENT begins.

Do NOT use:

- an earlier sponsor disclosure
- an earlier company mention
- an earlier casual product mention
- the beginning of the video
- a title/introduction mentioning the sponsor

If the creator says:

[00:11] This video is presented by PrizePicks.
[00:13] Now let's talk about basketball.
...
[05:01] Let's talk about PrizePicks.
[05:08] PrizePicks lets you...

START = 05:01

NOT 00:11.

============================================================
END TIMESTAMP
============================================================

The END must be where the creator finishes the promotional
content and returns to normal video content.

Look for transitions such as:

- "Anyway, back to the video."
- "Now let's continue."
- "Let's get back to..."
- returning directly to the normal topic
- clearly ending the advertisement

Do not extend the sponsor segment into unrelated content.

============================================================
SHORT MENTIONS
============================================================

Do NOT skip very short mentions merely because they contain
a sponsor or company name.

For example:

[02:10] We are sponsored by X.

This alone should generally NOT become a skippable segment.

Similarly:

[02:10] I use X all the time.

This is NOT a sponsor segment.

A short segment should only be considered a sponsor if there is
strong evidence of actual promotional activity, such as:

- discount code
- affiliate code
- URL
- call to action
- explicit product promotion
- sign-up instructions
- purchase instructions

Duration alone must NOT determine whether something is a sponsor.

============================================================
LONG SEGMENTS
============================================================

Be suspicious of extremely long sponsor segments.

Do NOT assume:

"Company mentioned at 00:10"
+
"company promoted at 05:00"

means:

00:10 -> 05:00

The sponsor segment should normally be the contiguous promotional
block around the actual advertisement.

If there is normal content between two sponsor mentions,
they are separate events.

============================================================
WHAT TO FLAG
============================================================

FLAG genuine:

- paid sponsor reads
- dedicated advertisements
- affiliate promotions
- discount codes
- promotional URLs
- sponsor product explanations
- sponsor calls to action
- creator promotions of products/services
- merch promotions
- Patreon promotions
- membership promotions

============================================================
WHAT NOT TO FLAG
============================================================

DO NOT FLAG:

- casual product mentions
- normal discussion of products
- news about a company
- a company being used as an example
- normal recommendations
- products naturally appearing in the content
- sponsor disclosures by themselves
- "this video is sponsored by..." by itself
- normal "like and subscribe"
- normal introductions
- normal conclusions
- normal discussion surrounding the sponsor

============================================================
TIMESTAMP ACCURACY
============================================================

The transcript uses:

[MM:SS] text

Use the timestamps directly.

The start and end should correspond as closely as possible
to the actual promotional block.

Do not invent timestamps.

============================================================
OUTPUT
============================================================

If there are NO genuine sponsor segments:

{
  "segments": []
}

If there is a genuine sponsor segment:

{
  "segments": [
    {
      "start": 301.0,
      "end": 362.0,
      "label": "sponsor",
      "reason": "Dedicated promotional read containing product information and a call to action"
    }
  ]
}

The "reason" should briefly explain why this is an actual
promotional segment.

Return ONLY valid JSON.

Do not use markdown.

Do not use ```json.

Do not include explanations outside the JSON.
"""


# --------------------------------------------------
# Sponsor detection
# --------------------------------------------------

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

    # --------------------------------------------------
    # Split transcript into windows
    # --------------------------------------------------

    chunks = split_transcript(
        transcript_text
    )

    print(
        f"Transcript split into "
        f"{len(chunks)} detection windows."
    )

    all_segments = []

    # --------------------------------------------------
    # Analyze each window
    # --------------------------------------------------

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

            # --------------------------------------------------
            # Get response
            # --------------------------------------------------

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

            # --------------------------------------------------
            # Clean response
            # --------------------------------------------------

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

            # --------------------------------------------------
            # Parse JSON
            # --------------------------------------------------

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

            # --------------------------------------------------
            # Validate top-level response
            # --------------------------------------------------

            if not isinstance(
                result,
                dict
            ):

                raise RuntimeError(
                    "Groq response was not a JSON object."
                )

            # --------------------------------------------------
            # Extract segments
            # --------------------------------------------------

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

            # --------------------------------------------------
            # Validate segments
            # --------------------------------------------------

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

                # --------------------------------------------------
                # Basic timestamp validation
                # --------------------------------------------------

                if start < 0:
                    continue

                if end <= start:
                    continue

                duration = end - start

                # --------------------------------------------------
                # Reject suspiciously large segments
                #
                # This protects us from exactly the problem we
                # just encountered:
                #
                # 11s -> 365s
                #
                # when the actual ad was much later.
                #
                # We don't automatically reject every long ad,
                # but anything above 5 minutes requires stronger
                # evidence from the model.
                # --------------------------------------------------

                reason = str(
                    segment.get(
                        "reason",
                        ""
                    )
                )

                if duration > 300:

                    strong_indicators = [
                        "discount",
                        "code",
                        "promo",
                        "promotion",
                        "sponsor",
                        "sponsored",
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

                # --------------------------------------------------
                # Store validated segment
                # --------------------------------------------------

                valid_segments.append(
                    {
                        "start": start,
                        "end": end,
                        "label": "sponsor",
                        "reason": reason
                    }
                )

            # --------------------------------------------------
            # Store results
            # --------------------------------------------------

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

            # Never fabricate sponsor results.

            continue

    # --------------------------------------------------
    # Merge duplicate / overlapping segments
    # --------------------------------------------------

    all_segments = merge_segments(
        all_segments
    )

    # --------------------------------------------------
    # Final result
    # --------------------------------------------------

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


# --------------------------------------------------
# Split transcript into windows
# --------------------------------------------------

def split_transcript(
    transcript_text: str,
    max_chars: int = 7000
) -> list[str]:

    lines = transcript_text.splitlines()

    chunks = []

    current_chunk = []

    current_length = 0

    for line in lines:

        line_length = len(line)

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

            current_chunk = []

            current_length = 0

        current_chunk.append(
            line
        )

        current_length += line_length

    # --------------------------------------------------
    # Add final window
    # --------------------------------------------------

    if current_chunk:

        chunks.append(
            "\n".join(
                current_chunk
            )
        )

    return chunks


# --------------------------------------------------
# Merge duplicate / overlapping segments
# --------------------------------------------------

def merge_segments(
    segments: list[dict]
) -> list[dict]:

    if not segments:
        return []

    # --------------------------------------------------
    # Sort chronologically
    # --------------------------------------------------

    segments = sorted(
        segments,
        key=lambda segment: segment["start"]
    )

    merged = [
        segments[0]
    ]

    # --------------------------------------------------
    # Merge overlapping / nearly adjacent segments
    # --------------------------------------------------

    for current in segments[1:]:

        previous = merged[-1]

        if (
            current["start"]
            <= previous["end"] + 2
        ):

            previous["end"] = max(
                previous["end"],
                current["end"]
            )

            # Preserve a useful reason.

            if (
                not previous.get("reason")
                and current.get("reason")
            ):

                previous["reason"] = (
                    current["reason"]
                )

        else:

            merged.append(
                current
            )

    return merged