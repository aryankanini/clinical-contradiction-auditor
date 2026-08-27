import { NavLink, Outlet } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { endpoints } from '../api/endpoints'
import { useRole } from '../hooks/useRole'
import type { Role } from '../api/types'

const NAV = [
  { to: '/', label: 'Dashboard', end: true, icon: '◈' },
  { to: '/batches', label: 'Patient Records', end: false, icon: '⊞' },
  { to: '/findings', label: 'Issues Found', end: false, icon: '⚑' },
  { to: '/queues', label: 'Work Queues', end: false, icon: '☰' },
  { to: '/rule-packs', label: 'Audit Rules', end: false, icon: '⊙' },
  { to: '/compliance', label: 'Compliance', end: false, icon: '✓' },
]

const ROLES: Role[] = ['steward', 'analyst', 'compliance']

function RoleSwitcher() {
  const { role, userId, setRole, setUserId } = useRole()
  return (
    <div className="flex items-center gap-2">
      <input
        aria-label="User ID"
        value={userId}
        onChange={(e) => setUserId(e.target.value)}
        className="w-32 rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-sm font-medium text-black focus:outline-none focus:ring-2 focus:ring-black"
      />
      <select
        aria-label="Role"
        value={role}
        onChange={(e) => setRole(e.target.value as Role)}
        className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-sm font-bold text-black capitalize focus:outline-none focus:ring-2 focus:ring-black"
      >
        {ROLES.map((r) => (
          <option key={r} value={r}>{r}</option>
        ))}
      </select>
    </div>
  )
}

function SystemBanner() {
  const { data } = useQuery({ queryKey: ['health'], queryFn: endpoints.health, staleTime: 30_000 })
  const warnings: string[] = []
  if (data?.audit_engine_is_placeholder) warnings.push('Using placeholder audit engine')
  if (data && !data.ai_enabled) warnings.push('AI explanations disabled')
  if (data && !data.database_reachable) warnings.push('Database unreachable')

  return (
    <div className="border-b border-blue-100 bg-blue-50 px-6 py-2 text-xs font-semibold text-blue-700">
      <span className="font-bold text-blue-900">Read-only audit tool</span>
      {' '}— findings here do not change patient records or clinical decisions.
      {warnings.map((w) => (
        <span key={w} className="ml-3 inline-block rounded-md bg-blue-200 px-2 py-0.5 text-blue-900">
          {w}
        </span>
      ))}
    </div>
  )
}

export function AppShell() {
  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <SystemBanner />
      <header className="flex items-center justify-between gap-6 border-b border-gray-200 bg-white px-6 py-4 shadow-sm">
        <div>
          <h1 className="text-base font-black tracking-tight text-black">
            Clinical Data Integrity Auditor
          </h1>
          <p className="text-xs font-medium text-gray-400">
            Automated patient record consistency checker
          </p>
        </div>
        <RoleSwitcher />
      </header>

      <div className="flex flex-1">
        <nav className="w-56 shrink-0 border-r border-gray-200 bg-white px-3 py-6">
          <p className="mb-3 px-3 text-xs font-black uppercase tracking-widest text-gray-400">
            Navigation
          </p>
          <ul className="space-y-1">
            {NAV.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-colors ${
                      isActive
                        ? 'bg-black text-white'
                        : 'text-gray-500 hover:bg-gray-100 hover:text-black'
                    }`
                  }
                >
                  <span className="text-base leading-none">{item.icon}</span>
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <main className="flex-1 overflow-auto p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
