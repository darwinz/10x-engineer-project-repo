/**
 * Render a loading indicator, nothing else.
 *
 * @param {{ label?: string }} props
 */
function LoadingSpinner({ label = 'Loading…' }) {
  return (
    <div role="status" className="flex flex-col items-center gap-3 py-12 text-gray-500">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-300 border-t-gray-900" />
      <span>{label}</span>
    </div>
  )
}

export default LoadingSpinner
