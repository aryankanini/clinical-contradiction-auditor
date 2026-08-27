import type { ReactNode } from 'react'

// ── Helpers ──────────────────────────────────────────────────────────────────

export function formatDate(iso: string | null | undefined) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export function humanise(s: string | null | undefined) {
  if (!s) return '—'
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

// ── Layout primitives ─────────────────────────────────────────────────────────

export function Card({
  title,
  action,
  children,
  className = '',
}: {
  title?: string
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <div className={`rounded-2xl border border-gray-200 bg-white p-6 shadow-sm ${className}`}>
      {(title || action) && (
        <div className="mb-4 flex items-center justify-between gap-4">
          {title && <h3 className="text-sm font-bold uppercase tracking-widest text-gray-500">{title}</h3>}
          {action}
        </div>
      )}
      {children}
    </div>
  )
}

export function Section({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`space-y-6 ${className}`}>{children}</div>
}

// ── Buttons ───────────────────────────────────────────────────────────────────

type BtnVariant = 'primary' | 'secondary' | 'danger' | 'ghost'

const BTN: Record<BtnVariant, string> = {
  primary: 'bg-black text-white hover:bg-gray-800 border-black',
  secondary: 'bg-white text-black border-gray-300 hover:bg-gray-50',
  danger: 'bg-red-600 text-white hover:bg-red-700 border-red-600',
  ghost: 'bg-transparent text-gray-600 border-transparent hover:bg-gray-100',
}

export function Button({
  variant = 'secondary',
  children,
  className = '',
  ...props
}: {
  variant?: BtnVariant
  children: ReactNode
  className?: string
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={`inline-flex items-center gap-2 rounded-xl border px-4 py-2 text-sm font-semibold transition disabled:opacity-40 ${BTN[variant]} ${className}`}
    >
      {children}
    </button>
  )
}

// ── Badges ────────────────────────────────────────────────────────────────────

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 border-red-200',
  high: 'bg-orange-100 text-orange-800 border-orange-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  low: 'bg-blue-100 text-blue-800 border-blue-200',
}

const STATUS_COLORS: Record<string, string> = {
  new: 'bg-gray-100 text-gray-700 border-gray-200',
  accepted: 'bg-green-100 text-green-800 border-green-200',
  escalated: 'bg-purple-100 text-purple-800 border-purple-200',
  deferred: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  disputed: 'bg-orange-100 text-orange-800 border-orange-200',
  resolved: 'bg-green-100 text-green-800 border-green-200',
  closed: 'bg-gray-100 text-gray-500 border-gray-200',
  completed: 'bg-green-100 text-green-800 border-green-200',
  failed: 'bg-red-100 text-red-800 border-red-200',
  running: 'bg-blue-100 text-blue-800 border-blue-200',
  queued: 'bg-gray-100 text-gray-700 border-gray-200',
  partial_ingest: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  accepted_ingest: 'bg-green-100 text-green-800 border-green-200',
}

function Badge({ label, colorClass }: { label: string; colorClass: string }) {
  return (
    <span className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-semibold ${colorClass}`}>
      {humanise(label)}
    </span>
  )
}

export function SeverityBadge({ severity }: { severity: string }) {
  return <Badge label={severity} colorClass={SEVERITY_COLORS[severity] ?? 'bg-gray-100 text-gray-700 border-gray-200'} />
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge label={status} colorClass={STATUS_COLORS[status] ?? 'bg-gray-100 text-gray-700 border-gray-200'} />
}

export function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    p1: 'bg-red-600 text-white border-red-600',
    p2: 'bg-orange-500 text-white border-orange-500',
    p3: 'bg-yellow-400 text-black border-yellow-400',
    p4: 'bg-gray-200 text-gray-700 border-gray-200',
  }
  return <Badge label={priority.toUpperCase()} colorClass={colors[priority] ?? 'bg-gray-100 text-gray-700 border-gray-200'} />
}

export function TypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    contradiction: 'bg-red-50 text-red-700 border-red-200',
    stale_state: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    timeline_violation: 'bg-purple-50 text-purple-700 border-purple-200',
    missing_relationship: 'bg-blue-50 text-blue-700 border-blue-200',
  }
  return <Badge label={type} colorClass={colors[type] ?? 'bg-gray-100 text-gray-700 border-gray-200'} />
}

// ── Stat tile ─────────────────────────────────────────────────────────────────

export function StatTile({
  label,
  value,
  sub,
  accent = false,
}: {
  label: string
  value: number | string
  sub?: string
  accent?: boolean
}) {
  return (
    <div className={`rounded-2xl border p-5 ${accent ? 'border-black bg-black text-white' : 'border-gray-200 bg-white'}`}>
      <p className={`text-xs font-bold uppercase tracking-widest ${accent ? 'text-gray-300' : 'text-gray-500'}`}>{label}</p>
      <p className={`mt-1 text-3xl font-black ${accent ? 'text-white' : 'text-black'}`}>{value}</p>
      {sub && <p className={`mt-0.5 text-xs ${accent ? 'text-gray-400' : 'text-gray-500'}`}>{sub}</p>}
    </div>
  )
}

// ── Feedback states ───────────────────────────────────────────────────────────

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-8 text-gray-400">
      <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
      </svg>
      <span className="text-sm font-medium">{label}</span>
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="py-12 text-center">
      <p className="text-sm font-medium text-gray-400">{message}</p>
    </div>
  )
}

export function ErrorState({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : 'Something went wrong.'
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">
      {msg}
    </div>
  )
}

export function SuccessState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm font-medium text-green-800">
      {message}
    </div>
  )
}

// ── Table ─────────────────────────────────────────────────────────────────────

export function Table({
  head,
  children,
}: {
  head: string[]
  children: ReactNode
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            {head.map((h) => (
              <th key={h} className="py-3 pr-4 text-xs font-bold uppercase tracking-widest text-gray-500">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  )
}

export function Tr({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <tr className={`border-b border-gray-100 hover:bg-gray-50 ${className}`}>{children}</tr>
}

export function Td({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <td className={`py-3 pr-4 ${className}`}>{children}</td>
}
