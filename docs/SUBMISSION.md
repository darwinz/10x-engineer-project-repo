# Module 1 Submission — The Brownfield Challenge

**Repository:** https://github.com/darwinz/10x-engineer-project-repo (branch `main`)

## Summary

Documented the PromptLab backend in `docs/SYSTEM_MODEL.md` — architecture, every route, request-to-storage data flow, the prompt/collection relationship, the storage layer and its limitations, external dependencies, and a context strategy section cross-referenced to the prompt log.

Fixed all four bugs, one commit each:

1. `GET /prompts/{id}` returns 404 instead of 500 for an unknown id.
2. `PUT /prompts/{id}` sets `updated_at` to the current time and preserves `created_at`.
3. `GET /prompts` sorts newest first; `sort_prompts_by_date` now honours its `descending` flag.
4. Deleting a collection no longer orphans its prompts. I chose **soft delete with cascade**: prompts and collections gain a `deleted_on` field, `DELETE` stamps it rather than removing the record, every read excludes soft-deleted rows, and deleting a collection stamps the same `deleted_on` on its prompts while leaving `collection_id` intact. Reasoning: deleting a collection is more destructive than deleting one prompt, so keeping the records means the collection or its prompts can be retrieved and, with a little extra logic, restored or moved to another collection.

Added `PATCH /prompts/{id}` for partial updates: only fields present in the body change; an explicit `null` clears `description` or `collection_id`; `null` on `title` or `content` is rejected with 400; a supplied `collection_id` must exist; `updated_at` is bumped; 404 for unknown or deleted prompts.

The test suite grew from 13 to 38, all passing, with the new tests written before each fix. Every modified or added function has a Google-style docstring whose `Args`/`Returns`/`Raises` match the implementation. The README's run instructions were rewritten and verified on a fresh clone from GitHub.

Process evidence: `docs/prompt-log.md` (P-01 to P-13, with two tagged iterations — P-03a and P-07) and `docs/ai-verification-note.md`, which documents a wrong AI claim about uvicorn's reload behaviour that I caught by re-reading the source and executing the script.

## Verification

```bash
git clone https://github.com/darwinz/10x-engineer-project-repo.git
cd 10x-engineer-project-repo/backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v        # 38 passed
python main.py          # http://localhost:8000/docs
```

## Known issues

- **Python 3.10–3.12 only.** The pinned `pydantic==2.5.3` cannot be installed on 3.13+ because its `pydantic-core` release has no 3.13 wheels and the source build fails. Documented in the README; `.python-version` pins 3.12.
- `datetime.utcnow()` is deprecated on Python 3.12 and emits a warning on every test run. Left as-is so the API's timestamp format does not change mid-module.
- Storage is in-memory and per-process. The store is empty on every start (including hot-reload restarts), and soft-deleted records are never purged.
- The starter's `python main.py` did not start at all — uvicorn exits with status 1 when given an app object together with `reload=True`. Fixed by passing the import string `"app.api:app"`. Noted here because it was outside the four listed bugs.
