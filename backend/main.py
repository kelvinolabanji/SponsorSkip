from dotenv import load_dotenv

load_dotenv()

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends

from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.ext.asyncio import AsyncSession

from db import init_db, get_session, VideoSegments

from transcript import (
    get_transcript,
    format_for_prompt,
    TranscriptUnavailable
)

from gemini_client import detect_sponsor_segments


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


# Allow the Chrome extension to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Simple endpoint for testing the extension → API connection
@app.get("/test")
async def test():
    return {
        "message": "SponsorSkip API is reachable"
    }


@app.get("/segments/{video_id}")
async def get_segments(
    video_id: str,
    session: AsyncSession = Depends(get_session)
):

    # --------------------------------------------------
    # Check database cache first
    # --------------------------------------------------

    cached = await session.get(
        VideoSegments,
        video_id
    )

    if cached:

        print()
        print("=" * 60)
        print("USING CACHED SPONSOR SEGMENTS")
        print("=" * 60)
        print(f"Video ID: {video_id}")
        print("=" * 60)
        print()

        return {
            "video_id": video_id,
            "segments": cached.segments,
            "cached": True
        }


    # --------------------------------------------------
    # Get YouTube transcript
    # --------------------------------------------------

    try:

        transcript = get_transcript(video_id)

        # Convert transcript into the exact text that
        # will be sent to Gemini.
        transcript_text = format_for_prompt(
            transcript
        )

        # --------------------------------------------------
        # Transcript debug information
        # --------------------------------------------------

        print()
        print("=" * 60)
        print("TRANSCRIPT RETRIEVED SUCCESSFULLY")
        print("=" * 60)

        print(f"Video ID: {video_id}")

        print(
            f"Transcript entries: {len(transcript)}"
        )

        print(
            f"Transcript characters: "
            f"{len(transcript_text)}"
        )

        print()

        print("FIRST 500 CHARACTERS:")
        print("-" * 60)

        print(
            transcript_text[:500]
        )

        print("-" * 60)

        print("=" * 60)
        print()

    except TranscriptUnavailable as e:

        raise HTTPException(
            status_code=422,
            detail=str(e)
        )


    # --------------------------------------------------
    # Send transcript to Gemini
    # --------------------------------------------------

    try:

        segments = detect_sponsor_segments(
            transcript_text
        )

    except Exception as error:

        error_message = str(error)

        # Gemini quota / rate limit
        if (
            "quota" in error_message.lower()
            or "429" in error_message
        ):

            raise HTTPException(
                status_code=429,
                detail=(
                    "Gemini API quota exceeded. "
                    "Please try again later."
                )
            )

        # Let other Gemini errors propagate
        raise


    # --------------------------------------------------
    # Save detected segments to database
    # --------------------------------------------------

    entry = VideoSegments(
        video_id=video_id,
        segments=segments
    )

    session.add(entry)

    await session.commit()


    # --------------------------------------------------
    # Return result
    # --------------------------------------------------

    return {
        "video_id": video_id,
        "segments": segments,
        "cached": False
    }