import { useId, useState } from 'react'

function validate(values) {
  const errors = {}
  if (!values.name.trim()) errors.name = 'Name is required.'
  return errors
}

/**
 * Create form for a collection: name and an optional description.
 * Used only by CollectionsPage, so it lives alongside it rather than in the
 * shared components/ folder.
 *
 * @param {{
 *   submitError?: string|null,
 *   isSubmitting?: boolean,
 *   onSubmit: (values: { name: string, description: string }) => void,
 *   onCancel: () => void,
 * }} props
 */
function CollectionForm({ submitError, isSubmitting, onSubmit, onCancel }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [clientErrors, setClientErrors] = useState({})
  const nameErrorId = useId()

  function handleSubmit(event) {
    event.preventDefault()
    const values = { name, description }
    const errors = validate(values)
    if (Object.keys(errors).length > 0) {
      setClientErrors(errors)
      return
    }
    setClientErrors({})
    onSubmit(values)
  }

  function handleNameChange(value) {
    setName(value)
    if (clientErrors.name && value.trim()) {
      setClientErrors((current) => ({ ...current, name: undefined }))
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      {submitError && (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">
          {submitError}
        </p>
      )}

      <div>
        <label htmlFor="collection-name" className="block text-sm font-medium text-gray-700">
          Name
        </label>
        <input
          id="collection-name"
          type="text"
          value={name}
          onChange={(event) => handleNameChange(event.target.value)}
          placeholder="e.g. Marketing"
          aria-invalid={Boolean(clientErrors.name)}
          aria-describedby={clientErrors.name ? nameErrorId : undefined}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        {clientErrors.name && (
          <p id={nameErrorId} role="alert" className="mt-1 text-sm text-red-700">
            {clientErrors.name}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="collection-description" className="block text-sm font-medium text-gray-700">
          Description <span className="text-gray-400">(optional)</span>
        </label>
        <input
          id="collection-description"
          type="text"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="What's this collection for?"
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
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
          {isSubmitting ? 'Creating…' : 'Create'}
        </button>
      </div>
    </form>
  )
}

export default CollectionForm
