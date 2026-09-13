/**
 * Render a routine "nothing here yet" message with an optional action
 * (e.g. "Create your first prompt"). Empty is expected, not exceptional —
 * storage is in-memory and resets on every backend restart.
 *
 * @param {{ message: string, actionLabel?: string, onAction?: () => void }} props
 */
function EmptyState({ message, actionLabel, onAction }) {
  return (
    <div role="status" className="flex flex-col items-center gap-3 rounded-md border border-dashed border-gray-300 py-12 text-center text-gray-500">
      <span>{message}</span>
      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700"
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}

export default EmptyState
