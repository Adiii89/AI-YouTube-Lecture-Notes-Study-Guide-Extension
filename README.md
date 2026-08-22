# YouTube Lecture Notes & Study Guide Generator

A Chrome extension (Manifest V3) backed by a FastAPI service that converts YouTube video transcripts into structured study materials. It supports multiple pedagogical formats (Cornell notes, active recall flashcards, detailed study guides, executive summaries, and action checklists), an in-page floating study drawer on YouTube with clickable timestamp navigation, and a grounded "Ask the Video" Q&A chat assistant.

---

## Overview

Taking comprehensive notes while watching educational lectures, tutorials, and technical talks is time-consuming and often interrupts the learning flow. Generic video summarizers typically produce unstructured paragraphs that omit formulas, key definitions, cue questions, and timestamp references.

This tool solves that by:
- Pulling official and auto-generated transcripts with microsecond precision directly from YouTube.
- Feeding timestamped text segments into structured prompt pipelines powered by OpenAI (GPT-4o / GPT-4o-mini) or Google Gemini (Gemini 2.5 Flash).
- Rendering structured notes, active recall flashcard decks, and Cornell note tables directly inside a popup or an in-page YouTube drawer.
- Enabling one-click video navigation: clicking any timestamp badge (`[MM:SS]`) instantly seeks the YouTube player to that exact moment in the video.
- Grounding an interactive conversational tutor strictly on the video transcript so you can clarify concepts without hallucinations.

---

## Architecture

The system consists of two decoupled components:

```
+-------------------------------------------------------------------------+
|                        CHROME EXTENSION (V3)                            |
|                                                                         |
|  +---------------------------+        +------------------------------+  |
|  |       Popup Window        |        |    YouTube In-Page Drawer    |  |
|  | - Note format selector    |        | - "AI Notes" injected button |  |
|  | - Markdown & Card preview |        | - Sliding sidebar drawer     |  |
|  | - Saved notes library     |        | - In-page video Q&A chat     |  |
|  | - Export tools (.md, PDF) |        | - Direct HTML5 video seeker  |  |
|  +-------------+-------------+        +--------------+---------------+  |
|                |                                     |                  |
|                +------------------+------------------+                  |
|                                   | chrome.storage.local (cache)        |
|                                   v                                     |
|                       Background Service Worker                         |
+-----------------------------------+-------------------------------------+
                                    | HTTP REST API (JSON)
                                    v
+-------------------------------------------------------------------------+
|                        FASTAPI BACKEND (PYTHON)                         |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  | Endpoints (/api/v1)                                               |  |
|  | - GET  /health              Health check and uptime status        |  |
|  | - POST /transcript/extract  Fetch transcript text and timestamps  |  |
|  | - POST /notes/generate      Generate structured study materials   |  |
|  | - POST /notes/chat          Grounded Q&A chat over transcript     |  |
|  | - GET  /notes/templates     List supported note templates         |  |
|  +--------------------------------+----------------------------------+  |
|                                   |                                     |
|                 +-----------------+-----------------+                   |
|                 v                                   v                   |
|  +------------------------------+   +--------------------------------+  |
|  |      Transcript Service      |   |       LLM Synthesis Engine     |  |
|  | - youtube-transcript-api     |   | - OpenAI API (gpt-4o-mini/4o)  |  |
|  | - Multi-format URL parser    |   | - Google GenAI (gemini-2.5)    |  |
|  | - Timestamp formatting       |   | - JSON schema enforcement      |  |
|  +------------------------------+   +--------------------------------+  |
+-------------------------------------------------------------------------+
```

---

## Features

### Note Formats
1. **Comprehensive Study Guide**: In-depth thematic breakdown, core concepts, formulas, definitions, key takeaways, and timestamp citations.
2. **Cornell Note-Taking System**: Structured cue column (keywords and review questions), detailed notes column, and a bottom synthesis summary.
3. **Active Recall Flashcards**: Front-and-back study cards with question, answer, difficulty tag, and timestamp anchor for spaced repetition.
4. **Executive Summary**: High-impact TL;DR with bulleted takeaways for rapid review.
5. **Action Items & Checklist**: Practical next steps, exercises, and implementation tasks extracted from the video.

### In-Page YouTube Integration
- Injects an **"AI Notes"** button directly below the YouTube video player.
- Opens a sliding drawer on the right side of the screen so you can read notes and ask questions while keeping the video visible.
- Clicking any timestamp badge (e.g. `[12:34]`) immediately jumps the YouTube video player to that timestamp.

### "Ask the Video" Chat Assistant
- Chat interface directly tied to the current video's transcript.
- Answers questions with timestamped source citations.
- Includes quick-prompt chips for instant summaries, key concept breakdowns, and practice quizzes.

### Offline Library & Export Options
- Automatically saves generated notes to local extension storage (`chrome.storage.local`).
- Filter and search through previously generated study guides.
- Export to formatted Markdown (`.md`), copy raw text, or trigger clean browser print-to-PDF formatting.

---

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, Pydantic v2, `pydantic-settings`, `uvicorn`, `httpx`
- **Transcript Extraction**: `youtube-transcript-api` (supporting manual and auto-generated captions across languages)
- **AI Providers**: OpenAI SDK (`openai`), Google GenAI SDK (`google-genai`)
- **Frontend / Extension**: Manifest V3, Vanilla JavaScript, CSS3 (glassmorphic dark UI), HTML5, Chrome Extension APIs (`storage`, `activeTab`, `scripting`)
- **Testing**: `pytest`, `httpx` AsyncClient

---

## Project Structure

```
.
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |   `-- v1/
|   |   |       |-- endpoints/
|   |   |       |   |-- health.py          # Health check endpoint
|   |   |       |   |-- notes.py           # Note generation and chat endpoints
|   |   |       |   `-- transcript.py     # Transcript extraction endpoints
|   |   |       `-- api.py                 # Router aggregation
|   |   |-- core/
|   |   |   `-- config.py                  # Pydantic settings and env loader
|   |   |-- schemas/
|   |   |   |-- notes.py                   # Pydantic models for notes and chat
|   |   |   `-- transcript.py              # Pydantic models for transcript requests
|   |   |-- services/
|   |   |   |-- notes_service.py           # LLM client orchestration (OpenAI / Gemini)
|   |   |   |-- prompts.py                 # Structured system and user prompt templates
|   |   |   `-- transcript_service.py      # YouTube transcript retrieval and formatting
|   |   |-- utils/
|   |   |   `-- youtube.py                 # URL regex extraction and timestamp math
|   |   `-- main.py                        # FastAPI application instance & CORS setup
|   |-- tests/
|   |   |-- conftest.py                    # Test fixtures
|   |   |-- test_health.py                 # Health route tests
|   |   |-- test_notes.py                  # Note generation and chat unit tests
|   |   `-- test_transcript.py             # Transcript parser and endpoint tests
|   `-- requirements.txt                   # Backend Python dependencies
|-- extension/
|   |-- background/
|   |   `-- service_worker.js              # Background service worker
|   |-- content/
|   |   |-- content.css                    # In-page drawer and button styles
|   |   `-- content.js                     # YouTube DOM injection and video controller
|   |-- icons/                             # Extension icons (16, 48, 128px)
|   |-- popup/
|   |   |-- popup.css                      # Popup glassmorphic theme styling
|   |   |-- popup.html                     # Main extension popup interface
|   |   `-- popup.js                       # UI controller, API client, local storage manager
|   `-- manifest.json                      # Chrome extension Manifest V3 definition
|-- PROJECT_EXPLAINER.md                   # Detailed technical explainer
|-- PROJECT_ROADMAP.md                     # Roadmap and milestone tracking
`-- README.md
```

---

## Getting Started

### Prerequisites
- Python 3.11 or higher
- Google Chrome (or any Chromium-based browser like Brave or Edge)
- An API key for either **OpenAI** (`OPENAI_API_KEY`) or **Google Gemini** (`GEMINI_API_KEY`)

---

### Step 1: Set Up and Run the Backend

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your environment variables:
   Create a `.env` file in the `backend/` directory (or root workspace):
   ```env
   # LLM Provider Selection: "auto", "openai", or "gemini"
   LLM_PROVIDER=auto

   # OpenAI Configuration (Optional if using Gemini)
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_MODEL=gpt-4o-mini

   # Google Gemini Configuration (Optional if using OpenAI)
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-2.5-flash

   # Server Settings
   HOST=127.0.0.1
   PORT=8000
   DEBUG=True
   ```

5. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

6. Verify the server is running by opening:
   - Health check: `http://127.0.0.1:8000/api/v1/health`
   - Interactive Swagger Docs: `http://127.0.0.1:8000/docs`

---

### Step 2: Install the Chrome Extension

1. Open Google Chrome and go to `chrome://extensions/`.
2. Enable **Developer mode** using the toggle switch in the top-right corner.
3. Click the **Load unpacked** button in the top-left corner.
4. Select the `extension` directory from this project repository.
5. The extension **AI YouTube Lecture Notes & Study Guide** will now appear in your extensions list.
6. Pin the extension to your Chrome toolbar for quick access.

---

## How to Use

1. Open any YouTube video that has subtitles/closed captions enabled (e.g. tutorials, university lectures, conference talks).
2. You can generate notes in two ways:
   - **Via Popup**: Click the extension icon in the toolbar, select your desired template format (e.g. Study Guide, Cornell Notes, Flashcards), and click **Generate Notes**.
   - **Via YouTube Page**: Click the **"AI Notes"** button located directly beneath the YouTube video player to slide open the side drawer.
3. Once notes are generated:
   - Click any timestamp badge (`[MM:SS]`) to jump the video directly to that point in the lecture.
   - Switch to the **Ask Video** tab to ask specific clarifying questions about the video content.
   - Use the toolbar buttons to copy notes, download a `.md` file, or print/save as PDF.
   - Revisit past study sessions anytime from the **Saved Library** tab.

---

## API Reference

### Health
- `GET /api/v1/health`
  - Returns service status, active LLM provider, and version information.

### Transcript
- `POST /api/v1/transcript/extract`
  - **Body**: `{"url": "https://www.youtube.com/watch?v=..."}` or `{"video_id": "..."}`
  - **Response**: Full transcript string with timestamp offsets and metadata.
- `GET /api/v1/transcript/{video_id}`
  - Fetches transcript directly by YouTube video ID.

### Lecture Notes
- `POST /api/v1/notes/generate`
  - **Body**:
    ```json
    {
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "template": "study_guide",
      "custom_instructions": "Focus on the mathematical derivations."
    }
    ```
  - **Supported Templates**: `study_guide`, `cornell`, `summary`, `flashcards`, `action_items`.
  - **Response**: Structured JSON payload matching the template schema and a rendered Markdown representation.
- `POST /api/v1/notes/chat`
  - **Body**:
    ```json
    {
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "question": "What was the main conclusion regarding gradient descent?",
      "history": []
    }
    ```
  - **Response**: Context-grounded answer with timestamp citations.
- `GET /api/v1/notes/templates`
  - Returns all supported study note templates with their descriptions and schema fields.

---

## Running Tests

The test suite covers URL parsing, transcript extraction fallback logic, prompt compilation, Pydantic schema validation, and mocked LLM responses.

Run tests using `pytest` from the `backend` directory:

```bash
cd backend
pytest -v
```

---

## Troubleshooting

- **"No transcript found for this video"**:
  - The video does not have closed captions or subtitles enabled by the creator or YouTube auto-captioning. Make sure the video has working captions in the YouTube player.
- **"Failed to fetch" in the extension**:
  - Ensure the FastAPI server is running on `http://127.0.0.1:8000`.
  - Check that your `.env` contains a valid `OPENAI_API_KEY` or `GEMINI_API_KEY`.
- **Changes to extension code not reflecting**:
  - Go to `chrome://extensions/` and click the reload icon on the extension card. Refresh the YouTube tab to load the updated content script.

---

## License

MIT License. Feel free to use, modify, and distribute for personal or educational purposes.
