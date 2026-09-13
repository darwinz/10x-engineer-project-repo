import CollectionCard from './CollectionCard'
import EmptyState from '../../components/EmptyState'

/**
 * Render the list of collections, or a routine empty state when there are
 * none.
 *
 * @param {{
 *   collections: import('../../types').Collection[],
 *   onDelete: (id: string) => void,
 *   onCreate: () => void,
 * }} props
 */
function CollectionList({ collections, onDelete, onCreate }) {
  if (collections.length === 0) {
    return (
      <EmptyState
        message="No collections yet. Create one to start grouping prompts."
        actionLabel="New collection"
        onAction={onCreate}
      />
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {collections.map((collection) => (
        <CollectionCard key={collection.id} collection={collection} onDelete={() => onDelete(collection.id)} />
      ))}
    </div>
  )
}

export default CollectionList
