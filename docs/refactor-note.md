# Refactor Note

## Code smell: Duplicated Code (Fowler)

In `backend/app/api.py`, this block appeared six times — verbatim in three places, trivially inlined (same condition, same status, same message, just without capturing the return value) in the other three:

```python
prompt = storage.get_prompt(prompt_id)
if not prompt:
    raise HTTPException(status_code=404, detail="Prompt not found")
```

Occurrences, by function: `get_prompt`, `update_prompt`, `patch_prompt`, `list_prompt_versions`, `get_prompt_version`, `restore_prompt_version`.

This is a duplication smell, not a style preference: six copies of the same lookup-and-error logic means a future change to it (a different status code, an additional check, a different error message) has to be made correctly six times, and nothing enforces that it will be. It had already been considered and deliberately deferred once before, at 4 occurrences (see `docs/agent-effect-note.md`), on the judgment that 4 repeats of a 3-line block across an otherwise-consistent file was still cheaper than an abstraction. At 6, with the pattern only growing as version-related endpoints were added, that judgment flips.

## The refactor

Extracted a single helper:

```python
def _get_prompt_or_404(prompt_id: str) -> Prompt:
    prompt = storage.get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt
```

and replaced all six call sites with a call to it — either `return _get_prompt_or_404(prompt_id)`, `existing = _get_prompt_or_404(prompt_id)`, or a bare `_get_prompt_or_404(prompt_id)` where the caller only needed the existence check, not the object. The leading underscore matches the existing module-level helper `_snapshot_version_if_changed` — both are internal to `api.py`, not routes.

**Why this is provably behavior-preserving, not just "should be fine":**

- Same condition: `storage.get_prompt(prompt_id)` falsy.
- Same status code: `404`.
- Same response body: `{"detail": "Prompt not found"}`.
- Same relative order: in every function, the prompt-existence check still runs at exactly the point it used to, relative to that function's other checks — e.g. `update_prompt` and `patch_prompt` still check the prompt exists *before* validating `collection_id`; `restore_prompt_version` still checks the prompt exists *before* looking up the version. Nothing was reordered.
- Net change is a pure lift-and-call: `app/api.py` shrank from 122 to 116 statements (six inlined blocks collapsed into six one-line calls, plus the helper defined once), consistent with duplication removed and nothing else added.

## Commits

| | Commit | State |
|---|---|---|
| **Before** | [`c24a844`](https://github.com/darwinz/10x-engineer-project-repo/commit/c24a8443c1a8d21b5c86e0d2b1de6f8fdc4bb838) | `docker: add Dockerfile, docker-compose.yml, and README Docker section` — verified green immediately before starting: `ruff check .` clean, 187 tests passing, 100% coverage. Nothing was pending in the working tree, so this existing commit *is* the baseline; no separate "pre-refactor" commit was needed. |
| **After** | [`f5c51dd`](https://github.com/darwinz/10x-engineer-project-repo/commit/f5c51dd12c39bbe23e0e6908509ab4dc0589ecde) | `refactor: extract _get_prompt_or_404, removing 6x duplicated lookup` |

`git diff --stat c24a844 f5c51dd` touches exactly one file: `backend/app/api.py` (30 insertions, 17 deletions). No test file was modified in either commit.

## Confirmation: public interface and observable behavior are unchanged

- **No test was edited, added, or removed** for this refactor. The same 187 tests that passed at `c24a844` pass, unmodified, at `f5c51dd` — same count, same 100% coverage across `api.py`, `models.py`, `storage.py`, `utils.py`. The tests are the evidence; they were not touched to produce it.
- **No route signature, path, method, status code, or response schema changed.** All 11 original endpoints plus the 3 prompt-version endpoints keep the exact routes, methods, and `response_model`s they had before.
- **No error message or status code changed** for any of the six call sites — confirmed both by re-reading each modified function and by the passing test suite, which asserts exact status codes and exact `{"detail": ...}` bodies for every one of these 404 paths (`test_get_prompt_not_found`, `test_update_prompt_not_found`, `test_patch_not_found`, `test_get_versions_for_unknown_prompt_returns_404`, `test_get_single_version_unknown_prompt_returns_404_prompt_not_found`, `test_restore_unknown_prompt_returns_404`, plus the soft-deleted-prompt variants of each).
- **`_get_prompt_or_404` is a private, module-internal helper**, not a route — it adds nothing to the API's public surface.

This refactor changed *how* six functions check that a prompt exists. It did not change *what* any of them do.
