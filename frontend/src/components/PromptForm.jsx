import { useState } from 'react'

/**
 * Find the field-level validation message for a given field name, if the
 * error is a 422 ValidationErrorDetail (`{ detail: [{ loc, msg }] }`).
 *
 * @param {string|{detail: Array<{loc: Array<string|number>, msg: string}>}|null|undefined} submitError
 * @param {string} field
 * @returns {string|undefined}
 */
function fieldError(submitError, field) {
  if (!submitError || typeof submitError === 'string' || !Array.isArray(submitError.detail)) {
    return undefined
  }
  const match = submitError.detail.find((item) => item.loc?.includes(field))
  return match?.msg
}

/**
 * Create/edit form for a prompt: title, {{variable}}-templated content, an
 * optional description, and an optional single collection.
 *
 * submitError may be a plain string (a 400/409 ApiErrorDetail message) or a
 * ValidationErrorDetail object (`{ detail: [...] }` from a 422 response) —
 * the latter is used to render field-level messages.
 *
 * @param {{
 *   initialValues?: { title?: string, content?: string, description?: string, collection_id?: string|null },
 *   collections: import('../types').Collection[],
 *   submitError?: string|{detail: Array<{loc: Array<string|number>, msg: string}>}|null,
 *   isSubmitting?: boolean,
 *   submitLabel?: string,
 *   onSubmit: (values: { title: string, content: string, description: string, collection_id: string }) => void,
 *   onCancel: () => void,
 * }} props
 */
function PromptForm({
  initialValues = {},
  collections,
  submitError,
  isSubmitting,
  submitLabel = 'Save',
  onSubmit,
  onCancel,
}) {
  const [title, setTitle] = useState(initialValues.title ?? '')
  const [content, setContent] = useState(initialValues.content ?? '')
  const [description, setDescription] = useState(initialValues.description ?? '')
  const [collectionId, setCollectionId] = useState(initialValues.collection_id ?? '')

  const formLevelError = typeof submitError === 'string' ? submitError : undefined

  function handleSubmit(event) {
    event.preventDefault()
    onSubmit({ title, content, description, collection_id: collectionId })
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {formLevelError && (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">
          {formLevelError}
        </p>
      )}

      <div>
        <label htmlFor="prompt-title" className="block text-sm font-medium text-gray-700">
          Title
        </label>
        <input
          id="prompt-title"
          type="text"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        {fieldError(submitError, 'title') && (
          <p className="mt-1 text-sm text-red-700">{fieldError(submitError, 'title')}</p>
        )}
      </div>

      <div>
        <label htmlFor="prompt-content" className="block text-sm font-medium text-gray-700">
          Content
        </label>
        <textarea
          id="prompt-content"
          value={content}
          onChange={(event) => setContent(event.target.value)}
          rows={6}
          placeholder="Use {{variable}} for templated values"
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono"
        />
        {fieldError(submitError, 'content') && (
          <p className="mt-1 text-sm text-red-700">{fieldError(submitError, 'content')}</p>
        )}
      </div>

      <div>
        <label htmlFor="prompt-description" className="block text-sm font-medium text-gray-700">
          Description <span className="text-gray-400">(optional)</span>
        </label>
        <input
          id="prompt-description"
          type="text"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        {fieldError(submitError, 'description') && (
          <p className="mt-1 text-sm text-red-700">{fieldError(submitError, 'description')}</p>
        )}
      </div>

      <div>
        <label htmlFor="prompt-collection" className="block text-sm font-medium text-gray-700">
          Collection <span className="text-gray-400">(optional)</span>
        </label>
        <select
          id="prompt-collection"
          value={collectionId}
          onChange={(event) => setCollectionId(event.target.value)}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="">No collection</option>
          {collections.map((collection) => (
            <option key={collection.id} value={collection.id}>
              {collection.name}
            </option>
          ))}
        </select>
        {fieldError(submitError, 'collection_id') && (
          <p className="mt-1 text-sm text-red-700">{fieldError(submitError, 'collection_id')}</p>
        )}
      </div>

      <div className="flex justify-end gap-3">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50"
        >
          {isSubmitting ? 'Saving…' : submitLabel}
        </button>
      </div>
    </form>
  )
}

export default PromptForm
