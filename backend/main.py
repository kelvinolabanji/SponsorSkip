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

from sponsor_detector import detect_sponsor_segments


# --------------------------------------------------
# Application lifespan
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    await init_db()

    yield


app = FastAPI(
    lifespan=lifespan
)


# --------------------------------------------------
# CORS
# --------------------------------------------------

# Allow the Chrome extension to communicate
# with the API.

app.add_middleware(
    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# --------------------------------------------------
# Test endpoint
# --------------------------------------------------

@app.get("/test")
async def test():

    return {
        "message": "SponsorSkip API is reachable"
    }


# --------------------------------------------------
# Sponsor segments endpoint
# --------------------------------------------------

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

        print(
            f"Video ID: {video_id}"
        )

        print(
            f"Segments: {cached.segments}"
        )

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

        transcript = get_transcript(
            video_id
        )

        # Convert transcript into the timestamped
        # text that will be sent to Groq.

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

        print(
            f"Video ID: {video_id}"
        )

        print(
            f"Transcript entries: "
            f"{len(transcript)}"
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
    # Send transcript to Groq
    # --------------------------------------------------

    print()

    print("#" * 60)
    print("STARTING SPONSOR DETECTION")
    print("#" * 60)

    try:

        segments = detect_sponsor_segments(
            transcript_text
        )

    except Exception as error:

        print()

        print("=" * 60)
        print("SPONSOR DETECTION FAILED")
        print("=" * 60)

        print(
            str(error)
        )

        print("=" * 60)

        print()

        raise HTTPException(
            status_code=502,
            detail=(
                "Sponsor detection service failed."
            )
        )


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