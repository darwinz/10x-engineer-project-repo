# Agent Effect Note

Evidence that `.github/copilot-instructions.md` changed generated output, not just advice that plausibly could have.

## Method

GitHub Copilot itself isn't available in this environment, but `.github/copilot-instructions.md` works the same way for any AI coding tool that reads repo custom instructions: it's extra context injected before the model generates code. To test whether it actually changes output, I gave the identical task to two independent, freshly-started agent instances with no shared context and no knowledge of each other:

- **Baseline** — given the repo and the task only. Free to read `app/api.py`, `app/models.py`, `app/storage.py` for style, but never told the instructions file exists.
- **Instructed** — given the repo and the task, plus one extra line: read `.github/copilot-instructions.md` first and follow it.

Both were asked, verbatim, to design a new `POST /prompts/bulk` endpoint that creates a list of prompts in one call and rejects bad input with a clear error — a real feature request, not one engineered to telegraph the "correct" answer. Neither was told what the answer should look like. Neither was allowed to edit files; both returned code as their final answer, which I capture below unedited.

## What changed

### 1. Error response shape

**Before (no instructions file):**

```python
if errors:
    raise HTTPException(
        status_code=400,
        detail={"message": "Invalid prompts in bulk request", "errors": errors},
    )
```

**After (instructions file read):**

```python
if not collection:
    raise HTTPException(
        status_code=400,
        detail=f"prompts[{index}]: collection not found",
    )
```

Every existing error in this API — confirmed in `app/api.py` and documented in `docs/API_REFERENCE.md` — returns `{"detail": "<message>"}`, a plain string. The baseline agent invented a new, richer shape (`{"detail": {"message": ..., "errors": [...]}}`) for this one endpoint. That's a real API contract inconsistency: a client written against the rest of PromptLab's error format (`response.json()["detail"]` as a string) would break specifically on this endpoint. The instructed agent's own stated reasoning: *"the repo convention that 422 is 'left entirely to FastAPI/Pydantic'... [and] `{"detail": "<message>"}` per the copilot-instructions error-handling section"* — it kept the string-detail shape and folded the per-item context into the message text instead of a new structure.

### 2. Response model reuse

**Before:** defined a new model duplicating an existing one, with a differently-named field for the same value:

```python
class PromptBulkResponse(BaseModel):
    prompts: List[Prompt]
    count: int
```

**After:** reused the existing list-response model instead of adding a near-duplicate:

```python
@app.post("/prompts/bulk", response_model=PromptList, status_code=201)
def create_prompts_bulk(bulk_data: PromptBulkCreate):
    ...
    return PromptList(prompts=created, total=len(created))
```

`PromptList` (`app/models.py`) already has exactly this shape — `prompts: List[Prompt]` plus a count. The baseline agent's `PromptBulkResponse` is a second, parallel schema for the same data, and it names the count field `count` where every other list endpoint in this API (`GET /prompts`, `GET /collections`) calls it `total`. A frontend built against `total` on every other list endpoint would need a one-off exception for this one. The instructed agent explicitly cited avoiding "a near-duplicate response shape" as the reason to reuse `PromptList`.

## Why this counts as evidence, not a coincidence

Both agents converged on the same Pydantic-validation strategy (reuse `PromptCreate` per list item, `Field(min_length=1)` for "at least one prompt required") and the same collection-existence check placed in the route handler — those patterns are directly visible by reading `create_prompt` in `app/api.py`, so any competent agent reading the existing code arrives there without help. The two things that *did* diverge — the error body's exact shape, and whether to add a new response model or reuse an existing one — are not visible by reading any single file in isolation; they're the kind of repo-wide consistency call that only a scan across every endpoint (or an explicit instruction) surfaces. `copilot-instructions.md` states both rules explicitly ("Every handler-raised error body is `{"detail": "<message>"}`" and the file-naming/no-near-duplicate guidance), and the instructed agent's output matches them while its own stated rationale quotes those exact rules. The baseline agent, working from the same files but without that instruction, produced an endpoint that would have shipped a genuine inconsistency into the API.

## Caveat

The comparison used a Claude subagent as a stand-in for Copilot in both conditions, since Copilot isn't installed in this environment. The mechanism under test — a model reading `.github/copilot-instructions.md` as extra context before generating code — is the same one Copilot uses; the model behind it is not. This note demonstrates that the file's content is capable of changing generated output in this repo, not that Copilot specifically will read or apply it identically.
