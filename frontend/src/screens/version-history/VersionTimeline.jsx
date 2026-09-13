import VersionListItem from './VersionListItem'
import EmptyState from '../../components/EmptyState'

/**
 * List of a prompt's versions, newest first, with one selectable.
 *
 * @param {{
 *   versions: import('../../types').PromptVersion[],
 *   selectedVersionNumber?: number,
 *   onSelect: (versionNumber: number) => void,
 * }} props
 */
function VersionTimeline({ versions, selectedVersionNumber, onSelect }) {
  if (versions.length === 0) {
    return <EmptyState message="No versions yet. Edit this prompt to create one." />
  }

  return (
    <ul className="flex flex-col gap-2">
      {versions.map((version) => (
        <VersionListItem
          key={version.version_number}
          version={version}
          isSelected={version.version_number === selectedVersionNumber}
          onSelect={() => onSelect(version.version_number)}
        />
      ))}
    </ul>
  )
}

export default VersionTimeline
