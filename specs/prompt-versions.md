# Spec: Prompt Version History

Status: Draft — planned for a future module. Not yet implemented.

## Overview and goals

Right now, `PUT` and `PATCH /prompts/{id}` overwrite a prompt's `title`, `content`, and `description` in place with no record of what they used to be. There is no way to see how a prompt evolved or to recover an earlier wording after a bad edit.

This spec adds automatic version history for prompts: every time a prompt is created, or an edit actually changes its content, a snapshot is saved. Users can list a prompt's history, view any past version, and restore a past version as the new current state.

**Goals**

- Every meaningful edit to a prompt's `title`, `content`, or `description` is recoverable.
- History is automatic — nothing new for a client to opt into when creating or editing a prompt through the existing endpoints.
- No-op edits (a `PATCH`/`PUT` that changes nothing) don't create version noise.
- Restoring an old version is itself an auditable edit, not a silent rewrite of history.

**Out of scope**

- Versioning `collection_id` — moving a prompt between collections is not a content change and never creates a version.
- Diffing between two versions.
- Deleting an individual version.
- Versioning collections themselves.

## User stories

### US-1: Every prompt has a version 1 from creation

As a user, when I create a prompt, I want its initial content saved as version 1, so history starts from day one instead of from the first edit.

**Acceptance criteria**

- Immediately after `POST /prompts` succeeds, `GET /prompts/{id}/versions` returns exactly one version, `version_number: 1`, whose `title`/`content`/`description` equal what was just created.
- That version's `created_at` equals the created prompt's `created_at`.

### US-2: Edits that change content create a new version

As a user, when I `PUT` or `PATCH` a prompt and actually change `title`, `content`, or `description`, I want a new version saved, so I can see what changed and when.

**Acceptance criteria**

- A `PATCH` that changes `content` only causes `GET /prompts/{id}/versions` to grow from N versions to N+1, and the new version's `version_number` is `N+1`.
- A `PUT` that changes any of `title`/`content`/`description` (even if others are unchanged) creates exactly one new version, not one per changed field.
- A `PATCH` whose body only sets `collection_id` (no `title`/`content`/`description` present) does **not** create a new version.

### US-3: No-op edits don't pollute history

As a user, when I `PUT` or `PATCH` a prompt with the exact same `title`, `content`, and `description` it already has, I don't want a new version created, so history reflects real changes only.

**Acceptance criteria**

- `PUT /prompts/{id}` with a body identical to the prompt's current `title`, `content`, and `description` (any `collection_id`) does not increase the version count.
- `updated_at` is still bumped on this no-op edit, matching existing `PUT`/`PATCH` behavior — only the *version count* is unaffected, not the timestamp behavior already in place.
- An empty-body `PATCH /prompts/{id}` (`{}`) does not create a new version.

### US-4: List a prompt's version history

As a user, I want to list every saved version of a prompt, newest first, so I can browse how it changed over time.

**Acceptance criteria**

- `GET /prompts/{id}/versions` on a prompt with 3 versions returns all 3, ordered by `version_number` descending (3, 2, 1), with `"total": 3`.
- `GET /prompts/{id}/versions` on an unknown or soft-deleted prompt id returns `404` with `{"detail": "Prompt not found"}`.

### US-5: View a specific past version

As a user, I want to fetch one specific version by number, so I can inspect exactly what it said.

**Acceptance criteria**

- `GET /prompts/{id}/versions/2` on a prompt that has a version 2 returns that version's stored `title`/`content`/`description`/`created_at`.
- `GET /prompts/{id}/versions/99` on a prompt that only has versions 1–3 returns `404` with `{"detail": "Version not found"}`.
- `GET /prompts/{id}/versions/not-a-number` returns `422` (FastAPI's built-in path-parameter type validation, since `version_number` is typed as `int` — no custom validation code needed).

### US-6: Restore a past version

As a user, I want to make an old version the prompt's current content again, so I can undo a bad edit without retyping it.

**Acceptance criteria**

- `POST /prompts/{id}/versions/2/restore` on a prompt currently at version 4 sets the live prompt's `title`/`content`/`description` to version 2's values, leaves `collection_id` untouched, bumps `updated_at`, and returns `200` with the updated `Prompt`.
- After that restore, `GET /prompts/{id}/versions` shows 5 versions total, and version 5's `title`/`content`/`description` equal version 2's (restore always appends, never rewrites or removes versions 3–4).
- Restoring the prompt's own current version (e.g. restoring version 4 while version 4 is current) still succeeds and still creates version 5 with identical content to version 4 — restore never short-circuits as a no-op, even when nothing would visibly change.
- `POST /prompts/{id}/versions/99/restore` for a version number that doesn't exist returns `404` with `{"detail": "Version not found"}`, and does not create a new version.
- `POST /prompts/{id}/versions/2/restore` on an unknown or soft-deleted prompt id returns `404` with `{"detail": "Prompt not found"}`.

## Data model changes

### New model: `PromptVersion` (`app/models.py`)

```python
class PromptVersion(BaseModel):
    """An immutable snapshot of a prompt's editable content at one point in time.

    Attributes:
        id: Server-generated uuid4 string, unique across all versions.
        prompt_id: The id of the Prompt this version belongs to.
        version_number: 1-based, increasing per prompt. 1 is always the
            state at creation.
        title: The prompt's title at this version.
        content: The prompt's template text at this version.
        description: The prompt's description at this version, or None.
        created_at: When this version was captured — equals the prompt's
            created_at for version_number 1, and the triggering edit's
            updated_at for every later version.
    """
    id: str = Field(default_factory=generate_id)
    prompt_id: str
    version_number: int
    title: str
    content: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=get_current_time)


class PromptVersionList(BaseModel):
    """Response body for GET /prompts/{id}/versions.

    Attributes:
        versions: The prompt's versions, newest (highest version_number) first.
        total: The number of versions in `versions`.
    """
    versions: List[PromptVersion]
    total: int
```

No changes to the existing `Prompt`, `PromptCreate`, `PromptUpdate`, or `PromptPatch` models — versioning is derived from the same fields they already carry.

### Storage changes (`app/storage.py`)

- New instance attribute: `self._versions: Dict[str, List[PromptVersion]] = {}`, keyed by `prompt_id`.
- `create_prompt_version(prompt_id: str, title: str, content: str, description: Optional[str], created_at: datetime) -> PromptVersion` — appends a new `PromptVersion` with `version_number = len(self._versions.get(prompt_id, [])) + 1` and returns it.
- `get_prompt_versions(prompt_id: str) -> List[PromptVersion]` — returns the prompt's versions in insertion order (callers sort descending for display, matching how `get_all_prompts` returns unsorted and `api.py` sorts).
- `get_prompt_version(prompt_id: str, version_number: int) -> Optional[PromptVersion]` — returns the matching version or `None`.
- Individual versions are never removed. There is no `delete_prompt_version`. Soft-deleting a prompt (`delete_prompt`) does not touch `_versions` — the history rows persist in storage, but the API layer 404s all version endpoints for a soft-deleted prompt (see below), so they become unreachable through the API, not physically deleted.

### API-layer logic (`app/api.py`)

- `create_prompt`: after `storage.create_prompt(...)`, call `storage.create_prompt_version(prompt.id, prompt.title, prompt.content, prompt.description, prompt.created_at)`.
- `update_prompt` (`PUT`) and `patch_prompt`: after computing the new field values but before/alongside calling `storage.update_prompt(...)`, compare the new `title`/`content`/`description` to the *existing* prompt's values. If any differ, call `create_prompt_version` with the new values and the same `updated_at` used for the prompt update. If none differ, skip version creation — the prompt update (including the `updated_at` bump) still happens as it does today.
- `restore_prompt_version` (backing `POST /prompts/{id}/versions/{version_number}/restore`): look up the prompt via the same 404 check every other prompt sub-resource endpoint uses; look up the version via `storage.get_prompt_version(prompt_id, version_number)`, `404 "Version not found"` if it's `None`. Compute one `updated_at = get_current_time()` and reuse that single value for both calls below — do not call `get_current_time()` twice, or the version's `created_at` and the prompt's `updated_at` will drift by microseconds:
  1. Build the updated `Prompt` from the existing prompt's `id`/`created_at`/`collection_id`/`deleted_on`, the restored version's `title`/`content`/`description`, and this `updated_at`; call `storage.update_prompt(prompt_id, updated_prompt)`.
  2. Call `storage.create_prompt_version(prompt_id, version.title, version.content, version.description, updated_at)` — unconditionally, with no "did anything change" check. Unlike `PUT`/`PATCH`, `restore` always creates a new version (US-6), even when its content is identical to the prompt's current state.
  3. Return the updated `Prompt` (step 1's result), not the new version.

## API endpoints

| Method | Endpoint | Description | Responses |
|---|---|---|---|
| `GET` | `/prompts/{id}/versions` | List a prompt's versions, newest first | `200` `404` |
| `GET` | `/prompts/{id}/versions/{version_number}` | Get one version | `200` `404` `422` |
| `POST` | `/prompts/{id}/versions/{version_number}/restore` | Make a past version the prompt's current content | `200` `404` `422` |

### `GET /prompts/{id}/versions`

**Request**

```bash
curl http://localhost:8000/prompts/80184e58-ec8f-43de-bd66-f35c1e3bd7f6/versions
```

**Response — `200`**

```json
{
  "versions": [
    {
      "id": "c1a0...",
      "prompt_id": "80184e58-ec8f-43de-bd66-f35c1e3bd7f6",
      "version_number": 2,
      "title": "Security review v2",
      "content": "Look for vulnerabilities:\n\n{{code}}",
      "description": "Now covers OWASP top 10",
      "created_at": "2026-08-24T05:43:00.871126"
    },
    {
      "id": "80184e58-...",
      "prompt_id": "80184e58-ec8f-43de-bd66-f35c1e3bd7f6",
      "version_number": 1,
      "title": "Security review",
      "content": "Look for vulnerabilities in:\n\n{{code}}",
      "description": "Security-focused review",
      "created_at": "2026-08-24T05:42:37.701035"
    }
  ],
  "total": 2
}
```

**Error — `404`** (unknown or soft-deleted prompt id): `{"detail": "Prompt not found"}`

### `GET /prompts/{id}/versions/{version_number}`

**Request**

```bash
curl http://localhost:8000/prompts/80184e58-ec8f-43de-bd66-f35c1e3bd7f6/versions/1
```

**Response — `200`**

```json
{
  "id": "80184e58-...",
  "prompt_id": "80184e58-ec8f-43de-bd66-f35c1e3bd7f6",
  "version_number": 1,
  "title": "Security review",
  "content": "Look for vulnerabilities in:\n\n{{code}}",
  "description": "Security-focused review",
  "created_at": "2026-08-24T05:42:37.701035"
}
```

**Errors**

- `404` — prompt unknown/soft-deleted: `{"detail": "Prompt not found"}`
- `404` — prompt exists but has no such version: `{"detail": "Version not found"}`
- `422` — `version_number` isn't an integer (FastAPI path-parameter validation)

### `POST /prompts/{id}/versions/{version_number}/restore`

**Request**

```bash
curl -X POST http://localhost:8000/prompts/80184e58-ec8f-43de-bd66-f35c1e3bd7f6/versions/1/restore
```

**Response — `200`** (the updated `Prompt`, same shape as `PUT`/`PATCH` responses)

```json
{
  "title": "Security review",
  "content": "Look for vulnerabilities in:\n\n{{code}}",
  "description": "Security-focused review",
  "collection_id": "f54e432e-405a-4739-9911-b89a993f1f95",
  "id": "80184e58-ec8f-43de-bd66-f35c1e3bd7f6",
  "created_at": "2026-08-24T05:42:37.701035",
  "updated_at": "2026-08-24T06:10:00.000000",
  "deleted_on": null
}
```

**Errors**

- `404` — prompt unknown/soft-deleted: `{"detail": "Prompt not found"}`
- `404` — no such version on this prompt: `{"detail": "Version not found"}`
- `422` — `version_number` isn't an integer

## Error conditions and edge cases

- **Soft-deleted prompt.** Every version endpoint for a soft-deleted prompt returns `404 {"detail": "Prompt not found"}` — identical to how the existing prompt endpoints treat a soft-deleted id. There is no way to view or restore history for a deleted prompt through the API.
- **Deleting a prompt does not delete its versions.** They stay in storage but become unreachable (see above) unless the prompt is later un-deleted — which this API does not support, so in practice they are permanently unreachable once a prompt is deleted.
- **Restoring never no-ops.** Even restoring the current version creates a new version (see US-6). There is no special case that skips version creation because "nothing changed" — that no-op suppression only applies to `PUT`/`PATCH` (US-3), not to `restore`.
- **`collection_id` is never part of a version and is never touched by restore.** Restoring content does not move a prompt between collections.
- **Version snapshots cannot fail validation.** Because a version is only ever built from an already-validated `Prompt` (at creation) or an already-validated update (which passed the same `Field` constraints as `Prompt`), there is no scenario where creating a version itself returns a validation error — the constraint check already happened one layer up, on the `Prompt` write that triggered it.
- **`version_number` is per-prompt, not global.** Two different prompts each have their own version 1. There is no cross-prompt version id in the URL — version numbers are only meaningful combined with a `prompt_id`.
- **No version limit.** Every qualifying edit adds a version indefinitely; this spec does not add pruning or a maximum history length.

## Implementation notes

- New endpoints belong in `app/api.py` under a new `# ============== Prompt Version Endpoints ==============` section, placed after the existing Prompt Endpoints.
- Tests belong in a new `TestPromptVersions` class in `backend/tests/test_api.py`, following the existing per-resource grouping (`TestHealth`, `TestPrompts`, `TestCollections`).
- Per `.github/copilot-instructions.md`: write a failing test for each acceptance criterion above before implementing; every new function gets a Google-style docstring; `storage.py` changes must not raise `HTTPException` — 404s for unknown prompts/versions are raised in `app/api.py`, same split as every existing endpoint.
- Once implemented, add these three endpoints to `docs/API_REFERENCE.md` following its existing per-endpoint format (request example, response example, errors).
