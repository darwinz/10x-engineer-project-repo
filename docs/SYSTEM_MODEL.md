# PromptLab Backend — System Model

This is my working model of the backend as I found it, before fixing anything. Every statement here was checked against the source or by running the code; where I ran something to confirm a behaviour I say so. Line numbers refer to the files as they were at the start of Module 1 (commit `1df4cbd`).

## 1. Architecture

PromptLab is a small REST API for storing prompt templates and grouping them into collections. It is a single-process FastAPI application with three thin tiers and no abstraction between them:

| Tier | File | What it does |
|---|---|---|
| HTTP | `backend/app/api.py` | One `FastAPI` instance and all ten route handlers. Handlers do their own existence checks and build model objects directly. |
| Domain | `backend/app/models.py` | Pydantic v2 models, plus `generate_id()` (uuid4) and `get_current_time()` (`datetime.utcnow()`). |
| Storage | `backend/app/storage.py` | A `Storage` class wrapping two dicts, instantiated once at import as the module-level `storage` singleton. |

`backend/app/utils.py` holds list helpers (sort, filter, search) used only by `GET /prompts`, plus two functions nobody calls. `backend/app/__init__.py` holds `__version__ = "0.1.0"`, which surfaces in `/health` and the OpenAPI title.

Things about the architecture that shape everything else:

- **State is global and mutable.** `storage = Storage()` runs at import time (`storage.py:69`). Every request and every test shares the same object. The app never resets it; the test suite does, via an autouse fixture in `conftest.py` that calls `storage.clear()` before and after each test.
- **There is no service layer.** Business rules ("a prompt's collection must exist") live in the route handlers, and they are duplicated between `POST /prompts` and `PUT /prompts/{id}`.
- **CORS is wide open** — `allow_origins=["*"]` with `allow_credentials=True` (`api.py:25-31`). Acceptable for a local tool. Note browsers refuse the `*` + credentials combination, so a credentialed cross-origin request would not actually succeed.
- **No custom error handling.** `HTTPException` is rendered by FastAPI's default handler as `{"detail": "..."}`. Any other exception falls through to Starlette's `ServerErrorMiddleware` and becomes a bare 500. Under `TestClient` the exception is re-raised into the test instead — which is why the Bug #1 tests fail with an `AttributeError` traceback rather than an assertion on status 500.

### The entry script does not work

`backend/main.py` calls `uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)` — passing the app **object** with `reload=True`. Uvicorn 0.27 rejects that combination: it logs `You must pass the application as an import string to enable 'reload' or 'workers'.` and calls `sys.exit(1)`. I ran it to be sure: `python main.py` prints that warning and exits with status 1 without ever binding a port. The README's "Run Locally" instructions therefore do not work as written. Running the server via the import-string form, `uvicorn app.api:app --reload` from `backend/`, starts normally (confirmed).

## 2. Entry points

**Process entry points**

- `uvicorn app.api:app --reload` from `backend/` — the working way to start the server.
- `python main.py` — intended entry point; currently exits immediately (see above).
- `pytest tests/ -v` from `backend/` — test suite (13 tests; 3 fail before fixes: two from Bug #1, one from Bug #3).

**HTTP routes**

Ten routes are defined in `api.py`. I confirmed the list by introspecting `app.routes` rather than reading the decorators alone.

| Method | Path | Handler | Success | Error responses |
|---|---|---|---|---|
| GET | `/health` | `health_check` | 200 `HealthResponse` | — |
| GET | `/prompts` | `list_prompts` | 200 `PromptList` | — |
| GET | `/prompts/{prompt_id}` | `get_prompt` | 200 `Prompt` | **500 on unknown id (Bug #1)** — should be 404 |
| POST | `/prompts` | `create_prompt` | 201 `Prompt` | 400 unknown `collection_id`; 422 validation |
| PUT | `/prompts/{prompt_id}` | `update_prompt` | 200 `Prompt` | 404 unknown prompt; 400 unknown `collection_id`; 422 validation |
| DELETE | `/prompts/{prompt_id}` | `delete_prompt` | 204 | 404 |
| GET | `/collections` | `list_collections` | 200 `CollectionList` | — |
| GET | `/collections/{collection_id}` | `get_collection` | 200 `Collection` | 404 |
| POST | `/collections` | `create_collection` | 201 `Collection` | 422 validation |
| DELETE | `/collections/{collection_id}` | `delete_collection` | 204 | 404 — **and orphans the collection's prompts (Bug #4)** |

FastAPI also mounts `/docs` (Swagger UI), `/redoc` and `/openapi.json` automatically.

`GET /prompts` accepts two optional query parameters: `collection_id` (exact match) and `search` (substring).

What is **not** there: `PATCH /prompts/{id}` (the missing endpoint this module adds), and any update route for collections at all — consistent with `Collection` having no `updated_at` field.

## 3. Data flow

### Creating a prompt — `POST /prompts`

1. Uvicorn hands the request to Starlette, which runs it through `CORSMiddleware` and matches `create_prompt` (`api.py:77`).
2. FastAPI parses the JSON body into `PromptCreate`. The field constraints live on `PromptBase` (`models.py:19-23`): `title` 1–200 characters, `content` at least 1, `description` optional up to 500, `collection_id` optional. A violation returns 422 before the handler body runs. The "at least 10 characters" rule in `utils.validate_prompt_content` is **not** applied anywhere — only the Pydantic constraints count.
3. If `collection_id` was supplied, the handler calls `storage.get_collection()`; `None` becomes `HTTPException(400, "Collection not found")` (`api.py:80-83`).
4. `Prompt(**prompt_data.model_dump())` builds the stored object. `id`, `created_at` and `updated_at` come from default factories (`models.py:35-37`). Each factory is called separately, so `created_at` and `updated_at` can differ by microseconds.
5. `storage.create_prompt()` (`storage.py:18-20`) does `self._prompts[prompt.id] = prompt` and returns the same object. No copy is made; what is stored is what is returned.
6. FastAPI serialises through `response_model=Prompt` and returns 201.

`utils.py` is not involved on create.

### Listing prompts — `GET /prompts`

A four-stage pipeline over a fresh copy of the whole store (`api.py:43-62`):

`storage.get_all_prompts()` → `filter_prompts_by_collection()` (only if `collection_id` given; exact string compare) → `search_prompts()` (only if `search` given; case-insensitive substring over **title and description only** — I confirmed `?search=C` returns nothing for a prompt whose `content` is `"C"`) → `sort_prompts_by_date(descending=True)` → `PromptList(total=len(prompts))`.

`total` is the count *after* filtering, not the size of the store. There is no pagination. The sort is where Bug #3 lives: `sort_prompts_by_date` ignores its `descending` argument and always sorts ascending by `created_at` (`utils.py:14`).

### Replacing a prompt — `PUT /prompts/{id}`

`storage.get_prompt()` → 404 if `None` → if `collection_id` given, `storage.get_collection()` → 400 if `None` → construct a **new** `Prompt` copying `id` and `created_at` from the existing object → `storage.update_prompt()` swaps the dict entry (`api.py:89-113`).

Two consequences. First, because `PromptUpdate` declares exactly the same required fields as `PromptCreate`, PUT is a full replacement: leave `description` out of the body and it becomes `None`. Second, the new object also copies `updated_at` from the old one (`api.py:110`) — that is Bug #2; the field never changes after creation.

### Deleting a collection — `DELETE /collections/{id}`

`storage.delete_collection()` is a bare `del` on the collections dict (`storage.py:52-56`); the handler returns 404 if it reports `False`, otherwise 204 (`api.py:149-160`). The prompts dict is never touched. I ran a script to see what that does to a prompt that was in the deleted collection:

- `GET /prompts` still lists it, with `collection_id` pointing at the deleted id.
- `GET /prompts?collection_id=<deleted id>` still returns it — the filter is a plain string compare.
- `GET /collections/<deleted id>` is 404.
- `PUT /prompts/{id}` sending the prompt back *unchanged* returns **400 "Collection not found"**, because the handler re-validates `collection_id` on every update.

That last one is the real damage from Bug #4: an ordinary read-edit-save round trip on an orphaned prompt fails until the client clears `collection_id` by hand. The API rejects as input the very state it produced.

### Errors

There is no custom exception handling. `HTTPException` → `{"detail": ...}` with the given status. Anything else → 500 with no body detail.

## 4. Models and relationships

```
PromptBase            title: str (1–200) · content: str (≥1) · description: str? (≤500) · collection_id: str?
├── PromptCreate      no additional fields — body of POST /prompts
├── PromptUpdate      no additional fields — body of PUT /prompts/{id}; identical to PromptCreate
└── Prompt            + id: str · created_at: datetime · updated_at: datetime — stored object and response model

CollectionBase        name: str (1–100) · description: str? (≤500)
├── CollectionCreate  no additional fields — body of POST /collections
└── Collection        + id: str · created_at: datetime — no updated_at, no list of prompts

PromptList            prompts: List[Prompt] · total: int
CollectionList        collections: List[Collection] · total: int
HealthResponse        status: str · version: str
```

**How prompts and collections relate.** Many prompts to one optional collection, represented only by the string `Prompt.collection_id`. A `Collection` has no reference back to its prompts. The only "join" is a linear scan — `storage.get_prompts_by_collection()` or `utils.filter_prompts_by_collection()`, which do the same thing. The link is validated when a prompt is created or replaced (400 if the collection does not exist) and nowhere else; in particular deleting a collection does not check or update anything.

**Identifiers and timestamps.** Ids are `str(uuid4())`. Timestamps are `datetime.utcnow()` — naive, no timezone — and serialise as `2026-08-22T01:26:06.085695` with no `Z`, so clients must treat them as UTC by convention. `utcnow()` is deprecated in Python 3.12; the test run prints the warning 19 times.

**Pydantic notes.** `Prompt` and `Collection` use the Pydantic v1 style `class Config: from_attributes = True`. Pydantic 2.5 honours it with a deprecation warning. Nothing in the code constructs a model from attributes, so the setting is inert.

**What this means for PATCH.** `PromptUpdate` cannot be reused for partial updates because every field on it is required. A partial-update model needs every field optional with a `None` default. Because `description` and `collection_id` are already nullable, "omitted" and "explicitly set to null" have to be told apart — `model_dump(exclude_unset=True)` is the Pydantic v2 way to do that.

## 5. Storage layer

`Storage` (`storage.py:11-66`) is two dicts, `_prompts` and `_collections`, keyed by id. Single-key operations (`get_*`, `create_*`, `update_prompt`, `delete_*`) are dict lookups. `get_all_prompts()`, `get_all_collections()` and `get_prompts_by_collection()` scan and return new lists. `clear()` empties both dicts and exists for the tests.

Limitations I can point to in the code:

1. **Volatile.** Everything lives in process memory; a restart empties the store. The module docstring says this is deliberate and would be replaced by a database.
2. **Process-local.** Running uvicorn with more than one worker would give each worker its own independent store.
3. **Read-modify-write is not atomic.** `PUT` does `get_prompt` then `update_prompt` as two separate calls. Individual dict operations are safe under the GIL, so the store cannot corrupt, but two concurrent updates to the same id are last-writer-wins.
4. **It hands out live references.** `get_prompt()` returns the stored object itself. Mutating that object changes the store without going through `update_prompt()`. The existing handlers never do this — they build a fresh `Prompt` and call `update_prompt()` — and I treat that as the codebase's convention.
5. **No referential integrity.** `Storage` has no idea prompts reference collections. `delete_collection()` deletes one key and nothing else.
6. **No pagination or indexing.** Every list, filter and search walks the whole store.
7. **`update_prompt()` returns `None` for an unknown id** rather than raising. The handler checks existence first so this branch is never reached today.

## 6. External dependencies

**Declared in `backend/requirements.txt`, all pinned:**

| Package | Version | Role |
|---|---|---|
| `fastapi` | 0.109.0 | Web framework, routing, validation, OpenAPI |
| `uvicorn` | 0.27.0 | ASGI server |
| `pydantic` | 2.5.3 | Models and request/response validation |
| `pytest` | 7.4.4 | Test runner |
| `pytest-cov` | 4.1.0 | Coverage plugin (not used by any provided config) |
| `httpx` | 0.26.0 | Required by Starlette's `TestClient` |

**Transitive packages that actually get installed** (checked with `importlib.metadata` in the environment I ran the tests in): `starlette` 0.35.1 (routing, middleware, `TestClient`), `pydantic-core` 2.14.6, `anyio`, `sniffio`, `typing-extensions`, `annotated-types`, `h11` (HTTP/1.1 for uvicorn), `click` (uvicorn's CLI), `httpcore`, `idna`, `certifi` (httpx), and `coverage`, `pluggy`, `iniconfig`, `packaging` (pytest).

**Standard library:** `datetime`, `uuid`, `typing`, and `re` (inside `extract_variables`).

**Runtime:** the README asks for Python 3.10+; I used 3.12.

**What it does not depend on:** no database, no network calls, no environment variables, no configuration file. The `config.yaml` at the repository root is a model list for an AI coding assistant (OpenRouter entries) — nothing under `backend/` reads it.

## 7. Things that exist but are not wired up

Worth knowing so nobody assumes they are in use. I grepped for callers; each has none.

- `utils.validate_prompt_content()` — a "≥10 characters" rule that no route applies.
- `utils.extract_variables()` — pulls `{{name}}` placeholders out of content; the README advertises this feature but no route exposes it.
- `storage.get_prompts_by_collection()` — the natural query for handling Bug #4; currently unused.
- `backend/frontend/`, `docs/`, `specs/` — empty apart from `.gitkeep`.

## 8. Context strategy

For each stage of the work I note whether I gave the AI the whole repository or specific files, and why. The reasons are based on the size of the code (587 lines across nine Python files) and how tightly it is coupled (every handler goes through the one `storage` singleton). Log IDs refer to `docs/prompt-log.md`.

| Stage | Context given | Why | Log |
|---|---|---|---|
| First-pass exploration (structure, create flow) | Whole repo | Small enough to hold entirely. The tiers are coupled through the shared `storage` object, so reading `api.py` alone would not show where data actually goes. | P-01 |
| Targeted behaviour question (collection delete) | Two functions (`api.py:149-160`, `storage.py:52-59`) plus a short script run against the app | The delete path is self-contained. For what happens *afterwards* — which crosses into `PUT` and the list filter — running it was more reliable than reasoning about it. | P-02 |
| Filling in the remaining model headings | Whole repo plus executed checks (route introspection, serialisation, search scope, installed packages) | The accuracy criterion fails on any missed route or dependency, so I needed full coverage; runtime claims were verified by execution rather than inference. | P-03 |
| Bug fixes #1–#3 | *Planned:* the single function containing each bug | Each is a local, one-line defect with no cross-file effect. | *to be logged* |
| Bug fix #4 | *Planned:* `delete_collection` in `api.py` plus `storage.py` | The fix spans the two tiers: the handler orchestrates, the storage layer supplies the query. | *to be logged* |
| PATCH endpoint | *Planned:* `api.py`, `models.py`, `tests/` | Needs a new model, must mirror the PUT handler's pattern, and must follow the existing test style. | *to be logged* |
| Docstrings and README | *Planned:* one function at a time; `README.md` on its own | Documenting one unit at a time keeps the docstring tied to what that function actually does. | *to be logged* |

The rows marked *planned* describe the intended approach and will be replaced with what actually happened, with log references, once those stages are done.
