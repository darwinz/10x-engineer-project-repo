import { useCallback, useEffect, useState } from 'react'
import { listCollections, createCollection, deleteCollection } from '../../api/collections'
import { ApiError } from '../../api/client'

/**
 * Loads all collections and exposes create/delete actions.
 */
function useCollections() {
  const [collections, setCollections] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await listCollections()
      setCollections(result.collections)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load collections.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional fetch-on-mount; no caching library per spec's state-management decision
    load()
  }, [load])

  async function create(data) {
    const created = await createCollection(data)
    setCollections((current) => [created, ...current])
    return created
  }

  async function remove(id) {
    await deleteCollection(id)
    setCollections((current) => current.filter((collection) => collection.id !== id))
  }

  return { collections, isLoading, error, reload: load, create, remove }
}

export default useCollections
