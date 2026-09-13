import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import AppShell from '../../components/AppShell'
import LoadingSpinner from '../../components/LoadingSpinner'
import ErrorBanner from '../../components/ErrorBanner'
import VersionTimeline from './VersionTimeline'
import VersionDetailPanel from './VersionDetailPanel'
import usePromptVersions from './usePromptVersions'
import { ApiError } from '../../api/client'

/**
 * Version history screen (`/prompts/:id/versions`): browse and restore a
 * prompt's past versions.
 */
function VersionHistoryPage() {
  const { id } = useParams()
  const { prompt, versions, isLoading, error, reload, restore } = usePromptVersions(id)

  const [selectedVersionNumber, setSelectedVersionNumber] = useState(null)
  const [isRestoring, setIsRestoring] = useState(false)
  const [restoreError, setRestoreError] = useState(null)

  const selected = selectedVersionNumber
    ? versions.find((version) => version.version_number === selectedVersionNumber)
    : null
  const currentVersion = versions[0]

  async function handleRestore() {
    if (!selectedVersionNumber) return
    setIsRestoring(true)
    setRestoreError(null)
    try {
      await restore(selectedVersionNumber)
    } catch (err) {
      setRestoreError(err instanceof ApiError ? err.message : 'Failed to restore version.')
    } finally {
      setIsRestoring(false)
    }
  }

  return (
    <AppShell>
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-xl font-semibold text-gray-900">
          Version history{prompt ? `: ${prompt.title}` : ''}
        </h1>
        {prompt && (
          <Link
            to={`/prompts/${prompt.id}`}
            className="text-sm font-medium text-gray-700 underline hover:text-gray-900"
          >
            Back to prompt
          </Link>
        )}
      </div>

      <div className="mt-6">
        {isLoading && <LoadingSpinner label="Loading versions…" />}
        {!isLoading && error && <ErrorBanner error={error} onRetry={reload} />}
        {!isLoading && !error && (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-[16rem_1fr]">
            <VersionTimeline
              versions={versions}
              selectedVersionNumber={selectedVersionNumber ?? undefined}
              onSelect={setSelectedVersionNumber}
            />
            <div>
              {restoreError && <ErrorBanner error={restoreError} />}
              <div className="mt-3">
                <VersionDetailPanel
                  version={selected}
                  isCurrent={Boolean(selected && currentVersion && selected.version_number === currentVersion.version_number)}
                  isRestoring={isRestoring}
                  onRestore={handleRestore}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  )
}

export default VersionHistoryPage
