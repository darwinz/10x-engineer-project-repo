import { request } from './client'

/**
 * GET /prompts, optionally filtered.
 *
 * @param {Object} [filters]
 * @param {string} [filters.collectionId]
 * @param {string} [filters.search]
 * @returns {Promise<import('../types').PromptList>}
 */
function listPrompts({ collectionId, search } = {}) {
  const params = new URLSearchParams()
  if (collectionId) params.set('collection_id', collectionId)
  if (search) params.set('search', search)
  const query = params.toString()
  return request(`/prompts${query ? `?${query}` : ''}`)
}

/**
 * GET /prompts/{id}
 * @param {string} id
 * @returns {Promise<import('../types').Prompt>}
 */
function getPrompt(id) {
  return request(`/prompts/${id}`)
}

/**
 * POST /prompts
 * @param {{ title: string, content: string, description?: string|null, collection_id?: string|null }} data
 * @returns {Promise<import('../types').Prompt>}
 */
function createPrompt(data) {
  return request('/prompts', { method: 'POST', body: JSON.stringify(data) })
}

/**
 * PATCH /prompts/{id} — send only the fields that changed.
 * @param {string} id
 * @param {Object} changes
 * @returns {Promise<import('../types').Prompt>}
 */
function updatePrompt(id, changes) {
  return request(`/prompts/${id}`, { method: 'PATCH', body: JSON.stringify(changes) })
}

/**
 * DELETE /prompts/{id}
 * @param {string} id
 * @returns {Promise<null>}
 */
function deletePrompt(id) {
  return request(`/prompts/${id}`, { method: 'DELETE' })
}

export { listPrompts, getPrompt, createPrompt, updatePrompt, deletePrompt }
