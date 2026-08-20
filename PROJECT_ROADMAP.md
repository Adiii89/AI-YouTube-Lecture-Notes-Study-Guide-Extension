# 🚀 AI YouTube Lecture Notes & Study Guide — Project Roadmap & Progress Tracker

> **An AI-powered Chrome Extension (Manifest V3) + FastAPI backend that transforms any YouTube video into academic study guides, Cornell notes, active recall flashcards, and an interactive "Ask the Video" AI tutor.**

---

## 📊 Completed Milestones (What We Have Done)

### ✅ Phase 1: Backend Foundation & Infrastructure
- [x] **FastAPI Application Setup**: High-performance REST API with automated OpenAPI/Swagger documentation at `/docs`.
- [x] **Configuration Management**: Centralized environment configuration via `pydantic-settings` reading `.env`.
- [x] **CORS Middleware**: Configured to securely accept requests from Chrome extension origins (`chrome-extension://*`) and local development ports.
- [x] **Health & Diagnostics**: Endpoint `GET /api/v1/health` for connection validation and uptime checks.

### ✅ Phase 2: YouTube Transcript Extraction Pipeline
- [x] **Universal Video ID Parser**: Extracts 11-character video IDs from 10+ URL formats (`watch?v=`, `youtu.be/`, Shorts, Embeds, Live, and raw IDs).
- [x] **Transcript Extraction Service**: Built around `youtube-transcript-api` (v1.2+ API) with automatic multi-language fallback and auto-generated caption support.
- [x] **Timestamp Normalizer**: Converts second offsets into `[MM:SS]` and `[HH:MM:SS]` string formats for AI citation anchoring.
- [x] **API Endpoints**: `POST /api/v1/transcript/extract`, `GET /api/v1/transcript/{video_id}`, and `POST /api/v1/transcript/parse/id`.

### ✅ Phase 3: AI Lecture Notes & Summarization Engine
- [x] **5 Structured Note-Taking Templates**:
  1. **Comprehensive Study Guide**: In-depth explanations, formulas, definitions, and timestamp citations `[MM:SS]`.
  2. **Cornell Note-Taking System**: Cue column (questions/keywords), detailed notes column, and summary box.
  3. **Executive Summary**: High-impact TL;DR with 5-7 core takeaways.
  4. **Active Recall Flashcards**: Q&A study cards with difficulty levels and timestamp anchors.
  5. **Action Items & Checklist**: Practical steps and implementation tasks.
- [x] **Dual AI Provider Support**:
  - **OpenAI**: `gpt-4o-mini`, `gpt-4o` using structured JSON output.
  - **Google Gemini**: `gemini-2.5-flash`, `gemini-2.0-flash` with system instructions and JSON mime-type.
- [x] **Dual Output**: Returns both structured JSON entities (for UI cards/tables) and synthesized Markdown (for export).
- [x] **Endpoints**: `POST /api/v1/notes/generate`, `GET /api/v1/notes/templates`.

### ✅ Phase 4: Manifest V3 Chrome Extension Frontend
- [x] **Manifest V3 Architecture**: Secure service worker, content scripts, and popup permissions (`activeTab`, `storage`, `scripting`).
- [x] **Dark Glassmorphic Popup UI**: Modern violet/dark aesthetic with format selectors, Markdown previewer, flashcard viewer, Cornell table renderer, and export toolbar (Copy, `.md` download, PDF print).
- [x] **In-Page Floating YouTube Sidebar**: Native-styled **"✨ AI Notes"** button injected directly below YouTube video player; sliding drawer allowing students to read/generate notes without leaving YouTube.
- [x] **Interactive Timestamp Seeking**: Clicking any timestamp badge (`[MM:SS]`) sends message to content script and instantly seeks the YouTube `<video>` player.

### ✅ Phase 5: Interactive Video AI Chat Assistant ("Ask the Video") & Library
- [x] **"Ask the Video" Chat Engine**: Context-grounded Q&A assistant answering questions strictly based on the lecture transcript.
- [x] **Timestamp Citations**: Answers automatically cite timestamps `[MM:SS]` that seek the video when clicked.
- [x] **Quick-Prompt Chips**: 1-click prompts for *3-Bullet Summary*, *Key Concept Breakdown*, and *Practice Quiz*.
- [x] **In-Page Chat Tab**: Integrated into the YouTube sliding drawer for real-time studying while watching.
- [x] **Saved Notes Library**: Searchable drawer in popup to browse, search, and reload previously generated notes from `chrome.storage.local`.
- [x] **Automated Test Suite**: 29/29 unit and integration tests passing in 1.4s.

---

## 🔮 Next to Implement (Future Roadmap)

### 📌 Phase 6: Export Integrations & Cloud Sync
- [ ] **1-Click Notion Sync**: Direct export of structured notes and Cornell tables into a user's Notion workspace database.
- [ ] **Obsidian / Anki Deck Export**: Export generated flashcards directly to `.apkg` (Anki Deck) format for spaced repetition.
- [ ] **Custom Styled PDF Generator**: Export study guides with university-grade typography, headers, and color-coded callouts.

### 📌 Phase 7: Audio Transcription Fallback (Whisper API)
- [ ] **OpenAI Whisper Fallback**: For YouTube videos with disabled or missing subtitles/captions, extract audio stream and transcribe using `whisper-1`.
- [ ] **Speaker Diarization**: Detect multiple speakers in debates, interviews, and panel discussions.

### 📌 Phase 8: Multi-Language Translation & Voice Dubbing
- [ ] **Live Multilingual Translation**: Translate lecture notes and study guides into 50+ languages.
- [ ] **Audio Summary Podcasts**: Generate 2-minute audio summaries of the lecture using OpenAI TTS (`tts-1`).

### 📌 Phase 9: Collaborative Study Groups & Web App
- [ ] **Web Dashboard**: Standalone Next.js web application for users without Chrome.
- [ ] **Shared Lecture Notebooks**: Shareable links to generated study guides with embedded video timestamps.

---

## 📁 Repository File Structure

```
YT_extension/
├── .env.example                     # Environment template
├── .gitignore                       # Git ignore rules (protects API keys)
├── PROJECT_ROADMAP.md               # Progress tracker & future roadmap
├── PROJECT_EXPLAINER.md             # In-depth architectural guide
├── backend/                         # FastAPI Python Backend
│   ├── .env                         # Local environment configuration
│   ├── requirements.txt             # Python dependencies
│   ├── app/
│   │   ├── main.py                  # FastAPI app entrypoint & CORS
│   │   ├── core/
│   │   │   └── config.py            # Pydantic settings & env resolution
│   │   ├── schemas/
│   │   │   ├── notes.py             # Note, Chat & Template schemas
│   │   │   └── transcript.py        # Transcript request/response schemas
│   │   ├── services/
│   │   │   ├── notes_service.py     # OpenAI & Gemini notes + chat engine
│   │   │   ├── prompts.py           # Note templates & chat prompt builders
│   │   │   └── transcript_service.py# YouTube transcript extraction
│   │   ├── utils/
│   │   │   └── youtube.py           # URL regex parser & timestamp formatting
│   │   └── api/
│   │       └── v1/
│   │           ├── api.py           # API v1 router aggregator
│   │           └── endpoints/
│   │               ├── health.py    # Health check endpoint
│   │               ├── notes.py     # Notes generation & chat endpoints
│   │               └── transcript.py# Transcript extraction endpoints
│   └── tests/
│       ├── conftest.py              # Pytest fixtures & test client
│       ├── test_health.py           # Health endpoint tests
│       ├── test_notes.py            # Notes & Chat unit/integration tests
│       └── test_transcript.py       # Transcript parser & service tests
└── extension/                       # Manifest V3 Chrome Extension
    ├── manifest.json                # Extension metadata & permissions
    ├── icons/                       # High-resolution extension icons
    ├── background/
    │   └── service_worker.js        # Background caching service
    ├── content/
    │   ├── content.js               # YouTube in-page UI & video seeker
    │   └── content.css              # In-page sidebar & button styling
    └── popup/
        ├── popup.html               # Popup HTML (Notes, Chat, Library)
        ├── popup.css                # Dark glassmorphic design
        └── popup.js                 # Popup controller & state manager
```
