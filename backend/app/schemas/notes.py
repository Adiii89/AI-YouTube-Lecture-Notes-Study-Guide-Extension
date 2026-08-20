from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class NoteFormat(str, Enum):
    COMPREHENSIVE = "comprehensive"
    CORNELL = "cornell"
    SUMMARY = "summary"
    FLASHCARDS = "flashcards"
    ACTION_ITEMS = "action_items"


class FlashcardItem(BaseModel):
    question: str = Field(..., description="Active recall study question")
    answer: str = Field(..., description="Concise, clear answer")
    timestamp_cue: Optional[str] = Field(default=None, description="Timestamp where this concept is discussed (e.g. '04:12')")
    difficulty: Optional[str] = Field(default="medium", description="Difficulty level: easy, medium, or hard")


class NoteSection(BaseModel):
    heading: str = Field(..., description="Topic or subtopic heading")
    timestamp_str: Optional[str] = Field(default=None, description="Starting timestamp for this section (e.g. '02:30')")
    summary: str = Field(..., description="Concise paragraph summary of the topic")
    key_points: List[str] = Field(default_factory=list, description="Bullet points explaining core ideas")


class CornellNoteSection(BaseModel):
    cue: str = Field(..., description="Cue column: Main keyword, question, or conceptual prompt")
    note: str = Field(..., description="Notes column: Detailed explanation, definitions, formulas, or diagrams")
    timestamp_str: Optional[str] = Field(default=None, description="Timestamp reference (e.g. '08:45')")


class NotesGenerationRequest(BaseModel):
    url_or_id: Optional[str] = Field(
        default=None,
        description="YouTube video URL or 11-character video ID. Required if transcript_text is omitted."
    )
    transcript_text: Optional[str] = Field(
        default=None,
        description="Raw full transcript text. If omitted, it will be automatically fetched using url_or_id."
    )
    segments: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional list of transcript segments with start timestamps for higher fidelity citations."
    )
    note_format: NoteFormat = Field(
        default=NoteFormat.COMPREHENSIVE,
        description="Desired format of notes: comprehensive, cornell, summary, flashcards, or action_items"
    )
    provider: Optional[str] = Field(
        default=None,
        description="LLM provider: 'openai', 'gemini', or 'auto' (defaults to server config LLM_PROVIDER)",
        examples=["openai", "gemini"]
    )
    custom_instructions: Optional[str] = Field(
        default=None,
        description="Optional specific user guidelines (e.g., 'Emphasize code implementation', 'Simplify for beginners')",
        examples=["Focus heavily on the mathematical proof and practical Python examples."]
    )
    target_language: str = Field(
        default="en",
        description="Target language for generated notes (e.g., 'en', 'es', 'fr', 'de', 'hi')"
    )
    model_name: Optional[str] = Field(
        default=None,
        description="Override LLM model name (e.g., 'gpt-4o-mini', 'gpt-4o', 'gemini-2.5-flash')"
    )


class NotesGenerationResponse(BaseModel):
    video_id: Optional[str] = Field(default=None, description="YouTube Video ID")
    title: str = Field(..., description="Generated title for the lecture or video")
    note_format: NoteFormat = Field(..., description="Format of the generated notes")
    provider: str = Field(..., description="LLM provider used (openai or gemini)")
    executive_summary: str = Field(..., description="High-level 2-3 sentence overview of the lecture")
    key_takeaways: List[str] = Field(..., description="Core actionable key takeaways from the video")
    markdown_content: str = Field(..., description="Full, beautifully formatted Markdown representation")
    sections: List[NoteSection] = Field(default_factory=list, description="Structured topic breakdown")
    cornell_notes: Optional[List[CornellNoteSection]] = Field(default=None, description="Cornell format cues and notes")
    flashcards: List[FlashcardItem] = Field(default_factory=list, description="Study flashcards and self-test items")
    total_duration_str: Optional[str] = Field(default=None, description="Total video runtime if known")
    word_count: int = Field(..., description="Word count of the generated markdown notes")
    model: str = Field(..., description="AI model used for generation")
    generation_time_ms: float = Field(..., description="Generation latency in milliseconds")


class TemplateInfo(BaseModel):
    id: NoteFormat = Field(..., description="Template ID")
    name: str = Field(..., description="Display title")
    description: str = Field(..., description="Description of format")
    best_for: str = Field(..., description="Best usage scenario")
    sample_preview: str = Field(..., description="Brief snippet showing visual style")


class TemplatesResponse(BaseModel):
    templates: List[TemplateInfo] = Field(..., description="List of available note templates")


# ==========================================
# Video Chat Assistant Schemas
# ==========================================

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content")


class VideoChatRequest(BaseModel):
    url_or_id: Optional[str] = Field(
        default=None,
        description="YouTube video URL or video ID. Required if transcript_text is omitted."
    )
    transcript_text: Optional[str] = Field(
        default=None,
        description="Raw or timestamped transcript text if already loaded by client."
    )
    question: str = Field(
        ...,
        description="User's question about the video content",
        examples=["Can you explain the formula at 04:15?", "Give me 3 practice quiz questions based on this lecture."]
    )
    chat_history: List[ChatMessage] = Field(
        default_factory=list,
        description="Prior conversation turns for multi-turn context"
    )
    provider: Optional[str] = Field(
        default=None,
        description="LLM provider: 'openai', 'gemini', or 'auto'"
    )
    model_name: Optional[str] = Field(
        default=None,
        description="Override model name"
    )


class VideoChatResponse(BaseModel):
    video_id: Optional[str] = Field(default=None, description="YouTube Video ID")
    answer: str = Field(..., description="AI response grounded in the video transcript")
    timestamp_citations: List[str] = Field(
        default_factory=list,
        description="List of cited timestamps extracted from the response (e.g. ['04:15', '08:30'])"
    )
    provider: str = Field(..., description="LLM provider used")
    model: str = Field(..., description="AI model used")
    generation_time_ms: float = Field(..., description="Response latency in milliseconds")
