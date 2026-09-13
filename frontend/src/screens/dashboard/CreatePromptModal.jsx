import PromptForm from '../../components/PromptForm'

/**
 * Modal wrapping PromptForm for creating a new prompt from the dashboard.
 *
 * @param {{
 *   open: boolean,
 *   collections: import('../../types').Collection[],
 *   submitError?: string|{detail: Array<{loc: Array<string|number>, msg: string}>}|null,
 *   isSubmitting?: boolean,
 *   onSubmit: (values: { title: string, content: string, description: string, collection_id: string }) => void,
 *   onCancel: () => void,
 * }} props
 */
function CreatePromptModal({ open, collections, submitError, isSubmitting, onSubmit, onCancel }) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-gray-900">New prompt</h2>
        <div className="mt-4">
          <PromptForm
            collections={collections}
            submitError={submitError}
            isSubmitting={isSubmitting}
            submitLabel="Create"
            onSubmit={onSubmit}
            onCancel={onCancel}
          />
        </div>
      </div>
    </div>
  )
}

export default CreatePromptModal
