import { Link } from 'react-router-dom'

/**
 * Summary card for one prompt in the dashboard list, linking to its detail
 * screen.
 *
 * @param {{ prompt: import('../../types').Prompt, collectionName?: string }} props
 */
function PromptCard({ prompt, collectionName }) {
  return (
    <Link
      to={`/prompts/${prompt.id}`}
      className="block rounded-lg border border-gray-200 bg-white p-4 shadow-sm transition hover:border-gray-400 hover:shadow"
    >
      <h3 className="font-semibold text-gray-900">{prompt.title}</h3>
      {prompt.description && <p className="mt-1 text-sm text-gray-600">{prompt.description}</p>}
      <p className="mt-2 line-clamp-2 font-mono text-xs text-gray-500">{prompt.content}</p>
      {collectionName && (
        <span className="mt-3 inline-block rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
          {collectionName}
        </span>
      )}
    </Link>
  )
}

export default PromptCard
