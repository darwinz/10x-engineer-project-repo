import { NavLink } from 'react-router-dom'

/**
 * Top nav (links to / and /collections) plus a content slot.
 *
 * @param {{ children: import('react').ReactNode }} props
 */
function AppShell({ children }) {
  const linkClass = ({ isActive }) =>
    `rounded-md px-3 py-2 text-sm font-medium ${
      isActive ? 'bg-gray-900 text-white' : 'text-gray-700 hover:bg-gray-100'
    }`

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <nav className="mx-auto flex max-w-5xl items-center gap-4 px-4 py-3">
          <span className="text-lg font-semibold text-gray-900">PromptLab</span>
          <NavLink to="/" end className={linkClass}>
            Prompts
          </NavLink>
          <NavLink to="/collections" className={linkClass}>
            Collections
          </NavLink>
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
    </div>
  )
}

export default AppShell
