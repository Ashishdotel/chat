# नेपाली भाषा बुद्धिमान च्याटबट
# Nepali Language Intelligent Chatbot

> **Final Year Thesis Project**  
> A multilingual AI chatbot with real-time language translation and document scanning, powered by **Anthropic Claude AI**.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Features](#2-features)
3. [Technology Stack](#3-technology-stack)
4. [Project Structure](#4-project-structure)
5. [Installation & Setup](#5-installation--setup)
6. [Running the Application](#6-running-the-application)
7. [API Documentation](#7-api-documentation)
8. [How to Use the Application](#8-how-to-use-the-application)
9. [System Architecture](#9-system-architecture)
10. [Code Documentation](#10-code-documentation)
11. [Supported Languages](#11-supported-languages)
12. [Environment Variables](#12-environment-variables)
13. [Author & Thesis Information](#13-author--thesis-information)

---

## 1. Project Overview

This project is a **university final-year thesis** that develops an intelligent chatbot for the Nepali language. The system goes beyond a basic chatbot by integrating:

- **Multilingual conversation** — users can choose any of 12 languages for the chatbot to reply in
- **Language translation** — translate typed text between 12 languages
- **Document scanning & translation** — upload a PDF or a photo of a document, the AI reads the text (OCR) and translates it
- **Knowledge base chat (RAG)** — upload PDF documents; the chatbot uses them to answer questions accurately
- **Conversation history** — all sessions saved in a database and can be resumed

The project demonstrates the practical application of Large Language Models (LLMs) for low-resource languages like Nepali, combined with modern web technologies.

---

## 2. Features

### 💬 Chat Features

| Feature | Description |
|---|---|
| Multilingual replies | Choose from 12 languages — bot always replies in selected language |
| Any-language input | Type in Nepali, English, or any language — bot understands all |
| Session memory | Bot remembers the last 20 messages in a conversation |
| Conversation history | All past chats saved, listed in sidebar, and resumable |
| RAG (document-based answers) | Upload a PDF; bot reads it and answers questions from it |
| Typing indicator | Shows animated dots while bot is generating reply |
| Error handling | Clear Nepali + English error messages |

### 🌐 Language Translator Features

| Feature | Description |
|---|---|
| Text translation | Type any text and translate between 12 languages |
| Auto language detection | Set source to "Auto-detect" — Claude identifies the language |
| Swap languages | One-click button to swap source and target languages |
| Copy output | Copy translated text to clipboard |
| Character count | Shows character count (max 5000) |

### 📄 Document / Image Translator Features

| Feature | Description |
|---|---|
| PDF translation | Upload text-based PDFs — text extracted and translated |
| Image OCR + translation | Upload JPG/PNG/WEBP photo of document — AI reads and translates |
| Drag & drop | Drag files directly into the upload zone |
| Side-by-side view | Original text and translation shown together |
| Progress indicator | Animated progress bar during processing |
| File size limit | Max 10MB per file |

---

## 3. Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| **AI Model** | Anthropic Claude (claude-sonnet-4-6) | Chat, translation, image OCR |
| **Backend** | FastAPI (Python) | REST API server |
| **Database** | SQLite + SQLAlchemy ORM | Store sessions and messages |
| **Authentication** | JWT via python-jose + passlib | User login (optional) |
| **Vector Search** | FAISS (Facebook AI Similarity Search) | RAG document retrieval |
| **PDF Processing** | pypdf | Extract text from PDF files |
| **Frontend** | HTML5 + CSS3 + Vanilla JavaScript | User interface |
| **Web Server** | Uvicorn (ASGI) | Serve the FastAPI app |
| **Fonts** | Google Fonts — Noto Sans Devanagari + Inter | Nepali and English text |

---

## 4. Project Structure

```
Nepali-chatbot/
│
├── backend/                        # All Python backend code
│   │
│   ├── auth/                       # Authentication system
│   │   ├── __init__.py
│   │   ├── jwt_handler.py          # Create and decode JWT tokens
│   │   └── dependencies.py        # FastAPI auth dependency injectors
│   │
│   ├── database/                   # Database layer
│   │   ├── __init__.py
│   │   ├── connection.py           # SQLAlchemy engine setup
│   │   ├── models.py               # ORM table definitions (User, Session, Message)
│   │   └── repository.py          # All database query functions
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py              # Pydantic request/response models
│   │
│   ├── routes/                     # API endpoint handlers
│   │   ├── __init__.py
│   │   ├── auth.py                 # POST /api/auth/register, /login, /me
│   │   ├── chat.py                 # POST /api/chat  (main chatbot)
│   │   ├── documents.py            # POST /api/documents/upload  (RAG)
│   │   ├── sessions.py             # GET /api/sessions/  (history)
│   │   └── translate.py            # POST /api/translate/text, /document
│   │
│   ├── services/                   # Business logic layer
│   │   ├── __init__.py
│   │   ├── chat_service.py         # Orchestrates chat: memory + RAG + LLM
│   │   └── rag_service.py          # PDF ingestion and vector retrieval
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   └── logger.py               # Centralised logging configuration
│   │
│   ├── config.py                   # App settings loaded from .env file
│   ├── llm.py                      # ALL Claude AI API calls (chat, translate, OCR)
│   ├── main.py                     # FastAPI app creation and router registration
│   ├── memory.py                   # Session memory: load/save conversation history
│   └── rag.py                      # RAG orchestrator: check if enabled, retrieve context
│
├── frontend/                       # Single-page web application
│   ├── index.html                  # Main HTML file (loaded at /)
│   ├── app.js                      # All JavaScript: chat logic + translator logic
│   └── style.css                   # All CSS styles
│
├── data/                           # Auto-created at runtime
│   ├── chatbot.db                  # SQLite database file
│   ├── documents/                  # Uploaded PDFs for RAG
│   └── vector_store/               # FAISS index files (index.faiss + metadata.json)
│
├── evaluation/                     # Thesis evaluation tools
│   ├── __init__.py
│   ├── evaluator.py                # Automated response quality evaluation
│   └── run_eval.py                 # Script to run evaluation tests
│
├── deployment/                     # Production deployment files
│   ├── Dockerfile                  # Docker container definition
│   ├── docker-compose.yml          # Multi-container orchestration
│   └── nginx.conf                  # Reverse proxy configuration
│
├── .env                            # Environment variables (API keys, settings)
├── requirements.txt                # Python package dependencies
└── README.md                       # This documentation file
```

---

## 5. Installation & Setup

### Prerequisites

- **Python 3.11** or higher — [Download Python](https://python.org)
- **Anthropic API Key** — [Get key from console.anthropic.com](https://console.anthropic.com/settings/keys)
- Internet connection (for Claude API calls)

### Step 1 — Navigate to the project folder

```bash
cd C:\Users\YourName\Downloads\Nepali-chatbot\Nepali-chatbot
```

### Step 2 — Create a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### Step 3 — Install all dependencies

```bash
pip install -r requirements.txt
pip install anthropic
```

This installs: FastAPI, Uvicorn, SQLAlchemy, pypdf, FAISS, python-jose, passlib, anthropic, and all other required packages.

### Step 4 — Configure the .env file

Open the `.env` file and set your Anthropic API key:

```env
# ============================================================
# NEPALI CHATBOT — Environment Configuration
# ============================================================

# Anthropic Claude Configuration
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
ANTHROPIC_MODEL=claude-sonnet-4-6
ANTHROPIC_MAX_TOKENS=1024

# Application Configuration
APP_NAME="Nepali Language Intelligent Chatbot"
APP_VERSION="1.0.0"
DEBUG=True

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Database Configuration
DATABASE_URL=sqlite:///./data/chatbot.db

# RAG Configuration
RAG_ENABLED=False

# Authentication
SECRET_KEY=change-this-to-a-random-secret-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### Step 5 — Create required data directories

```bash
# Windows
mkdir data\documents
mkdir data\vector_store

# Mac / Linux
mkdir -p data/documents data/vector_store
```

---

## 6. Running the Application

### Start the server

```bash
# Make sure you are inside: Nepali-chatbot\Nepali-chatbot\
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see output like:
```
INFO  Nepali Language Intelligent Chatbot v1.0.0
INFO  Model: claude-sonnet-4-6
INFO  Uvicorn running on http://0.0.0.0:8000
INFO  Application startup complete.
```

### Open the application

| URL | Description |
|---|---|
| http://localhost:8000 | Main application (Chat + Translator) |
| http://localhost:8000/docs | Interactive API documentation (Swagger UI) |
| http://localhost:8000/redoc | Alternative API documentation (ReDoc) |
| http://localhost:8000/health | Health check endpoint |

### Stop the server

Press `Ctrl + C` in the terminal.

---

## 7. API Documentation

Complete interactive documentation is available at **http://localhost:8000/docs** when the server is running.

---

### 7.1 Chat API

#### `POST /api/chat` — Send a message

**Request Body (JSON):**
```json
{
  "message": "नेपालको राजधानी कुन हो?",
  "session_id": "optional-uuid-to-continue-existing-chat",
  "language": "ne"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | Yes | The user's message (1–2000 characters) |
| `session_id` | string | No | Continue an existing session; omit to start new |
| `language` | string | No | Reply language code. Default: `"ne"` (Nepali) |

**Response (JSON):**
```json
{
  "reply": "नेपालको राजधानी काठमाडौं हो।",
  "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "model_used": "claude-sonnet-4-6",
  "timestamp": "2025-01-01T12:00:00",
  "rag_used": false
}
```

#### `DELETE /api/chat/{session_id}` — Clear a session

Clears the conversation memory for a given session.

---

### 7.2 Translation API

#### `GET /api/translate/languages` — List supported languages

**Response:**
```json
{
  "languages": {
    "ne": "Nepali (नेपाली)",
    "en": "English",
    "hi": "Hindi (हिन्दी)",
    "zh": "Chinese (中文)",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)",
    "es": "Spanish (Español)",
    "fr": "French (Français)",
    "de": "German (Deutsch)",
    "ar": "Arabic (العربية)",
    "pt": "Portuguese (Português)",
    "ru": "Russian (Русский)"
  }
}
```

---

#### `POST /api/translate/text` — Translate typed text

**Request Body (JSON):**
```json
{
  "text": "Hello, how are you?",
  "source_language": "auto",
  "target_language": "ne"
}
```

| Field | Type | Description |
|---|---|---|
| `text` | string | Text to translate (1–5000 characters) |
| `source_language` | string | Language code or `"auto"` for auto-detection |
| `target_language` | string | Target language code (e.g. `"ne"`, `"en"`) |

**Response:**
```json
{
  "translated_text": "नमस्ते, तपाईं कस्तो हुनुहुन्छ?",
  "source_language": "auto",
  "target_language": "ne",
  "char_count": 32
}
```

---

#### `POST /api/translate/document` — Translate PDF or image

**Request (multipart/form-data):**

| Field | Type | Description |
|---|---|---|
| `file` | File | PDF or image file (max 10MB) |
| `target_language` | string | Target language code |
| `source_language` | string | Source language code or `"auto"` |

Supported file types: `.pdf`, `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`

**Response:**
```json
{
  "translated_text": "नमस्ते संसार ...",
  "original_text": "Hello World ...",
  "source_language": "auto",
  "target_language": "ne",
  "filename": "document.pdf",
  "page_count": 2,
  "char_count": 156
}
```

---

### 7.3 Sessions API

#### `GET /api/sessions/` — List all sessions

Returns a list of all conversation sessions sorted by most recent.

**Response:**
```json
[
  {
    "id": "f47ac10b-...",
    "title": "नेपालको राजधानी कुन हो?",
    "message_count": 6,
    "updated_at": "2025-01-01T12:00:00",
    "created_at": "2025-01-01T11:00:00"
  }
]
```

#### `GET /api/sessions/{session_id}` — Get session with messages

Returns full session data including all messages.

#### `DELETE /api/sessions/{session_id}` — Delete a session

---

### 7.4 Documents (RAG) API

#### `POST /api/documents/upload` — Upload PDF for knowledge base

**Request (multipart/form-data):** Upload a `.pdf` file (max 50MB).

The system will:
1. Save the PDF to `data/documents/`
2. Extract all text using pypdf
3. Split text into chunks
4. Create embeddings for each chunk
5. Store embeddings in FAISS vector index
6. Automatically enable RAG

**Response:**
```json
{
  "message": "'file.pdf' सफलतापूर्वक इन्डेक्स गरियो!",
  "filename": "file.pdf",
  "page_count": 10,
  "chunk_count": 45,
  "total_vectors": 45,
  "rag_enabled": true
}
```

#### `GET /api/documents/status` — RAG system status

#### `DELETE /api/documents/{filename}` — Remove a document

---

### 7.5 Health Check

#### `GET /health`

```json
{
  "status": "healthy",
  "app_name": "Nepali Language Intelligent Chatbot",
  "version": "1.0.0",
  "message": "नेपाली च्याटबट सर्भर चलिरहेको छ।"
}
```

---

## 8. How to Use the Application

### 8.1 Starting a Chat

1. Open **http://localhost:8000** in your browser
2. In the **"Reply in:"** dropdown (top right of chat), select your language
3. Type your message in the text box at the bottom
4. Press **Enter** to send (or **Shift+Enter** for a new line)
5. The bot will reply in your selected language

**Example conversations:**
```
You:  नेपालको सबैभन्दा अग्लो हिमाल कुन हो?
Bot:  नेपालको सबैभन्दा अग्लो हिमाल माउन्ट एभरेस्ट हो।

You:  What does 'माया' mean in English?
Bot:  'माया' means love/affection in English.

You:  Translate "good morning" to Nepali
Bot:  "Good morning" को नेपाली अनुवाद "शुभ प्रभात" हो।
```

### 8.2 Using the Language Translator (Text)

1. Click the **🌐 Translate** tab at the top
2. Make sure **✏️ Text** subtab is selected
3. Select the source language (or leave as "Auto-detect")
4. Select the target language
5. Type your text in the left box
6. Click **🌐 Translate**
7. Translation appears in the right box
8. Click **📋 Copy** to copy the result

### 8.3 Translating a Document or Image (OCR)

1. Click the **🌐 Translate** tab
2. Click the **📄 Document / Image** subtab
3. Select the target language from the dropdown
4. Either drag a file onto the upload zone, or click **Browse File**
5. Supported files: PDF, JPG, PNG, WEBP, GIF (max 10MB)
6. Wait for processing (progress bar shown)
7. Original text and translated text appear side by side
8. Click **📋 Copy Translation** to copy

**Best results for image scanning:**
- Use a clear, well-lit photo
- Make sure text is straight and readable
- Works best with printed text (typed documents)
- Also works on handwritten text (lower accuracy)

### 8.4 Uploading Documents for Knowledge Base (RAG)

1. In the **left sidebar**, find the **📄 Documents** panel
2. Drag a PDF file onto the upload zone, or click **"फाइल छान्नुहोस्"**
3. Wait for indexing (progress shown)
4. The RAG badge will turn green and show **ON**
5. Now chat normally — the bot will reference your document when relevant

**Example with RAG:**
- Upload a PDF about Nepal's history
- Ask: "नेपालको एकीकरण कसले गर्‍यो?"
- The bot reads from your uploaded document and answers accurately

### 8.5 Managing Conversation History

- All conversations appear in the **left sidebar** under "पुराना कुराकानीहरू"
- Click any conversation to **load** it
- Click the **✕** button on a conversation to **delete** it
- Click **"नयाँ कुराकानी"** (New Chat) to start fresh
- Click **↻** to refresh the history list

---

## 9. System Architecture

### Overall Flow

```
┌──────────────────────────────────────────┐
│            User's Web Browser            │
│  (HTML + CSS + JavaScript — no framework) │
└──────────────────┬───────────────────────┘
                   │  HTTP / JSON
                   ▼
┌──────────────────────────────────────────┐
│           FastAPI Web Server             │
│              (port 8000)                 │
│                                          │
│  Routes:                                 │
│  ├── /api/chat        → chat_service.py  │
│  ├── /api/translate   → llm.py           │
│  ├── /api/documents   → rag_service.py   │
│  └── /api/sessions    → repository.py   │
└──────┬───────────────┬───────────────────┘
       │               │
       ▼               ▼
┌────────────┐  ┌─────────────────────┐
│  SQLite DB │  │  Anthropic Claude   │
│  (history) │  │  API (claude-sonnet)│
└────────────┘  └─────────────────────┘
       │
       ▼
┌────────────────────┐
│  FAISS Vector Store│
│  (RAG documents)   │
└────────────────────┘
```

### Chat Request Flow

```
User types message
       │
       ▼
POST /api/chat  {message, session_id, language}
       │
       ▼
chat_service.process_chat()
       │
       ├─── 1. Load session history from SQLite
       │
       ├─── 2. If RAG enabled:
       │         embed query → FAISS search → get top-4 relevant chunks
       │         prepend chunks to message as context
       │
       ├─── 3. Save user message to SQLite
       │
       ├─── 4. Call Claude API
       │         system: "Reply in [language]"
       │         messages: [history... + augmented_user_message]
       │
       ├─── 5. Save Claude's reply to SQLite
       │
       └─── 6. Return {reply, session_id, model_used, rag_used}
```

### Translation Flow

```
POST /api/translate/text  {text, source_lang, target_lang}
       │
       ▼
llm.translate_text()
       │
       ▼
Claude API:
  system: "You are a professional translator"
  user:   "Translate from [source] to [target]: [text]"
       │
       ▼
Return only translated text (no explanations)
```

### Image OCR + Translation Flow

```
POST /api/translate/document  {image file, target_lang}
       │
       ▼
Read file bytes → encode as base64
       │
       ▼
llm.translate_image_document()
       │
       ▼
Claude Vision API:
  [image as base64] + "Extract all text and translate to [language]"
       │
       ▼
Parse response:
  ORIGINAL TEXT: [OCR result]
  TRANSLATED TEXT: [translation]
       │
       ▼
Return both original and translated text
```

---

## 10. Code Documentation

### backend/llm.py — AI Integration Layer

This is the most important file. It is the **only** file that communicates with the Anthropic Claude API.

**Key functions:**

| Function | Parameters | Returns | Description |
|---|---|---|---|
| `get_chat_response()` | `history, user_message, language` | `str` | Sends conversation to Claude, returns reply text |
| `translate_text()` | `text, source_lang, target_lang` | `dict` | Translates text, returns `{translated_text, char_count}` |
| `translate_image_document()` | `base64_image, image_mime, target_lang` | `dict` | OCR + translate image, returns `{original_text, translated_text}` |
| `_build_system_prompt()` | `language` | `str` | Builds the system instruction telling Claude which language to use |

**`LANGUAGE_NAMES` dict:** Maps language codes (`"ne"`, `"en"`, etc.) to display names used in prompts.

---

### backend/config.py — Settings

Uses **Pydantic BaseSettings** to load all configuration from the `.env` file.

The `@lru_cache()` decorator on `get_settings()` ensures the `.env` file is only read **once** when the server starts — not on every request.

---

### backend/services/chat_service.py — Chat Logic

The `process_chat()` function is the heart of the chat feature:

1. Creates a new session UUID if needed
2. Loads the last N messages from SQLite (conversation memory)
3. If RAG is enabled, searches FAISS for relevant document chunks
4. Augments the user message with document context
5. Saves user message → calls Claude → saves reply
6. Returns `(reply, session_id, rag_used)`

---

### backend/routes/translate.py — Translation Routes

Three endpoints:
- `GET /languages` — returns `LANGUAGE_NAMES` dict for frontend dropdowns
- `POST /text` — validates request, calls `llm.translate_text()`
- `POST /document` — detects file type (PDF or image), extracts/encodes content, calls appropriate LLM function

For PDFs: uses `pypdf.PdfReader` to extract text, truncates to 4000 chars if too long.  
For images: base64-encodes the file, sends to `llm.translate_image_document()`.

---

### frontend/app.js — Frontend Logic

| Section | Functions | Description |
|---|---|---|
| State management | `STATE` object | Tracks session, language, loading state |
| Tab switching | `switchMainTab()`, `switchSubtab()` | Show/hide Chat or Translate panels |
| Session management | `loadSession()`, `saveSession()`, `clearSession()` | Persist session ID in localStorage |
| Language selection | `chatLanguageSelect` event | Save chosen language to localStorage |
| Chat flow | `handleSend()`, `sendMessageToAPI()` | Send message, receive reply, render in UI |
| UI rendering | `appendMessage()`, `setLoading()`, `resetUI()` | Update the chat interface |
| History panel | `loadSessionHistory()`, `loadPastSession()` | Load and display past conversations |
| RAG panel | `uploadDocument()`, `loadRAGStatus()` | Sidebar PDF upload for knowledge base |
| Text translator | `handleTranslateText()`, `copyTranslation()` | Text translation tab logic |
| Document translator | `handleDocumentTranslate()`, `resetDocTranslator()` | File upload + OCR translation logic |

---

### frontend/style.css — Styling

The CSS uses **CSS Custom Properties (variables)** defined in `:root` for consistent theming:

| Variable | Value | Used For |
|---|---|---|
| `--primary` | `#2563eb` | Buttons, active states |
| `--bg-main` | `#0f172a` | Page background (dark) |
| `--bg-surface` | `#1e293b` | Sidebar, header |
| `--bg-elevated` | `#273549` | Cards, panels |
| `--text-primary` | `#f1f5f9` | Main text |
| `--font-nepali` | Noto Sans Devanagari | All Nepali text |
| `--font-ui` | Inter | All UI labels and English text |

---

## 11. Supported Languages

| Code | Language | Script |
|---|---|---|
| `ne` | Nepali | Devanagari — नेपाली |
| `en` | English | Latin |
| `hi` | Hindi | Devanagari — हिन्दी |
| `zh` | Chinese (Simplified) | Han — 中文 |
| `ja` | Japanese | Kanji/Kana — 日本語 |
| `ko` | Korean | Hangul — 한국어 |
| `es` | Spanish | Latin — Español |
| `fr` | French | Latin — Français |
| `de` | German | Latin — Deutsch |
| `ar` | Arabic | Arabic script — العربية |
| `pt` | Portuguese | Latin — Português |
| `ru` | Russian | Cyrillic — Русский |

---

## 12. Environment Variables

All configuration is stored in the `.env` file:

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | **Yes** | — | Anthropic Claude API key |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-6` | Claude model to use |
| `ANTHROPIC_MAX_TOKENS` | No | `1024` | Maximum tokens per response |
| `APP_NAME` | No | `Nepali Language Intelligent Chatbot` | Application name |
| `APP_VERSION` | No | `1.0.0` | Version string |
| `DEBUG` | No | `False` | Enable debug mode & hot reload |
| `HOST` | No | `0.0.0.0` | Server bind address |
| `PORT` | No | `8000` | Server port |
| `DATABASE_URL` | No | `sqlite:///./data/chatbot.db` | Database location |
| `RAG_ENABLED` | No | `False` | Enable/disable RAG by default |
| `SECRET_KEY` | No | (insecure default) | JWT signing secret |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `1440` | JWT expiry (24 hours) |

---

## 13. Author & Thesis Information

| Field | Detail |
|---|---|
| **Student** |Ashish Dotel |
| **Email** | ashishdotel007@gmail.com |
| **Thesis Title** | Development of a Nepali Language Intelligent Chatbot with Multilingual Translation Capabilities |
| **Project Type** | Final Year  Thesis |
| **Year** | 2025 |
| **Technologies** | FastAPI, ollama
, SQLite, FAISS, HTML/CSS/JS |

### Key Contributions of This Thesis

1. **Multilingual chatbot** for the Nepali language using state-of-the-art LLM (Claude)
2. **Document OCR + translation** using Claude Vision multimodal capability
3. **RAG implementation** allowing domain-specific knowledge to be injected into conversations
4. **Full-stack web application** with persistent conversation history
5. **12-language support** making the system accessible to a wide audience

---

*Built with Anthropic Claude AI · FastAPI · SQLite · FAISS*
