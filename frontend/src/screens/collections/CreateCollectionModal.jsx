import CollectionForm from './CollectionForm'

/**
 * Modal wrapping CollectionForm for creating a new collection.
 *
 * @param {{
 *   open: boolean,
 *   submitError?: string|null,
 *   isSubmitting?: boolean,
 *   onSubmit: (values: { name: string, description: string }) => void,
 *   onCancel: () => void,
 * }} props
 */
function CreateCollectionModal({ open, submitError, isSubmitting, onSubmit, onCancel }) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-gray-900">New collection</h2>
        <div className="mt-4">
          <CollectionForm
            submitError={submitError}
            isSubmitting={isSubmitting}
            onSubmit={onSubmit}
            onCancel={onCancel}
          />
        </div>
      </div>
    </div>
  )
}

export default CreateCollectionModal
