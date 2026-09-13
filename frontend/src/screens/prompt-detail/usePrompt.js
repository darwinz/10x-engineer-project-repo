import { useCallback, useEffect, useState } from 'react'
import { getPrompt, updatePrompt, deletePrompt } from '../../api/prompts'
import { ApiError } from '../../api/client'

/**
 * Loads a single prompt and exposes patch/delete actions.
 *
 * Editing is PATCH-only (never PUT). An empty string for `description` or
 * `collection_id` in the edit form means "clear this field", so it is
 * converted to `null` here before diffing against the loaded prompt —
 * fields that are unchanged from the loaded prompt are omitted from the
 * PATCH body entirely, matching the backend's null-vs-omitted semantics.
 *
 * @param {string} promptId
 */
function usePrompt(promptId) {
  const [prompt, setPrompt] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      setPrompt(await getPrompt(promptId))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load prompt.')
    } finally {
      setIsLoading(false)
    }
  }, [promptId])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional fetch-on-mount; no caching library per spec's state-management decision
    load()
  }, [load])

  async function save(values) {
    const changes = {}
    const description = values.description === '' ? null : values.description
    const collectionId = values.collection_id === '' ? null : values.collection_id

    if (values.title !== prompt.title) changes.title = values.title
    if (values.content !== prompt.content) changes.content = values.content
    if (description !== (prompt.description ?? null)) changes.description = description
    if (collectionId !== (prompt.collection_id ?? null)) changes.collection_id = collectionId

    const updated = await updatePrompt(promptId, changes)
    setPrompt(updated)
    return updated
  }

  async function remove() {
    await deletePrompt(promptId)
  }

  return { prompt, isLoading, error, reload: load, save, remove }
}

export default usePrompt
