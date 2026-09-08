# PromptLab API Reference

Base URL (local development): `http://localhost:8000`

Interactive, always-current docs are also served by the running app at `/docs` (Swagger UI) and `/openapi.json` (raw OpenAPI schema).

## Authentication

**None.** Every endpoint is open — there is no API key, session, or bearer token requirement, and `CORSMiddleware` is configured with `allow_origins=["*"]` so any origin can call the API from a browser.

This is acceptable for local development only. Before this service is deployed anywhere reachable outside a developer's machine, it needs an authentication layer (e.g. API keys or OAuth2) and a locked-down CORS origin list — neither exists yet.

## Conventions

- All request and response bodies are JSON (`Content-Type: application/json`).
- Timestamps (`created_at`, `updated_at`, `deleted_on`) are naive UTC, serialized without a timezone suffix (e.g. `2026-08-24T05:42:37.701035`). Treat every timestamp as UTC.
- `id` values are server-generated UUIDv4 strings. Clients never set them.
- **Soft delete.** `DELETE` never removes a record — it stamps `deleted_on` with the current time. Soft-deleted prompts and collections are excluded from every read endpoint, and calling `DELETE` a second time on the same id returns `404`, identical to deleting an id that never existed.
- Deleting a collection cascades: every active prompt in that collection is soft-deleted with the *same* `deleted_on` timestamp as the collection. Each prompt's `collection_id` is left in place rather than cleared.

## Error format

Errors raised explicitly by the API (404, 400) return:

```json
{ "detail": "<human-readable message>" }
```

Request validation failures (422), raised by FastAPI/Pydantic before a route handler runs, return a list instead:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "content"],
      "msg": "Field required",
      "input": { "title": "x" },
      "url": "https://errors.pydantic.dev/2.5/v/missing"
    }
  ]
}
```

`loc` points at the offending field, `msg` is a human-readable reason, and `type` is a stable machine-readable error code (`missing`, `string_too_short`, etc.).

## Status codes used

| Code | Meaning | When it happens |
|---|---|---|
| `200` | OK | Successful `GET`, `PUT`, or `PATCH` |
| `201` | Created | Successful `POST` |
| `204` | No Content | Successful `DELETE` — empty body |
| `400` | Bad Request | A referenced `collection_id` does not belong to an active collection, or a `PATCH` tries to null out a required field (`title`/`content`) |
| `404` | Not Found | No active record exists with the given id — including one that was already soft-deleted |
| `422` | Unprocessable Entity | The request body fails Pydantic validation (missing/wrong-typed/out-of-range field) |

---

## Health

### `GET /health`

Health check. No parameters, no authentication.

**Request**

```bash
curl http://localhost:8000/health
```

**Response** — `200`

```json
{ "status": "healthy", "version": "0.1.0" }
```

---

## Prompts

A prompt has a `title` (1–200 chars), `content` (1+ chars, may reference `{{variables}}`), an optional `description` (≤500 chars), and an optional `collection_id`.

### `GET /prompts`

List active prompts, newest first (sorted by `created_at` descending).

**Query parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `collection_id` | string | no | Only return prompts with this exact `collection_id` |
| `search` | string | no | Case-insensitive substring match against `title` and `description`. Applied after `collection_id` filtering |

**Request**

```bash
curl http://localhost:8000/prompts
curl "http://localhost:8000/prompts?collection_id=f54e432e-405a-4739-9911-b89a993f1f95"
curl "http://localhost:8000/prompts?search=security"
```

```js
const res = await fetch("http://localhost:8000/prompts?search=security");
const { prompts, total } = await res.json();
```

**Response** — `200`

```json
{
  "prompts": [
    {
      "title": "Security review",
      "content": "Look for vulnerabilities in:\n\n{{code}}",
      "description": "Security-focused review",
      "collection_id": "f54e432e-405a-4739-9911-b89a993f1f95",
      "id": "80184e58-ec8f-43de-bd66-f35c1e3bd7f6",
      "created_at": "2026-08-24T05:42:37.701035",
      "updated_at": "2026-08-24T05:42:37.701038",
      "deleted_on": null
    }
  ],
  "total": 1
}
```

### `GET /prompts/{id}`

Get a single prompt.

**Request**

```bash
curl http://localhost:8000/prompts/80184e58-ec8f-43de-bd66-f35c1e3bd7f6
```

**Response** — `200`

```json
{
  "title": "Security review",
  "content": "Look for vulnerabilities in:\n\n{{code}}",
  "description": "Security-focused review",
  "collection_id": "f54e432e-405a-4739-9911-b89a993f1f95",
  "id": "80184e58-ec8f-43de-bd66-f35c1e3bd7f6",
  "created_at": "2026-08-24T05:42:37.701035",
  "updated_at": "2026-08-24T05:42:37.701038",
  "deleted_on": null
}
```

**Error** — `404` (unknown or soft-deleted id)

```bash
curl -i http://localhost:8000/prompts/does-not-exist
```

```json
{ "detail": "Prompt not found" }
```

### `POST /prompts`

Create a prompt.

**Body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | yes | 1–200 characters |
| `content` | string | yes | 1+ characters |
| `description` | string \| null | no | ≤500 characters |
| `collection_id` | string \| null | no | Must reference an active collection if provided |

**Request**

```bash
curl -X POST http://localhost:8000/prompts \
  -H 'Content-Type: application/json' \
  -d '{
        "title": "Security review",
        "content": "Look for vulnerabilities in:\n\n{{code}}",
        "description": "Security-focused review",
        "collection_id": "f54e432e-405a-4739-9911-b89a993f1f95"
      }'
```

```js
const res = await fetch("http://localhost:8000/prompts", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    title: "Security review",
    content: "Look for vulnerabilities in:\n\n{{code}}",
    description: "Security-focused review",
    collection_id: "f54e432e-405a-4739-9911-b89a993f1f95",
  }),
});
```

**Response** — `201`

```json
{
  "title": "Security review",
  "content": "Look for vulnerabilities in:\n\n{{code}}",
  "description": "Security-focused review",
  "collection_id": "f54e432e-405a-4739-9911-b89a993f1f95",
  "id": "80184e58-ec8f-43de-bd66-f35c1e3bd7f6",
  "created_at": "2026-08-24T05:42:37.701035",
  "updated_at": "2026-08-24T05:42:37.701038",
  "deleted_on": null
}
```

**Errors**

`400` — `collection_id` given but no active collection has that id:

```bash
curl -X POST http://localhost:8000/prompts \
  -H 'Content-Type: application/json' \
  -d '{"title": "x", "content": "some content", "collection_id": "nope"}'
```

```json
{ "detail": "Collection not found" }
```

`422` — a required field is missing:

```bash
curl -X POST http://localhost:8000/prompts \
  -H 'Content-Type: application/json' -d '{"title": "x"}'
```

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "content"],
      "msg": "Field required",
      "input": { "title": "x" },
      "url": "https://errors.pydantic.dev/2.5/v/missing"
    }
  ]
}
```

### `PUT /prompts/{id}`

Full replace. **Every** field in the body is required — this is not a merge. `id` and `created_at` are preserved; `updated_at` is set to the current time.

**Body** — same shape as `POST /prompts`, all fields required (send `null` explicitly to clear `description`/`collection_id`).

**Request**

```bash
curl -X PUT http://localhost:8000/prompts/80184e58-ec8f-43de-bd66-f35c1e3bd7f6 \
  -H 'Content-Type: application/json' \
  -d '{
        "title": "Security review v2",
        "content": "Look for vulnerabilities:\n\n{{code}}",
        "description": "Now covers OWASP top 10",
        "collection_id": null
      }'
```

**Response** — `200`

```json
{
  "title": "Security review v2",
  "content": "Look for vulnerabilities:\n\n{{code}}",
  "description": "Now covers OWASP top 10",
  "collection_id": null,
  "id": "80184e58-ec8f-43de-bd66-f35c1e3bd7f6",
  "created_at": "2026-08-24T05:42:37.701035",
  "updated_at": "2026-08-24T05:43:00.871126",
  "deleted_on": null
}
```

**Errors** — `404` if the id doesn't exist or is deleted; `400` for an unknown `collection_id`; `422` for a missing/invalid field (same formats as `POST`).

### `PATCH /prompts/{id}`

Partial update, added in Module 1. Only the fields present in the request body are changed — an omitted field keeps its current value. Sending a field as JSON `null` **clears** it, except `title` and `content`, which are required on every prompt and cannot be nulled. `id` and `created_at` are preserved; `updated_at` is always bumped to the current time, even if the body is `{}`.

**Body** — all fields optional:

| Field | Type | Behavior when present |
|---|---|---|
| `title` | string \| null | Updates title (1–200 chars). `null` → `400` |
| `content` | string \| null | Updates content (1+ chars). `null` → `400` |
| `description` | string \| null | Updates description, or clears it if `null` |
| `collection_id` | string \| null | Moves the prompt, or removes it from its collection if `null`. Must reference an active collection if not `null` |

**Request — update one field**

```bash
curl -X PATCH http://localhost:8000/prompts/80184e58-ec8f-43de-bd66-f35c1e3bd7f6 \
  -H 'Content-Type: application/json' \
  -d '{"description": "Updated guidance for PR reviews"}'
```

```js
const res = await fetch(`http://localhost:8000/prompts/${id}`, {
  method: "PATCH",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ description: "Updated guidance for PR reviews" }),
});
```

**Response** — `200` (only `description` and `updated_at` changed)

```json
{
  "title": "Security review",
  "content": "Look for vulnerabilities in:\n\n{{code}}",
  "description": "Updated guidance for PR reviews",
  "collection_id": "f54e432e-405a-4739-9911-b89a993f1f95",
  "id": "80184e58-ec8f-43de-bd66-f35c1e3bd7f6",
  "created_at": "2026-08-24T05:42:37.701035",
  "updated_at": "2026-08-24T05:42:53.688817",
  "deleted_on": null
}
```

**Request — clear the collection**

```bash
curl -X PATCH http://localhost:8000/prompts/80184e58-ec8f-43de-bd66-f35c1e3bd7f6 \
  -H 'Content-Type: application/json' \
  -d '{"collection_id": null}'
```

**Response** — `200` (`collection_id` now `null`)

```json
{
  "title": "Security review",
  "content": "Look for vulnerabilities in:\n\n{{code}}",
  "description": "Updated guidance for PR reviews",
  "collection_id": null,
  "id": "80184e58-ec8f-43de-bd66-f35c1e3bd7f6",
  "created_at": "2026-08-24T05:42:37.701035",
  "updated_at": "2026-08-24T05:42:53.697170",
  "deleted_on": null
}
```

**Error — nulling a required field**

```bash
curl -X PATCH http://localhost:8000/prompts/80184e58-ec8f-43de-bd66-f35c1e3bd7f6 \
  -H 'Content-Type: application/json' -d '{"title": null}'
```

`400`:

```json
{ "detail": "title cannot be null" }
```

Other errors: `404` for an unknown/deleted id; `400` if `collection_id` is set to a value that isn't an active collection.

### `DELETE /prompts/{id}`

Soft-delete a prompt. No response body.

**Request**

```bash
curl -X DELETE http://localhost:8000/prompts/80184e58-ec8f-43de-bd66-f35c1e3bd7f6
```

**Response** — `204`, empty body.

**Error** — `404` if the id doesn't exist or was already deleted:

```bash
curl -i -X DELETE http://localhost:8000/prompts/80184e58-ec8f-43de-bd66-f35c1e3bd7f6
```

```json
{ "detail": "Prompt not found" }
```

---

## Collections

A collection has a `name` (1–100 chars) and an optional `description` (≤500 chars).

### `GET /collections`

List every active collection. No parameters.

**Request**

```bash
curl http://localhost:8000/collections
```

**Response** — `200`

```json
{
  "collections": [
    {
      "name": "Code Review",
      "description": "Prompts for reviewing PRs",
      "id": "f54e432e-405a-4739-9911-b89a993f1f95",
      "created_at": "2026-08-24T05:42:22.225698",
      "deleted_on": null
    }
  ],
  "total": 1
}
```

### `GET /collections/{id}`

Get a single collection.

**Request**

```bash
curl http://localhost:8000/collections/f54e432e-405a-4739-9911-b89a993f1f95
```

**Response** — `200`

```json
{
  "name": "Code Review",
  "description": "Prompts for reviewing PRs",
  "id": "f54e432e-405a-4739-9911-b89a993f1f95",
  "created_at": "2026-08-24T05:42:22.225698",
  "deleted_on": null
}
```

**Error** — `404`:

```json
{ "detail": "Collection not found" }
```

### `POST /collections`

Create a collection.

**Body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | yes | 1–100 characters |
| `description` | string \| null | no | ≤500 characters |

**Request**

```bash
curl -X POST http://localhost:8000/collections \
  -H 'Content-Type: application/json' \
  -d '{"name": "Code Review", "description": "Prompts for reviewing PRs"}'
```

```js
const res = await fetch("http://localhost:8000/collections", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ name: "Code Review", description: "Prompts for reviewing PRs" }),
});
```

**Response** — `201`

```json
{
  "name": "Code Review",
  "description": "Prompts for reviewing PRs",
  "id": "f54e432e-405a-4739-9911-b89a993f1f95",
  "created_at": "2026-08-24T05:42:22.225698",
  "deleted_on": null
}
```

**Error** — `422` for an invalid `name` (e.g. empty string):

```bash
curl -X POST http://localhost:8000/collections \
  -H 'Content-Type: application/json' -d '{"name": ""}'
```

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "name"],
      "msg": "String should have at least 1 character",
      "input": "",
      "ctx": { "min_length": 1 },
      "url": "https://errors.pydantic.dev/2.5/v/string_too_short"
    }
  ]
}
```

### `DELETE /collections/{id}`

Soft-delete a collection **and cascade the same delete to every active prompt in it** (their `collection_id` is left unchanged). No response body.

**Request**

```bash
curl -X DELETE http://localhost:8000/collections/f54e432e-405a-4739-9911-b89a993f1f95
```

**Response** — `204`, empty body.

**Verify the cascade:**

```bash
curl "http://localhost:8000/prompts?collection_id=f54e432e-405a-4739-9911-b89a993f1f95"
# {"prompts":[],"total":0}
```

**Error** — `404` if the id doesn't exist or was already deleted:

```json
{ "detail": "Collection not found" }
```

---

## Endpoint summary

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
