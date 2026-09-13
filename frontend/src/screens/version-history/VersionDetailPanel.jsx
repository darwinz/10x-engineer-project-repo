/**
 * Full content of the selected version, with a restore action.
 *
 * @param {{
 *   version: import('../../types').PromptVersion|null,
 *   isCurrent: boolean,
 *   isRestoring?: boolean,
 *   onRestore: () => void,
 * }} props
 */
function VersionDetailPanel({ version, isCurrent, isRestoring, onRestore }) {
  if (!version) {
    return <p className="text-sm text-gray-500">Select a version to view its content.</p>
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-lg font-semibold text-gray-900">Version {version.version_number}</h2>
        {!isCurrent && (
          <button
            type="button"
            onClick={onRestore}
            disabled={isRestoring}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50"
          >
            {isRestoring ? 'Restoring…' : 'Restore this version'}
          </button>
        )}
        {isCurrent && <span className="text-xs font-medium text-gray-500">Current version</span>}
      </div>

      <dl className="mt-4 space-y-3 text-sm">
        <div>
          <dt className="font-medium text-gray-700">Title</dt>
          <dd className="text-gray-600">{version.title}</dd>
        </div>
        {version.description && (
          <div>
            <dt className="font-medium text-gray-700">Description</dt>
            <dd className="text-gray-600">{version.description}</dd>
          </div>
        )}
        <div>
          <dt className="font-medium text-gray-700">Content</dt>
          <dd>
            <pre className="mt-1 whitespace-pre-wrap rounded-md bg-gray-50 p-4 font-mono text-sm text-gray-800">
              {version.content}
            </pre>
          </dd>
        </div>
      </dl>
    </div>
  )
}

export default VersionDetailPanel
