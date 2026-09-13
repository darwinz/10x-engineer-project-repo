import { request } from './client'

/**
 * GET /collections
 * @returns {Promise<import('../types').CollectionList>}
 */
function listCollections() {
  return request('/collections')
}

/**
 * POST /collections
 * @param {{ name: string, description?: string|null }} data
 * @returns {Promise<import('../types').Collection>}
 */
function createCollection(data) {
  return request('/collections', { method: 'POST', body: JSON.stringify(data) })
}

/**
 * DELETE /collections/{id}
 * @param {string} id
 * @returns {Promise<null>}
 */
function deleteCollection(id) {
  return request(`/collections/${id}`, { method: 'DELETE' })
}

export { listCollections, createCollection, deleteCollection }
