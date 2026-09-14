# Deployment

PromptLab is deployed as two independently-hosted services:

| Service | Platform | Why |
|---|---|---|
| Frontend (React/Vite SPA) | [Vercel](https://vercel.com) | Purpose-built for static/SPA builds; free, fast, trivial to wire to a Git repo. |
| Backend (FastAPI) | [Render](https://render.com) (free web service) | See below — Vercel's serverless model is a poor fit for this backend as written. |

**Live URLs (current deployment):**

- Frontend: **https://frontend-brandon-johnsons-projects-f70ddf1b.vercel.app**
- Backend: **https://promptlab-backend-g2g1.onrender.com** (interactive docs at `/docs`)

Both are wired to auto-deploy from the `main` branch of `https://github.com/darwinz/10x-engineer-project-repo` — a push to `main` redeploys both services with no manual step, though the two use different mechanisms (see [Redeploying / updating](#redeploying--updating)). If you're setting this up from scratch (a new fork, a new Render/Vercel account), follow every step below; nothing here was configured by hand that isn't also written down here.

## Why the backend isn't on Vercel too

PromptLab's storage is **deliberately in-memory** (see `specs/frontend.md`'s Overview — "resets on every backend restart" is treated as a normal, expected state, not a bug). That design assumes a single persistent process.

Vercel Functions don't provide that: a Python ASGI app deployed there runs as serverless functions, and Vercel gives no guarantee that concurrent or sequential requests hit the same warm instance. In practice this would mean a prompt you just created could be missing on the very next request, served by a different cold instance with empty memory. That's not "resets on restart," it's "randomly inconsistent under normal use," and it would make the app look broken in a live demo.

Render's free web service runs the backend as one container, one process, exactly like `docker compose up` does locally — the in-memory model behaves the way it was built to behave. If you later replace in-memory storage with a real database, moving the backend to Vercel Functions (or anywhere else) becomes a reasonable option again.

## Environment variables and secrets

**The app itself has no secrets.** No auth, no database credentials, no third-party API keys. There is exactly one real secret in this project, and it exists purely to make CI able to trigger a deploy — see below.

| Variable | Where it's set | Value | Sensitive? |
|---|---|---|---|
| `VITE_API_BASE_URL` | Vercel → Project → Settings → Environment Variables (Production) | `https://promptlab-backend-g2g1.onrender.com` | No — this is plain config, visible in any browser's network tab. Baked in **at build time** by Vite, so changing it requires a new build, not just a restart. |
| `PORT` | Render → Service → Environment | `8000` | No. Tells Render which port to route traffic to. The backend's `Dockerfile` hardcodes `uvicorn ... --port 8000`; this just tells Render to match it instead of Render's own default (10000). |
| `RENDER_DEPLOY_HOOK_URL` | GitHub → repo → Settings → Secrets and variables → Actions | A Render-issued URL (`https://api.render.com/deploy/srv-...?key=...`) | **Yes.** Anyone holding it can trigger a deploy of the backend. Not read-access to data, but still not something to expose. |

**How `RENDER_DEPLOY_HOOK_URL` was set**, and how any future secret should be: it was never typed into a chat, a file, or a terminal command's arguments where it would land in shell history or these docs. The Render dashboard generated it; it was piped directly into `gh secret set RENDER_DEPLOY_HOOK_URL -R darwinz/10x-engineer-project-repo`, which stores it GitHub-side, encrypted, and exposes it to workflow runs only as `${{ secrets.RENDER_DEPLOY_HOOK_URL }}` — never in logs, never checked into the repo. `git log -p` and `git grep` over the full history confirm it appears nowhere in tracked files.

If this project later adds another real secret (an LLM API key, a database URL with credentials, etc.), follow the same pattern:
- **Never** commit it to a `.env` file, `vercel.json`, `render.yaml`, or any tracked file.
- Set it directly in the platform's environment variable UI (Vercel dashboard/CLI `vercel env add`, Render dashboard/CLI `render services update` or the dashboard's Environment tab) — both platforms store these encrypted and scope them per-environment.
- For local development, use a `.env`/`.env.local` file that's `.gitignore`d (both `frontend/.gitignore` and a future `backend/.gitignore` should list it), and — per this project's convention — prefer resolving local secrets from a password manager (e.g. `op read op://Vault/Item/field` for 1Password) rather than typing them into plaintext files at all.
- `git status` before committing, and grep the diff for anything that looks like a key before pushing. A leaked secret in git history isn't fixed by deleting the file in a later commit — it requires history rewriting and rotating the credential.

## Prerequisites

- A GitHub account with push access to a fork of this repo (or this repo itself).
- A [Render](https://render.com) account (free), linked to the same GitHub account/org as above.
- A [Vercel](https://vercel.com) account (free), linked to the same GitHub account/org.
- Optional, for the exact commands below: [Render CLI](https://render.com/docs/cli) (`brew install render`) and [Vercel CLI](https://vercel.com/docs/cli) (`npm i -g vercel`). Everything here is also doable by clicking through each platform's dashboard — the CLI just makes it scriptable and precise.

Nothing else is required. There's no database to provision, no message queue, no cache — the backend's only dependency is itself.

## Deploying the backend (Render)

The repo root has a committed `render.yaml` — a [Render Blueprint](https://render.com/docs/blueprint-spec) that fully describes the service (Docker runtime, `backend/Dockerfile`, free plan, `PORT=8000`). It's validated with:

```bash
render blueprints validate
```

### Option A — Dashboard, from the Blueprint (recommended for a fresh setup)

1. Go to the [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**.
2. Connect your GitHub account if you haven't, and select the repo (`darwinz/10x-engineer-project-repo` or your fork).
3. Render detects `render.yaml` at the repo root and shows one service to create: `promptlab-backend`. Confirm branch `main`, plan `free`, and click **Apply**.
4. Render builds `backend/Dockerfile` and deploys it. When it's live, copy the assigned URL (shown on the service's dashboard page, looks like `https://<name>-<random>.onrender.com`).

This is a one-time step that requires a human in the loop — Render's Blueprint flow needs you to authorize the GitHub connection in a browser; it can't be scripted headlessly from a fresh account.

### Option B — CLI (what was actually run for the live deployment above)

Equivalent to the Blueprint, without the dashboard:

```bash
render login                     # opens a browser for one-time device auth
render workspace set <your-workspace-id>

render services create \
  --name promptlab-backend \
  --type web_service \
  --runtime docker \
  --repo https://github.com/darwinz/10x-engineer-project-repo \
  --branch main \
  --root-directory backend \
  --plan free \
  --env-var PORT=8000 \
  --confirm --output json
```

Because this repo is **public**, Render can clone it directly from the URL — no GitHub App installation/authorization needed for this path (only Option A's Blueprint flow needs that, since it browses your repo list). If you fork this to a private repo, use Option A instead.

The command's JSON output includes `serviceDetails.url` — that's your backend's live URL.

**Important:** the service comes back reporting `autoDeploy: "yes"` / `autoDeployTrigger: "commit"`, but that field alone does **not** mean pushes will redeploy it — that requires Render's GitHub App to actually be installed with access to the repo (checkable at `https://github.com/settings/installations`), which this CLI path (creating from a bare repo URL) does not set up. Creating the service via Option A's dashboard Blueprint flow *does* install it, since that flow is how you browse/select the repo in the first place. This project's live deployment was created via this CLI path and got exactly this gap — see [Redeploying / updating](#redeploying--updating) for the fix that was actually used (a GitHub Actions step calling a Render Deploy Hook), which works regardless of which path you used here.

Watch a deploy's status (triggered either way) with:

```bash
render deploys list <service-id> --output json
```

### Verifying the backend

```bash
curl -s https://<your-backend-url>/prompts
# {"prompts":[],"total":0}
```

## Deploying the frontend (Vercel)

`frontend/vercel.json` pins the build settings explicitly (framework, build/install commands, output directory) so nothing depends on Vercel's autodetection guessing right.

### Option A — Dashboard, from Git import

1. [Vercel Dashboard](https://vercel.com/new) → **Import Git Repository** → select this repo.
2. **Root Directory**: set to `frontend` (this repo is a monorepo — the Vite app doesn't live at the repo root). This is the one setting that isn't inferred automatically and must be set explicitly, in the dashboard's "Configure Project" step before the first deploy.
3. Framework preset, build command, output directory are picked up from `frontend/vercel.json` automatically.
4. Before deploying, add the environment variable: **`VITE_API_BASE_URL`** = your backend's URL from the Render step, scoped to **Production** (and Preview, if you want preview deployments to also hit the real backend). This must be set *before* the first build — Vite inlines `VITE_*` variables at build time, not at request time.
5. Deploy.

### Option B — CLI (what was actually run for the live deployment above)

```bash
cd frontend
vercel link --yes                                    # creates/links the Vercel project

echo -n "https://promptlab-backend-g2g1.onrender.com" \
  | vercel env add VITE_API_BASE_URL production       # set before building, see above

vercel --prod --yes                                   # build + deploy to production
```

To get auto-deploy-on-push (so a future `git push origin main` redeploys the frontend without rerunning `vercel --prod` by hand), the project also needs to be Git-connected:

```bash
vercel git connect https://github.com/darwinz/10x-engineer-project-repo.git --yes
vercel project update frontend --root-directory frontend
```

**Gotcha hit during this deployment, worth knowing in advance:** `vercel git connect` fails with *"Make sure there aren't any typos and that you have access to the repository"* if the Vercel-for-GitHub App hasn't been granted access to the specific repo yet — even for a repo you own. Fix it at **https://github.com/settings/installations** → Vercel → Configure → add the repo to its access list, then retry the command. This is a one-time, human-only step (like Render's Blueprint GitHub auth) — it can't be done from a script or CLI token.

**Second gotcha:** `vercel link`/`vercel --prod` run from inside `frontend/` deploy correctly on their own (they just upload that directory), but once Git integration is connected, Vercel checks out the *whole* repo for each build and needs to be told to build from the `frontend/` subdirectory — that's the `vercel project update --root-directory frontend` line above. Skipping it means Git-triggered builds silently try to build the repo root (which has no `package.json`) and fail.

### Verifying the frontend

Open the production URL in a browser. The dashboard should load, show the empty-state ("No prompts yet…"), and creating a prompt should succeed with no CORS or network errors in the console — confirming it's actually talking to the Render backend, not just serving static HTML.

## CORS

The backend already has permissive CORS (`allow_origins=["*"]` in `backend/app/api.py`) since the app has no auth and nothing user-specific to protect — this needed no change to support the deployed frontend's origin. If auth is added later, tighten this to the frontend's specific origin(s).

## Running it without deploying anywhere (Docker)

If you don't want to create Render/Vercel accounts at all, both services run locally the same way they do deployed — from what's committed, no manual setup:

```bash
docker compose up --build
```

This builds both `backend/Dockerfile` and `frontend/Dockerfile`, serving the API at `http://localhost:8000` and the UI at `http://localhost:5173`, wired together (`VITE_API_BASE_URL=http://localhost:8000` is set in `docker-compose.yml`). See the root `README.md`'s Docker section for details (hot reload for both, what's in each image, etc.).

This satisfies the assignment's "runnable via a documented container command" allowance directly — no separate local-dev command needed for the frontend anymore.

## Redeploying / updating

Both services redeploy on push to `main`, but via two different mechanisms — worth understanding, because they were set up differently and failed differently before landing on what's below.

### Vercel — native Git integration

The frontend project is Git-connected (`vercel git connect`, see above), which is Vercel's own webhook-based integration. This just works: a push to `main` shows up as a new production deployment within seconds, confirmed by its `githubCommitSha` matching the pushed commit. Watch it with `vercel ls frontend` or the project's dashboard page. No CI step is involved — Vercel handles it entirely on its own.

### Render — GitHub Actions calling a Deploy Hook

Render's own "auto-deploy on push" needs its GitHub App installed on the repo (see the callout in the Render section above). Setting that up requires a human clicking through Render's own GitHub authorization — not something achievable by API/CLI alone — and wasn't available in this project's setup. Rather than leave the backend without auto-deploy, `.github/workflows/ci.yml` has a `deploy-backend` job:

```yaml
deploy-backend:
  name: Deploy backend (Render)
  needs: test
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
  runs-on: ubuntu-latest
  steps:
    - name: Trigger Render deploy hook
      run: curl -fsS -X POST "${{ secrets.RENDER_DEPLOY_HOOK_URL }}"
```

It runs only after `test` passes, only on pushes to `main` (never on pull requests, where the secret wouldn't be available to a fork anyway), and calls Render's Deploy Hook — a per-service URL from the Render dashboard (Service → Settings → Deploy Hook) that triggers a deploy of the latest commit on the service's configured branch when POSTed to. This is arguably a *better* setup than relying on Render's own auto-deploy: the backend only redeploys if the test suite actually passes first, which Render's own commit-trigger has no concept of.

**If you're setting this up from scratch:** create the service (Option A or B above), then in the Render dashboard grab its Deploy Hook URL, then run `gh secret set RENDER_DEPLOY_HOOK_URL -R <your-fork>` and paste it when prompted — the `deploy-backend` job is already in `.github/workflows/ci.yml` and will pick it up on the next push.

**Gotcha:** if your clone has more than one remote (this repo does — `origin` plus an `upstream` pointing at the course template), plain `gh secret set RENDER_DEPLOY_HOOK_URL` fails with `multiple remotes detected. please specify which repo to use`. Pass `-R <owner>/<repo>` explicitly, as above — that's not optional here.

### Environment variable changes

Both `VITE_API_BASE_URL` (Vercel) and any future config need a **new build** to take effect, not just a restart — they're baked in at build/deploy time. For Vercel, an empty commit or `vercel --prod` from `frontend/` triggers one; for Render, a push (via the Deploy Hook above) or `render deploys create <service-id>` does.

## Verification evidence

Claims above aren't just asserted — both auto-deploy paths were proven across two separate real pushes to `main`, not just the initial setup:

| Commit | Vercel deployment | Render deploy | GitHub Actions run |
|---|---|---|---|
| `1d99330` (added deployment.md) | `frontend-3irewtnkw-...vercel.app`, state `READY`, `githubCommitSha` matches exactly | — (this push predates the `deploy-backend` job) | — |
| `97105fb` (added `deploy-backend` job) | `frontend-o7bys7rnd-...vercel.app`, state `READY`, `githubCommitSha` matches exactly | `dep-dajp36e7bikc73cuqg6g`, `trigger: "deploy_hook"`, `status: "live"`, same commit | [Run 34812844036](https://github.com/darwinz/10x-engineer-project-repo/actions/runs/34812844036) — both `Lint & Test` and `Deploy backend (Render)` jobs green |

The backend was also confirmed responding correctly after that deploy: `curl https://promptlab-backend-g2g1.onrender.com/prompts` → `200 {"prompts":[],"total":0}`.

Separately, a full CRUD round trip was run against the live deployment through an actual browser, not just curl: created a prompt titled "Deployment Smoke Test" on the production Vercel URL, confirmed it appeared (proving the frontend's `fetch` reached the Render backend, CORS included), then deleted it via the same UI to leave the deployment clean.

## Known limitations of this deployment

- **In-memory storage still resets.** Deploying doesn't change the app's fundamental behavior: a Render restart (including the free tier spinning the service down after ~15 minutes of inactivity, and back up on the next request) clears all prompts and collections, same as restarting it locally. This is a pre-existing, intentional characteristic of the app (see `specs/frontend.md`), not something the deployment introduces — but it's worth knowing before treating the live URL as a stable demo of persisted data.
- **Render free-tier cold starts.** After idling, the first request to the backend can take 30–60 seconds while the container spins back up. The frontend will show its normal loading state during this, not an error, but it can look stalled.
- **No custom domain configured.** Both services use their platform-assigned `*.onrender.com` / `*.vercel.app` URLs. Adding a custom domain is a dashboard step (Render: Settings → Custom Domains; Vercel: Settings → Domains) not covered here since none was requested.
