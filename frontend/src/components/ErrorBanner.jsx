/**
 * Render one error (network failure or an ApiErrorDetail message) with an
 * optional retry action.
 *
 * @param {{ error: string, onRetry?: () => void }} props
 */
function ErrorBanner({ error, onRetry }) {
  return (
    <div
      role="alert"
      className="flex items-center justify-between gap-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
    >
      <span>{error}</span>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="shrink-0 rounded-md border border-red-300 px-3 py-1 font-medium hover:bg-red-100"
        >
          Retry
        </button>
      )}
    </div>
  )
}

export default ErrorBanner
