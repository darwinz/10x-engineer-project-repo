# AI Verification Note

One instance, from the exploration stage, where the AI's output looked right, was wrong, and would have gone into the system model as fact if I had not pushed back. Traceable to **P-03** (where the claim was made) and **P-03a** (where it was caught) in `docs/prompt-log.md`.

## What the AI produced

In P-03 I asked Claude to cover the remaining headings for `SYSTEM_MODEL.md` — architecture, entry points, dependencies and so on. Under *Architecture* it reported a problem with `backend/main.py`, which starts the server with:

```python
uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

The claim, quoted from the P-03 response:

> `main.py` passes the app object to `uvicorn.run(..., reload=True)` so reload is silently disabled … `python main.py` works, but edits require a restart.

It backed this up by saying uvicorn's `run()` source "contains the warning *You must pass the application as an import string to enable 'reload'*". That part is true, and it made the conclusion sound verified.

## Why it was wrong

Uvicorn 0.27.0 does not warn and carry on. The branch that emits that warning ends with `sys.exit(1)`:

```python
if (config.reload or config.workers > 1) and not isinstance(app, str):
    logger = logging.getLogger("uvicorn.error")
    logger.warning(
        "You must pass the application as an import string to enable 'reload' or "
        "'workers'."
    )
    sys.exit(1)
```

So `python main.py` does not "work with reload disabled". It prints the warning and exits with status 1 before binding a port. The README's *Run Locally* instruction, which tells you to run `python main.py`, does not start the server at all.

The AI had found the warning string in the source and stopped reading there. The conclusion was an inference from the presence of a warning — "a warning means it continues" — not from what the code does after the warning.

## How I detected it

When I asked for the `SYSTEM_MODEL.md` draft I added an explicit constraint: it **must** be accurate to the codebase and the AI must **not guess**. That prompt is logged verbatim as P-03a. Rather than letting the earlier claim flow into the document, the AI re-checked it under that constraint in two steps, both of which I could see in the session:

1. It printed the lines of `uvicorn.run` *around* the warning instead of just searching for the string, which exposed the `sys.exit(1)` immediately after it.
2. It ran `python main.py` with a timeout. Output:

   ```
   WARNING:  You must pass the application as an import string to enable 'reload' or 'workers'.
   exit code: 1
   ```

   For contrast it then ran `uvicorn app.api:app --port 8765`, which started normally (`Application startup complete`).

The exit code is what settled it. A warning followed by a running server and a warning followed by exit status 1 are different behaviours, and only the second matches the code.

## What I did instead

- Did not accept the "reload silently disabled" description. `docs/SYSTEM_MODEL.md` §1 now has a subsection, *The entry script does not work*, that states the actual behaviour, quotes the exit code, and names the working alternative (`uvicorn app.api:app --reload` from `backend/`).
- Recorded the wrong sentence verbatim in the P-03 log entry, with the source lines that contradict it, per the log's convention for mistakes.
- Carried the finding forward into the rest of the module: every end-to-end check in P-05 through P-08 starts the server with the import-string form, and the README run instructions are being rewritten so that a fresh clone actually starts (C1.6). Whether to fix `main.py` itself — a one-token change to `uvicorn.run("app.api:app", ...)` — is a decision for the README task; either way the instruction the assessor follows will be one that works.

## Why this one matters

It is not a syntax error and nothing in an editor would have flagged it. The sentence was plausible, partly correct, and cited real evidence from the dependency's source. Had it gone into the system model unchecked, the document would have described `python main.py` as a working entry point with a minor limitation, and the README would have kept an instruction that fails on every machine.
