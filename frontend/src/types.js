/**
 * Shared JSDoc type definitions mirroring backend/app/models.py.
 *
 * This project is plain JavaScript, not TypeScript (see specs/frontend.md,
 * Overview) — these @typedef blocks document every field's name, type, and
 * nullability in one place, but nothing here is checked by a compiler.
 */

/**
 * @typedef {Object} Prompt
 * @property {string} id
 * @property {string} title - 1-200 chars
 * @property {string} content - 1+ chars, may contain {{variable}} placeholders
 * @property {string|null} description - 0-500 chars
 * @property {string|null} collection_id
 * @property {string} created_at - naive UTC ISO, no timezone suffix
 * @property {string} updated_at
 * @property {string|null} deleted_on - always null in normal reads
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

export {}
