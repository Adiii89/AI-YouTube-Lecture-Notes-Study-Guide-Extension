import logging
from typing import List, Optional
from fastapi import HTTPException, status
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    VideoUnplayable,
    AgeRestricted,
    IpBlocked,
    RequestBlocked,
    YouTubeRequestFailed,
    YouTubeTranscriptApiException,
)

from app.schemas.transcript import TranscriptResponse, TranscriptSegment
from app.utils.youtube import format_timestamp, extract_video_id

logger = logging.getLogger(__name__)


class TranscriptService:
    """Service for fetching, selecting, and processing YouTube video transcripts."""

    def __init__(self, default_languages: Optional[List[str]] = None):
        self.default_languages = default_languages or ["en", "en-US", "en-GB"]
        self.api = YouTubeTranscriptApi()

    def extract_and_fetch(
        self,
        url_or_id: str,
        languages: Optional[List[str]] = None,
        preserve_formatting: bool = False
    ) -> TranscriptResponse:
        """
        Validate URL/ID and fetch the transcript.
        """
        video_id = extract_video_id(url_or_id)
        if not video_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid YouTube URL or video ID: '{url_or_id}'"
            )

        return self.get_transcript(
            video_id=video_id,
            languages=languages or self.default_languages,
            preserve_formatting=preserve_formatting
        )

    def get_transcript(
        self,
        video_id: str,
        languages: Optional[List[str]] = None,
        preserve_formatting: bool = False
    ) -> TranscriptResponse:
        """
        Fetch transcript for a given 11-char video ID, with language fallback.
        """
        target_languages = languages or self.default_languages

        try:
            transcript_list = self.api.list(video_id)
            transcript = None

            # 1. Try to find user's requested languages directly
            try:
                transcript = transcript_list.find_transcript(target_languages)
            except NoTranscriptFound:
                pass

            # 2. If not found, try to find manually created transcript in any language
            if transcript is None:
                try:
                    available_codes = [t.language_code for t in transcript_list]
                    if available_codes:
                        transcript = transcript_list.find_manually_created_transcript(available_codes)
                except Exception:
                    pass

            # 3. If still not found, try any available generated transcript
            if transcript is None:
                try:
                    for t in transcript_list:
                        transcript = t
                        break
                except Exception:
                    pass

            # 4. If found but not in target languages, attempt translation
            if transcript and target_languages and transcript.language_code not in target_languages:
                if getattr(transcript, "is_translatable", False):
                    target_lang = target_languages[0]
                    try:
                        transcript = transcript.translate(target_lang)
                    except Exception as trans_err:
                        logger.warning(
                            f"Failed to translate transcript to {target_lang}: {trans_err}. Using original language."
                        )

            if transcript is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No available transcript found for video '{video_id}' in requested languages ({target_languages})."
                )

            # Fetch transcript dataclass
            fetched = transcript.fetch(preserve_formatting=preserve_formatting)
            raw_data = fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else list(fetched)
            language_name = getattr(fetched, "language", getattr(transcript, "language", "Unknown"))
            language_code = getattr(fetched, "language_code", getattr(transcript, "language_code", "en"))
            is_generated = getattr(fetched, "is_generated", getattr(transcript, "is_generated", False))
            is_translatable = getattr(transcript, "is_translatable", False)

        except (
            TranscriptsDisabled,
            NoTranscriptFound,
            VideoUnavailable,
            VideoUnplayable,
            AgeRestricted,
            IpBlocked,
            RequestBlocked,
            YouTubeRequestFailed,
            YouTubeTranscriptApiException,
        ) as yt_err:
            self._handle_youtube_exception(yt_err, video_id)
        except HTTPException:
            raise
        except Exception as e:
            # Fallback to direct fetch call if list had unexpected issue
            try:
                fetched = self.api.fetch(
                    video_id,
                    languages=target_languages,
                    preserve_formatting=preserve_formatting
                )
                raw_data = fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else list(fetched)
                language_name = getattr(fetched, "language", "English")
                language_code = getattr(fetched, "language_code", target_languages[0] if target_languages else "en")
                is_generated = getattr(fetched, "is_generated", False)
                is_translatable = True
            except Exception as fallback_err:
                logger.error(f"Error fetching transcript for {video_id}: {fallback_err}")
                self._handle_youtube_exception(fallback_err, video_id)

        # Process segments & build response
        return self._build_transcript_response(
            video_id=video_id,
            raw_segments=raw_data,
            language=language_name,
            language_code=language_code,
            is_generated=is_generated,
            is_translatable=is_translatable
        )

    def _build_transcript_response(
        self,
        video_id: str,
        raw_segments: List[dict],
        language: str,
        language_code: str,
        is_generated: bool,
        is_translatable: bool
    ) -> TranscriptResponse:
        segments: List[TranscriptSegment] = []
        text_parts: List[str] = []
        max_end_time = 0.0

        for item in raw_segments:
            # item can be dict or object with text/start/duration
            seg_text = item.get("text", "") if isinstance(item, dict) else getattr(item, "text", "")
            cleaned_text = " ".join(seg_text.split())
            if not cleaned_text:
                continue

            start = float(item.get("start", 0.0) if isinstance(item, dict) else getattr(item, "start", 0.0))
            duration = float(item.get("duration", 0.0) if isinstance(item, dict) else getattr(item, "duration", 0.0))
            end_time = start + duration
            if end_time > max_end_time:
                max_end_time = end_time

            segments.append(
                TranscriptSegment(
                    text=cleaned_text,
                    start=round(start, 2),
                    duration=round(duration, 2),
                    timestamp_str=format_timestamp(start)
                )
            )
            text_parts.append(cleaned_text)

        full_text = " ".join(text_parts)
        word_count = len(full_text.split()) if full_text else 0

        return TranscriptResponse(
            video_id=video_id,
            language=language,
            language_code=language_code,
            is_generated=is_generated,
            is_translatable=is_translatable,
            total_duration_seconds=round(max_end_time, 2),
            total_duration_str=format_timestamp(max_end_time),
            word_count=word_count,
            segment_count=len(segments),
            segments=segments,
            full_text=full_text
        )

    def _handle_youtube_exception(self, err: Exception, video_id: str):
        if isinstance(err, TranscriptsDisabled):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subtitles/transcripts are disabled for video '{video_id}'."
            )
        elif isinstance(err, NoTranscriptFound):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No matching transcript found for video '{video_id}'."
            )
        elif isinstance(err, (VideoUnavailable, VideoUnplayable)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video '{video_id}' is unavailable, private, or cannot be played."
            )
        elif isinstance(err, AgeRestricted):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Video '{video_id}' is age-restricted and cannot be accessed without authentication."
            )
        elif isinstance(err, (IpBlocked, RequestBlocked)):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="YouTube transcript request blocked or rate limited. Please try again later."
            )
        elif isinstance(err, YouTubeRequestFailed):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to communicate with YouTube services: {str(err)}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving transcript: {str(err)}"
            )


transcript_service = TranscriptService()
