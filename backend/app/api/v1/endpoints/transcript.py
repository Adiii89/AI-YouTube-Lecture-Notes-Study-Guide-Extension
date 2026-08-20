from typing import List, Optional
from fastapi import APIRouter, Query, status, HTTPException
from app.schemas.transcript import (
    TranscriptRequest,
    TranscriptResponse,
    TranscriptErrorResponse,
)
from app.services.transcript_service import transcript_service
from app.utils.youtube import extract_video_id

router = APIRouter()


@router.post(
    "/extract",
    response_model=TranscriptResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract YouTube Transcript",
    description="Extracts, formats, and calculates timestamps for any valid YouTube video URL or ID.",
    responses={
        400: {"model": TranscriptErrorResponse, "description": "Invalid YouTube URL or Video ID"},
        404: {"model": TranscriptErrorResponse, "description": "Transcript or Video not found / disabled"},
        429: {"model": TranscriptErrorResponse, "description": "YouTube rate limit exceeded"},
        502: {"model": TranscriptErrorResponse, "description": "YouTube upstream communication error"},
    }
)
async def extract_transcript(request: TranscriptRequest) -> TranscriptResponse:
    """
    Extract transcript from a YouTube video URL or ID.
    Supports standard URLs, youtu.be, shorts, embeds, and raw IDs.
    """
    return transcript_service.extract_and_fetch(
        url_or_id=request.url_or_id,
        languages=request.languages,
        preserve_formatting=request.preserve_formatting
    )


@router.get(
    "/parse/id",
    summary="Validate & Parse YouTube URL",
    description="Extracts the clean 11-character video ID from any YouTube URL format without fetching transcript.",
)
async def parse_youtube_id(
    url: str = Query(..., description="YouTube URL to parse")
):
    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract a valid YouTube video ID from the provided URL."
        )
    return {
        "valid": True,
        "video_id": video_id,
        "standard_url": f"https://www.youtube.com/watch?v={video_id}",
        "embed_url": f"https://www.youtube.com/embed/{video_id}"
    }


@router.get(
    "/{video_id}",
    response_model=TranscriptResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Transcript by Video ID",
    description="Fetches the transcript directly for an 11-character YouTube video ID.",
    responses={
        400: {"model": TranscriptErrorResponse, "description": "Invalid Video ID"},
        404: {"model": TranscriptErrorResponse, "description": "Transcript or Video not found"},
    }
)
async def get_transcript_by_id(
    video_id: str,
    lang: Optional[str] = Query(
        default=None,
        description="Comma-separated language codes in priority order (e.g. 'en,es')"
    )
) -> TranscriptResponse:
    """
    Fetch transcript using the direct video ID.
    """
    cleaned_id = extract_video_id(video_id)
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid YouTube video ID format: '{video_id}'. Must be 11 alphanumeric characters."
        )

    languages = [l.strip() for l in lang.split(",") if l.strip()] if lang else None
    return transcript_service.get_transcript(
        video_id=cleaned_id,
        languages=languages
    )
