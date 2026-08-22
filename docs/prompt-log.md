# Prompt Log — Module 1 Brownfield Challenge

**Tool:** Claude Code (CLI), model `claude-fable-5`
**Author:** Brandon Johnson
**Period:** 2026-08-21 onward
**Scope:** Every substantive prompt sent while understanding the PromptLab backend, fixing Bugs #1–#4, implementing `PATCH /prompts/{id}`, and writing the documentation. Purely mechanical prompts ("yes, go ahead", "run the tests again") are omitted unless they form part of an iteration chain.

Logging began after the log format itself was agreed; the earlier setup conversation (reading the project brief, choosing the Bug #4 strategy, choosing an interactive workflow) is summarised in `docs/SYSTEM_MODEL.md` but not logged entry-by-entry here.

## Legend

| Field | Meaning |
|---|---|
| **ID** (`P-nn`) | Stable identifier. `docs/ai-verification-note.md` and the context strategy section of `docs/SYSTEM_MODEL.md` cite entries by this ID. |
| **Stage** | Exploration · Bug fix · PATCH endpoint · Documentation · Verification |
| **Context given** | What the AI was pointed at for this prompt: *Whole repo*, a list of specific files, or *None (conversation only)*. |
| **Why that context** | One line justifying the choice, based on the size or coupling of the code. |
| **Prompt (verbatim)** | The exact text sent. Never paraphrased — iteration is only judgeable from exact wording. |
| **Response (summarised)** | The relevant part of what came back. Quoted verbatim wherever the exact wording matters (especially for a caught mistake). |
| **Outcome** | *Accepted* · *Iterated → P-nn* · *Wrong → see AI-verification note* |
| **Why I changed my next prompt** | One line: what was missing or wrong, and whether the next prompt narrowed context, added a constraint, or restructured the ask. |

## Conventions

1. **Iteration chains are tagged in the heading.** An entry that narrows context, adds a constraint, or restructures a previous prompt is titled `P-nn — <task> (iteration of P-mm: <narrowed context | added constraint | restructured>)`.
2. **Mistakes are quoted verbatim.** When a response turns out to be wrong, the incorrect part is quoted exactly so the AI-verification note can cite it against the source line that contradicts it.

---

## Entries

## P-01 — Explain the codebase structure and the create-prompt request flow

**Stage:** Exploration
**Context given:** Whole repo (`backend/main.py`, `backend/app/*.py`, `backend/tests/*.py`, `requirements.txt`, `README.md`, `config.yaml`)
**Why that context:** The entire backend is 587 lines across 9 Python files, and every route goes through the single module-level `storage` singleton — small enough to hold whole, and coupled enough that reading one file in isolation would hide how the tiers connect.

**Prompt (verbatim):**
> Explain the structure of this codebase.  Walk me through the request flow for creating a prompt.

**Response (summarised — relevant part):**
Claude produced a file tree and described three thin tiers: `api.py` (10 routes, reference-checking done in handlers), `models.py` (Pydantic v2: `PromptBase → PromptCreate/PromptUpdate → Prompt`; `CollectionBase → CollectionCreate → Collection`, which has no `updated_at`), and `storage.py` (two dicts, no persistence). Stated the prompt↔collection relationship is one-directional by string `collection_id`, enforced on `POST`/`PUT` (400) but not on collection delete (Bug #4). Identified dead code with zero callers (verified by grep): `utils.validate_prompt_content`, `utils.extract_variables`, `storage.get_prompts_by_collection`. Noted `config.yaml` is an AI-assistant model config not read by the app.

`POST /prompts` flow as given: CORS middleware → route match (`api.py:77`) → Pydantic validation of `PromptCreate` (422 on failure; the `≥10 chars` rule in `utils.validate_prompt_content` is *not* applied) → handler checks `collection_id` exists (400 if not, `api.py:80-83`) → `Prompt(**model_dump())` generates `id` (uuid4), `created_at`, `updated_at` (`datetime.utcnow()`, naive) → `storage.create_prompt` stores the object in `_prompts` dict → serialised via `response_model=Prompt`, status 201. `utils.py` is not involved on create.

**Outcome:** Accepted
**Why I changed my next prompt:** Structure and create flow were clear; moved to the one relationship the overview flagged as unenforced (collection delete) and narrowed context to that path.

## P-02 — Explain collection-deletion behaviour and its effect on prompts

**Stage:** Exploration
**Context given:** Files: `backend/app/api.py` lines 149–160 (`delete_collection`), `backend/app/storage.py` lines 52–59 (`delete_collection`, `get_prompts_by_collection`), plus a 10-line script run against the live app to confirm downstream effects.
**Why that context:** The delete path is self-contained — two functions, ~20 lines — so whole-repo context adds nothing. Behavioural consequences (what later requests do with an orphan) were checked by execution rather than reasoning, since they cross into `PUT /prompts` and `GET /prompts` filter logic.

**Prompt (verbatim):**
> Explain the collection-deletion behavior and what happens to its prompts

**Response (summarised — relevant part):**
`DELETE /collections/{id}` calls `storage.delete_collection` (a bare `del` on the dict), 404s if absent, else returns 204. `_prompts` is never touched. Confirmed by running it: after delete, the orphan still appears in `GET /prompts` with the stale `collection_id`; `GET /prompts?collection_id=<deleted>` still returns it (pure string filter); `GET /collections/<deleted>` is 404; and — the practical damage — `PUT /prompts/{id}` echoing the orphan back unchanged returns **400 "Collection not found"** because `api.py:96-99` re-validates `collection_id` on every update. Flagged that `storage.get_prompts_by_collection` (zero callers) is the natural tool for the null-the-field fix, and that the provided `test_delete_collection_with_prompts` asserts the buggy behaviour and is expected to be updated per its own docstring.

**Outcome:** Accepted
**Why I changed my next prompt:** Delete behaviour was fully explained; broadened back out to whole-repo context to cover every remaining SYSTEM_MODEL.md heading in one pass, since C1.1 fails on any omitted route or dependency.

## P-03 — Cover the remaining SYSTEM_MODEL.md headings

**Stage:** Exploration
**Context given:** Whole repo, plus an executed probe script (route introspection via `app.routes`, datetime serialisation, search scope, `uvicorn.run` source, installed package versions via `importlib.metadata`).
**Why that context:** C1.1 requires *every* route and *every* dependency; omission is the listed failure mode, so the full repo was needed. Claims about runtime behaviour (auto-generated routes, naive-datetime JSON format, whether search covers `content`, whether `reload=True` works with an app object, real transitive dependency versions) were verified by execution rather than stated from memory.

**Prompt (verbatim):**
> What else can you tell me about the Architecture, Entry points, Data flow, Models and relationships, Storage layer, External dependencies, and Context strategy section?

**Response (summarised — relevant part):**
Per heading: **Architecture** — single-module monolith, global `storage` singleton created on import, wide-open CORS (`*` + credentials, which browsers reject), and `main.py` passes the app *object* to `uvicorn.run(..., reload=True)` so reload is silently disabled (uvicorn source contains the "must pass ... as an import string" warning). **Entry points** — table of all 10 routes with handler, success code and error codes, plus FastAPI's auto `/docs`, `/redoc`, `/openapi.json` (confirmed via `app.routes`); no PATCH and no collection update route. **Data flow** — `GET /prompts` is a 4-stage pipeline (all → filter → search → sort); search covers title+description only, not `content` (confirmed: `?search=C` returned 0); PUT is full-replace because `PromptUpdate == PromptCreate`; unhandled exceptions become bare 500s (re-raised under `TestClient`). **Models** — inheritance tree, IDs uuid4, timestamps naive `utcnow()` serialised without `Z`, v1-style `Config` inert; PATCH will need an all-`Optional` model with `exclude_unset`. **Storage** — seven enumerated limitations (volatile, process-local, non-atomic RMW, live references, no referential integrity, no pagination, `update_prompt` returns `None` on miss). **Dependencies** — six pinned direct deps; verified transitive list with versions; stdlib `datetime`/`uuid`/`typing`/`re`; no DB, network, env vars; `config.yaml` unused by the app. **Context strategy** — a stage-by-stage table (whole-repo for exploration → file/function-level for fixes → single-unit for docs) cross-referenced to log IDs.

**Outcome:** Partly wrong → see `docs/ai-verification-note.md`. The response stated, verbatim: *"`main.py` passes the app object to `uvicorn.run(..., reload=True)` so reload is silently disabled ... `python main.py` works, but edits require a restart."* The first half is right; the conclusion is not. Uvicorn 0.27 logs the warning and then calls `sys.exit(1)` (`uvicorn.run` source, the branch under `if (config.reload or config.workers > 1) and not isinstance(app, str)`). Confirmed by running `python main.py`: it prints the warning and exits with status 1 without binding a port. The claim was made from having seen the warning *string* in the source without reading the lines after it.
**Why I changed my next prompt:** The SYSTEM_MODEL.md draft was requested with an explicit accuracy constraint ("MUST be accurate to the codebase, DO NOT GUESS"), which prompted re-verifying the `reload` claim by reading the surrounding source and executing `main.py` — that is what surfaced the error. The draft was written with the corrected behaviour. (The draft-generation prompt itself was not logged at Brandon's request.)

