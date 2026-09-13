import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import AppShell from '../../components/AppShell'
import LoadingSpinner from '../../components/LoadingSpinner'
import ErrorBanner from '../../components/ErrorBanner'
import PromptForm from '../../components/PromptForm'
import DeleteConfirmDialog from '../../components/DeleteConfirmDialog'
import PromptViewPanel from './PromptViewPanel'
import usePrompt from './usePrompt'
import { listCollections } from '../../api/collections'
import { ApiError } from '../../api/client'

/**
 * Prompt detail screen (`/prompts/:id`): view, edit (PATCH-only), and
 * delete a single prompt.
 */
function PromptDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { prompt, isLoading, error, reload, save, remove } = usePrompt(id)

  const [collections, setCollections] = useState([])
  const [isLoadingCollections, setIsLoadingCollections] = useState(true)
  const [collectionsError, setCollectionsError] = useState(null)
  const [isEditing, setIsEditing] = useState(false)
  const [saveError, setSaveError] = useState(null)
  const [isSaving, setIsSaving] = useState(false)

  const [isDeleteOpen, setIsDeleteOpen] = useState(false)
  const [deleteError, setDeleteError] = useState(null)
  const [isDeleting, setIsDeleting] = useState(false)

  const loadCollections = useCallback(() => {
    setIsLoadingCollections(true)
    setCollectionsError(null)
    return listCollections()
      .then((result) => setCollections(result.collections))
      .catch(() => setCollectionsError('Could not load your collections.'))
      .finally(() => setIsLoadingCollections(false))
  }, [])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional fetch-on-mount; no caching library per spec's state-management decision
    loadCollections()
  }, [loadCollections])

  const collectionName = prompt?.collection_id
    ? collections.find((collection) => collection.id === prompt.collection_id)?.name
    : undefined

  async function handleSave(values) {
    setIsSaving(true)
    setSaveError(null)
    try {
      await save(values)
      setIsEditing(false)
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.body ?? err.message : 'Failed to save prompt.')
    } finally {
      setIsSaving(false)
    }
  }

  async function handleDelete() {
    setIsDeleting(true)
    setDeleteError(null)
    try {
      await remove()
      navigate('/')
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : 'Failed to delete prompt.')
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <AppShell>
      {isLoading && <LoadingSpinner label="Loading prompt…" />}
      {!isLoading && error && <ErrorBanner error={error} onRetry={reload} />}
      {!isLoading && !error && prompt && !isEditing && (
        <PromptViewPanel
          prompt={prompt}
          collectionName={collectionName}
          onEdit={() => {
            setSaveError(null)
            setIsEditing(true)
          }}
          onDelete={() => {
            setDeleteError(null)
            setIsDeleteOpen(true)
          }}
        />
      )}
      {!isLoading && !error && prompt && isEditing && (
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h1 className="mb-4 text-lg font-semibold text-gray-900">Edit prompt</h1>
          {collectionsError && (
            <div className="mb-4">
              <ErrorBanner error={collectionsError} onRetry={loadCollections} />
            </div>
          )}
          <PromptForm
            initialValues={prompt}
            collections={collections}
            isLoadingCollections={isLoadingCollections}
            submitError={saveError}
            isSubmitting={isSaving}
            submitLabel="Save changes"
            onSubmit={handleSave}
            onCancel={() => setIsEditing(false)}
          />
        </div>
      )}

      <DeleteConfirmDialog
        open={isDeleteOpen}
        title="Delete prompt"
        message="This prompt and its version history will be removed from view. This cannot be undone."
        error={deleteError}
        isDeleting={isDeleting}
        onConfirm={handleDelete}
        onCancel={() => setIsDeleteOpen(false)}
      />
    </AppShell>
  )
}

export default PromptDetailPage
