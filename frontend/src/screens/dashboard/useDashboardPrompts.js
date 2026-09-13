import { useCallback, useEffect, useState } from 'react'
import { listPrompts, createPrompt, deletePrompt } from '../../api/prompts'
import { listCollections } from '../../api/collections'
import { ApiError } from '../../api/client'

/**
 * Loads the dashboard's prompt list (optionally filtered by collection or
 * search text) plus the collections used to populate the filter bar and
 * create-prompt form, and exposes create/delete actions.
 *
 * @param {{ collectionId?: string, search?: string }} filters
 */
function useDashboardPrompts({ collectionId, search } = {}) {
  const [prompts, setPrompts] = useState([])
  const [collections, setCollections] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [promptList, collectionList] = await Promise.all([
        listPrompts({ collectionId, search }),
        listCollections(),
      ])
      setPrompts(promptList.prompts)
      setCollections(collectionList.collections)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load prompts.')
    } finally {
      setIsLoading(false)
    }
  }, [collectionId, search])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional fetch-on-mount; no caching library per spec's state-management decision
    load()
  }, [load])

  async function create(data) {
    const created = await createPrompt(data)
    setPrompts((current) => [created, ...current])
    return created
  }

  async function remove(id) {
    await deletePrompt(id)
    setPrompts((current) => current.filter((prompt) => prompt.id !== id))
  }

  return { prompts, collections, isLoading, error, reload: load, create, remove }
}

export default useDashboardPrompts
