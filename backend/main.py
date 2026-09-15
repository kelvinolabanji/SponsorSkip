from dotenv import load_dotenv
load_dotenv()
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db import init_db, get_session, VideoSegments
from transcript import get_transcript, format_for_prompt, TranscriptUnavailable
from groq_client import detect_sponsor_segments


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/segments/{video_id}")
async def get_segments(video_id: str, session: AsyncSession = Depends(get_session)):
    cached = await session.get(VideoSegments, video_id)
    if cached:
        return {"video_id": video_id, "segments": cached.segments, "cached": True}

    try:
        transcript = get_transcript(video_id)
    except TranscriptUnavailable:
        raise HTTPException(status_code=422, detail="No transcript available for this video")

    prompt_text = format_for_prompt(transcript)
    segments = detect_sponsor_segments(prompt_text)

    entry = VideoSegments(video_id=video_id, segments=segments)
    session.add(entry)
    await session.commit()

    return {"video_id": video_id, "segments": segments, "cached": False}
