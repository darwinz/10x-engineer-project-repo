import { Link } from 'react-router-dom'

/**
 * Read-only view of a prompt's title, content, description, and collection,
 * plus actions to edit, delete, or browse its version history.
 *
 * @param {{
 *   prompt: import('../../types').Prompt,
 *   collectionName?: string,
 *   onEdit: () => void,
 *   onDelete: () => void,
 * }} props
 */
function PromptViewPanel({ prompt, collectionName, onEdit, onDelete }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">{prompt.title}</h1>
          {collectionName && (
            <span className="mt-1 inline-block rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
              {collectionName}
            </span>
          )}
        </div>
        <div className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={onEdit}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100"
          >
            Edit
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="rounded-md border border-red-300 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50"
          >
            Delete
          </button>
        </div>
      </div>

      {prompt.description && <p className="mt-3 text-sm text-gray-600">{prompt.description}</p>}

      <pre className="mt-4 whitespace-pre-wrap rounded-md bg-gray-50 p-4 font-mono text-sm text-gray-800">
        {prompt.content}
      </pre>

      <Link
        to={`/prompts/${prompt.id}/versions`}
        className="mt-4 inline-block text-sm font-medium text-gray-700 underline hover:text-gray-900"
      >
        View version history
      </Link>
    </div>
  )
}

export default PromptViewPanel
