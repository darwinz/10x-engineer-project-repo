/**
 * Shared fetch wrapper: base URL, JSON parsing, and error shapes matching
 * ApiErrorDetail / ValidationErrorDetail from types.js.
 *
 * Every other file under api/ calls `request()` — none of them touch
 * `fetch` directly, so this is the one place a response shape actually
 * gets parsed (see specs/frontend.md, Overview, on why that matters more
 * here than it would in a typed codebase).
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

/**
 * Thrown by `request()` for any non-2xx response.
 *
 * `body` is the parsed JSON body — an ApiErrorDetail ({ detail: string })
 * for a 400/404/409, or a ValidationErrorDetail ({ detail: [...] }) for a
 * 422. Callers that need to distinguish the two check `Array.isArray(err.body?.detail)`.
 */
class ApiError extends Error {
  constructor(status, body) {
    const message = typeof body?.detail === 'string' ? body.detail : `Request failed with status ${status}`
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

/**
 * Make a JSON request against the API and return the parsed body.
 *
 * @param {string} path - e.g. "/prompts" or "/prompts/abc123"
 * @param {RequestInit} [options]
 * @returns {Promise<*>} The parsed JSON body, or null for a 204.
 * @throws {ApiError} If the response status is not 2xx.
 * @throws {Error} If the network request itself fails (backend unreachable).
 */
async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (response.status === 204) {
    return null
  }

  const body = await response.json().catch(() => null)

  if (!response.ok) {
    throw new ApiError(response.status, body)
  }

  return body
}

export { API_BASE_URL, ApiError, request }
