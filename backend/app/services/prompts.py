from typing import List, Optional
from app.schemas.notes import NoteFormat, ChatMessage


def format_transcript_with_timestamps(segments: List[dict]) -> str:
    """
    Format a list of segment dictionaries into a concise timestamped text block for LLM context.
    """
    lines = []
    for s in segments:
        text = s.get("text", "").strip()
        start = s.get("timestamp_str", "") or s.get("start", "")
        if text:
            if start:
                lines.append(f"[{start}] {text}")
            else:
                lines.append(text)
    return "\n".join(lines)


SYSTEM_PROMPT = """You are an expert AI Professor, Academic Researcher, and Master Note-Taker.
Your goal is to transform lecture and video transcripts into clear, rigorous, beautifully structured educational study materials.

Guidelines:
1. Grounding: Rely strictly on the information provided in the transcript. Do not hallucinate external claims.
2. Timestamps: Reference timestamps from the transcript whenever discussing specific topics (format: `[MM:SS]` or `[HH:MM:SS]`).
3. Clarity & Depth: Explain complex concepts with intuitive analogies, structured bullet points, definitions, and code/formulas where applicable.
4. Output Format: You MUST output ONLY valid JSON matching the requested JSON structure.
"""


CHAT_SYSTEM_PROMPT = """You are an expert AI Video Teaching Assistant and Interactive Study Partner.
You are helping a student understand a YouTube video or lecture based on its full transcript.

Guidelines:
1. Grounding: Answer questions accurately based on the video's content and transcript.
2. Timestamp Citations: Whenever you reference a specific part of the video, provide the timestamp citation format `[MM:SS]` (e.g. `[03:45]`).
3. Clarity & Tone: Be encouraging, pedagogical, concise, and structured (use bold text, bullet points, and code blocks where helpful).
4. Out of scope: If the user asks about something completely absent from the video, state what the video discusses and briefly answer the question if relevant.
"""


def build_notes_prompt(
    transcript_text: str,
    note_format: NoteFormat,
    custom_instructions: Optional[str] = None,
    target_language: str = "en"
) -> str:
    format_instructions = {
        NoteFormat.COMPREHENSIVE: """
Generate comprehensive academic lecture notes.
JSON schema to return:
{
  "title": "Clear, engaging title of the lecture",
  "executive_summary": "2-4 sentence executive overview of what this video teaches",
  "key_takeaways": [
    "Takeaway 1...",
    "Takeaway 2...",
    "Takeaway 3...",
    "Takeaway 4..."
  ],
  "sections": [
    {
      "heading": "Section Topic Title",
      "timestamp_str": "MM:SS",
      "summary": "Summary of this subtopic",
      "key_points": [
        "In-depth explanation 1 with details",
        "In-depth explanation 2 with details"
      ]
    }
  ],
  "flashcards": [
    {
      "question": "Active recall study question?",
      "answer": "Clear, concise answer",
      "timestamp_cue": "MM:SS",
      "difficulty": "easy | medium | hard"
    }
  ],
  "markdown_content": "# Comprehensive formatted markdown string of all the notes above with headers, bullet points, and timestamp links"
}
""",
        NoteFormat.CORNELL: """
Generate notes in the Cornell Note-Taking System format.
JSON schema to return:
{
  "title": "Lecture Title",
  "executive_summary": "Executive overview of the material",
  "key_takeaways": ["Key point 1", "Key point 2", "Key point 3"],
  "sections": [
    {
      "heading": "Main Lecture Topic",
      "timestamp_str": "MM:SS",
      "summary": "Brief section summary",
      "key_points": ["Notes point 1", "Notes point 2"]
    }
  ],
  "cornell_notes": [
    {
      "cue": "Key question, term, or prompt for cue column",
      "note": "Detailed explanation, formula, or breakdown for notes column",
      "timestamp_str": "MM:SS"
    }
  ],
  "flashcards": [],
  "markdown_content": "# Cornell Notes formatted markdown containing Cue Column table, Notes, and Summary box"
}
""",
        NoteFormat.SUMMARY: """
Generate a high-impact executive summary and key insights.
JSON schema to return:
{
  "title": "Video Title",
  "executive_summary": "Concise 3-5 sentence core thesis and summary",
  "key_takeaways": [
    "Crucial insight 1",
    "Crucial insight 2",
    "Crucial insight 3",
    "Crucial insight 4",
    "Crucial insight 5"
  ],
  "sections": [
    {
      "heading": "Key Topic / Insight",
      "timestamp_str": "MM:SS",
      "summary": "Breakdown of the key point",
      "key_points": ["Detail A", "Detail B"]
    }
  ],
  "flashcards": [],
  "markdown_content": "# Executive Summary in Markdown with bullet points, bold key terms, and takeaway highlights"
}
""",
        NoteFormat.FLASHCARDS: """
Generate active recall flashcards and quiz questions from this lecture.
JSON schema to return:
{
  "title": "Flashcards: Topic Name",
  "executive_summary": "Brief summary of topics tested in these flashcards",
  "key_takeaways": ["Core concept tested 1", "Core concept tested 2"],
  "sections": [],
  "flashcards": [
    {
      "question": "Specific question testing understanding?",
      "answer": "Precise, complete explanation",
      "timestamp_cue": "MM:SS",
      "difficulty": "easy | medium | hard"
    }
  ],
  "markdown_content": "# Flashcard Study Guide in Markdown formatted as Q&A review cards"
}
""",
        NoteFormat.ACTION_ITEMS: """
Generate practical action items, exercises, and implementation takeaways from this video.
JSON schema to return:
{
  "title": "Action Plan & Next Steps: Topic Name",
  "executive_summary": "Overview of practical applications from the lecture",
  "key_takeaways": ["Practical principle 1", "Practical principle 2"],
  "sections": [
    {
      "heading": "Action Step / Exercise",
      "timestamp_str": "MM:SS",
      "summary": "What to do and why it matters",
      "key_points": ["Step 1", "Step 2", "Common pitfalls to avoid"]
    }
  ],
  "flashcards": [],
  "markdown_content": "# Action Plan in Markdown with checklists and step-by-step implementation tasks"
}
"""
    }

    instructions_block = format_instructions.get(note_format, format_instructions[NoteFormat.COMPREHENSIVE])

    custom_block = f"\nAdditional User Instructions:\n{custom_instructions}\n" if custom_instructions else ""
    language_block = f"\nOutput language must be: {target_language}\n" if target_language != "en" else ""

    return f"""Please generate notes for the following video transcript.

{instructions_block}
{custom_block}
{language_block}

Transcript Content:
---
{transcript_text}
---

Return ONLY the raw JSON without markdown code fences or other wrapping.
"""


def build_chat_prompt(
    transcript_text: str,
    question: str,
    chat_history: List[ChatMessage]
) -> List[dict]:
    """
    Construct multi-turn conversation messages including video transcript context.
    """
    messages = [
        {
            "role": "system",
            "content": f"{CHAT_SYSTEM_PROMPT}\n\nVideo Transcript with Timestamps:\n---\n{transcript_text}\n---"
        }
    ]

    # Append prior conversation history
    for msg in chat_history:
        messages.append({
            "role": msg.role if msg.role in ("user", "assistant", "system") else "user",
            "content": msg.content
        })

    # Append current question
    messages.append({
        "role": "user",
        "content": question
    })

    return messages
