/**
 * Summary card for one collection, with a delete action.
 *
 * @param {{ collection: import('../../types').Collection, onDelete: () => void }} props
 */
function CollectionCard({ collection, onDelete }) {
  return (
    <div className="flex items-start justify-between gap-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div>
        <h3 className="font-semibold text-gray-900">{collection.name}</h3>
        {collection.description && <p className="mt-1 text-sm text-gray-600">{collection.description}</p>}
      </div>
      <button
        type="button"
        onClick={onDelete}
        className="shrink-0 rounded-md border border-red-300 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50"
      >
        Delete
      </button>
    </div>
  )
}

export default CollectionCard
