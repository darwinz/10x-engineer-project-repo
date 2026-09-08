# PromptLab

A REST API for storing, organizing, and versioning AI prompt templates — think "Postman for prompts."

[![Python 3.10–3.12](https://img.shields.io/badge/python-3.10--3.12-blue)](#prerequisites)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688)](#tech-stack)
[![Tests: 38 passing](https://img.shields.io/badge/tests-38%20passing-brightgreen)](#running-the-tests)

## Overview

PromptLab gives AI engineers a dedicated workspace for prompt templates instead of scattering them across docs, Slack threads, and code comments. A **prompt** is a title plus template text that may contain `{{variables}}`, with an optional description and an optional collection. A **collection** is a named group that prompts can belong to, useful for organizing prompts by project, model, or use case.

The backend is a FastAPI service with full CRUD for prompts and collections, partial updates, collection-scoped and full-text filtering, and soft deletes so nothing is destroyed by accident. Storage is currently in-memory (see [Known Limitations](#known-limitations)); a persistent store, authentication, and a React frontend are on the roadmap.

## Features

- **Prompt management** — create, read, update (full or partial), and delete prompt templates
- **Variable templating** — reference `{{input}}`-style placeholders in prompt content
- **Collections** — group related prompts under a named, searchable label
- **Search & filter** — list prompts by collection or free-text search across title and description
- **Partial updates** — `PATCH` changes only the fields you send; `PUT` replaces the whole record
- **Soft deletes** — deleting a prompt or collection stamps `deleted_on` instead of destroying data; deleting a collection cascades to its prompts
- **Interactive API docs** — Swagger UI and OpenAPI schema generated automatically by FastAPI
- **CORS enabled** — ready to be called from a browser-based frontend during development

## Tech Stack

| Layer | Technology |
|---|---|
| API framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Data validation | [Pydantic](https://docs.pydantic.dev/) v2 |
| Server | [uvicorn](https://www.uvicorn.org/) |
| Testing | [pytest](https://docs.pytest.org/) + [httpx](https://www.python-httpx.org/) via `TestClient` |
| Frontend | React + Vite *(planned)* |
| CI/CD | GitHub Actions + Docker *(planned)* |

## Prerequisites

- **Python 3.10, 3.11, or 3.12** — Python 3.13+ is not supported. The pinned `pydantic==2.5.3` depends on a `pydantic-core` release with no 3.13 wheels, so `pip install` falls back to compiling from source and fails. A `.python-version` file pins 3.12 for `pyenv`/`uv` users.
- **Git**

## Installation

```bash
git clone https://github.com/darwinz/10x-engineer-project-repo.git
cd 10x-engineer-project-repo/backend

python3.12 -m venv .venv          # or python3.11 / python3.10
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Quick Start

Start the server:

```bash
python main.py
```

The API listens on **http://localhost:8000**. `main.py` runs uvicorn with `--reload`, so it restarts on code changes under `backend/` — note that a restart also clears the in-memory store.

Interactive docs are available at:

- Swagger UI: **http://localhost:8000/docs**
- OpenAPI schema: **http://localhost:8000/openapi.json**

Verify it's running:

```bash
curl http://localhost:8000/health
# {"status":"healthy","version":"0.1.0"}
```

Create your first prompt:

```bash
curl -X POST http://localhost:8000/prompts \
  -H 'Content-Type: application/json' \
  -d '{
        "title": "Code review",
        "content": "Review this code:\n\n{{code}}",
        "description": "Standard code review template"
      }'
```

## API Reference

All endpoints accept and return JSON, and require no authentication (see [Known Limitations](#known-limitations)). Interactive, always-up-to-date documentation is served at `/docs`.

**Full reference with request/response examples for every endpoint — including `PATCH`, error formats, and status codes — lives in [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md).**

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/prompts` | List prompts (filter by `collection_id`, `search`) |
| `GET` | `/prompts/{id}` | Get one prompt |
| `POST` | `/prompts` | Create a prompt |
| `PUT` | `/prompts/{id}` | Full replace |
| `PATCH` | `/prompts/{id}` | Partial update |
| `DELETE` | `/prompts/{id}` | Soft-delete a prompt |
| `GET` | `/collections` | List collections |
| `GET` | `/collections/{id}` | Get one collection |
| `POST` | `/collections` | Create a collection |
| `DELETE` | `/collections/{id}` | Soft-delete a collection (cascades to its prompts) |

## Development Setup

With the virtual environment active (see [Installation](#installation)):

```bash
# Run with auto-reload (same as `python main.py`)
uvicorn app.api:app --reload --port 8000
```

### Running the tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

The suite (38 tests) uses FastAPI's `TestClient`, so the server does not need to be running separately. The `DeprecationWarning` lines about `datetime.utcnow()` are expected — see [Known Limitations](#known-limitations).

### Project structure

```
10x-engineer-project-repo/
├── backend/
│   ├── app/
│   │   ├── api.py              # FastAPI app and all routes
│   │   ├── models.py           # Pydantic request/response models
│   │   ├── storage.py          # In-memory storage with soft delete
│   │   └── utils.py            # Sort / filter / search helpers
│   ├── tests/                  # pytest suite (API + unit tests)
│   ├── main.py                 # Entry point (`python main.py`)
│   └── requirements.txt        # Pinned dependencies
├── docs/
│   └── SYSTEM_MODEL.md         # Architecture, routes, data flow, storage
├── frontend/                   # React frontend (planned)
├── specs/                      # Feature specifications (planned)
└── .python-version             # Pins Python 3.12 for pyenv / uv
```

### Known Limitations

- **Storage is in-memory and per-process.** The store starts empty on every launch — including hot-reload restarts — and is lost when the server stops. Running with multiple uvicorn workers would give each worker its own store.
- **`datetime.utcnow()` is deprecated** on Python 3.12 and emits a warning on every test run. It still works correctly; migrating to a timezone-aware call is deferred so the API's timestamp format doesn't change mid-module.
- **Timestamps are naive UTC** and serialize without a timezone suffix (e.g. `2026-08-22T05:13:14.923906`) — treat them as UTC.

## Contributing

This project follows a lightweight, PR-based workflow:

1. **Branch from `main`** using a short, descriptive name (e.g. `fix/collection-cascade`, `feat/prompt-tags`).
2. **Write tests first** for any bug fix or new behavior, then implement — the suite is the source of truth for correctness.
3. **Keep commits focused and conventional.** Prefix messages with `feat:`, `fix:`, `docs:`, `test:`, or `refactor:`, and scope each commit to one logical change.
4. **Document public functions.** New or modified functions should carry a docstring whose `Args` / `Returns` / `Raises` match the implementation.
5. **Run the full suite before opening a PR:**
   ```bash
   cd backend && pytest tests/ -v
   ```
6. **Open a pull request against `main`** with a summary of the change and how it was verified (a `curl` transcript or test output is sufficient for API changes).

For larger changes — a new storage backend, authentication, or a frontend — open an issue or start a discussion first so the approach can be agreed on before implementation.
