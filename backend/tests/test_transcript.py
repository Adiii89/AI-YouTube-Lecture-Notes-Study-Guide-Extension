from unittest.mock import MagicMock, patch
import pytest
from fastapi import status
from starlette.testclient import TestClient
from youtube_transcript_api import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    RequestBlocked,
)
from youtube_transcript_api._transcripts import FetchedTranscript, FetchedTranscriptSnippet

from app.core.config import settings
from app.utils.youtube import extract_video_id, format_timestamp
from app.services.transcript_service import TranscriptService, transcript_service


# ==========================================
# 1. YouTube Utility Tests
# ==========================================

def test_extract_video_id_valid_urls():
    test_cases = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("http://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120s&list=PL123", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ?t=45", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/v/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ]
    for url, expected_id in test_cases:
        assert extract_video_id(url) == expected_id, f"Failed for {url}"


def test_extract_video_id_invalid():
    invalid_cases = [
        "",
        "   ",
        "https://example.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch",
        "https://www.youtube.com/watch?v=short",
        "https://www.youtube.com/watch?v=toolongvideoid12345",
        "invalid_id",
    ]
    for case in invalid_cases:
        assert extract_video_id(case) is None, f"Expected None for {case}"


def test_format_timestamp():
    assert format_timestamp(0) == "00:00"
    assert format_timestamp(45.2) == "00:45"
    assert format_timestamp(75.9) == "01:15"
    assert format_timestamp(599) == "09:59"
    assert format_timestamp(600) == "10:00"
    assert format_timestamp(3600) == "01:00:00"
    assert format_timestamp(3665.4) == "01:01:05"


# ==========================================
# 2. TranscriptService Unit Tests (Mocked)
# ==========================================

def create_mock_fetched():
    return FetchedTranscript(
        snippets=[
            FetchedTranscriptSnippet(text="Hello and welcome", start=0.0, duration=2.5),
            FetchedTranscriptSnippet(text="to this tutorial on machine learning", start=2.5, duration=3.0),
            FetchedTranscriptSnippet(text="today we will cover neural networks", start=5.5, duration=4.0),
        ],
        video_id="dQw4w9WgXcQ",
        language="English",
        language_code="en",
        is_generated=False
    )


def test_transcript_service_successful_fetch():
    service = TranscriptService()

    mock_transcript = MagicMock()
    mock_transcript.fetch.return_value = create_mock_fetched()
    mock_transcript.language = "English"
    mock_transcript.language_code = "en"
    mock_transcript.is_generated = False
    mock_transcript.is_translatable = True

    mock_transcript_list = MagicMock()
    mock_transcript_list.find_transcript.return_value = mock_transcript

    with patch.object(service.api, "list", return_value=mock_transcript_list):
        result = service.get_transcript("dQw4w9WgXcQ")

        assert result.video_id == "dQw4w9WgXcQ"
        assert result.language == "English"
        assert result.language_code == "en"
        assert not result.is_generated
        assert result.segment_count == 3
        assert result.word_count == 15
        assert result.total_duration_seconds == 9.5
        assert result.total_duration_str == "00:09"
        assert result.segments[0].timestamp_str == "00:00"
        assert result.segments[1].timestamp_str == "00:02"
        assert "Hello and welcome to this tutorial on machine learning" in result.full_text


def test_transcript_service_disabled_transcripts():
    service = TranscriptService()

    with patch.object(service.api, "list", side_effect=TranscriptsDisabled("dQw4w9WgXcQ")):
        with pytest.raises(Exception) as exc_info:
            service.get_transcript("dQw4w9WgXcQ")
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "disabled" in exc_info.value.detail.lower()


def test_transcript_service_video_unavailable():
    service = TranscriptService()

    with patch.object(service.api, "list", side_effect=VideoUnavailable("dQw4w9WgXcQ")):
        with pytest.raises(Exception) as exc_info:
            service.get_transcript("dQw4w9WgXcQ")
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "unavailable" in exc_info.value.detail.lower()


def test_transcript_service_rate_limit():
    service = TranscriptService()

    with patch.object(service.api, "list", side_effect=RequestBlocked("dQw4w9WgXcQ")):
        with pytest.raises(Exception) as exc_info:
            service.get_transcript("dQw4w9WgXcQ")
        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS


# ==========================================
# 3. API Integration Tests
# ==========================================

def test_parse_youtube_id_endpoint_success(client: TestClient):
    response = client.get(
        f"{settings.API_V1_STR}/transcript/parse/id",
        params={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["valid"] is True
    assert data["video_id"] == "dQw4w9WgXcQ"
    assert "https://www.youtube.com/watch?v=dQw4w9WgXcQ" in data["standard_url"]


def test_parse_youtube_id_endpoint_invalid(client: TestClient):
    response = client.get(
        f"{settings.API_V1_STR}/transcript/parse/id",
        params={"url": "not_a_valid_url"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_extract_transcript_endpoint_invalid_url(client: TestClient):
    response = client.post(
        f"{settings.API_V1_STR}/transcript/extract",
        json={"url_or_id": "invalid_url_string"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_extract_transcript_endpoint_success(client: TestClient):
    mock_transcript = MagicMock()
    mock_transcript.fetch.return_value = create_mock_fetched()
    mock_transcript.language = "English"
    mock_transcript.language_code = "en"
    mock_transcript.is_generated = False
    mock_transcript.is_translatable = True

    mock_transcript_list = MagicMock()
    mock_transcript_list.find_transcript.return_value = mock_transcript

    with patch.object(transcript_service.api, "list", return_value=mock_transcript_list):
        response = client.post(
            f"{settings.API_V1_STR}/transcript/extract",
            json={"url_or_id": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["video_id"] == "dQw4w9WgXcQ"
        assert data["segment_count"] == 3
        assert len(data["segments"]) == 3
        assert data["segments"][0]["text"] == "Hello and welcome"
        assert data["word_count"] > 0


def test_get_transcript_by_id_endpoint(client: TestClient):
    mock_transcript = MagicMock()
    mock_transcript.fetch.return_value = create_mock_fetched()
    mock_transcript.language = "English"
    mock_transcript.language_code = "en"
    mock_transcript.is_generated = False
    mock_transcript.is_translatable = True

    mock_transcript_list = MagicMock()
    mock_transcript_list.find_transcript.return_value = mock_transcript

    with patch.object(transcript_service.api, "list", return_value=mock_transcript_list):
        response = client.get(f"{settings.API_V1_STR}/transcript/dQw4w9WgXcQ")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["video_id"] == "dQw4w9WgXcQ"
        assert data["language_code"] == "en"


def test_get_transcript_by_id_invalid_length(client: TestClient):
    response = client.get(f"{settings.API_V1_STR}/transcript/short_id")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
