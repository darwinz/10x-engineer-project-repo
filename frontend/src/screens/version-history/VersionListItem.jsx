/**
 * One row in the version timeline: version number, timestamp, and a
 * selected/active affordance.
 *
 * @param {{
 *   version: import('../../types').PromptVersion,
 *   isSelected: boolean,
 *   onSelect: () => void,
 * }} props
 */
function VersionListItem({ version, isSelected, onSelect }) {
  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        className={`w-full rounded-md border px-3 py-2 text-left text-sm ${
          isSelected ? 'border-gray-900 bg-gray-900 text-white' : 'border-gray-200 bg-white hover:bg-gray-50'
        }`}
      >
        <span className="font-medium">Version {version.version_number}</span>
        <span className={`ml-2 text-xs ${isSelected ? 'text-gray-300' : 'text-gray-500'}`}>
          {new Date(version.created_at).toLocaleString()}
        </span>
      </button>
    </li>
  )
}

export default VersionListItem
