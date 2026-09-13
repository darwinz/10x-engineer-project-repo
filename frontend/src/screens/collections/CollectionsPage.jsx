import { useState } from 'react'
import AppShell from '../../components/AppShell'
import LoadingSpinner from '../../components/LoadingSpinner'
import ErrorBanner from '../../components/ErrorBanner'
import DeleteConfirmDialog from '../../components/DeleteConfirmDialog'
import CollectionList from './CollectionList'
import CreateCollectionModal from './CreateCollectionModal'
import useCollections from './useCollections'
import { ApiError } from '../../api/client'

/**
 * Collections screen (`/collections`): browse, create, and delete
 * collections.
 */
function CollectionsPage() {
  const { collections, isLoading, error, reload, create, remove } = useCollections()

  const [isModalOpen, setIsModalOpen] = useState(false)
  const [createError, setCreateError] = useState(null)
  const [isCreating, setIsCreating] = useState(false)

  const [pendingDeleteId, setPendingDeleteId] = useState(null)
  const [deleteError, setDeleteError] = useState(null)
  const [isDeleting, setIsDeleting] = useState(false)

  async function handleCreate(values) {
    setIsCreating(true)
    setCreateError(null)
    try {
      await create({ name: values.name, description: values.description || null })
      setIsModalOpen(false)
    } catch (err) {
      setCreateError(err instanceof ApiError ? err.message : 'Failed to create collection.')
    } finally {
      setIsCreating(false)
    }
  }

  async function handleDelete() {
    setIsDeleting(true)
    setDeleteError(null)
    try {
      await remove(pendingDeleteId)
      setPendingDeleteId(null)
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : 'Failed to delete collection.')
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <AppShell>
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-xl font-semibold text-gray-900">Collections</h1>
        <button
          type="button"
          onClick={() => {
            setCreateError(null)
            setIsModalOpen(true)
          }}
          className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700"
        >
          New collection
        </button>
      </div>

      <div className="mt-6">
        {isLoading && <LoadingSpinner label="Loading collections…" />}
        {!isLoading && error && <ErrorBanner error={error} onRetry={reload} />}
        {!isLoading && !error && (
          <CollectionList
            collections={collections}
            onDelete={(id) => {
              setDeleteError(null)
              setPendingDeleteId(id)
            }}
            onCreate={() => setIsModalOpen(true)}
          />
        )}
      </div>

      <CreateCollectionModal
        open={isModalOpen}
        submitError={createError}
        isSubmitting={isCreating}
        onSubmit={handleCreate}
        onCancel={() => setIsModalOpen(false)}
      />

      <DeleteConfirmDialog
        open={pendingDeleteId !== null}
        title="Delete collection"
        message="Prompts in this collection will also be deleted. This cannot be undone."
        error={deleteError}
        isDeleting={isDeleting}
        onConfirm={handleDelete}
        onCancel={() => setPendingDeleteId(null)}
      />
    </AppShell>
  )
}

export default CollectionsPage
