import { useCallback, useEffect, useState } from 'react'
import { listPromptVersions, getPromptVersion, restorePromptVersion } from '../../api/promptVersions'
import { getPrompt } from '../../api/prompts'
import { ApiError } from '../../api/client'

/**
 * Loads a prompt's version list plus the parent prompt (for its title), and
 * exposes actions to fetch one version's full content and restore it.
 *
 * @param {string} promptId
 */
function usePromptVersions(promptId) {
  const [prompt, setPrompt] = useState(null)
  const [versions, setVersions] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [promptResult, versionList] = await Promise.all([
        getPrompt(promptId),
        listPromptVersions(promptId),
      ])
      setPrompt(promptResult)
      setVersions(versionList.versions)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load version history.')
    } finally {
      setIsLoading(false)
    }
  }, [promptId])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional fetch-on-mount; no caching library per spec's state-management decision
    load()
  }, [load])

  function fetchVersion(versionNumber) {
    return getPromptVersion(promptId, versionNumber)
  }

  async function restore(versionNumber) {
    const restored = await restorePromptVersion(promptId, versionNumber)
    setPrompt(restored)
    await load()
    return restored
  }

  return { prompt, versions, isLoading, error, reload: load, fetchVersion, restore }
}

export default usePromptVersions
