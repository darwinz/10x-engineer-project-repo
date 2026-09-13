import { useId, useState } from 'react'

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
 * Client-side required-field checks, so a blank title/content is caught
 * before a round trip to the server.
 */
function validate(values) {
  const errors = {}
  if (!values.title.trim()) errors.title = 'Title is required.'
  if (!values.content.trim()) errors.content = 'Content is required.'
  return errors
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
 *   isLoadingCollections?: boolean,
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
  isLoadingCollections,
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
  const [clientErrors, setClientErrors] = useState({})

  const titleErrorId = useId()
  const contentErrorId = useId()
  const descriptionErrorId = useId()
  const collectionErrorId = useId()

  const formLevelError = typeof submitError === 'string' ? submitError : undefined
  const titleError = clientErrors.title ?? fieldError(submitError, 'title')
  const contentError = clientErrors.content ?? fieldError(submitError, 'content')
  const descriptionError = fieldError(submitError, 'description')
  const collectionError = fieldError(submitError, 'collection_id')

  function handleSubmit(event) {
    event.preventDefault()
    const values = { title, content, description, collection_id: collectionId }
    const errors = validate(values)
    if (Object.keys(errors).length > 0) {
      setClientErrors(errors)
      return
    }
    setClientErrors({})
    onSubmit(values)
  }

  function handleTitleChange(value) {
    setTitle(value)
    if (clientErrors.title && value.trim()) {
      setClientErrors((current) => ({ ...current, title: undefined }))
    }
  }

  function handleContentChange(value) {
    setContent(value)
    if (clientErrors.content && value.trim()) {
      setClientErrors((current) => ({ ...current, content: undefined }))
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
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
          onChange={(event) => handleTitleChange(event.target.value)}
          placeholder="e.g. Summarize Article"
          aria-invalid={Boolean(titleError)}
          aria-describedby={titleError ? titleErrorId : undefined}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        {titleError && (
          <p id={titleErrorId} role="alert" className="mt-1 text-sm text-red-700">
            {titleError}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="prompt-content" className="block text-sm font-medium text-gray-700">
          Content
        </label>
        <textarea
          id="prompt-content"
          value={content}
          onChange={(event) => handleContentChange(event.target.value)}
          rows={6}
          placeholder="Use {{variable}} for templated values"
          aria-invalid={Boolean(contentError)}
          aria-describedby={contentError ? contentErrorId : undefined}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono"
        />
        {contentError && (
          <p id={contentErrorId} role="alert" className="mt-1 text-sm text-red-700">
            {contentError}
          </p>
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
          placeholder="What is this prompt for?"
          aria-invalid={Boolean(descriptionError)}
          aria-describedby={descriptionError ? descriptionErrorId : undefined}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        {descriptionError && (
          <p id={descriptionErrorId} role="alert" className="mt-1 text-sm text-red-700">
            {descriptionError}
          </p>
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
          disabled={isLoadingCollections}
          aria-invalid={Boolean(collectionError)}
          aria-describedby={collectionError ? collectionErrorId : undefined}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm disabled:opacity-50"
        >
          <option value="">{isLoadingCollections ? 'Loading collections…' : 'No collection'}</option>
          {collections.map((collection) => (
            <option key={collection.id} value={collection.id}>
              {collection.name}
            </option>
          ))}
        </select>
        {collectionError && (
          <p id={collectionErrorId} role="alert" className="mt-1 text-sm text-red-700">
            {collectionError}
          </p>
        )}
      </div>

      <div className="flex flex-wrap justify-end gap-3">
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
          aria-busy={isSubmitting}
          className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50"
        >
          {isSubmitting ? 'Saving…' : submitLabel}
        </button>
      </div>
    </form>
  )
}

export default PromptForm
