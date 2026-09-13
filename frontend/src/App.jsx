import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import PromptDashboardPage from './screens/dashboard/PromptDashboardPage'
import PromptDetailPage from './screens/prompt-detail/PromptDetailPage'
import VersionHistoryPage from './screens/version-history/VersionHistoryPage'
import CollectionsPage from './screens/collections/CollectionsPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<PromptDashboardPage />} />
        <Route path="/prompts/:id" element={<PromptDetailPage />} />
        <Route path="/prompts/:id/versions" element={<VersionHistoryPage />} />
        <Route path="/collections" element={<CollectionsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
