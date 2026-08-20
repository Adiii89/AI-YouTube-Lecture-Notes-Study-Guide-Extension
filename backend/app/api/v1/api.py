from fastapi import APIRouter
from app.api.v1.endpoints import health, transcript, notes

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(transcript.router, prefix="/transcript", tags=["Transcript"])
api_router.include_router(notes.router, prefix="/notes", tags=["Lecture Notes"])
