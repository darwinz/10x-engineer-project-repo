/**
 * Filter the dashboard's prompt list by collection and free-text search.
 *
 * @param {{
 *   collections: import('../../types').Collection[],
 *   collectionId: string,
 *   search: string,
 *   onCollectionChange: (collectionId: string) => void,
 *   onSearchChange: (search: string) => void,
 * }} props
 */
function PromptFilterBar({ collections, collectionId, search, onCollectionChange, onSearchChange }) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <input
        type="search"
        value={search}
        onChange={(event) => onSearchChange(event.target.value)}
        placeholder="Search prompts…"
        aria-label="Search prompts"
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm sm:w-64"
      />
      <select
        value={collectionId}
        onChange={(event) => onCollectionChange(event.target.value)}
        aria-label="Filter by collection"
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm sm:w-auto"
      >
        <option value="">All collections</option>
        {collections.map((collection) => (
          <option key={collection.id} value={collection.id}>
            {collection.name}
          </option>
        ))}
      </select>
    </div>
  )
}

export default PromptFilterBar
