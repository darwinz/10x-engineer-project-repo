# Spec: PromptLab Frontend (React + Vite)

Status: Draft — planned for a future module. Not yet implemented.

## Overview

A React (Vite, JavaScript) single-page app consuming the existing FastAPI backend documented in `docs/API_REFERENCE.md`, against the models in `backend/app/models.py`. No auth exists on the backend and CORS is already open (`allow_origins=["*"]`), so this spec adds no login flow, token storage, or auth headers — every request is a plain, unauthenticated fetch.

**JavaScript, not TypeScript.** This matches the current scaffold as-is (`npm create vite@latest -- --template react` produces plain JavaScript — `.jsx`, no `tsconfig.json`, no `typescript` package) — no conversion needed before Section 2's screens are built. The trade-off is worth stating plainly rather than glossing over: without TypeScript, a mismatched field name or a wrong optional/required assumption at the `api/` boundary (Section 6) surfaces at runtime, not at compile time. The data model below is still fully documented — as JSDoc `@typedef` blocks rather than TypeScript `interface`s — so every field's name, type, and nullability is written down in one place; it just isn't checked by a compiler. That's exactly why the `api/` layer (Section 6) matters more here than it would in a typed codebase: it's the one place every response shape gets touched, so a shape bug is easier to catch there in review or a quick manual check than if untyped data could drift at every call site independently.

**Ground truth this spec is built against** (endpoints actually implemented, not the tagging/versioning aspirations in other specs beyond what's live):

| Method | Endpoint |
|---|---|
| `GET` | `/health` |
| `GET` | `/prompts` (`?collection_id=`, `?search=`) |
| `POST` | `/prompts` |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/prompts/{id}` |
| `GET` | `/prompts/{id}/versions` |
| `GET` | `/prompts/{id}/versions/{version_number}` |
| `POST` | `/prompts/{id}/versions/{version_number}/restore` |
| `GET` / `POST` | `/collections` |
| `GET` / `DELETE` | `/collections/{id}` |

**Explicitly out of scope**: no Tags screen, no tag filter control, no call to any `/tags` or `/prompts/{id}/tags` endpoint. `specs/tagging-system.md` describes a future feature with no backend implementation yet — the UI must not reference it beyond one line in [Future Screens](#future-screens-not-built-now).

**Data model** (from `backend/app/models.py`, documented here as JSDoc `@typedef` blocks so every field's shape and nullability is written down even without TypeScript):

```js
/**
 * @typedef {Object} Prompt
 * @property {string} id
 * @property {string} title - 1-200 chars
 * @property {string} content - 1+ chars, may contain {{variable}} placeholders
 * @property {string|null} description - 0-500 chars
 * @property {string|null} collection_id
 * @property {string} created_at - naive UTC ISO, no timezone suffix
 * @property {string} updated_at
 * @property {string|null} deleted_on - always null in normal reads — soft-deleted rows never come back
 */

/**
 * @typedef {Object} Collection
 * @property {string} id
 * @property {string} name - 1-100 chars
 * @property {string|null} description - 0-500 chars
 * @property {string} created_at
 * @property {string|null} deleted_on
 */

/**
 * @typedef {Object} PromptVersion
 * @property {string} id
 * @property {string} prompt_id
 * @property {number} version_number - 1-based, increasing
 * @property {string} title
 * @property {string} content
 * @property {string|null} description
 * @property {string} created_at
 */

/**
 * @typedef {Object} PromptList
 * @property {Prompt[]} prompts
 * @property {number} total
 */

/**
 * @typedef {Object} CollectionList
 * @property {Collection[]} collections
 * @property {number} total
 */

/**
 * @typedef {Object} PromptVersionList
 * @property {PromptVersion[]} versions
 * @property {number} total
 */

// Every handler-raised error (400/404) is this shape:
/**
 * @typedef {Object} ApiErrorDetail
 * @property {string} detail
 */

// Every 422 (Pydantic validation) is this shape instead:
/**
 * @typedef {Object} ValidationErrorDetail
 * @property {Array<{type: string, loc: Array<string|number>, msg: string, input?: *}>} detail
 */
```

Because storage is in-memory and resets on every backend restart, **"there is nothing yet" is a routine, expected state for every screen** — not a rare edge case to handle apologetically. Every empty-state design below treats a fresh/reset backend as the normal first-run experience, not a broken one.

---

## 1. Screens

| Screen | Route | Purpose (one sentence) |
|---|---|---|
| Prompt Dashboard | `/` | Browse, search, and filter every active prompt, and the entry point for creating a new one. |
| Prompt Detail | `/prompts/:id` | View a single prompt's full content, edit it in place, delete it, and jump to its version history. |
| Version History | `/prompts/:id/versions` | Browse every saved version of one prompt and restore an older one as its current content. |
| Collections | `/collections` | Browse, create, and delete collections, understanding that deleting one takes its prompts with it. |

`/` also accepts `?collection_id=<id>` (set when arriving from a Collection card) and `?search=<text>` (set when the user types in the dashboard's own search box) — both are the same screen, not a fifth one.

## Future screens (not built now)

- **Tags** — no route, no component, no fetch. `specs/tagging-system.md` describes `Tag`, `GET/POST /tags`, and `GET/POST /prompts/{id}/tags`, none of which exist in `backend/app/api.py` today. If that spec ships, the natural addition is a `TagFilterChips` control on the Dashboard and a `TagsPage` mirroring `CollectionsPage` — not designed further here, since designing UI against an endpoint that returns a 404 today would be speculative.

---

## 2. Component inventory

Naming convention: `*Page` components are **containers** (own data-fetching and mutation calls, own the loading/error/empty decision for their screen). Everything else is **presentational** (props in, JSX out, no `fetch` calls, no knowledge of endpoints) unless explicitly marked container. This mirrors the Module 3 refactor's discipline — extract the single responsibility, don't let one component both fetch data and render four different visual states inline.

Props below are documented with a plain type in parentheses, not TypeScript syntax — there's no compiler checking these, so treat them as the contract to code and review against, not an enforced guarantee.

### Shared (used by more than one screen)

| Component | Type | Responsibility | Props |
|---|---|---|---|
| `AppShell` | presentational | Top nav (links to `/` and `/collections`) plus a content slot. | `children` (node) |
| `LoadingSpinner` | presentational | Render a loading indicator, nothing else. | `label` (string, optional) |
| `ErrorBanner` | presentational | Render one error (network failure or an `ApiErrorDetail`) with an optional retry action. | `error` (string), `onRetry` (function, optional) |
| `EmptyState` | presentational | Render a "nothing here yet" block with an optional call-to-action. | `title` (string), `message` (string), `actionLabel` (string, optional), `onAction` (function, optional) |
| `DeleteConfirmDialog` | presentational | Ask the user to confirm a destructive action before it fires; stays open and shows `error` instead of closing if the confirmed action fails. | `isOpen` (boolean), `title` (string), `message` (string), `confirmLabel` (string), `error` (string or null), `onConfirm` (function), `onCancel` (function) |
| `PromptForm` | presentational | Controlled form for `title`/`content`/`description`/`collection_id`; used by both prompt-create and prompt-edit — it never calls an endpoint itself. | `initialValues` (object: `{ title, content, description, collection_id }`), `collections` (array of `Collection`), `submitLabel` (string), `isSubmitting` (boolean), `submitError` (string or null), `onSubmit` (function, receives the form values), `onCancel` (function) |

### Prompt Dashboard (`/`)

| Component | Type | Responsibility | Props |
|---|---|---|---|
| `PromptDashboardPage` | container | Reads `collection_id`/`search` from the URL, fetches the matching prompt list and the collection list (for the filter dropdown and name lookups), owns the create-prompt modal's open state. | *(route-level; no props)* |
| `PromptFilterBar` | presentational | Search box + collection dropdown; reports changes upward, decides nothing about fetching. | `searchValue` (string), `onSearchChange` (function, receives the new search text), `collections` (array of `Collection`), `selectedCollectionId` (string or null), `onCollectionChange` (function, receives the new collection id or null) |
| `PromptList` | presentational | Render one `PromptCard` per prompt. Only ever rendered when the list is non-empty — the page decides loading/error/empty. | `prompts` (array of `Prompt`), `collectionsById` (object mapping collection id to `Collection`), `onSelect` (function, receives the prompt id), `onDelete` (function, receives the prompt id) |
| `PromptCard` | presentational | One prompt preview: title, truncated content, collection badge if any, `updated_at`, a delete affordance. | `prompt` (`Prompt`), `collectionName` (string, optional), `onSelect` (function), `onDelete` (function) |
| `CreatePromptButton` | presentational | Opens the create modal. | `onClick` (function) |
| `CreatePromptModal` | container | Wraps `PromptForm`; on submit, calls `POST /prompts`; on success, calls `onCreated` and closes. | `isOpen` (boolean), `collections` (array of `Collection`), `onClose` (function), `onCreated` (function, receives the created `Prompt`) |

### Prompt Detail (`/prompts/:id`)

| Component | Type | Responsibility | Props |
|---|---|---|---|
| `PromptDetailPage` | container | Fetches the prompt and the collection list on mount; owns view/edit toggle; on save, diffs the form against the loaded prompt and sends only changed fields via `PATCH`; owns delete confirmation and the `DELETE` call; redirects to `/` after a successful delete. | *(route-level; reads `:id` from the router)* |
| `PromptViewPanel` | presentational | Read-only display of title/content/description/collection name/timestamps, with buttons to edit, delete, and view version history. | `prompt` (`Prompt`), `collectionName` (string, optional), `onEdit` (function), `onDelete` (function), `onViewVersions` (function) |
| `PromptForm` | *(shared, see above)* | Reused here in edit mode, `initialValues` populated from the loaded prompt. | — |

### Version History (`/prompts/:id/versions`)

| Component | Type | Responsibility | Props |
|---|---|---|---|
| `VersionHistoryPage` | container | Fetches the parent prompt (for its title, as a breadcrumb) and `GET /prompts/{id}/versions` on mount; owns which version is selected for the detail panel; owns the restore call and post-restore refetch. | *(route-level; reads `:id` from the router)* |
| `VersionTimeline` | presentational | List of `VersionListItem`s, newest first. | `versions` (array of `PromptVersion`), `currentVersionNumber` (number), `selectedVersionNumber` (number or null), `onSelect` (function, receives the version number) |
| `VersionListItem` | presentational | One row: version number, `created_at`, a "current" badge if applicable. | `version` (`PromptVersion`), `isCurrent` (boolean), `isSelected` (boolean), `onClick` (function) |
| `VersionDetailPanel` | presentational | Full title/content/description of the selected version, plus a restore button. Always enabled, even on the current version — `POST .../restore` always succeeds and always creates a new version per the spec, so disabling it for "no visible change" would misrepresent what the API actually does. | `version` (`PromptVersion` or null), `isCurrent` (boolean), `isRestoring` (boolean), `onRestore` (function) |

### Collections (`/collections`)

| Component | Type | Responsibility | Props |
|---|---|---|---|
| `CollectionsPage` | container | Fetches `GET /collections` on mount; owns the create-modal state and the delete-confirm + `DELETE` call. | *(route-level; no props)* |
| `CollectionList` | presentational | Render one `CollectionCard` per collection. | `collections` (array of `Collection`), `onSelect` (function, receives the collection id), `onDelete` (function, receives the collection id) |
| `CollectionCard` | presentational | Name, description, `created_at`, a "View prompts" link (navigates to `/?collection_id=<id>`), a delete affordance. | `collection` (`Collection`), `onSelect` (function), `onDelete` (function) |
| `CreateCollectionModal` | container | Wraps `CollectionForm`; on submit, calls `POST /collections`; on success, calls `onCreated` and closes. | `isOpen` (boolean), `onClose` (function), `onCreated` (function, receives the created `Collection`) |
| `CollectionForm` | presentational | Controlled form for `name`/`description`. | `initialValues` (object: `{ name, description }`), `isSubmitting` (boolean), `submitError` (string or null), `onSubmit` (function, receives the form values), `onCancel` (function) |

**Why `PromptForm` is one component, not two**: create and edit need the identical fields, identical client-side length limits (mirroring the backend's `Field` constraints so a user sees "200 characters max" before submitting, not only after a 422 comes back), and identical layout. A `CreatePromptForm`/`EditPromptForm` split would duplicate all of that and let the two drift — the same duplication smell `docs/refactor-note.md` documented in the backend, avoided here by construction instead of fixed after the fact.

---

## 3. Screen → endpoint mapping

| Screen | Endpoint | Trigger | What happens with the response |
|---|---|---|---|
| Dashboard | `GET /prompts?collection_id=&search=` | Mount, and whenever the URL's `collection_id`/`search` params change (filter bar edits push a new URL) | `PromptList` renders `response.prompts`; the count badge (if shown) uses `response.total` |
| Dashboard | `GET /collections` | Mount (once) | Populates the filter dropdown and the `collectionsById` map `PromptCard` uses to show a collection name instead of a raw id |
| Dashboard | `POST /prompts` | `CreatePromptModal` form submit | On `201`, close the modal, call `onCreated(prompt)`, which prepends the new prompt to the dashboard's in-memory list (no full refetch needed since the response body is the complete new `Prompt`) |
| Dashboard | `DELETE /prompts/{id}` | Clicking a `PromptCard`'s delete button, after `DeleteConfirmDialog` confirms | On `204`, remove that id from the dashboard's local prompt list |
| Prompt Detail | `GET /prompts/{id}` | Mount, and again after a successful `PATCH` (to reload the canonical `updated_at`) | Populates `PromptViewPanel`/`PromptForm` |
| Prompt Detail | `GET /collections` | Mount (once) | Populates the collection name shown in view mode and the dropdown in edit mode |
| Prompt Detail | `PATCH /prompts/{id}` | `PromptForm` submit while in edit mode | Body contains only the fields that differ from the loaded prompt. On `200`, replace local prompt state with the response body and switch back to view mode |
| Prompt Detail | `DELETE /prompts/{id}` | Delete button, after confirmation | On `204`, navigate to `/` |
| Version History | `GET /prompts/{id}` | Mount | Used only for the page's title/breadcrumb text, not re-fetched again on this screen |
| Version History | `GET /prompts/{id}/versions` | Mount, and again after a successful restore | `VersionTimeline` renders `response.versions`; the highest `version_number` is `currentVersionNumber` |
| Version History | `POST /prompts/{id}/versions/{n}/restore` | `VersionDetailPanel`'s restore button | On `200`, refetch `GET /prompts/{id}/versions` (a new version now exists) and show a brief confirmation; the returned `Prompt` is not otherwise displayed on this screen |
| Collections | `GET /collections` | Mount | `CollectionList` renders `response.collections` |
| Collections | `POST /collections` | `CreateCollectionModal` form submit | On `201`, close the modal, prepend the new collection to local state |
| Collections | `DELETE /collections/{id}` | Delete button, after a confirmation that explicitly names the cascade | On `204`, remove that id from local state (its prompts are now gone too, but this screen doesn't need to know that — the Dashboard will simply no longer return them) |

**`PUT /prompts/{id}` is deliberately never called by this UI**, even though it's a real endpoint. `PATCH` covers every edit this form supports — including clearing `description` or `collection_id`, since the diffed payload can send an explicit `null` for a field the user emptied — without `PUT`'s requirement to resend every field or silently blank out anything the caller omits. There's no screen in this spec that needs a "replace everything, no partial option" guarantee `PATCH` doesn't already give.

**Clearing a field sends an explicit `null`, not an empty string.** A cleared `description` textarea and a "No collection" dropdown selection both start as `""` in the DOM — before diffing against the loaded prompt, `usePrompt.js`'s save function converts an empty `description` or `collection_id` to `null` prior to comparison and submission. This is the only way to produce `PromptPatch`'s "explicitly cleared" case rather than "field omitted, leave as-is." `title` and `content` are exempt from this conversion: the backend rejects `null` on either with a `400`, and the form's own `min_length=1` validation already turns an empty `title`/`content` into a client-side validation error before a request is ever sent.

---

## 4. State management approach

**Decision: local state per screen (`useState`/`useEffect`, or a small custom hook per resource like `usePrompt(id)`), no global store, no client-side cache library (no Redux, Zustand, React Query, SWR).**

Reasoning, sized to this app specifically:

- **The data is small and cheap to refetch.** Storage is in-memory on a single backend process; a `GET /collections` call costs single-digit milliseconds. There's no latency or server-load reason to cache it client-side.
- **Cross-screen shared state is minimal.** The only data used on more than one screen is the collections list (Dashboard filter, Prompt Detail's dropdown, the Collections screen itself) — three call sites, each already needing to be "fresh" on its own mount anyway (a collection created on the Collections screen should show up in the Dashboard's filter the next time someone opens it, which a plain refetch-on-mount already gives for free, no invalidation logic required).
- **No optimistic-update or offline requirements.** Every mutation (`POST`, `PATCH`, `DELETE`) has an immediate, cheap round trip and updates local state directly from the real response body — there's no case here where the UX needs to assume success before the server confirms it.
- **No auth/session state exists to manage globally** (see Overview) — one of the usual reasons reached for a global store doesn't apply here at all.

A global store or fetch-caching library would be solving problems this app doesn't have: cache invalidation across many consumers, optimistic UI, deduplication of expensive requests. Introducing one now would be exactly the kind of premature abstraction this project's own conventions (`.github/copilot-instructions.md`) already warn against. If PromptLab grows to the point where the same prompt/collection data needs to stay in sync across many more simultaneously-open views, or list-fetches become expensive, React Query is the natural next step — but that's a future problem, not this one.

---

## 5. Loading, error, and empty states

For each screen: what renders, and how you'd actually check it in a browser — not just what the code is supposed to do.

### Prompt Dashboard

| State | Renders | How to verify |
|---|---|---|
| Loading | `LoadingSpinner` in place of the list while `GET /prompts` is in flight | DevTools → Network → throttle to "Slow 3G", reload `/`, confirm the spinner is visible before the list appears and is gone once it does — no flash of an empty list first |
| Error | `ErrorBanner` with the failure message and a "Retry" button that re-fires the same fetch | Stop the backend process, reload `/`, confirm a readable error message appears (not a blank white page or an unhandled-exception overlay); restart the backend, click Retry, confirm the list loads |
| Empty | `EmptyState` — "No prompts yet" + a "Create your first prompt" button that opens the same `CreatePromptModal` as the toolbar button | Restart the backend (clears in-memory storage) or filter to a collection with nothing in it, reload `/`, confirm the empty-state block renders (not a bare header with nothing under it), and that its button opens the create modal |

### Prompt Detail

| State | Renders | How to verify |
|---|---|---|
| Loading | `LoadingSpinner` while `GET /prompts/{id}` is in flight | DevTools Network tab: confirm exactly one `GET /prompts/{id}` fires on mount and the spinner is visible until it resolves |
| Error (not found) | A dedicated "Prompt not found" message using the API's own `detail` text, with a link back to `/` — distinct from the transient-failure banner below | Navigate directly to `/prompts/does-not-exist`, confirm the not-found message renders, not an infinite spinner or a crash |
| Error (transient) | `ErrorBanner` with Retry, same pattern as the Dashboard | Stop the backend, reload a valid prompt's URL, confirm the retry-capable banner (not the not-found message) renders; restart the backend, click Retry, confirm it loads |
| Empty | Not applicable — the backend's own `Field` constraints (`content: min_length=1`) guarantee a `Prompt` can never have blank content, so there's no "prompt with nothing in it" state to design for | N/A — noting this explicitly instead of silently skipping it |

### Version History

| State | Renders | How to verify |
|---|---|---|
| Loading | `LoadingSpinner` while `GET /prompts/{id}/versions` is in flight | DevTools Network tab: confirm the versions request fires once on mount |
| Error (not found) | "Prompt not found" if the prompt id in the URL doesn't exist; surface the API's actual `detail` string ("Prompt not found" vs. a hypothetical "Version not found" from the restore action) rather than one generic message, so the two failure modes are distinguishable to the user | Navigate directly to `/prompts/does-not-exist/versions`, confirm "Prompt not found" renders |
| Error (transient) | `ErrorBanner` with Retry | Stop the backend, reload, confirm the retry banner; restart, click Retry, confirm recovery |
| Empty | Not applicable in the "zero versions" sense — every prompt has at least version 1 from creation (`specs/prompt-versions.md`, US-1), so the minimum real state is a one-item timeline with that single entry marked current | Create a brand-new prompt, immediately open its version history, confirm exactly one entry renders and is marked current — not an empty-state block |

### Collections

| State | Renders | How to verify |
|---|---|---|
| Loading | `LoadingSpinner` while `GET /collections` is in flight | DevTools throttle + reload `/collections`, confirm spinner-then-list |
| Error | `ErrorBanner` with Retry | Stop the backend, reload `/collections`, confirm the banner; restart, click Retry, confirm recovery |
| Empty | `EmptyState` — "No collections yet" + "Create your first collection" | Restart the backend, navigate to `/collections`, confirm the empty-state block, not a bare list container |

### Form validation errors (Create/Edit Prompt, Create Collection)

All three forms can also receive a `422` from the backend (e.g., a title over 200 characters slips past a client-side check due to a bug, or a race with another client). The `422` body is the `ValidationErrorDetail` shape in [Overview](#overview) — an array, not a string. `PromptForm`/`CollectionForm` must read `error.detail[].loc`/`.msg` and show the message next to the specific field named in `loc`, not just a generic banner; a `400` (e.g. "Collection not found" if a collection was deleted in another tab between opening the form and submitting) is the plain-string shape and renders as a single form-level error above the submit button. Verify by: temporarily lowering `PromptForm`'s client-side title max-length check below the server's 200 (or removing it entirely) in a local build, submitting a 201-character title, and confirming the exact field-level message from the `422` response appears under the Title input rather than a blank failure or a raw JSON dump.

### Mutation failures (network-level, not validation)

A `POST`/`PATCH`/`DELETE` can also fail because the backend is unreachable rather than because of a `422`/`400` — e.g. the process crashes mid-edit. For create/edit forms this renders no differently than a validation failure: `submitError` is set to a generic message ("Could not reach the server — try again.") and shown in the same slot a field-level or form-level `422`/`400` message would occupy, so the form doesn't need a second failure UI. For delete, this is why `DeleteConfirmDialog` (Section 2) carries an `error` (string or null) prop: on a failed `DELETE` the dialog does not close — it stays open and renders that message below its confirm/cancel buttons, so the user isn't left unsure whether the delete actually happened. It closes only after a confirmed success. Verify by: stopping the backend, opening delete-confirmation on any prompt or collection, clicking confirm, and checking the dialog stays open with a visible error rather than silently closing or leaving the item in an ambiguous half-deleted state; restart the backend, click confirm again, confirm it now succeeds and the dialog closes.

---

## 6. Folder structure

**Principle: grouped by feature/screen, not by file type** — because each of PromptLab's four screens is close to a self-contained vertical slice (its own page, its own screen-specific components, its own data-fetching hook), colocating them keeps everything needed to understand or change one screen in one folder instead of forcing a jump between separate `components/`, `hooks/`, and `pages/` directories for every single edit.

```
frontend/src/
├── screens/
│   ├── dashboard/
│   │   ├── PromptDashboardPage.jsx
│   │   ├── PromptFilterBar.jsx
│   │   ├── PromptList.jsx
│   │   ├── PromptCard.jsx
│   │   ├── CreatePromptModal.jsx
│   │   └── useDashboardPrompts.js        # wraps GET /prompts with the URL's filter params
│   ├── prompt-detail/
│   │   ├── PromptDetailPage.jsx
│   │   ├── PromptViewPanel.jsx
│   │   └── usePrompt.js                  # GET/PATCH/DELETE /prompts/{id}
│   ├── version-history/
│   │   ├── VersionHistoryPage.jsx
│   │   ├── VersionTimeline.jsx
│   │   ├── VersionListItem.jsx
│   │   ├── VersionDetailPanel.jsx
│   │   └── usePromptVersions.js          # GET /prompts/{id}/versions, POST .../restore
│   └── collections/
│       ├── CollectionsPage.jsx
│       ├── CollectionList.jsx
│       ├── CollectionCard.jsx
│       ├── CreateCollectionModal.jsx
│       ├── CollectionForm.jsx
│       └── useCollections.js             # GET/POST/DELETE /collections
├── components/                            # used by more than one screen — see Section 2
│   ├── AppShell.jsx
│   ├── LoadingSpinner.jsx
│   ├── ErrorBanner.jsx
│   ├── EmptyState.jsx
│   ├── DeleteConfirmDialog.jsx
│   └── PromptForm.jsx
├── api/
│   ├── client.js                          # fetch wrapper: base URL, JSON parsing, matches the ApiErrorDetail/ValidationErrorDetail shapes from types.js
│   ├── prompts.js                         # functions: listPrompts, getPrompt, createPrompt, updatePrompt, deletePrompt
│   ├── promptVersions.js                  # listPromptVersions, getPromptVersion, restorePromptVersion
│   └── collections.js                     # listCollections, createCollection, deleteCollection
├── types.js                                 # JSDoc @typedef blocks: Prompt, Collection, PromptVersion, *List, ApiErrorDetail, ValidationErrorDetail
├── index.css                                # @import "tailwindcss" (v4) — see Section 7
├── App.jsx                                  # React Router route table
└── main.jsx                                 # imports index.css once
```

`api/` and `types.js` are the one deliberate exception to feature-grouping: request/response shapes and fetch functions are shared infrastructure every screen depends on, not something owned by any single one, so they live at the top level rather than being duplicated or arbitrarily assigned to whichever screen happened to need them first.

---

## 7. Styling

**Decision: Tailwind CSS v4**, utility classes applied directly in each component's JSX — no CSS Modules, no styled-components, no separate per-component stylesheet.

Reasoning:

- **Consistent with the folder-structure principle in Section 6.** Keeping a class string on the element itself keeps a component's markup and its appearance in one file, rather than splitting every component across a `.jsx` and a co-located `.module.css` that have to be kept in sync.
- **Sized to the app.** Four screens with a small, repeated set of visual patterns (cards, list rows, modals, form fields, banners) don't need a component-styling abstraction built for a much larger design system — the same "don't reach for infrastructure this app doesn't need" reasoning already applied to state management in Section 4.
- **Composes cleanly with the shared components in Section 2.** `ErrorBanner`, `EmptyState`, `LoadingSpinner`, `DeleteConfirmDialog`, and both forms each own their utility classes internally; no component in the Section 2 inventory gains a styling-related prop as a result of this decision — appearance is internal to each component, not something a parent configures.

Setup — v4 drops the config-file-and-directives pattern earlier Tailwind versions used, so there is deliberately less here than a v3 setup would have:

- `npm install tailwindcss @tailwindcss/vite`.
- `vite.config.js` — add the `@tailwindcss/vite` plugin alongside `@vitejs/plugin-react`.
- `src/index.css` — a single `@import "tailwindcss";` line (v4 syntax; the old three-directive `@tailwind base/components/utilities` form is v3-only and does not work in v4), imported once in `main.jsx`.
- No `tailwind.config.js` or `postcss.config.js` is required by default — v4 auto-detects content and needs no PostCSS pipeline of its own when using the Vite plugin. A `tailwind.config.js` remains optional, only if a custom theme or a plugin is added later.

---

## 8. Linting

**Decision: ESLint**, not oxlint — chosen over oxlint's speed advantage for its maturity and its React-hooks rule depth, given how much of Section 4's state management leans on custom per-resource hooks (`usePrompt`, `useCollections`, `usePromptVersions`).

- Config includes `eslint-plugin-react-hooks`, so those three hooks get `exhaustive-deps` and rules-of-hooks enforcement — the specific correctness gap that motivated ESLint over oxlint in the first place. Without TypeScript (see Overview) there's no `typescript-eslint` layer here — this codebase's only compile-time-adjacent check is this hooks linting, not type checking, so the `api/` layer's shape correctness (Section 6) leans more on careful review and manual verification than a typed codebase would need.
- Config lives at `frontend/eslint.config.js` (flat config), at the root of `frontend/`, alongside `package.json` and `vite.config.js`.
- Runs as a CI gate the same way `ruff` already does for the backend (`docs/ci-gate-evidence.md`'s pattern: lint + test on every push/PR), not just an editor-only check.
