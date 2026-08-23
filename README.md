# PromptLab

**Your AI Prompt Engineering Platform**

---

## Welcome to the Team! 👋

Congratulations on joining the PromptLab engineering team! You've been brought on to help us build the next generation of prompt engineering tools.

### What is PromptLab?

PromptLab is an internal tool for AI engineers to **store, organize, and manage their prompts**. Think of it as a "Postman for Prompts" — a professional workspace where teams can:

- 📝 Store prompt templates with variables (`{{input}}`, `{{context}}`)
- 📁 Organize prompts into collections
- 🏷️ Tag and search prompts
- 📜 Track version history
- 🧪 Test prompts with sample inputs

### The Current Situation

The previous developer left us with a *partially working* backend. The core structure is there, but:

- There are **several bugs** that need fixing
- Some **features are incomplete**
- The **documentation is minimal** (you'll fix that)
- There are **no tests** worth mentioning
- **No CI/CD pipeline** exists
- **No frontend** has been built yet

Your job over the next 4 weeks is to transform this into a **production-ready, full-stack application**.

---

## What This Service Is

PromptLab's backend is a small REST API for storing prompt templates and grouping them into collections. A **prompt** has a title, the template text (which may contain `{{variables}}`), an optional description and an optional `collection_id`. A **collection** is a named label that prompts can belong to. Everything is held in memory inside the server process — there is no database yet — so the store starts empty each time the server starts and is lost when it stops.

The API is built with FastAPI and Pydantic and served by uvicorn. It exposes CRUD endpoints for prompts and collections, a partial-update (`PATCH`) endpoint for prompts, list filtering by collection and by search term, and a health check. Deletes are *soft*: a deleted prompt or collection is stamped with `deleted_on` and hidden from every endpoint rather than removed, and deleting a collection also soft-deletes the prompts in it.

## Running It

### Prerequisites

- **Python 3.10, 3.11 or 3.12.** Python 3.13+ will not work: the pinned `pydantic==2.5.3` depends on a `pydantic-core` release that has no 3.13 wheels, so `pip install` tries to compile it from Rust source and fails. A `.python-version` file pins 3.12 for pyenv and uv users.
- Git

### Run locally

From a fresh clone, these steps create an isolated environment, install the pinned dependencies, and start the server with hot reload.

```bash
git clone https://github.com/darwinz/10x-engineer-project-repo.git
cd 10x-engineer-project-repo/backend

python3.12 -m venv .venv          # or python3.11 / python3.10
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python main.py
```

The server listens on **http://localhost:8000**. Interactive API docs (Swagger UI) are at **http://localhost:8000/docs** and the raw OpenAPI schema at `/openapi.json`.

`python main.py` runs uvicorn with `--reload`, so it restarts when a file under `backend/` changes. That restart also empties the in-memory store, so create test data *after* any code edits. If you prefer to invoke uvicorn directly:

```bash
uvicorn app.api:app --reload --port 8000
```

### Quick check

With the server running, in another terminal:

```bash
curl http://localhost:8000/health
# {"status":"healthy","version":"0.1.0"}

curl -X POST http://localhost:8000/prompts \
  -H 'Content-Type: application/json' \
  -d '{"title":"Code review","content":"Review this code:\n\n{{code}}"}'
```

### Run the tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

All tests should pass. The suite uses FastAPI's `TestClient`, so the server does not need to be running. (The `DeprecationWarning` lines about `datetime.utcnow()` are expected — see *Known issues*.)

### Known issues

- `datetime.utcnow()` is deprecated in Python 3.12 and produces a warning on every test run. It still works; replacing it with a timezone-aware call is deferred so the API's timestamp format doesn't change mid-module.
- Timestamps are naive UTC and serialise without a timezone suffix (e.g. `2026-08-22T05:13:14.923906`). Treat them as UTC.
- Storage is in-memory and per-process. Running uvicorn with more than one worker would give each worker its own store.

---

## Project Structure

```
10x-engineer-project-repo/
├── README.md                    # You are here
├── .python-version              # Pins Python 3.12 for pyenv / uv
│
├── backend/
│   ├── app/
│   │   ├── __init__.py         # Package version
│   │   ├── api.py              # FastAPI app and all routes
│   │   ├── models.py           # Pydantic models
│   │   ├── storage.py          # In-memory storage with soft delete
│   │   └── utils.py            # Sort / filter / search helpers
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py         # Test fixtures
│   │   ├── test_api.py         # Endpoint tests
│   │   └── test_utils.py       # Helper unit tests
│   ├── main.py                 # Entry point (python main.py)
│   └── requirements.txt        # Pinned dependencies
│
├── docs/
│   ├── SYSTEM_MODEL.md          # Architecture, routes, data flow, storage, dependencies
│   ├── prompt-log.md            # AI prompt log for Module 1
│   └── ai-verification-note.md  # An AI mistake caught during Module 1
│
├── frontend/                    # You'll create this in Week 4
├── specs/                       # You'll create this in Week 2
└── .github/                     # You'll set up CI/CD in Week 3
```

---

## Your Mission

### 🧪 Experimentation Encouraged!
While we provide guidelines, **you are the engineer**. If you see a better way to solve a problem using AI, do it!
- Want to swap the storage layer for a real database? **Go for it.**
- Want to add Authentication? **Do it.**
- Want to rewrite the API in a different style? **As long as tests pass, you're clear.**

The goal is to learn how to build *better* software *faster* with AI. Don't be afraid to break things and rebuild them better.

### Week 1: Fix the Backend
- Understand this codebase using AI
- Find and fix the bugs
- Implement missing features

### Week 2: Document Everything
- Write proper documentation
- Create feature specifications
- Set up coding standards

### Week 3: Make it Production-Ready
- Write comprehensive tests
- Implement new features with TDD
- Set up CI/CD and Docker

### Week 4: Build the Frontend
- Create a React frontend
- Connect it to the backend
- Polish the user experience

---

## API Endpoints (Current)

| Method | Endpoint | Description | Responses |
|--------|----------|-------------|-----------|
| GET | `/health` | Health check | 200 |
| GET | `/prompts` | List prompts, newest first. Optional `?collection_id=` and `?search=` (matches title and description) | 200 |
| GET | `/prompts/{id}` | Get one prompt | 200 · 404 |
| POST | `/prompts` | Create a prompt | 201 · 400 unknown collection · 422 |
| PUT | `/prompts/{id}` | Replace a prompt (all fields required); bumps `updated_at` | 200 · 404 · 400 · 422 |
| PATCH | `/prompts/{id}` | Partial update — only fields in the body change; `null` clears `description`/`collection_id`; `null` `title`/`content` is 400; bumps `updated_at` | 200 · 404 · 400 · 422 |
| DELETE | `/prompts/{id}` | Soft-delete a prompt | 204 · 404 |
| GET | `/collections` | List collections | 200 |
| GET | `/collections/{id}` | Get one collection | 200 · 404 |
| POST | `/collections` | Create a collection | 201 · 422 |
| DELETE | `/collections/{id}` | Soft-delete a collection and all prompts in it | 204 · 404 |

Soft-deleted records are excluded from every endpoint above; a second DELETE on the same id returns 404.

---

## Tech Stack

- **Backend**: Python 3.10–3.12, FastAPI, Pydantic
- **Frontend**: React, Vite (Week 4)
- **Testing**: pytest
- **DevOps**: Docker, GitHub Actions (Week 3)

---

Good luck, and welcome to the team! 🚀
