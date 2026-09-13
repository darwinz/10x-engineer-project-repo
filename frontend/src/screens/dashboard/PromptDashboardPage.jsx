import { useEffect, useMemo, useState } from 'react'
import AppShell from '../../components/AppShell'
import LoadingSpinner from '../../components/LoadingSpinner'
import ErrorBanner from '../../components/ErrorBanner'
import PromptFilterBar from './PromptFilterBar'
import PromptList from './PromptList'
import CreatePromptModal from './CreatePromptModal'
import useDashboardPrompts from './useDashboardPrompts'
import { ApiError } from '../../api/client'

const SEARCH_DEBOUNCE_MS = 300

/**
 * Dashboard screen (`/`): browse, search, filter, and create prompts.
 */
function PromptDashboardPage() {
  const [collectionId, setCollectionId] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')

  useEffect(() => {
    const timeout = setTimeout(() => setSearch(searchInput), SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(timeout)
  }, [searchInput])

  const { prompts, collections, isLoading, error, reload, create } = useDashboardPrompts({
    collectionId,
    search,
  })

  const [isModalOpen, setIsModalOpen] = useState(false)
  const [createError, setCreateError] = useState(null)
  const [isCreating, setIsCreating] = useState(false)

  const collectionsById = useMemo(
    () => Object.fromEntries(collections.map((collection) => [collection.id, collection])),
    [collections],
  )

  const hasActiveFilters = Boolean(collectionId || search)

  async function handleCreate(values) {
    setIsCreating(true)
    setCreateError(null)
    try {
      await create({
        title: values.title,
        content: values.content,
        description: values.description || null,
        collection_id: values.collection_id || null,
      })
      setIsModalOpen(false)
    } catch (err) {
      setCreateError(err instanceof ApiError ? err.body ?? err.message : 'Failed to create prompt.')
    } finally {
      setIsCreating(false)
    }
  }

  function openModal() {
    setCreateError(null)
    setIsModalOpen(true)
  }

  return (
    <AppShell>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-gray-900">Prompts</h1>
        <button
          type="button"
          onClick={openModal}
          className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700"
        >
          New prompt
        </button>
      </div>

      <div className="mt-4">
        <PromptFilterBar
          collections={collections}
          collectionId={collectionId}
          search={searchInput}
          onCollectionChange={setCollectionId}
          onSearchChange={setSearchInput}
        />
      </div>

      <div className="mt-6">
        {isLoading && <LoadingSpinner label="Loading prompts…" />}
        {!isLoading && error && <ErrorBanner error={error} onRetry={reload} />}
        {!isLoading && !error && (
          <PromptList
            prompts={prompts}
            collectionsById={collectionsById}
            onCreate={openModal}
            hasActiveFilters={hasActiveFilters}
          />
        )}
      </div>

      <CreatePromptModal
        open={isModalOpen}
        collections={collections}
        isLoadingCollections={isLoading}
        submitError={createError}
        isSubmitting={isCreating}
        onSubmit={handleCreate}
        onCancel={() => setIsModalOpen(false)}
      />
    </AppShell>
  )
}

export default PromptDashboardPage
