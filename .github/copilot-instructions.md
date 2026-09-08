# Copilot instructions — PromptLab backend

Repo-specific conventions for AI-generated code in this project. These are drawn from how `backend/app/` and `backend/tests/` are actually written, not generic Python advice — if a suggestion conflicts with something below, follow this file.

## Coding standards

- **Target Python 3.10–3.12 only.** Never suggest syntax or stdlib features exclusive to 3.13+. The pin `pydantic==2.5.3` in `backend/requirements.txt` has no 3.13 wheel for `pydantic-core`, so a 3.13 suggestion will fail to install, not just fail lint.
- **Pydantic v2 idioms only.** Use `model_dump()`, not `.dict()`; use `Field(...)` for constraints, not validators for things a `Field` already expresses (`min_length`, `max_length`). Don't suggest Pydantic v1 patterns (`class Config: orm_mode = True`, `.json()`, etc.).
- **Every function and class gets a Google-style docstring** (`Args:` / `Returns:` / `Raises:` as applicable) that describes actual behavior, defaults, and edge cases — not the function name restated as a sentence. Compare a bad and good example for the same function:

  ```python
  def validate_prompt_content(content: str) -> bool:
      """Validates the prompt content."""   # restates the name — do not do this
  ```

  ```python
  def validate_prompt_content(content: str) -> bool:
      """Check whether prompt content meets the minimum content requirements.

      Content is valid when, after stripping leading/trailing whitespace, it
      is non-empty and at least 10 characters long.

      Args:
          content: The prompt template text to validate.

      Returns:
          True if `content` is non-empty, is not just whitespace, and has at
          least 10 characters once stripped; False otherwise.
      """
  ```
- **Naming:** `snake_case` for functions, variables, and modules; `PascalCase` for Pydantic models and classes; a module-level singleton is lowercase (`storage = Storage()` in `app/storage.py`), never `Storage` or `STORAGE`.

## Preferred patterns and conventions

- **Soft delete, always.** Nothing is ever removed from `Storage`'s dicts. A delete stamps `deleted_on` via `get_current_time()`; every read path (`get_prompt`, `get_all_prompts`, `get_collection`, `get_all_collections`, `get_prompts_by_collection`) filters `deleted_on is None` unless `include_deleted=True` is explicitly requested. New read methods must follow the same filter — don't add a method that returns soft-deleted rows by default.
- **`Storage` returns live objects, not copies.** Mutating a `Prompt`/`Collection` returned from storage mutates the stored record directly. This is intentional (see `update_prompt`); don't "fix" it by adding `.model_copy()` without discussing it — it would break the update-in-place pattern the route handlers rely on.
- **IDs and timestamps are server-generated, never client-supplied.** Use `generate_id()` and `get_current_time()` from `app/models.py` — don't call `uuid4()` or `datetime.utcnow()`/`datetime.now()` directly elsewhere. This keeps ID format and timestamp format (naive UTC) centralized in one place.
- **Partial updates use `model_dump(exclude_unset=True)`** to distinguish "field omitted" from "field explicitly set to `null`" (see `PromptPatch` / `patch_prompt`). Don't use `exclude_none=True` for a `PATCH` body — that erases the "explicit null means clear this field" signal the endpoint depends on.
- **Cross-resource validation lives in the route handler, not the model or storage layer.** E.g., "does `collection_id` point to an active collection?" is checked in `app/api.py` by calling `storage.get_collection(...)`, not inside a Pydantic validator or inside `Storage`. Keep that split: models validate shape, `api.py` validates cross-resource rules, `storage.py` never raises.

### Style (PEP 8)

This codebase follows [PEP 8](https://peps.python.org/pep-0008/) where the existing files already do, and the rules below are grounded in what's actually shipped in `app/*.py` — not restated from the PEP in the abstract. Where existing code falls short of a rule, that's called out explicitly as debt, not as something to copy into new code.

- **Two blank lines before and after every top-level `def`/`class`**, one blank line between methods inside a class (PEP 8 §Blank Lines). Every module in `app/` already does this — e.g. `generate_id`/`get_current_time` in `models.py`, and every class in `models.py`. Match it in new code.
- **Import grouping: standard library, then third-party, then local `app.*` imports, each group separated by a blank line** (PEP 8 §Imports). This is *not* consistently followed today — `app/api.py` puts `fastapi` (third-party) ahead of `typing` (stdlib), and `app/models.py` puts `uuid` (stdlib) after `pydantic` (third-party). Don't propagate that mis-ordering into new imports; group new imports correctly even in a file whose existing imports aren't grouped, and fix the ordering of any import block you're already touching for another reason.
- **Line length: keep new lines at or under 99 characters.** PEP 8's canonical limit is 79, but nothing in this repo enforces it, so 99 — not 79 — is the actual ceiling for new code. One existing line (`storage.py`'s `get_collection` signature) is 104 characters; that's a single already-shipped outlier, not a second, looser ceiling — don't use it to justify writing new lines past 99. Prefer wrapping (parenthesized multi-line expressions, like the import block in `api.py`) over a long single line.
- **Double-quoted strings**, matching the near-universal style across every file in `app/`. The only single-quoted string literal in the codebase is the regex in `utils.py`'s `extract_variables` (`r'\{\{(\w+)\}\}'`) — a stylistic outlier, not an example to follow; it doesn't contain a `"`, so there was no escaping reason for it either. Use double quotes for new strings, and reserve single quotes for the one case that actually justifies them: a string that itself contains a `"`.
- **f-strings for interpolation** (`f"{field} cannot be null"` in `api.py`), never `.format()` or `%`-formatting.
- **Type hints: every function has fully typed parameters. Return types are typed everywhere *except* FastAPI route handlers in `api.py`.** Every function in `models.py`, `storage.py`, and `utils.py` has a return-type annotation; all 11 route handlers in `api.py` (and `Storage.__init__`/`Storage.clear`) omit one, relying on each route's `response_model=` to declare the response contract instead — that split is consistent, not an oversight, so match it: a new route handler follows the existing route handlers (typed params, no return type, `response_model` set); a new function anywhere else gets a full return-type annotation like every other non-route function already has. Keep using `typing.Optional[X]` / `typing.List[X]` (as every existing file does) rather than the newer PEP 604/585 syntax (`X | None`, `list[X]`) — both are valid on this project's Python 3.10–3.12 floor, but mixing the two styles across the same small codebase is worse than picking the one already in use everywhere.
- **No wildcard imports** (`from x import *`) — none exist today; don't introduce one.
- **No trailing whitespace.** Blank lines inside function bodies in both `api.py` (13 instances) and `storage.py` (9 instances) currently have trailing spaces, inherited from the original scaffold; that's pre-existing debt, not a pattern to match — new or touched lines should have none.

## File naming conventions

- `backend/app/api.py` — FastAPI route handlers only. No business logic beyond orchestrating `storage` and `utils` calls and raising `HTTPException`.
- `backend/app/models.py` — Pydantic request/response schemas, plus the tiny generator helpers (`generate_id`, `get_current_time`) they depend on. No route logic.
- `backend/app/storage.py` — the `Storage` class and the module-level `storage` singleton. No FastAPI imports.
- `backend/app/utils.py` — pure functions that take model objects (or primitives) and return a value, with no side effects and no `HTTPException`.
- New modules follow the same one-word, `snake_case.py` convention under `backend/app/` — no `camelCase.py`, no `PascalCase.py`, no multi-word files without underscores.
- Tests mirror the module they cover: `backend/tests/test_api.py` for anything reachable through an HTTP route, `backend/tests/test_utils.py` for pure helpers. A new `app/<name>.py` module gets a matching `tests/test_<name>.py`, not a new file under a different name.

## Error handling approach

- **404** — the referenced id doesn't exist, or refers to a soft-deleted record. Raised in `api.py` after a `storage.get_*` call returns `None`/`False`.
- **400** — the request is well-formed and passes Pydantic validation, but violates a business rule this API enforces itself: an unknown `collection_id`, or a `PATCH` that tries to null out `title`/`content`.
- **422** — left entirely to FastAPI/Pydantic via `Field` constraints on the request model. Don't hand-write validation in a route handler for something a `Field(min_length=..., max_length=...)` already covers.
- **Every handler-raised error body is `{"detail": "<message>"}`.** Don't introduce a different error shape (error codes, nested objects) for a subset of endpoints — the whole API is consistent on this.
- **`storage.py` and `utils.py` never raise for expected failure cases** — they signal "not found" or "no match" via `None`, `False`, or an empty list. Only `api.py` decides what HTTP status a failure becomes.

## Testing requirements

- **Write the failing test before the fix**, per this project's established process (see `docs/prompt-log.md` for the Module 1 examples). A bug fix or new endpoint isn't "shown correct" until there's a test that failed beforehand and passes after.
- **Use the fixtures in `backend/tests/conftest.py`** — `client` (a `TestClient`) and the autouse `clear_storage` fixture. Never instantiate `Storage()` or `TestClient(app)` directly inside a test; that bypasses the isolation `clear_storage` provides between tests.
- **Test API behavior through HTTP**, in `test_api.py`, by calling `client.get/post/put/patch/delete(...)` — not by importing and calling route functions directly. Test pure helpers directly, in `test_utils.py`, by calling the function with constructed `Prompt`/`Collection` objects.
- **Cover the success case and every documented error case.** A new endpoint or modified endpoint needs tests for its `200`/`201`/`204` path and each applicable `400`/`404`/`422` in `docs/API_REFERENCE.md` — not just the happy path.
- **The full suite must pass before a PR**: `cd backend && pytest tests/ -v`. A `DeprecationWarning` about `datetime.utcnow()` is expected (see README's Known Limitations) and is not a failing test.
