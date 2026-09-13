import PromptCard from './PromptCard'
import EmptyState from '../../components/EmptyState'

/**
 * Render the dashboard's grid of prompt cards, or a routine empty state
 * when there are none (a fresh in-memory backend has no prompts yet).
 *
 * @param {{
 *   prompts: import('../../types').Prompt[],
 *   collectionsById: Record<string, import('../../types').Collection>,
 *   onCreate: () => void,
 * }} props
 */
function PromptList({ prompts, collectionsById, onCreate }) {
  if (prompts.length === 0) {
    return (
      <EmptyState
        message="No prompts yet. Create your first prompt to get started."
        actionLabel="New prompt"
        onAction={onCreate}
      />
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {prompts.map((prompt) => (
        <PromptCard
          key={prompt.id}
          prompt={prompt}
          collectionName={prompt.collection_id ? collectionsById[prompt.collection_id]?.name : undefined}
        />
      ))}
    </div>
  )
}

export default PromptList
