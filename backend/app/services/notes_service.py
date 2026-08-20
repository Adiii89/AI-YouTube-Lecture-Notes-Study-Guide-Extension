import json
import logging
import re
import time
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from google import genai
from google.genai import types
from google.genai.errors import APIError as GeminiAPIError
import openai
from openai import OpenAI, APIError as OpenAIAPIError

from app.core.config import settings
from app.schemas.notes import (
    NoteFormat,
    FlashcardItem,
    NoteSection,
    CornellNoteSection,
    NotesGenerationRequest,
    NotesGenerationResponse,
    TemplateInfo,
    TemplatesResponse,
    VideoChatRequest,
    VideoChatResponse,
)
from app.services.prompts import (
    SYSTEM_PROMPT,
    CHAT_SYSTEM_PROMPT,
    build_notes_prompt,
    build_chat_prompt,
    format_transcript_with_timestamps,
)
from app.services.transcript_service import transcript_service

logger = logging.getLogger(__name__)

TEMPLATES_CATALOG: List[TemplateInfo] = [
    TemplateInfo(
        id=NoteFormat.COMPREHENSIVE,
        name="Comprehensive Study Guide",
        description="In-depth academic lecture notes with timestamped topic breakdowns, key takeaways, and flashcards.",
        best_for="Long tutorials, university lectures, complex technical courses",
        sample_preview="### [02:15] Neural Architecture\n- Core layers and activation functions\n- Mathematical derivation..."
    ),
    TemplateInfo(
        id=NoteFormat.CORNELL,
        name="Cornell Note-Taking System",
        description="Structured notes split into Cue column (questions/keywords), Notes column (explanations), and Summary Box.",
        best_for="Revision, exam prep, structured classroom learning",
        sample_preview="| Cues / Questions | Notes & Key Formulas |\n| --- | --- |\n| What is Gradient Descent? | Optimization algorithm minimizing cost function... |"
    ),
    TemplateInfo(
        id=NoteFormat.SUMMARY,
        name="Executive Summary & Insights",
        description="High-level overview, 5-7 core takeaways, and essential terminology.",
        best_for="Podcasts, tech keynotes, quick video overviews",
        sample_preview="### Executive Summary\nThis video explores...\n\n### Key Takeaways\n- 1. Scalability limits\n- 2. Modern solutions..."
    ),
    TemplateInfo(
        id=NoteFormat.FLASHCARDS,
        name="Active Recall Flashcards",
        description="Curated flashcards with direct question/answer pairs and timestamp cues for active recall study.",
        best_for="Quiz preparation, spaced repetition, quick self-testing",
        sample_preview="**Q: What is Backpropagation? [08:30]**\n> A: The process of calculating gradients via the chain rule..."
    ),
    TemplateInfo(
        id=NoteFormat.ACTION_ITEMS,
        name="Action Plan & Practical Steps",
        description="Actionable steps, coding exercises, checklists, and implementation guidelines from the video.",
        best_for="Coding tutorials, productivity videos, business walkthroughs",
        sample_preview="- [ ] Step 1: Install FastAPI dependencies [01:45]\n- [ ] Step 2: Implement router endpoints..."
    )
]


class NotesService:
    """Service for generating structured lecture notes & interactive video chat using OpenAI or Google Gemini."""

    def get_templates(self) -> TemplatesResponse:
        """Return list of supported lecture note templates."""
        return TemplatesResponse(templates=TEMPLATES_CATALOG)

    def _resolve_provider_and_model(
        self,
        requested_provider: Optional[str],
        requested_model: Optional[str]
    ) -> Tuple[str, str]:
        """
        Determine which LLM provider (openai or gemini) and model to use.
        """
        provider = (requested_provider or settings.LLM_PROVIDER or "auto").lower()

        if provider == "auto":
            if settings.OPENAI_API_KEY:
                provider = "openai"
            elif settings.GEMINI_API_KEY:
                provider = "gemini"
            else:
                provider = "openai"

        if provider == "openai":
            if requested_model and not requested_model.lower().startswith("gemini"):
                model = requested_model
            else:
                model = settings.OPENAI_MODEL or "gpt-4o-mini"
            return "openai", model
        elif provider == "gemini":
            if requested_model and not requested_model.lower().startswith("gpt"):
                model = requested_model
            else:
                model = settings.GEMINI_MODEL or "gemini-2.5-flash"
            return "gemini", model
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported LLM provider '{provider}'. Must be 'openai' or 'gemini'."
            )

    def generate_notes(self, request: NotesGenerationRequest) -> NotesGenerationResponse:
        """
        Generate structured lecture notes from a YouTube video URL/ID or raw transcript.
        """
        start_time = time.time()
        video_id: Optional[str] = None
        total_duration_str: Optional[str] = None
        transcript_content = ""

        # 1. Resolve transcript text and video ID
        if request.transcript_text:
            transcript_content = request.transcript_text.strip()
            if request.segments:
                transcript_content = format_transcript_with_timestamps(request.segments)
            video_id = request.url_or_id
        elif request.url_or_id:
            transcript_data = transcript_service.extract_and_fetch(request.url_or_id)
            video_id = transcript_data.video_id
            total_duration_str = transcript_data.total_duration_str
            raw_segs = [s.model_dump() for s in transcript_data.segments]
            transcript_content = format_transcript_with_timestamps(raw_segs)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'url_or_id' or 'transcript_text' must be provided."
            )

        if not transcript_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transcript content is empty. Cannot generate notes."
            )

        # 2. Resolve Provider & Model
        provider, model_name = self._resolve_provider_and_model(
            requested_provider=request.provider,
            requested_model=request.model_name
        )

        # 3. Build Prompt
        prompt = build_notes_prompt(
            transcript_text=transcript_content,
            note_format=request.note_format,
            custom_instructions=request.custom_instructions,
            target_language=request.target_language
        )

        # 4. Call LLM (OpenAI or Gemini)
        if provider == "openai":
            raw_output = self._call_openai(model_name, prompt)
        else:
            raw_output = self._call_gemini(model_name, prompt)

        parsed_json = self._parse_json_response(raw_output)

        # 5. Extract structured fields
        title = parsed_json.get("title", f"Lecture Notes: {video_id or 'Video'}")
        executive_summary = parsed_json.get("executive_summary", "")
        key_takeaways = parsed_json.get("key_takeaways", [])
        markdown_content = parsed_json.get("markdown_content", "")

        sections_raw = parsed_json.get("sections", [])
        sections = [
            NoteSection(
                heading=s.get("heading", "Topic"),
                timestamp_str=s.get("timestamp_str"),
                summary=s.get("summary", ""),
                key_points=s.get("key_points", [])
            )
            for s in sections_raw if isinstance(s, dict)
        ]

        cornell_raw = parsed_json.get("cornell_notes", None)
        cornell_notes = None
        if isinstance(cornell_raw, list):
            cornell_notes = [
                CornellNoteSection(
                    cue=c.get("cue", ""),
                    note=c.get("note", ""),
                    timestamp_str=c.get("timestamp_str")
                )
                for c in cornell_raw if isinstance(c, dict)
            ]

        flashcards_raw = parsed_json.get("flashcards", [])
        flashcards = [
            FlashcardItem(
                question=f.get("question", ""),
                answer=f.get("answer", ""),
                timestamp_cue=f.get("timestamp_cue"),
                difficulty=f.get("difficulty", "medium")
            )
            for f in flashcards_raw if isinstance(f, dict)
        ]

        # If markdown content is missing or too short, synthesize clean markdown
        if not markdown_content or len(markdown_content.strip()) < 50:
            markdown_content = self._synthesize_markdown(
                title=title,
                note_format=request.note_format,
                summary=executive_summary,
                takeaways=key_takeaways,
                sections=sections,
                cornell=cornell_notes,
                flashcards=flashcards
            )

        duration_ms = round((time.time() - start_time) * 1000, 2)
        word_count = len(markdown_content.split()) if markdown_content else 0

        return NotesGenerationResponse(
            video_id=video_id,
            title=title,
            note_format=request.note_format,
            provider=provider,
            executive_summary=executive_summary,
            key_takeaways=key_takeaways,
            markdown_content=markdown_content,
            sections=sections,
            cornell_notes=cornell_notes,
            flashcards=flashcards,
            total_duration_str=total_duration_str,
            word_count=word_count,
            model=model_name,
            generation_time_ms=duration_ms
        )

    def chat_with_video(self, request: VideoChatRequest) -> VideoChatResponse:
        """
        Interactive Q&A grounded strictly in the video transcript with timestamp citations.
        """
        start_time = time.time()
        video_id: Optional[str] = None
        transcript_content = ""

        # 1. Resolve Transcript
        if request.transcript_text:
            transcript_content = request.transcript_text.strip()
            video_id = request.url_or_id
        elif request.url_or_id:
            transcript_data = transcript_service.extract_and_fetch(request.url_or_id)
            video_id = transcript_data.video_id
            raw_segs = [s.model_dump() for s in transcript_data.segments]
            transcript_content = format_transcript_with_timestamps(raw_segs)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'url_or_id' or 'transcript_text' must be provided for chat."
            )

        if not transcript_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transcript content is empty. Cannot answer questions."
            )

        # 2. Resolve Provider & Model
        provider, model_name = self._resolve_provider_and_model(
            requested_provider=request.provider,
            requested_model=request.model_name
        )

        # 3. Build Chat Messages
        messages = build_chat_prompt(
            transcript_text=transcript_content,
            question=request.question,
            chat_history=request.chat_history
        )

        # 4. Call Provider
        answer_text = ""
        if provider == "openai":
            answer_text = self._chat_openai(model_name, messages)
        else:
            answer_text = self._chat_gemini(model_name, messages)

        # 5. Extract timestamp citations like [04:15] or [01:05:20]
        timestamp_citations = list(dict.fromkeys(re.findall(r"\[(\d{1,2}:\d{2}(?::\d{2})?)\]", answer_text)))

        duration_ms = round((time.time() - start_time) * 1000, 2)

        return VideoChatResponse(
            video_id=video_id,
            answer=answer_text,
            timestamp_citations=timestamp_citations,
            provider=provider,
            model=model_name,
            generation_time_ms=duration_ms
        )

    def _call_openai(self, model: str, prompt: str) -> str:
        """Call OpenAI Chat Completions API with structured JSON output."""
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OPENAI_API_KEY is not configured. Please set OPENAI_API_KEY in backend/.env."
            )
        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            return response.choices[0].message.content or "{}"
        except OpenAIAPIError as err:
            logger.error(f"OpenAI API Error: {err}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"OpenAI AI Service Error: {str(err)}"
            )
        except Exception as e:
            logger.error(f"Unexpected OpenAI error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate notes with OpenAI: {str(e)}"
            )

    def _chat_openai(self, model: str, messages: List[dict]) -> str:
        """Call OpenAI for interactive conversational Q&A."""
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OPENAI_API_KEY is not configured."
            )
        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.4
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OpenAI Chat Error: {str(e)}"
            )

    def _call_gemini(self, model: str, prompt: str) -> str:
        """Call Google Gemini Generate Content API."""
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GEMINI_API_KEY is not configured. Please set GEMINI_API_KEY in backend/.env."
            )
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )
            return response.text or "{}"
        except GeminiAPIError as err:
            logger.error(f"Gemini API Error: {err}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gemini AI Service Error: {str(err)}"
            )
        except Exception as e:
            logger.error(f"Unexpected Gemini error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate notes with Gemini: {str(e)}"
            )

    def _chat_gemini(self, model: str, messages: List[dict]) -> str:
        """Call Google Gemini for interactive conversational Q&A."""
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GEMINI_API_KEY is not configured."
            )
        try:
            client = genai.Client(api_key=api_key)
            system_inst = CHAT_SYSTEM_PROMPT
            # Combine transcript context from system message with conversation
            conversation_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
            response = client.models.generate_content(
                model=model,
                contents=conversation_text,
                config=types.GenerateContentConfig(
                    system_instruction=system_inst,
                    temperature=0.4
                )
            )
            return response.text or ""
        except Exception as e:
            logger.error(f"Gemini chat error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gemini Chat Error: {str(e)}"
            )

    def _parse_json_response(self, text: str) -> dict:
        """Clean and parse JSON from model output."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\n```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except Exception:
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}")
            if start_idx != -1 and end_idx != -1:
                try:
                    return json.loads(cleaned[start_idx:end_idx + 1])
                except Exception:
                    pass
            logger.warning(f"Could not parse JSON from model response: {text[:200]}")
            return {
                "title": "Lecture Notes",
                "executive_summary": "Notes generated successfully.",
                "key_takeaways": [],
                "markdown_content": text,
                "sections": []
            }

    def _synthesize_markdown(
        self,
        title: str,
        note_format: NoteFormat,
        summary: str,
        takeaways: List[str],
        sections: List[NoteSection],
        cornell: Optional[List[CornellNoteSection]],
        flashcards: List[FlashcardItem]
    ) -> str:
        lines = [f"# {title}\n", f"**Format:** {note_format.value.title()}\n"]

        if summary:
            lines.append(f"## Executive Summary\n{summary}\n")

        if takeaways:
            lines.append("## Key Takeaways")
            for t in takeaways:
                lines.append(f"- {t}")
            lines.append("")

        if sections:
            lines.append("## Detailed Lecture Breakdown\n")
            for s in sections:
                ts_header = f" [{s.timestamp_str}]" if s.timestamp_str else ""
                lines.append(f"### {s.heading}{ts_header}")
                if s.summary:
                    lines.append(f"{s.summary}\n")
                if s.key_points:
                    for pt in s.key_points:
                        lines.append(f"- {pt}")
                lines.append("")

        if cornell:
            lines.append("## Cornell Notes Table\n")
            lines.append("| Cues / Questions | Notes & Explanations | Time |")
            lines.append("| :--- | :--- | :--- |")
            for c in cornell:
                ts = c.timestamp_str or "-"
                lines.append(f"| **{c.cue}** | {c.note} | `{ts}` |")
            lines.append("")

        if flashcards:
            lines.append("## Active Recall Flashcards\n")
            for i, f in enumerate(flashcards, 1):
                ts = f" `[{f.timestamp_cue}]`" if f.timestamp_cue else ""
                lines.append(f"#### Q{i}: {f.question}{ts}")
                lines.append(f"> **Answer:** {f.answer}\n")

        return "\n".join(lines)


notes_service = NotesService()
