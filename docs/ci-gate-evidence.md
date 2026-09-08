# CI Gate Evidence

Proof that `.github/workflows/ci.yml` actually fails the build when it should — not just a pipeline that runs tests and reports on them regardless of outcome. This is a documented, real experiment against the live GitHub Actions runs on the `Week3` branch of [`darwinz/10x-engineer-project-repo`](https://github.com/darwinz/10x-engineer-project-repo), not a hypothetical description of what the workflow is supposed to do.

## Method

1. Confirm the pipeline passes on a normal commit.
2. Intentionally break one assertion in an existing, passing test.
3. Push it and capture the resulting run — it must show `failure`, not `success`.
4. Revert the break, push again, and confirm the run goes back to `success`.

All four commits and all three runs below are real and can be opened directly.

## Step 1 — Baseline: pipeline passes

**Commit:** [`561ee5a`](https://github.com/darwinz/10x-engineer-project-repo/commit/561ee5ad62b0e73c46cdb4d48f0ff9a49eb31c42) — `ci: add GitHub Actions workflow (lint + test + coverage gate)`

**Run:** [33999598709](https://github.com/darwinz/10x-engineer-project-repo/actions/runs/33999598709) — **`success`**

```
Lint with ruff:
All checks passed!

Run tests with coverage (fails if coverage drops below 80%):
---------- coverage: platform linux, python 3.12.14-final-0 ----------
TOTAL               267      0   100%
Required test coverage of 80% reached. Total coverage: 100.00%
====================== 187 passed, 276 warnings in 1.54s =======================
```

## Step 2 — Break a test on purpose

Changed one line in `backend/tests/test_api.py`, in an existing test that was passing:

```diff
-        assert data["status"] == "healthy"
+        assert data["status"] == "INTENTIONALLY-BROKEN-FOR-CI-GATE-CHECK"
```

**Commit:** [`0dcf2a1`](https://github.com/darwinz/10x-engineer-project-repo/commit/0dcf2a1f25f29ce6464c11996cb7d46a3307296c) — `test: intentionally break test_health_check to verify CI gate fails (temporary)`

Verified locally before pushing, to confirm it was a real failure and not a typo:

```
$ pytest tests/ --cov=app --cov-report=term-missing --cov-fail-under=80
...
Required test coverage of 80% reached. Total coverage: 100.00%
================= 1 failed, 186 passed, 276 warnings in 1.01s ==================
```

(Coverage stays at 100% here — this is a genuine *test-failure* gate, not a coverage-threshold gate. The two are independent mechanisms in the same step, and this experiment specifically proves the first one, since that's the one a pipeline can silently fail to enforce.)

## Step 3 — Capture the failed run

**Run:** [33999667990](https://github.com/darwinz/10x-engineer-project-repo/actions/runs/33999667990) — **`failure`**

```
JOBS
X Lint & Test in 12s (ID 101396151075)
  ✓ Set up job
  ✓ Check out repository
  ✓ Set up Python
  ✓ Install dependencies
  ✓ Lint with ruff
  X Run tests with coverage (fails if coverage drops below 80%)
  - Post Set up Python
  ✓ Post Check out repository
  ✓ Complete job

X Process completed with exit code 1.
```

Actual pytest output from that run's log:

```
E       AssertionError: assert 'healthy' == 'INTENTIONALL...CI-GATE-CHECK'
E         - INTENTIONALLY-BROKEN-FOR-CI-GATE-CHECK
E         + healthy

tests/test_api.py:17: AssertionError
...
---------- coverage: platform linux, python 3.12.14-final-0 ----------
TOTAL               267      0   100%
Required test coverage of 80% reached. Total coverage: 100.00%
=========================== short test summary info ============================
FAILED tests/test_api.py::TestHealth::test_health_check - AssertionError: assert 'healthy' == 'INTENTIONALL...CI-GATE-CHECK'
================= 1 failed, 186 passed, 276 warnings in 1.35s ==================
```

The run's overall conclusion is `failure` (confirmed via `gh run view 33999667990` and the GitHub UI) — the lint step passed, but the test step's non-zero exit code failed the job, which failed the run. Nothing downstream was silently marked green.

## Step 4 — Revert and confirm the gate goes back to green

**Commit:** [`1ba3370`](https://github.com/darwinz/10x-engineer-project-repo/commit/1ba337054d163950236b1be402309cb0e3693576) — `Revert "test: intentionally break test_health_check to verify CI gate fails (temporary)"` (a real `git revert`, not a manual edit — the diff is the exact inverse of Step 2's)

**Run:** [33999778405](https://github.com/darwinz/10x-engineer-project-repo/actions/runs/33999778405) — **`success`**

```
Lint with ruff:
All checks passed!

Run tests with coverage (fails if coverage drops below 80%):
TOTAL               267      0   100%
Required test coverage of 80% reached. Total coverage: 100.00%
====================== 187 passed, 276 warnings in 1.59s =======================
```

## Conclusion

| Step | Commit | Run | Conclusion |
|---|---|---|---|
| Baseline | `561ee5a` | [33999598709](https://github.com/darwinz/10x-engineer-project-repo/actions/runs/33999598709) | ✅ success |
| Break a test | `0dcf2a1` | [33999667990](https://github.com/darwinz/10x-engineer-project-repo/actions/runs/33999667990) | ❌ **failure** |
| Revert | `1ba3370` | [33999778405](https://github.com/darwinz/10x-engineer-project-repo/actions/runs/33999778405) | ✅ success |

The pipeline goes red exactly when it should and only then — a broken test fails the run, and fixing it turns the run green again on the next push, with no manual intervention on the workflow itself. The coverage gate (`--cov-fail-under=80`) is a separate, independent mechanism from this test-failure gate; both live in the same `pytest` invocation, so either one failing fails the same step. This experiment specifically targeted the test-failure path, since a pipeline that runs `pytest` but ignores its exit code — for example by piping through something that always exits 0, or treating a report file as the source of truth instead of the process exit code — is the failure mode this evidence is meant to rule out.
