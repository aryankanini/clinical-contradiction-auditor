import type { ReactNode } from 'react'

const SEVERITY_STYLES: Record<string, string> = {
  critical: 'bg-red-50 text-red-800 ring-red-200',
  high: 'bg-orange-50 text-orange-800 ring-orange-200',
  medium: 'bg-amber-50 text-amber-900 ring-amber-200',
  low: 'bg-sky-50 text-sky-800 ring-sky-200',
}

const STATUS_STYLES: Record<string, string> = {
  new: 'bg-slate-100 text-slate-700 ring-slate-200',
  under_review: 'bg-blue-50 text-blue-800 ring-blue-200',
  accepted: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  deferred: 'bg-slate-100 text-slate-600 ring-slate-200',
  escalated: 'bg-orange-50 text-orange-800 ring-orange-200',
  disputed: 'bg-purple-50 text-purple-800 ring-purple-200',
  non_actionable: 'bg-yellow-50 text-yellow-900 ring-yellow-200',
  in_remediation: 'bg-indigo-50 text-indigo-800 ring-indigo-200',
  remediated: 'bg-teal-50 text-teal-800 ring-teal-200',
  closed: 'bg-green-50 text-green-900 ring-green-200',
  closed_no_action: 'bg-slate-100 text-slate-600 ring-slate-200',
}

const BASE_BADGE =
  'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset whitespace-nowrap'

export function humanise(value: string): string {
  return value.replace(/_/g, ' ')
}

export function SeverityBadge({ severity }: { severity: string }) {
  const style = SEVERITY_STYLES[severity] ?? 'bg-slate-100 text-slate-700 ring-slate-200'
  return <span className={`${BASE_BADGE} ${style}`}>{severity}</span>
}

export function PriorityBadge({ priority }: { priority: string }) {
  return (
    <span className={`${BASE_BADGE} bg-slate-100 text-slate-700 ring-slate-200 uppercase`}>
      {priority}
    </span>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? 'bg-slate-100 text-slate-700 ring-slate-200'
  return <span className={`${BASE_BADGE} ${style}`}>{humanise(status)}</span>
}

export function Card({
  title,
  action,
  children,
}: {
  title?: string
  action?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="rounded-lg border border-[var(--color-line)] bg-[var(--color-surface)]">
      {(title || action) && (
        <header className="flex items-center justify-between gap-3 border-b border-[var(--color-line)] px-4 py-3">
          {title && <h2 className="text-sm font-semibold">{title}</h2>}
          {action}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  )
}

export function Button({
  children,
  onClick,
  variant = 'default',
  disabled,
  type = 'button',
}: {
  children: ReactNode
  onClick?: () => void
  variant?: 'default' | 'primary' | 'subtle'
  disabled?: boolean
  type?: 'button' | 'submit'
}) {
  const styles = {
    primary: 'bg-slate-900 text-white hover:bg-slate-700 disabled:bg-slate-400',
    default:
      'bg-white text-slate-800 ring-1 ring-inset ring-[var(--color-line)] hover:bg-slate-50 disabled:text-slate-400',
    subtle: 'bg-transparent text-slate-600 hover:text-slate-900 hover:underline',
  }[variant]

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center rounded-md px-3 py-1.5 text-sm font-medium transition disabled:cursor-not-allowed ${styles}`}
    >
      {children}
    </button>
  )
}

export function EmptyState({ message }: { message: string }) {
  return (
    <p className="py-8 text-center text-sm text-[var(--color-muted)]">{message}</p>
  )
}

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : 'Something went wrong.'
  return (
    <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-800 ring-1 ring-inset ring-red-200">
      {message}
    </div>
  )
}

export function Loading() {
  return <p className="py-8 text-center text-sm text-[var(--color-muted)]">Loading…</p>
}

export function StatTile({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <div className="rounded-lg border border-[var(--color-line)] bg-[var(--color-surface)] px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-[var(--color-muted)]">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${tone ?? ''}`}>{value}</p>
    </div>
  )
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}
