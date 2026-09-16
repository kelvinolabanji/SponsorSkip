from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from db import init_db, get_session, VideoSegments
from transcript import get_transcript, format_for_prompt, TranscriptUnavailable
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
    cached = await session.get(VideoSegments, video_id)

    if cached:
        return {
            "video_id": video_id,
            "segments": cached.segments,
            "cached": True
        }

    try:
        transcript = get_transcript(video_id)

    except TranscriptUnavailable:
        raise HTTPException(
            status_code=422,
            detail="No transcript available for this video"
        )

    prompt_text = format_for_prompt(transcript)

    try:
        segments = detect_sponsor_segments(prompt_text)

    except Exception as error:
        error_message = str(error)

        if "quota" in error_message.lower() or "429" in error_message:
            raise HTTPException(
                status_code=429,
                detail="Gemini API quota exceeded. Please try again later."
            )

        raise

    entry = VideoSegments(
        video_id=video_id,
        segments=segments
    )

    session.add(entry)
    await session.commit()

    return {
        "video_id": video_id,
        "segments": segments,
        "cached": False
    }