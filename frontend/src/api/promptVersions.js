import { request } from './client'

/**
 * GET /prompts/{promptId}/versions
 * @param {string} promptId
 * @returns {Promise<import('../types').PromptVersionList>}
 */
function listPromptVersions(promptId) {
  return request(`/prompts/${promptId}/versions`)
}

/**
 * GET /prompts/{promptId}/versions/{versionNumber}
 * @param {string} promptId
 * @param {number} versionNumber
 * @returns {Promise<import('../types').PromptVersion>}
 */
function getPromptVersion(promptId, versionNumber) {
  return request(`/prompts/${promptId}/versions/${versionNumber}`)
}

/**
 * POST /prompts/{promptId}/versions/{versionNumber}/restore
 * @param {string} promptId
 * @param {number} versionNumber
 * @returns {Promise<import('../types').Prompt>}
 */
function restorePromptVersion(promptId, versionNumber) {
  return request(`/prompts/${promptId}/versions/${versionNumber}/restore`, { method: 'POST' })
}

export { listPromptVersions, getPromptVersion, restorePromptVersion }
