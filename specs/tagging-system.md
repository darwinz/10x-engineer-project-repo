# Spec: Tagging System

Status: Draft — planned for a future module. Not yet implemented.

## Overview and goals

Collections are the only way to group prompts today, and a prompt can belong to at most one. That doesn't cover cross-cutting organization — e.g. a prompt might belong to the "Code Review" collection but also deserve the labels `security` and `python`, shared with prompts in other collections.

This spec adds tags: short, reusable, many-to-many labels. A tag is a first-class resource with its own CRUD; prompts reference zero or more tags by id; prompts can be filtered by tag alongside the existing `collection_id`/`search` filters.

**Goals**

- A prompt can carry multiple tags, independent of its (single, optional) collection.
- Tags are reusable, named resources — `security` is one tag shared by every prompt that uses it, not a copy per prompt.
- Tag names are unique (case-insensitively) among active tags, so `Security` and `security` can't both exist as separate tags.
- Attaching/detaching is idempotent and safely retryable.
- Deleting a tag cleanly detaches it everywhere instead of leaving dangling references.

**Out of scope**

- Tag colors, categories, or hierarchies (parent/child tags).
- Bulk tag operations (attach one tag to many prompts in one call).
- Renaming a tag (would require a dedicated `PATCH /tags/{id}` and a merge story for name collisions — deferred).
- Filtering prompts by multiple tags at once (`AND`/`OR` across tags) — only a single `?tag_id=` filter, matching the existing single-`collection_id`-filter shape.

## User stories

### US-1: Create a tag

As a user, I want to create a named tag once, so I can reuse it across many prompts.

**Acceptance criteria**

- `POST /tags` with `{"name": "security"}` returns `201` with a `Tag` carrying a server-generated `id`, the given `name`, `created_at`, and `deleted_on: null`.
- `POST /tags` with `{"name": ""}` returns `422` with a field-level message identifying `name` (Pydantic `min_length=1`), not a hand-written 400.
- `POST /tags` with a `name` longer than 32 characters returns `422` with a field-level message identifying `name` (Pydantic `max_length=32`), not a hand-written 400.
- `POST /tags` with `{"name": "  security  "}` (leading/trailing whitespace) stores and returns `"name": "security"` — the name is trimmed before validation and storage.
- `POST /tags` with `{"name": "Security"}` when an active tag named `security` already exists returns `409` with `{"detail": "Tag with this name already exists"}`. The comparison is case-insensitive on the trimmed name.
- Creating a tag with a name that matches a *soft-deleted* tag's name (any case) succeeds — the uniqueness check only considers active tags.

### US-2: List and look up tags

As a user, I want to list all tags and fetch one by id, so I can browse what's available and confirm a tag's details.

**Acceptance criteria**

- `GET /tags` returns `200` with `{"tags": [...], "total": N}` listing every active tag, ordered oldest-created first (creation order, not sorted by name or re-sorted by date) — the same ordering `GET /collections` already uses, unlike `GET /prompts`, which sorts newest-first.
- `GET /tags?search=sec` returns only active tags whose `name` contains `sec`, case-insensitive via `.lower()` — same matching rule and mechanism as `GET /prompts?search=`.
- `GET /tags/{id}` returns `200` with that tag, or `404` with `{"detail": "Tag not found"}` for an unknown or soft-deleted id.

### US-3: Delete a tag

As a user, I want to delete a tag I no longer need, so it stops appearing as an option, without deleting any prompts.

**Acceptance criteria**

- `DELETE /tags/{id}` on an active tag returns `204` with an empty body.
- After that delete, `GET /tags/{id}` returns `404`, and the tag no longer appears in `GET /tags`.
- After that delete, every prompt that had this tag attached has it removed from its `tag_ids` — confirmed by `GET /prompts/{id}` showing the tag's id no longer present. **No prompt is deleted or otherwise modified beyond losing this one tag reference.**
- `DELETE /tags/{id}` on an unknown or already-deleted id returns `404` with `{"detail": "Tag not found"}`.

### US-4: Attach a tag to a prompt

As a user, I want to add an existing tag to a prompt, so the prompt shows up when I filter by that tag.

**Acceptance criteria**

- `POST /prompts/{prompt_id}/tags` with `{"tag_id": "<id>"}` returns `200` with the updated `Prompt`, whose `tag_ids` now includes `<id>`.
- Calling it again with the same `tag_id` (already attached) returns `200` with the `Prompt` unchanged — no duplicate entry in `tag_ids`, and no error. Attaching is idempotent.
- `POST /prompts/{prompt_id}/tags` for an unknown or soft-deleted `prompt_id` returns `404` with `{"detail": "Prompt not found"}`.
- `POST /prompts/{prompt_id}/tags` with a `tag_id` that doesn't exist or is soft-deleted returns `404` with `{"detail": "Tag not found"}`.
- A prompt already carrying 10 tags returns `400` with `{"detail": "A prompt cannot have more than 10 tags"}` when attaching an 11th *distinct* tag. Re-attaching one of the 10 it already has still succeeds (per the idempotency rule above) even at the cap.

### US-5: Detach a tag from a prompt

As a user, I want to remove a tag from one prompt without deleting the tag itself, so I can fix a mis-tagged prompt.

**Acceptance criteria**

- `DELETE /prompts/{prompt_id}/tags/{tag_id}` returns `200` with the updated `Prompt`, whose `tag_ids` no longer includes `tag_id`. The `Tag` resource itself still exists and is unaffected.
- `DELETE /prompts/{prompt_id}/tags/{tag_id}` for an unknown or soft-deleted `prompt_id` returns `404` with `{"detail": "Prompt not found"}`.
- `DELETE /prompts/{prompt_id}/tags/{tag_id}` where `tag_id` is not currently attached to the prompt — whether because it was never attached or because it doesn't exist at all — returns `404` with `{"detail": "Tag not attached to prompt"}`.

### US-6: See a prompt's full tags, and filter prompts by tag

As a user, I want to see the full details (not just ids) of a prompt's tags, and list prompts that carry a given tag, so I can browse by label the same way I already browse by collection.

**Acceptance criteria**

- `GET /prompts/{id}/tags` returns `200` with `{"tags": [...], "total": N}` — the full `Tag` objects for every id in that prompt's `tag_ids`. For a prompt with no tags, it returns `{"tags": [], "total": 0}`, not `404`.
- `GET /prompts/{id}/tags` for an unknown or soft-deleted prompt id returns `404` with `{"detail": "Prompt not found"}`.
- `GET /prompts?tag_id=<id>` returns only active prompts whose `tag_ids` contains `<id>`, sorted newest-first — same sort as the unfiltered list.
- `GET /prompts?tag_id=<id>&collection_id=<cid>` combines both filters with `AND`, matching how `collection_id` and `search` already combine.
- `GET /prompts?tag_id=<unknown-id>` (a syntactically valid id matching no tag) returns `{"prompts": [], "total": 0}`, not an error — identical to how an unmatched `collection_id` behaves today.

## Data model changes

### New model: `Tag` (`app/models.py`)

```python
class TagCreate(BaseModel):
    """Request body for POST /tags.

    Attributes:
        name: The tag's display name, 1-32 characters after trimming.
            Whitespace is trimmed before validation.
    """
    name: str = Field(..., min_length=1, max_length=32)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: str) -> str:
        """Trim whitespace before the min_length/max_length checks run.

        Runs as a "before" validator so `Field`'s length constraints see the
        trimmed string, not the raw input — a value that's only whitespace
        (e.g. "   ") becomes "" and correctly fails min_length=1 with a 422,
        rather than passing length validation and being stored blank.
        """
        return value.strip() if isinstance(value, str) else value


class Tag(TagCreate):
    """A stored tag, and the response body for every tag endpoint.

    Attributes:
        id: Server-generated uuid4 string.
        created_at: Naive UTC time the tag was created.
        deleted_on: Naive UTC time the tag was soft-deleted, or None while
            it is active. Never settable by clients.
    """
    id: str = Field(default_factory=generate_id)
    created_at: datetime = Field(default_factory=get_current_time)
    deleted_on: Optional[datetime] = None

    class Config:
        from_attributes = True


class TagList(BaseModel):
    """Response body for GET /tags and GET /prompts/{id}/tags.

    Attributes:
        tags: The matching tags.
        total: The number of tags in `tags`.
    """
    tags: List[Tag]
    total: int


class PromptTagAttach(BaseModel):
    """Request body for POST /prompts/{prompt_id}/tags.

    Attributes:
        tag_id: The id of an existing, active tag to attach to the prompt.
    """
    tag_id: str = Field(..., min_length=1)
```

An empty `tag_id` (`{"tag_id": ""}`) is therefore rejected with `422` before the handler runs, rather than falling through to a `404 "Tag not found"` — a malformed request and a syntactically valid-but-unmatched id are different failures and get different status codes.

### Change to existing model: `Prompt` (`app/models.py`)

Add one field to the existing `Prompt` model (not to `PromptBase`, so it stays out of `PromptCreate`/`PromptUpdate`/`PromptPatch` request bodies — tags are only ever managed through the endpoints in this spec):

```python
class Prompt(PromptBase):
    id: str = Field(default_factory=generate_id)
    created_at: datetime = Field(default_factory=get_current_time)
    updated_at: datetime = Field(default_factory=get_current_time)
    deleted_on: Optional[datetime] = None
    tag_ids: List[str] = Field(default_factory=list)   # new
```

**Explicitly specified, not left implicit:** because `tag_ids` lives on `Prompt` and not on `PromptBase`, a `tag_ids` field sent in a `POST /prompts`, `PUT /prompts/{id}`, or `PATCH /prompts/{id}` body is silently ignored (Pydantic's default behavior for a field a request model doesn't declare) — tags must be managed via `/prompts/{prompt_id}/tags`. Because storage is in-memory and reset on every process start, no data migration is needed for this new field; it simply defaults to `[]`.

### Storage changes (`app/storage.py`)

- New instance attribute: `self._tags: Dict[str, Tag] = {}`.
- `create_tag(tag: Tag) -> Tag`
- `get_tag(tag_id: str, include_deleted: bool = False) -> Optional[Tag]`
- `get_all_tags(self) -> List[Tag]` — active only, in creation (insertion) order, oldest first. This matches `get_all_collections`, which also returns unsorted/insertion order with no date-based re-sort in `list_collections` — unlike `GET /prompts`, which explicitly sorts newest-first in `app/api.py`. `GET /tags` does not re-sort this list, so it is oldest-first, same as `GET /collections`.
- `find_tag_by_name(name: str) -> Optional[Tag]` — case-insensitive match against active tags' (trimmed) names, comparing with `.lower()` (not `.casefold()`), for consistency with the case-insensitive comparison `search_prompts` already uses in `app/utils.py`. Used for the uniqueness check in `POST /tags`.
- `delete_tag(tag_id: str) -> bool` — soft-deletes the tag (stamps `deleted_on`) **and** removes `tag_id` from every prompt's `tag_ids` that currently has it, in the same call. This mirrors how `delete_collection` already cascades to prompts, except it detaches rather than deletes them.
- `attach_tag(prompt_id: str, tag_id: str) -> Optional[Prompt]` — appends `tag_id` to the prompt's `tag_ids` if not already present; returns the prompt, or `None` if the prompt doesn't exist/is deleted. Enforcing "does the tag exist" and "is the prompt at the 10-tag cap" are cross-resource checks and belong in `app/api.py`, not here — consistent with how collection-reference validation already works for `collection_id`.
- `detach_tag(prompt_id: str, tag_id: str) -> Optional[Prompt]` — removes `tag_id` from the prompt's `tag_ids` if present; returns the prompt, or `None` if the prompt doesn't exist/is deleted. Whether `tag_id` was actually present is checked by the caller (`app/api.py`) to decide between success and the `404 "Tag not attached to prompt"` case.

## API endpoints

| Method | Endpoint | Description | Responses |
|---|---|---|---|
| `POST` | `/tags` | Create a tag | `201` `409` `422` |
| `GET` | `/tags` | List active tags, optional `?search=` | `200` |
| `GET` | `/tags/{id}` | Get one tag | `200` `404` |
| `DELETE` | `/tags/{id}` | Soft-delete a tag and detach it from every prompt | `204` `404` |
| `GET` | `/prompts/{id}/tags` | Full tag details for one prompt | `200` `404` |
| `POST` | `/prompts/{id}/tags` | Attach an existing tag to a prompt | `200` `404` `400` |
| `DELETE` | `/prompts/{id}/tags/{tag_id}` | Detach a tag from a prompt | `200` `404` |
| `GET` | `/prompts?tag_id=` | *(extends existing endpoint)* Filter prompts by tag | `200` |

### `POST /tags`

**Request**

```bash
curl -X POST http://localhost:8000/tags \
  -H 'Content-Type: application/json' -d '{"name": "security"}'
```

**Response — `201`**

```json
{ "id": "9c2e...", "name": "security", "created_at": "2026-08-24T06:00:00.000000", "deleted_on": null }
```

**Errors**

- `422` — `name` empty or over 32 characters (Pydantic field validation):
  ```json
  {"detail": [{"type": "string_too_long", "loc": ["body", "name"], "msg": "String should have at most 32 characters", "input": "...", "ctx": {"max_length": 32}, "url": "https://errors.pydantic.dev/2.5/v/string_too_long"}]}
  ```
- `409` — case-insensitive duplicate among active tags: `{"detail": "Tag with this name already exists"}`

### `GET /tags` / `GET /tags/{id}`

```bash
curl http://localhost:8000/tags
curl "http://localhost:8000/tags?search=sec"
curl http://localhost:8000/tags/9c2e...
```

`200` responses use `TagList` / `Tag` as shown above. `GET /tags/{id}` on a missing/deleted id: `404 {"detail": "Tag not found"}`.

### `DELETE /tags/{id}`

```bash
curl -X DELETE http://localhost:8000/tags/9c2e...
```

`204`, empty body. `404 {"detail": "Tag not found"}` if unknown or already deleted.

### `GET /prompts/{id}/tags`

```bash
curl http://localhost:8000/prompts/80184e58-ec8f-43de-bd66-f35c1e3bd7f6/tags
```

**Response — `200`**

```json
{ "tags": [{"id": "9c2e...", "name": "security", "created_at": "...", "deleted_on": null}], "total": 1 }
```

`404 {"detail": "Prompt not found"}` for an unknown/deleted prompt.

### `POST /prompts/{id}/tags`

```bash
curl -X POST http://localhost:8000/prompts/80184e58-ec8f-43de-bd66-f35c1e3bd7f6/tags \
  -H 'Content-Type: application/json' -d '{"tag_id": "9c2e..."}'
```

**Response — `200`** — the updated `Prompt`, `tag_ids` now including `"9c2e..."`.

**Errors**

- `404` prompt not found: `{"detail": "Prompt not found"}`
- `404` tag not found/deleted: `{"detail": "Tag not found"}`
- `400` at the 10-tag cap, attaching a new (11th) distinct tag: `{"detail": "A prompt cannot have more than 10 tags"}`

### `DELETE /prompts/{id}/tags/{tag_id}`

```bash
curl -X DELETE http://localhost:8000/prompts/80184e58-ec8f-43de-bd66-f35c1e3bd7f6/tags/9c2e...
```

**Response — `200`** — the updated `Prompt`, with `tag_id` removed from `tag_ids`.

**Errors**

- `404` prompt not found: `{"detail": "Prompt not found"}`
- `404` tag not currently attached: `{"detail": "Tag not attached to prompt"}`

### `GET /prompts?tag_id=`

```bash
curl "http://localhost:8000/prompts?tag_id=9c2e..."
curl "http://localhost:8000/prompts?tag_id=9c2e...&collection_id=f54e432e-...&search=review"
```

**Response — `200`** — `PromptList`, same shape as the existing endpoint, filtered to prompts whose `tag_ids` contains the given id, combined with `collection_id`/`search` via `AND` when present.

**No error cases.** A `tag_id` that doesn't match any tag returns `{"prompts": [], "total": 0}`, not an error — see "An unmatched `tag_id` filter is not an error" below.

## Error conditions and edge cases

- **Name uniqueness is case-insensitive and scoped to active tags only.** `security`, `Security`, and `SECURITY` can never coexist as three separate active tags; deleting one frees its name for reuse (US-1).
- **Whitespace is trimmed before every check** — validation length, uniqueness comparison, and storage all operate on the trimmed name.
- **Deleting a tag cascades to detachment, never to prompt deletion.** This is the opposite direction from `DELETE /collections/{id}`, which cascades to *deleting* its prompts — tagging cascades only ever remove a reference, never a resource (US-3).
- **Attach/detach are asymmetric on idempotency.** Attaching an already-attached tag succeeds silently (US-4); detaching a tag that isn't attached is a `404`, not a silent success (US-5) — because "detach a tag you thought was there" signals a client-side state mismatch worth surfacing, while "attach a tag that's already there" is a normal, harmless retry.
- **The 10-tag cap is per-prompt, checked only on the path that adds a genuinely new tag_id.** It never blocks detaching, never blocks re-attaching an existing tag, and never blocks attaching to a *different* prompt that's under the cap.
- **`tag_ids` is response-only from the general prompt endpoints.** It cannot be set or cleared via `POST`/`PUT`/`PATCH /prompts`; only the two `/prompts/{id}/tags...` endpoints mutate it.
- **An unmatched `tag_id` filter is not an error.** `GET /prompts?tag_id=<bogus>` returns an empty list, consistent with how an unmatched `collection_id` already behaves — filters don't validate that their value refers to a real resource.
- **A prompt can have zero tags.** `tag_ids: []` is the default and a fully valid, common state — `GET /prompts/{id}/tags` returns `{"tags": [], "total": 0}`, not a `404`.
- **Check order is fixed, not incidental.** `POST /prompts/{id}/tags` checks, in this order: (1) does the prompt exist and is it active → `404 "Prompt not found"`; (2) does the tag exist and is it active → `404 "Tag not found"`; (3) is the prompt already at the 10-tag cap and is this a genuinely new `tag_id` → `400`. `DELETE /prompts/{id}/tags/{tag_id}` checks: (1) prompt exists/active → `404 "Prompt not found"`; (2) `tag_id` is present in the prompt's `tag_ids` → `404 "Tag not attached to prompt"` if not (this single check covers both "tag never existed" and "tag exists but isn't on this prompt" — see US-5). A request that fails more than one check always reports the *first* one it fails, per this order.

## Implementation notes

- New endpoints belong in `app/api.py`: the four `/tags...` endpoints under a new `# ============== Tag Endpoints ==============` section, and the two `/prompts/{id}/tags...` endpoints near the existing Prompt Endpoints (after `delete_prompt`, since they act on an existing prompt). `list_prompts` gains a `tag_id: Optional[str] = None` query parameter and a corresponding filter step, mirrored from the existing `collection_id` filter.
- Tests belong in a new `TestTags` class in `backend/tests/test_api.py`, plus new cases added to `TestPrompts` for the `tag_id` filter and the `tag_ids` field appearing on prompt responses — following this project's existing per-resource grouping.
- Per `.github/copilot-instructions.md`: write a failing test for each acceptance criterion above before implementing; every new function gets a Google-style docstring; cross-resource checks (tag exists, prompt not at cap) belong in `app/api.py`, not `storage.py`; the `409` and `400` bodies still use the project's `{"detail": "<message>"}` shape, not a new error format.
- Once implemented, add these endpoints to `docs/API_REFERENCE.md`, including the `409` status code in its status-codes table (new to the API; not currently used by any endpoint) and the extended `GET /prompts` query-parameter table.
