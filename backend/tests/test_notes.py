import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi import status
from starlette.testclient import TestClient

from app.core.config import settings
from app.schemas.notes import (
    NoteFormat,
    NotesGenerationRequest,
    VideoChatRequest,
    ChatMessage,
)
from app.schemas.transcript import TranscriptResponse, TranscriptSegment
from app.services.notes_service import NotesService, notes_service
from app.services.prompts import (
    build_notes_prompt,
    build_chat_prompt,
    format_transcript_with_timestamps,
)


# ==========================================
# 1. Prompt & Template Tests
# ==========================================

def test_format_transcript_with_timestamps():
    segments = [
        {"text": "Intro to AI", "timestamp_str": "00:00"},
        {"text": "Deep Learning basics", "timestamp_str": "01:30"},
    ]
    result = format_transcript_with_timestamps(segments)
    assert "[00:00] Intro to AI" in result
    assert "[01:30] Deep Learning basics" in result


def test_build_notes_prompt_formats():
    for fmt in NoteFormat:
        prompt = build_notes_prompt(
            transcript_text="Sample transcript text",
            note_format=fmt,
            custom_instructions="Focus on theory",
            target_language="en"
        )
        assert "Sample transcript text" in prompt
        assert "Focus on theory" in prompt


def test_build_chat_prompt():
    messages = build_chat_prompt(
        transcript_text="[02:15] Backprop is introduced.",
        question="Can you explain backprop?",
        chat_history=[ChatMessage(role="user", content="Hi"), ChatMessage(role="assistant", content="Hello!")]
    )
    assert len(messages) == 4
    assert messages[0]["role"] == "system"
    assert "[02:15] Backprop" in messages[0]["content"]
    assert messages[-1]["content"] == "Can you explain backprop?"


def test_get_templates_endpoint(client: TestClient):
    response = client.get(f"{settings.API_V1_STR}/notes/templates")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "templates" in data
    template_ids = [t["id"] for t in data["templates"]]
    assert "comprehensive" in template_ids
    assert "cornell" in template_ids
    assert "summary" in template_ids
    assert "flashcards" in template_ids
    assert "action_items" in template_ids


# ==========================================
# 2. NotesService Unit & Integration Tests
# ==========================================

MOCK_COMPREHENSIVE_RESPONSE = {
    "title": "Machine Learning Foundations",
    "executive_summary": "An introduction to machine learning principles and neural network architectures.",
    "key_takeaways": [
        "Supervised learning trains models on labeled inputs.",
        "Backpropagation optimizes network weights.",
        "Regularization prevents overfitting."
    ],
    "sections": [
        {
            "heading": "Neural Network Basics",
            "timestamp_str": "02:15",
            "summary": "Explains perceptual layers and non-linear activations.",
            "key_points": [
                "Layers are composed of interconnected nodes.",
                "ReLU activation prevents gradient vanishing."
            ]
        }
    ],
    "flashcards": [
        {
            "question": "What is the purpose of backpropagation?",
            "answer": "To calculate the gradient of the loss function with respect to weights.",
            "timestamp_cue": "05:10",
            "difficulty": "medium"
        }
    ],
    "markdown_content": "# Machine Learning Foundations\n\n## Executive Summary\nAn introduction to machine learning.\n\n## Key Takeaways\n- Supervised learning.\n"
}


MOCK_CORNELL_RESPONSE = {
    "title": "Calculus for Deep Learning",
    "executive_summary": "Covers partial derivatives and the chain rule.",
    "key_takeaways": ["Chain rule enables backprop", "Gradients guide optimization"],
    "sections": [
        {
            "heading": "The Chain Rule",
            "timestamp_str": "03:45",
            "summary": "Mathematical formulation of composite derivatives.",
            "key_points": ["d/dx [f(g(x))] = f'(g(x)) * g'(x)"]
        }
    ],
    "cornell_notes": [
        {
            "cue": "What is the Chain Rule?",
            "note": "A formula for computing the derivative of the composite of two or more functions.",
            "timestamp_str": "03:45"
        }
    ],
    "flashcards": [],
    "markdown_content": "# Calculus Cornell Notes\n\n| Cue | Note | Time |\n| --- | --- | --- |\n| Chain Rule | Formula | 03:45 |"
}


def test_generate_notes_missing_inputs(client: TestClient):
    with patch.object(settings, "OPENAI_API_KEY", "test-key"):
        response = client.post(
            f"{settings.API_V1_STR}/notes/generate",
            json={"note_format": "comprehensive"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_generate_notes_missing_openai_key():
    service = NotesService()
    with patch.object(settings, "OPENAI_API_KEY", None), \
         patch.object(settings, "LLM_PROVIDER", "openai"):
        with pytest.raises(Exception) as exc_info:
            service.generate_notes(
                NotesGenerationRequest(
                    transcript_text="Some text",
                    note_format=NoteFormat.COMPREHENSIVE,
                    provider="openai"
                )
            )
        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "OPENAI_API_KEY is not configured" in exc_info.value.detail


def test_generate_notes_missing_gemini_key():
    service = NotesService()
    with patch.object(settings, "GEMINI_API_KEY", None), \
         patch.object(settings, "LLM_PROVIDER", "gemini"):
        with pytest.raises(Exception) as exc_info:
            service.generate_notes(
                NotesGenerationRequest(
                    transcript_text="Some text",
                    note_format=NoteFormat.COMPREHENSIVE,
                    provider="gemini"
                )
            )
        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "GEMINI_API_KEY is not configured" in exc_info.value.detail


def test_generate_notes_with_openai_success(client: TestClient):
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(MOCK_COMPREHENSIVE_RESPONSE)
    mock_chat_completion = MagicMock()
    mock_chat_completion.choices = [mock_choice]

    with patch.object(settings, "OPENAI_API_KEY", "test-openai-key"), \
         patch("openai.resources.chat.completions.Completions.create", return_value=mock_chat_completion):

        response = client.post(
            f"{settings.API_V1_STR}/notes/generate",
            json={
                "transcript_text": "Hello and welcome to machine learning tutorial.",
                "note_format": "comprehensive",
                "provider": "openai"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["provider"] == "openai"
        assert data["title"] == "Machine Learning Foundations"
        assert len(data["key_takeaways"]) == 3
        assert len(data["sections"]) == 1
        assert data["sections"][0]["timestamp_str"] == "02:15"
        assert len(data["flashcards"]) == 1


def test_generate_notes_with_gemini_success(client: TestClient):
    with patch.object(settings, "GEMINI_API_KEY", "test-gemini-key"), \
         patch.object(notes_service, "_call_gemini", return_value=json.dumps(MOCK_COMPREHENSIVE_RESPONSE)):

        response = client.post(
            f"{settings.API_V1_STR}/notes/generate",
            json={
                "transcript_text": "Hello and welcome to machine learning tutorial.",
                "note_format": "comprehensive",
                "provider": "gemini"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["provider"] == "gemini"
        assert data["title"] == "Machine Learning Foundations"


def test_generate_notes_cornell_format_with_openai(client: TestClient):
    with patch.object(settings, "OPENAI_API_KEY", "test-openai-key"), \
         patch.object(notes_service, "_call_openai", return_value=json.dumps(MOCK_CORNELL_RESPONSE)):

        response = client.post(
            f"{settings.API_V1_STR}/notes/generate",
            json={
                "transcript_text": "Derivatives and chain rule explanation.",
                "note_format": "cornell",
                "provider": "openai"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["note_format"] == "cornell"
        assert data["cornell_notes"] is not None
        assert len(data["cornell_notes"]) == 1
        assert data["cornell_notes"][0]["cue"] == "What is the Chain Rule?"


def test_generate_notes_from_youtube_url(client: TestClient):
    mock_transcript_resp = TranscriptResponse(
        video_id="dQw4w9WgXcQ",
        language="English",
        language_code="en",
        is_generated=False,
        is_translatable=True,
        total_duration_seconds=180.0,
        total_duration_str="03:00",
        word_count=50,
        segment_count=2,
        segments=[
            TranscriptSegment(text="Welcome to the lecture.", start=0.0, duration=2.0, timestamp_str="00:00"),
            TranscriptSegment(text="Today we study AI.", start=2.0, duration=3.0, timestamp_str="00:02")
        ],
        full_text="Welcome to the lecture. Today we study AI."
    )

    with patch.object(settings, "OPENAI_API_KEY", "test-openai-key"), \
         patch("app.services.transcript_service.transcript_service.extract_and_fetch", return_value=mock_transcript_resp), \
         patch.object(notes_service, "_call_openai", return_value=json.dumps(MOCK_COMPREHENSIVE_RESPONSE)):

        response = client.post(
            f"{settings.API_V1_STR}/notes/generate",
            json={
                "url_or_id": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "note_format": "comprehensive",
                "provider": "openai"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["video_id"] == "dQw4w9WgXcQ"
        assert data["provider"] == "openai"
        assert data["title"] == "Machine Learning Foundations"
        assert data["total_duration_str"] == "03:00"


# ==========================================
# 3. Interactive Video Chat Tests
# ==========================================

def test_chat_with_video_openai_success(client: TestClient):
    mock_choice = MagicMock()
    mock_choice.message.content = "At [03:45], the instructor explains how the chain rule propagates gradients."
    mock_chat_completion = MagicMock()
    mock_chat_completion.choices = [mock_choice]

    with patch.object(settings, "OPENAI_API_KEY", "test-openai-key"), \
         patch("openai.resources.chat.completions.Completions.create", return_value=mock_chat_completion):

        response = client.post(
            f"{settings.API_V1_STR}/notes/chat",
            json={
                "transcript_text": "[03:45] The chain rule propagates derivatives.",
                "question": "Where is the chain rule discussed?",
                "provider": "openai"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["provider"] == "openai"
        assert "chain rule propagates gradients" in data["answer"]
        assert "03:45" in data["timestamp_citations"]


def test_chat_with_video_gemini_success(client: TestClient):
    with patch.object(settings, "GEMINI_API_KEY", "test-gemini-key"), \
         patch.object(notes_service, "_chat_gemini", return_value="At [01:20] and [04:50] neural layers are broken down."):

        response = client.post(
            f"{settings.API_V1_STR}/notes/chat",
            json={
                "transcript_text": "[01:20] Neural layers. [04:50] Activation functions.",
                "question": "What parts discuss layers?",
                "provider": "gemini"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["provider"] == "gemini"
        assert len(data["timestamp_citations"]) == 2
        assert "01:20" in data["timestamp_citations"]
        assert "04:50" in data["timestamp_citations"]
