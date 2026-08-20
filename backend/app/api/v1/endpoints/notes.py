from fastapi import APIRouter, status
from app.schemas.notes import (
    NotesGenerationRequest,
    NotesGenerationResponse,
    TemplatesResponse,
    VideoChatRequest,
    VideoChatResponse,
)
from app.schemas.transcript import TranscriptErrorResponse
from app.services.notes_service import notes_service

router = APIRouter()


@router.get(
    "/templates",
    response_model=TemplatesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Available Note Templates",
    description="Returns the list of supported lecture note structures (Comprehensive, Cornell, Summary, Flashcards, Action Items) with descriptions."
)
async def get_templates() -> TemplatesResponse:
    """List all supported note-taking formats and styles."""
    return notes_service.get_templates()


@router.post(
    "/generate",
    response_model=NotesGenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate AI Lecture Notes",
    description="Generates AI lecture notes and summaries from a YouTube video URL, ID, or raw transcript.",
    responses={
        400: {"model": TranscriptErrorResponse, "description": "Invalid input or missing transcript/URL"},
        404: {"model": TranscriptErrorResponse, "description": "YouTube video or transcript not found"},
        502: {"model": TranscriptErrorResponse, "description": "Upstream AI service error"},
        503: {"model": TranscriptErrorResponse, "description": "AI API key is not configured"},
    }
)
async def generate_notes(request: NotesGenerationRequest) -> NotesGenerationResponse:
    """
    Generate study materials using OpenAI or Google Gemini.
    Accepts either `url_or_id` to automatically extract the transcript, or direct `transcript_text`.
    """
    return notes_service.generate_notes(request)


@router.post(
    "/chat",
    response_model=VideoChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat with Video Transcript (Ask the Video)",
    description="Interactive Q&A assistant grounded in the video's transcript with timestamp citations.",
    responses={
        400: {"model": TranscriptErrorResponse, "description": "Invalid input or missing question"},
        404: {"model": TranscriptErrorResponse, "description": "YouTube video or transcript not found"},
        502: {"model": TranscriptErrorResponse, "description": "Upstream AI service error"},
        503: {"model": TranscriptErrorResponse, "description": "AI API key is not configured"},
    }
)
async def chat_with_video(request: VideoChatRequest) -> VideoChatResponse:
    """
    Ask any question about the video lecture and receive a grounded explanation with timestamp citations.
    """
    return notes_service.chat_with_video(request)
