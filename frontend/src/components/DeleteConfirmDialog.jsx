import { useId } from 'react'
import useModalA11y from '../hooks/useModalA11y'

/**
 * Confirm-before-delete dialog. On a failed delete (network-level failure),
 * the dialog stays open and shows an inline error rather than closing.
 *
 * @param {{
 *   open: boolean,
 *   title: string,
 *   message: string,
 *   error?: string|null,
 *   isDeleting?: boolean,
 *   onConfirm: () => void,
 *   onCancel: () => void,
 * }} props
 */
function DeleteConfirmDialog({ open, title, message, error, isDeleting, onConfirm, onCancel }) {
  const titleId = useId()
  const messageId = useId()
  const containerRef = useModalA11y(open, () => {
    if (!isDeleting) onCancel()
  })

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={messageId}
        className="w-full max-w-sm rounded-lg bg-white p-6 shadow-xl"
      >
        <h2 id={titleId} className="text-lg font-semibold text-gray-900">
          {title}
        </h2>
        <p id={messageId} className="mt-2 text-sm text-gray-600">
          {message}
        </p>
        {error && (
          <p role="alert" className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">
            {error}
          </p>
        )}
        <div className="mt-6 flex flex-wrap justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={isDeleting}
            className="rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isDeleting}
            aria-busy={isDeleting}
            className="rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
          >
            {isDeleting ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default DeleteConfirmDialog
