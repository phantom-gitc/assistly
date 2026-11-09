# Assistly — Backend

A **FastAPI** backend for a real-time customer support system with:
- **AI bot** (Gemini) for automated replies
- **Human agent takeover** via WebSocket
- **Admin panel** for managing agents and rooms
- **Qdrant** vector DB for semantic knowledge-base search

---

## Folder Structure

```
backend/
├── main.py                   # FastAPI app entry point
├── requirements.txt
├── .env.example              # Copy to .env and fill in secrets
│
├── app/
│   ├── core/
│   │   ├── config.py         # Settings loaded from .env
│   │   ├── database.py       # SQLAlchemy engine & session
│   │   ├── security.py       # JWT creation/verification & role guards
│   │   └── deps.py           # Shared get_db() dependency
│   │
│   ├── models/
│   │   ├── user.py           # User ORM model (customer | agent | admin)
│   │   ├── chat_room.py      # ChatRoom ORM model
│   │   └── message.py        # Message ORM model
│   │
│   ├── schemas/
│   │   ├── user.py           # Pydantic user schemas
│   │   ├── chat_room.py      # Pydantic chat room schemas
│   │   └── message.py        # Pydantic message schemas
│   │
│   ├── services/
│   │   ├── knowledge_service.py  # Qdrant semantic search
│   │   ├── document_service.py   # PDF/text extraction and RAG indexing
│   │   └── ai_service.py         # Gemini reply generation
│   │
│   └── routers/
│       ├── auth.py           # POST /auth/login  GET /auth/me
│       ├── users.py          # POST /users/register
│       ├── chat.py           # Customer & agent REST + WebSocket endpoints
│       └── admin.py          # Admin endpoints (agents, rooms)
│
└── scripts/
    ├── create_collection.py  # Create Qdrant collection (run once)
    ├── add_knowledge.py      # Seed FAQ knowledge base
    ├── search_knowledge.py   # Test semantic search
    ├── create_admin.py       # Seed admin user (run once)
    └── test_db.py            # Verify DB connection
```

---

## Quick Start

### 1. Prerequisites
- Python 3.11+
- PostgreSQL database
- [Qdrant Cloud](https://cloud.qdrant.io) account (free tier works)
- [Google AI Studio](https://aistudio.google.com) API key (Gemini)

### 2. Setup

```powershell
cd backend

# Create and activate an isolated backend environment (Python 3.11+)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS/Linux alternative:
# python3 -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# The existing project .env has been moved to backend/.env.
# For a fresh checkout only, copy .env.example to .env and set real secrets.
```

### 3. Initialise services

```bash
# Create Qdrant collection (once)
python scripts/create_collection.py

# Seed FAQ knowledge base
python scripts/add_knowledge.py

# Verify semantic retrieval returns relevant FAQ results
python scripts/search_knowledge.py

# Create admin user (once)
python scripts/create_admin.py

# Verify DB connection
python scripts/test_db.py
```

### 4. Run the server

```bash
uvicorn main:app --reload
```

API docs: http://localhost:8000/docs

The API reads `backend/.env` directly, regardless of the shell's current directory. Keep real credentials out of source control. The existing Qdrant collection default is versioned for Gemini Embedding 2 so vectors from older embedding models cannot be mixed. Create this collection and seed it before expecting grounded AI answers. If you change the embedding model later, use a fresh collection and re-embed every knowledge entry.

### Production

Install dependencies from `requirements.txt`, provide production environment variables (including the exact HTTPS frontend origin in `ALLOWED_ORIGINS`), initialize the database and Qdrant collection, seed knowledge, and create an admin account with a strong unique password. Run Uvicorn without `--reload`, behind an HTTPS reverse proxy. Set `VITE_API_URL` to the HTTPS API origin when building the frontend. Configure the frontend host to serve its `index.html` for client-side routes and support WebSocket upgrades.

---

## API Overview

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/users/register` | — | Register customer |
| POST | `/auth/login` | — | Login (returns JWT) |
| GET | `/auth/me` | Any | Get own profile |
| POST | `/chat/guest/rooms` | — | Start a registration-free visitor chat (8 starts/IP/minute, per process) |
| POST | `/chat/rooms` | Customer | Create chat room |
| GET | `/chat/rooms/{id}/messages` | Customer | Get message history |
| WS | `/chat/ws/{room_id}?token=` | Customer | Live chat WebSocket |
| GET | `/chat/agent/rooms` | Agent | View assigned rooms |
| PUT | `/chat/agent/rooms/{id}/takeover` | Agent | Switch to human mode |
| PUT | `/chat/agent/rooms/{id}/handback` | Agent | Return to bot mode |
| WS | `/chat/ws/agent/{room_id}?token=` | Agent | Agent WebSocket |
| POST | `/admin/agents` | Admin | Create agent |
| GET | `/admin/agents` | Admin | List all agents |
| PUT | `/admin/agents/{id}/activate` | Admin | Activate agent |
| PUT | `/admin/agents/{id}/deactivate` | Admin | Deactivate agent |
| GET | `/admin/rooms` | Admin | List all rooms |
| PUT | `/admin/rooms/{id}/assign/{agent_id}` | Admin | Assign agent to room |
| PUT | `/admin/rooms/{id}/close` | Admin | Close a room |
| DELETE | `/admin/rooms/{id}` | Admin | Delete a room and its message history |
| GET | `/admin/knowledge/documents` | Admin | List indexed company documents |
| POST | `/admin/knowledge/documents` | Admin | Upload and index PDF, TXT, or Markdown |
| DELETE | `/admin/knowledge/documents/{document_id}` | Admin | Remove document chunks and vectors |

Company knowledge can be uploaded from the **Admin → Knowledge** tab. Uploads are limited to 10 MB and 100 PDF pages. PDFs must contain selectable text; TXT and Markdown files must use UTF-8. Extracted text is chunked, stored in PostgreSQL, and embedded into the configured Qdrant collection. The original file is not retained. Ensure the collection has been created and FAQ seed script has run before uploading documents.

Visitors can begin a private chat at `/guest` without registering. A guest session uses the same authenticated chat endpoints as a customer and expires with the configured access token lifetime. The in-process start limit is a basic safeguard; configure shared rate limiting at the edge or in a shared store when running multiple production workers.

---

## Chat Mode Lifecycle

```
Customer creates room  →  chat_mode = "bot"
                              ↓
                    AI replies automatically
                              ↓
        Admin assigns agent  →  Agent connects via WebSocket
                              ↓
        Agent calls /takeover →  chat_mode = "human"  (AI silent)
                              ↓
        Agent calls /handback →  chat_mode = "bot"   (AI resumes)
        (or agent disconnects and no other agent is in the room)
```

---

## User Roles

| Role | Can do |
|------|--------|
| `customer` | Create room, send messages, view own history |
| `agent` | View assigned rooms, send replies, takeover/handback |
| `admin` | Everything agents can do + manage agents + manage all rooms |

