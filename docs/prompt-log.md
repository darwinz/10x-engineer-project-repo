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

**Outcome:** Iterated → P-03a; partly wrong → see `docs/ai-verification-note.md`. The response stated, verbatim: *"`main.py` passes the app object to `uvicorn.run(..., reload=True)` so reload is silently disabled ... `python main.py` works, but edits require a restart."* The first half is right; the conclusion is not. Uvicorn 0.27 logs the warning and then calls `sys.exit(1)` (`uvicorn.run` source, the branch under `if (config.reload or config.workers > 1) and not isinstance(app, str)`). Confirmed by running `python main.py`: it prints the warning and exits with status 1 without binding a port. The claim was made from having seen the warning *string* in the source without reading the lines after it.
**Why I changed my next prompt:** The SYSTEM_MODEL.md draft was requested with an explicit accuracy constraint ("MUST be accurate to the codebase, DO NOT GUESS"), which prompted re-verifying the `reload` claim by reading the surrounding source and executing `main.py` — that is what surfaced the error. The draft was written with the corrected behaviour. Logged as P-03a.

## P-03a — Draft SYSTEM_MODEL.md under an explicit accuracy constraint (iteration of P-03: added constraint)

**Stage:** Documentation → Verification
**Context given:** Whole repo (the same material as P-01/P-03), plus re-reading the `uvicorn.run` source around the reload warning and executing `backend/main.py` and `uvicorn app.api:app` directly.
**Why that context:** The draft had to cover every heading, so whole-repo context was still appropriate; the added constraint changed *how* the context was used — claims about runtime behaviour were re-verified by execution before being written down.

**Prompt (verbatim):**
> Generate a draft of the SYSTEM_MODEL.md based on what we've discussed.  It MUST be accurate to the codebase, DO NOT GUESS.  Cover the areas that we've discussed in the write-up.

**Response (summarised — relevant part):**
Before writing, Claude re-checked the one P-03 claim it had made from inference — that `reload=True` with an app object is "silently disabled" and `python main.py` still works. Printing the `uvicorn.run` source *around* the warning showed the branch ends in `sys.exit(1)`. Running `python main.py` confirmed it: the warning prints and the process exits with status 1 without binding a port; `uvicorn app.api:app --port 8765` started normally for contrast. Claude flagged the correction explicitly ("my P-03 claim was wrong"), then wrote `docs/SYSTEM_MODEL.md` (184 lines) with a dedicated subsection *The entry script does not work*, all eight required headings, and the context strategy table with P-01–P-03 rows filled and later stages marked *planned*. It also updated P-03's outcome in this log to quote the wrong sentence verbatim, per convention 2.

**Outcome:** Accepted — draft committed as `f269c50`. The caught mistake is written up in `docs/ai-verification-note.md`.
**Why I changed my next prompt:** The exploration was complete and the draft was committed; the next prompt moved to setting up the bug-fix branch and the first fix.

## P-04 — Set up the bug-fix branch and fix Bug #1 (GET /prompts/{id} 500 → 404)

**Stage:** Bug fix
**Context given:** Files: `backend/app/api.py` — the `get_prompt` handler (lines 65–74) and the neighbouring `get_collection` handler as the pattern to mirror; `backend/tests/test_api.py` — `test_get_prompt_not_found` and `test_delete_prompt`.
**Why that context:** The defect is a single attribute access on `None` inside one function. The correct 404 pattern already exists three handlers down in the same file, so the fix needs no context beyond that file and its two tests.

**Prompt (verbatim):**
> Create a new git branch from main for bug fixes.  We're going to fix some bugs in this codebase.  All existing tests should continue to pass, so nothing regresses.  Tests are needed for all endpoints, and if none exists for an endpoint we should add one.  If a test exists for an endpoint, we should work toward those tests passing.  We'll do one bug fix at a time, each in a separate commit. Start with fixing Bug #1 — GET /prompts/{id} should return 404 instead of 500.

**Response (summarised — relevant part):**
Claude first flagged that `main` (`1df4cbd`) does not contain the prompt log or system model — only `module-1-brownfield` does — and asked where to base the branch; I chose to branch from `module-1-brownfield` so the log stays on the working branch. Created `bugfixes`, confirmed the red baseline (3 failed / 10 passed), then replaced the `if prompt.id: return prompt` guard with the codebase's existing pattern: `if not prompt: raise HTTPException(status_code=404, detail="Prompt not found")` followed by `return prompt`. Removed the `BUG #1` comment block. Tightened `test_delete_prompt`'s post-delete assertion from `in [404, 500]` to `== 404`, as the test's own comment instructed for after the fix. Re-ran the suite: 12 passed, 1 failed — the remaining failure is `test_sorting_order` (Bug #3), unchanged. No regressions.

**Outcome:** Accepted
**Why I changed my next prompt:** The fix was in and the unit tests passed; I wanted an end-to-end check against a running server, not just `TestClient`, before moving to the next bug.

## P-05 — curl command to verify the Bug #1 fix

**Stage:** Verification
**Context given:** None beyond the conversation — the fixed `get_prompt` handler from P-04 and the `main.py` finding from P-03 (server must be started with `uvicorn app.api:app`, not `python main.py`).
**Why that context:** Verifying a single endpoint's HTTP behaviour needs no source context; it needs a running server and the request.

**Prompt (verbatim):**
> Provide a curl command to test the fixed bug

**Response (summarised — relevant part):**
Gave `uvicorn app.api:app --port 8000` as the start command (noting `python main.py` exits), then `curl -i http://localhost:8000/prompts/does-not-exist`. Ran it against a live server rather than only describing the expected output; the real response was `HTTP/1.1 404 Not Found` with body `{"detail":"Prompt not found"}`. Also created a prompt via `POST` and fetched it by id to show the contrasting `200`. Stopped the server afterwards.

**Outcome:** Accepted
**Why I changed my next prompt:** Ran the curl myself against the server and got the 404 — Bug #1 confirmed end-to-end, so moved on to Bug #2.

## P-06 — Confirm Bug #1 end-to-end; fix Bug #2 (PUT does not update `updated_at`)

**Stage:** Verification → Bug fix
**Context given:** Files: `backend/app/api.py` — the `update_prompt` handler (lines 89–113) only; `backend/tests/test_api.py` — `test_update_prompt`.
**Why that context:** A one-line defect inside one handler (`updated_at=existing.updated_at`), with the correct helper (`get_current_time`) already imported at the top of the same file. The provided test already contained the exact assertion for this bug, commented out.

**Prompt (verbatim):**
> The response is correct now.  Bug #1 is fixed.
>
> curl -i http://localhost:8000/prompts/does-not-exist
> HTTP/1.1 404 Not Found
> date: Sat, 22 Aug 2026 07:23:11 GMT
> server: uvicorn
> content-length: 29
> content-type: application/json
>
> {"detail":"Prompt not found"}
>
> Fix Bug #2 — PUT should update the updated_at timestamp

**Response (summarised — relevant part):**
Test-first: uncommented the provided `assert data["updated_at"] != original_updated_at` in `test_update_prompt`, added `assert data["updated_at"] > original_updated_at` (must move *forward*, not merely differ) and `assert data["created_at"] == ...` (the fix must not disturb `created_at`), and added `test_update_prompt_not_found` (PUT on an unknown id → 404) since PUT had no not-found test. Confirmed red: `test_update_prompt` failed. Then changed `updated_at=existing.updated_at` to `updated_at=get_current_time()` in the `Prompt(...)` construction and removed the `BUG #2` comments. Re-ran: 13 passed, 1 failed (`test_sorting_order`, Bug #3, untouched). No regressions.

**Outcome:** Iterated → P-07
**Why I changed my next prompt:** Running the suggested curl sequence against my local server showed `updated_at` identical before and after PUT. The output had told me *how* to verify but not that the already-running server would be serving the old code, so I added an explicit constraint: verify the field changes and the test passes before calling the bug complete.

## P-07 — Bug #2 appears not to work: verify before declaring it complete (iteration of P-06: added constraint)

**Stage:** Bug fix → Verification
**Context given:** Files: `backend/app/api.py` (`update_prompt` as fixed in P-06), `backend/tests/test_api.py::test_update_prompt`; plus live process inspection (`lsof` on port 8000, process start time vs. commit time) and the curl sequence run against two servers.
**Why that context:** The report contradicted a passing test, so the question was not "is the code right" but "what is the running server executing". That needed process state, not more source.

**Prompt (verbatim):**
> The updated_at is identical for both.  Let's take a closer look at Bug #2.  The updated_at should update to the current time.  The test should also verify that it's passing.  Please check your work and verify that the updated_at is getting updated and that the test is passing before Bug #2 is complete.

**Response (summarised — relevant part):**
Reproduced before changing anything. On disk `api.py:104` reads `updated_at=get_current_time()` and `test_update_prompt` passes on a clean run. `lsof` showed a Python process (pid 3373) listening on 8000 that had been **started at 01:22:30 — two minutes before the fix was committed at 01:24:39**. Running the POST → sleep → PUT sequence against that server reproduced the report exactly: `updated_at` unchanged (`…36.352294` both times). Starting a fresh server on port 8001 from the current code and running the identical sequence gave `created_at` unchanged and `updated_at` advanced by 1.07 s (`…50.842749` → `…51.909182`). Conclusion: the fix is correct; the server was started before the fix and uvicorn without `--reload` does not re-import. Advised restarting with `uvicorn app.api:app --port 8000 --reload`, and acknowledged the P-06 response should have said to restart before curling.

**Outcome:** Accepted — Bug #2 verified both by test and end-to-end on a fresh server.
**Why I changed my next prompt:** Restarted my server and saw `updated_at` change — Bug #2 confirmed. For Bug #3 I asked up front for a curl verification set, so the restart lesson is built into the request.

## P-08 — Fix Bug #3 (GET /prompts sorts oldest first) and provide curl verification

**Stage:** Bug fix → Verification
**Context given:** Files: `backend/app/utils.py` — `sort_prompts_by_date` (lines 7–14) only; `backend/tests/test_api.py::test_sorting_order`. End-to-end check on a fresh server (port 8001).
**Why that context:** The sort is a single three-line helper whose `descending` parameter was ignored; the route (`api.py:60`) already calls it with `descending=True`, so only the helper needed to change.

**Prompt (verbatim):**
> My server was running prior to the changes, and I assumed it was watching for updates.  I've since restarted that server and can see now that the bug is fixed.
>
> Let's move to Bug #3.  GET /prompts should return newest first but returns oldest first.  Find the sorting logic, fix the order, and verify.  Once done, provide a set of commands I can verify myself through curl.

**Response (summarised — relevant part):**
Located the defect in `utils.sort_prompts_by_date`: `sorted(prompts, key=lambda p: p.created_at)` with the `descending` argument never used. Changed it to `sorted(prompts, key=lambda p: p.created_at, reverse=descending)` and removed the `BUG #3` comments. Added `tests/test_utils.py` with three unit tests for the helper: default is newest-first, `descending=False` is oldest-first, and the input list is not mutated. Suite: **17 passed, 0 failed** — first fully green run. End-to-end on a fresh server: created "First", "Second", "Third" 200 ms apart; `GET /prompts` returned Third, Second, First with descending `created_at` values. Provided a curl command set for self-verification.

**Outcome:** Accepted — confirmed via curl on my own server: three prompts created in sequence came back newest first from `GET /prompts`.
**Why I changed my next prompt:** Bug #3 confirmed. For Bug #4 I replaced the strategy chosen during setup (null the field) with soft delete + cascade, stated the reasoning I want on record, and required a test-first approach.

## P-09 — Fix Bug #4 with cascading soft delete, test-first

**Stage:** Bug fix
**Context given:** Files: `backend/app/models.py` (`Prompt`, `Collection`), `backend/app/storage.py` (whole file — every read and both deletes), `backend/app/api.py` (`delete_collection`, `delete_prompt`, and the reads that must now 404/400), `backend/tests/test_api.py`.
**Why that context:** Unlike Bugs #1–#3, soft delete is not a local change: once records stay in the store, every read path has to exclude them or "deleted" data leaks back out. The storage layer is where all reads and deletes meet, so the whole file was in scope; the handlers needed checking but turned out not to need changes because they already route through `storage.get_*`.

**Prompt (verbatim):**
> Let's fix Bug #4.  Deleting a collection is orphaning its prompts.  Make sure deletion is soft delete, so set a deleted_on datetime field that is null by default and is set to a value on delete.  Same with the prompts.  Cascade soft delete the prompts that belong to a collection on collection deletion.  Add a test before implementing the logic (test-driven development).  The reasoning for this strategy, is that deleting a collection is more desctructive than deleting a single prompt, so if there was a problem after deletion, we could still retrieve the collection or the prompts and potentially re-enable or undelete the collection or move a prompt to another collection with some additional logic added.

**Response (summarised — relevant part):**
Claude first stated the design it would test against, because soft delete has consequences beyond the delete handler: `deleted_on: Optional[datetime] = None` on `Prompt` and `Collection` only (not on the create/update bodies); every read excludes soft-deleted records (GET by id → 404, lists omit, PUT on deleted → 404, POST into a deleted collection → 400); deleting twice → 404; cascade stamps the *same* `deleted_on` on the collection and its active prompts and leaves `collection_id` intact for a future undelete; `get_prompt`/`get_collection` gain `include_deleted=False` so tests and future restore logic can reach soft-deleted records.

**Red:** replaced the provided `test_delete_collection_with_prompts` (which asserted the orphaned state) and added ten tests across `TestCollections` and a new `TestSoftDelete` class — not-found, empty collection, cascade with shared timestamp and preserved `collection_id`, other collections' prompts untouched, delete-twice 404, create-into-deleted 400, `deleted_on` null by default, prompt soft delete visible via `include_deleted`, update-deleted 404, and clients unable to set `deleted_on`. 5 failed / 22 passed.

**Green:** `models.py` — `deleted_on` field on both stored models. `storage.py` — `get_prompt`/`get_collection` return `None` for soft-deleted unless `include_deleted=True`; `get_all_*` and `get_prompts_by_collection` filter on `deleted_on is None`; `delete_prompt(prompt_id, deleted_on=None)` stamps instead of `del`; `delete_collection` stamps the collection, then cascades via `get_prompts_by_collection` + `delete_prompt` with the same timestamp; `update_prompt` refuses deleted records. `api.py` — the handlers are unchanged in logic; the `BUG #4` comment block was replaced with the strategy reasoning. **27 passed, 0 failed** — all 13 original tests still pass.

**End-to-end check — with a process mistake.** Claude ran the curl check and wrote the log entry in parallel, and the first version of this paragraph described the expected result (204 → 404 / 404 / 400) *before the script had returned*. The script itself was faulty — the `Content-Type` header was held in an unquoted zsh variable, which does not word-split, so every POST got 422, the ids were empty, and the id-based requests returned 307 redirects. Claude flagged this unprompted, re-ran the check with quoted headers, and only then recorded the result: before delete, 2 prompts and `deleted_on: None`; DELETE 204; afterwards GET collection 404, GET its prompt 404, `GET /prompts` lists only the unrelated "Loose" prompt; second DELETE 404; POST into the deleted collection 400. The conclusion was the same as the premature claim, but the claim had been written without evidence.

**Outcome:** Accepted — confirmed via curl on my own server: collection and its prompt both 404 after delete, unrelated prompt still listed.
**Why I changed my next prompt:** All four bugs fixed and confirmed; moved to the missing endpoint. I specified the null-handling rule up front (null clears optional fields, 400 for required ones) rather than leaving it to the AI.

## P-10 — Implement PATCH /prompts/{id} for partial updates, test-first

**Stage:** PATCH endpoint
**Context given:** Files: `backend/app/api.py` — the `update_prompt` (PUT) handler as the pattern to mirror, plus the handler ordering used elsewhere (404 → 400 → build → store); `backend/app/models.py` — `PromptBase`/`PromptUpdate` to derive the constraints; `backend/tests/test_api.py` — existing test style.
**Why that context:** A new endpoint has to match the conventions of the one it sits beside, so the PUT handler and the model hierarchy were the necessary inputs. The storage layer needed no change (PUT's `get_prompt` → `update_prompt` path is reused as-is), so it was left out.

**Prompt (verbatim):**
> Implement PATCH /prompts/{id} for partial model updates.  Only update fields provided in the request - don't require all fields.  Update updated_at to current timestamp.  Return 404 if the ID doesn't resolve to an existing prompt.  Follow the patterns already in the codebase.  Ensure there's a test and make sure it passes before completion.  If a field is provided in the request and the value is null, it should null that field in the model unless it's a field that requires a value, in which case a 400 response code should be given.

**Response (summarised — relevant part):**
Design stated first: a `PromptPatch` model with every field `Optional` and the same length constraints as `PromptBase` when a value is given; `model_dump(exclude_unset=True)` to distinguish *omitted* from *explicitly null*; null on `title`/`content` → 400 (`"<field> cannot be null"`); null on `description`/`collection_id` clears it; a non-null `collection_id` validated exactly as PUT does (400 "Collection not found"); `updated_at` set on every successful PATCH; Pydantic constraint violations (e.g. `""`) remain 422 for consistency with POST/PUT.

**Red:** added a `TestPatchPrompt` class with 11 tests — single-field patch leaves others unchanged and persists; multi-field patch; 404 unknown id; 404 on a soft-deleted prompt; null clears `description` and `collection_id`; null `title`/`content` → 400 and nothing changes (including `updated_at`); `""` → 422; unknown `collection_id` → 400; moving a prompt into a collection; empty body changes nothing but bumps `updated_at`; `id`/`created_at`/`deleted_on` in the body are ignored. 11 failed (405 — no route) / 27 passed.

**Green:** `models.py` — `PromptPatch(BaseModel)`. `api.py` — `patch_prompt` handler placed where the "PATCH endpoint is missing" note was, built in the PUT handler's shape: `storage.get_prompt` → 404; `updates = model_dump(exclude_unset=True)`; 400 for null required fields; collection check; new `Prompt(...)` with `updates.get(field, existing.field)` per field, `created_at` preserved, `updated_at=get_current_time()`; `storage.update_prompt`. **38 passed, 0 failed.**

**End-to-end** (fresh server, results observed before this entry was written): PATCH `{title}` → 200 with only `title` changed and `updated_at` advanced; PATCH `{description:null, collection_id:null}` → 200 with both cleared; PATCH `{title:null}` → 400 `"title cannot be null"`; PATCH `{title:""}` → 422; PATCH unknown `collection_id` → 400; PATCH unknown prompt id → 404.

**Outcome:** Accepted — all C1.4 items complete (4 bugs, PATCH, 38 tests green); pushed to `bugfixes` and opened PR #2 on my fork.
**Why I changed my next prompt:** The code work was done; moved to Task 1.9 documentation, starting with the docstrings.

## P-11 — Google-style docstrings on every modified or added function

**Stage:** Documentation
**Context given:** `git diff 1df4cbd` to enumerate exactly which functions and classes changed, then each function body individually while writing its docstring. No whole-repo context.
**Why that context:** C1.6 fails on an `Args` entry that doesn't exist or a `Raises` that doesn't match. The diff is the authoritative list of what must be documented, and the body of each function is the only source of truth for its Args/Returns/Raises — wider context would invite describing behaviour that isn't there.

**Prompt (verbatim):**
> Add Google-style docstrings to every function we modified or added

**Response (summarised — relevant part):**
Claude noted that a signature-only grep of the diff misses functions whose bodies changed without their signature changing, and worked from the full diff instead. Docstrings added with `Args`, `Returns` and `Raises` (the latter only where the function actually raises, listing the specific `HTTPException` status codes and their triggers): `api.py` — `get_prompt`, `update_prompt`, `patch_prompt`, `delete_collection`; `storage.py` — the `Storage` class and all eight modified methods (`get_prompt`, `get_all_prompts`, `update_prompt`, `delete_prompt`, `get_collection`, `get_all_collections`, `delete_collection`, `get_prompts_by_collection`); `utils.py` — `sort_prompts_by_date`; `models.py` — `Prompt`, `Collection`, `PromptPatch` (class docstrings with `Attributes`). The 29 new test functions/classes and the two provided tests that were edited got one-line docstrings describing the behaviour checked rather than restating the name. Then an AST-based check: every function/class overlapping a changed hunk since `1df4cbd` (53 total) has a docstring; for every app function, the set of `Args` names equals the real parameter set and a `Raises` section is present exactly when the body contains a `raise`. Result: 0 missing, 0 mismatches. Suite: 38 passed.

**Outcome:** Accepted
**Why I changed my next prompt:** Docstrings done; moved to the second half of Task 1.9, the README, with the clean-clone requirement stated as a hard constraint.

## P-12 — README: what the service is and how to run it, verified on a clean clone

**Stage:** Documentation → Verification
**Context given:** Files: `README.md` (whole file), `backend/main.py`, `backend/requirements.txt`; the P-03/P-03a finding about `uvicorn.run` and the Python 3.13 / `pydantic-core` build failure I hit earlier in the session. Then a fresh `git clone` into a scratch directory, following only the README.
**Why that context:** The README is judged by whether its steps work on a fresh machine, so the inputs were the README itself, the entry script it tells you to run, and the dependency file it tells you to install — plus the two environment failures already known. Verification by actually cloning is the only way to know the steps work.

**Prompt (verbatim):**
> In the README, add a section explaining what the service is and how to run it.  The steps must work on a clean clone.

**Response (summarised — relevant part):**
Identified what in the existing README fails or misleads on a clean clone: `python main.py` exits with status 1 (P-03a); "Python 3.10+" includes 3.13, which cannot build the pinned `pydantic-core`; `cd promptlab` names a directory that does not exist; `pip install` with no virtual environment; an endpoint table that still lists the bugs and omits PATCH. Changes: (1) `backend/main.py` now calls `uvicorn.run("app.api:app", ...)` — the import-string form — so `python main.py` starts and hot reload works; the unused `from app.api import app` import was dropped and the module docstring explains why. (2) Added `.python-version` = `3.12`. (3) Replaced the Quick Start with *What This Service Is* (prompts, collections, in-memory store, soft delete) and *Running It* (prerequisites with the 3.10–3.12 limit and the reason, clone → venv → install → `python main.py`, the reload-empties-the-store caveat, a curl quick check, test instructions, known issues). Updated the project-structure tree and the endpoint table to the current state, including PATCH and soft-delete semantics. **Clean-clone check:** cloned the branch into a scratch directory and ran the README commands verbatim — `python3.12 -m venv .venv`, `pip install -r requirements.txt`, `pytest tests/ -v` → 38 passed, `python main.py` → uvicorn started with the reloader, `curl /health` → `{"status":"healthy","version":"0.1.0"}`, POST created a prompt, `/openapi.json` lists the PATCH route.

**Outcome:** Accepted
**Why I changed my next prompt:** README verified on a clean clone; the last document still describing the pre-fix code was the system model, so I asked for it to be brought up to date and for the work to go in its own PR.

## P-13 — Update SYSTEM_MODEL.md for soft delete, PATCH, and the final context strategy table

**Stage:** Documentation
**Context given:** Files: `docs/SYSTEM_MODEL.md` (whole), the final `backend/app/api.py`, `models.py`, `storage.py`, and `docs/prompt-log.md` for the log IDs cited in the context table. Plus a short script exercising the storage layer and `PromptPatch` to confirm the new claims before committing.
**Why that context:** Every *After Module 1* note had to be checked against the code as it now is, not as remembered from the fixes; the context table cites log entries by ID, so the log was needed to make sure each reference points at a real entry.

**Prompt (verbatim):**
> Update SYSTEM_MODEL.md with the soft delete, PATCH, and final context strategy table.  Commit changes and create a new PR

**Response (summarised — relevant part):**
Kept the document's "as found" framing and added **After Module 1** notes rather than rewriting history: §1 — `main.py` now passes the import string and `python main.py` works; §2 — test count 13→38, the four routes whose behaviour changed, and an eleventh-route table row for `PATCH /prompts/{id}` with its 404/400/422 cases; §3 — `updated_at` now set on PUT, a new *Partially updating a prompt* flow (exclude_unset, null rules, preserved `created_at`, empty body), and a *soft delete with cascade* subsection replacing the four orphan rows with the post-fix behaviour and recording the strategy reasoning; §4 — `deleted_on` on `Prompt`/`Collection`, `PromptPatch` in the model tree, and why clients cannot set `deleted_on`; §5 — how soft delete changed every storage read and delete, `include_deleted`, limitation 5 revised, new limitation 8 (deleted rows accumulate); §7 — `get_prompts_by_collection` is now used by the cascade. Replaced the four *planned* rows of the context table with rows for P-03a and P-04 through P-13, each with the actual context given and the reason, and a closing paragraph on the pattern (whole repo for exploration, single function for local fixes, whole file for the one cross-cutting change). Verified before committing: deleting a collection twice returns `True` then `False`; cascade timestamps match; `update_prompt` on a deleted id returns `None`; `PromptPatch` drops `id`/`deleted_on` from its input; every `P-nn` cited in the document exists in this log. Created branch `system-model-update` from `bugfixes` and opened a PR against `bugfixes` (PR #2 is still open, so stacking avoids duplicating its commits).

**Outcome:** Accepted — merged via PR #3 (into `bugfixes`) and PR #4 (into `main`). PR #2 had been merged before the docstring, README and system-model commits were pushed, so a follow-up PR #4 carried them to `main`; nothing was lost.
**Why I changed my next prompt:** Module complete. Remaining prompts were merge confirmations and the submission summary.

