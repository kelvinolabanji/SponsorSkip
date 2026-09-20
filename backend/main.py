"""FastAPI application for SponsorSkip."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session, init_db
from logging_config import configure_logging
from segment_service import SegmentDetectionFailed, get_or_detect_segments
from transcript import TranscriptUnavailable

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)

# Allow the Chrome extension to communicate with the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/test")
async def test():
    return {"message": "SponsorSkip API is reachable"}


@app.get("/segments/{video_id}")
async def get_segments(video_id: str, session: AsyncSession = Depends(get_session)):
    try:
        segments, cached = await get_or_detect_segments(video_id, session)
    except TranscriptUnavailable as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except SegmentDetectionFailed as error:
        raise HTTPException(
            status_code=502, detail="Sponsor detection service failed."
        ) from error

    return {"video_id": video_id, "segments": segments, "cached": cached}
