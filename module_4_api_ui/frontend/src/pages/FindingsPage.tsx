import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { endpoints } from '../api/endpoints'
import {
  Card, EmptyState, ErrorState, Loading, PriorityBadge, SeverityBadge,
  StatusBadge, TypeBadge, Table, Tr, Td, Button, formatDate,
} from '../components/primitives'

const SEVERITIES = ['critical', 'high', 'medium', 'low']
const TYPES = ['contradiction', 'stale_state', 'timeline_violation', 'missing_relationship']
const TYPE_LABELS: Record<string, string> = {
  contradiction: 'Contradiction',
  stale_state: 'Stale Record',
  timeline_violation: 'Timeline Issue',
  missing_relationship: 'Missing Link',
}

export function FindingsQueuePage() {
  const [params, setParams] = useSearchParams()

  const filters = {
    audit_run_id: params.get('audit_run_id') ? Number(params.get('audit_run_id')) : undefined,
    batch_id: params.get('batch_id') ? Number(params.get('batch_id')) : undefined,
    queue_id: params.get('queue_id') ? Number(params.get('queue_id')) : undefined,
    severity: params.getAll('severity'),
    finding_type: params.getAll('finding_type'),
    open_only: params.get('open_only') === 'true',
    search: params.get('search') ?? undefined,
    page: Number(params.get('page') ?? 1),
  }

  const findings = useQuery({
    queryKey: ['findings', Object.fromEntries(params.entries())],
    queryFn: () => endpoints.listFindings(filters),
  })

  function toggle(key: string, value: string) {
    const next = new URLSearchParams(params)
    const current = next.getAll(key)
    next.delete(key)
    const updated = current.includes(value)
      ? current.filter((v) => v !== value)
      : [...current, value]
    updated.forEach((v) => next.append(key, v))
    next.delete('page')
    setParams(next)
  }

  function setPage(p: number) {
    const next = new URLSearchParams(params)
    next.set('page', String(p))
    setParams(next)
  }

  const hasFilters = params.toString().length > 0

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-black text-black">Issues Found</h2>
        <p className="mt-1 text-sm text-gray-500">
          All data quality issues detected across patient records, ordered by priority.
        </p>
      </div>

      {/* Filter bar */}
      <Card>
        <div className="flex flex-wrap items-center gap-6">
          <div>
            <p className="mb-2 text-xs font-bold uppercase tracking-widest text-gray-400">Severity</p>
            <div className="flex flex-wrap gap-2">
              {SEVERITIES.map((s) => (
                <button
                  key={s}
                  onClick={() => toggle('severity', s)}
                  className={`rounded-full px-3 py-1 text-xs font-bold transition ${
                    params.getAll('severity').includes(s)
                      ? 'bg-black text-white'
                      : 'border border-gray-200 bg-white text-gray-600 hover:border-black'
                  }`}
                >
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="mb-2 text-xs font-bold uppercase tracking-widest text-gray-400">Issue Type</p>
            <div className="flex flex-wrap gap-2">
              {TYPES.map((t) => (
                <button
                  key={t}
                  onClick={() => toggle('finding_type', t)}
                  className={`rounded-full px-3 py-1 text-xs font-bold transition ${
                    params.getAll('finding_type').includes(t)
                      ? 'bg-black text-white'
                      : 'border border-gray-200 bg-white text-gray-600 hover:border-black'
                  }`}
                >
                  {TYPE_LABELS[t]}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={filters.open_only}
                onChange={(e) => {
                  const next = new URLSearchParams(params)
                  if (e.target.checked) next.set('open_only', 'true')
                  else next.delete('open_only')
                  setParams(next)
                }}
                className="h-4 w-4 rounded border-gray-300"
              />
              Open issues only
            </label>

            {hasFilters && (
              <button
                onClick={() => setParams(new URLSearchParams())}
                className="text-xs font-semibold text-gray-500 hover:text-black hover:underline"
              >
                Clear all filters
              </button>
            )}
          </div>
        </div>
      </Card>

      {/* Results */}
      <Card>
        {findings.isLoading && <Loading />}
        {findings.error && <ErrorState error={findings.error} />}
        {findings.data && !findings.data.items.length && (
          <EmptyState message="No issues match these filters." />
        )}
        {findings.data && findings.data.items.length > 0 && (
          <>
            <Table head={['Priority', 'Severity', 'Type', 'Description', 'Status', 'AI', 'Detected']}>
              {findings.data.items.map((f) => (
                <Tr key={f.id}>
                  <Td><PriorityBadge priority={f.priority} /></Td>
                  <Td><SeverityBadge severity={f.severity} /></Td>
                  <Td><TypeBadge type={f.finding_type} /></Td>
                  <Td className="max-w-sm">
                    <Link to={`/findings/${f.id}`} className="font-semibold text-black hover:underline" title={f.summary}>
                      {f.summary.length > 90 ? f.summary.slice(0, 90) + '…' : f.summary}
                    </Link>
                  </Td>
                  <Td><StatusBadge status={f.status} /></Td>
                  <Td>
                    {f.has_explanation ? (
                      <span className="text-xs font-bold text-green-700">✓ Explained</span>
                    ) : (
                      <span className="text-xs text-gray-400">—</span>
                    )}
                  </Td>
                  <Td className="text-xs text-gray-500">{formatDate(f.created_at)}</Td>
                </Tr>
              ))}
            </Table>

            <div className="mt-4 flex items-center justify-between text-sm text-gray-500">
              <span>{findings.data.total} issue(s) total</span>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  disabled={filters.page <= 1}
                  onClick={() => setPage(filters.page - 1)}
                >
                  ← Previous
                </Button>
                <span className="font-semibold text-black">
                  Page {findings.data.page} of {findings.data.total_pages}
                </span>
                <Button
                  variant="ghost"
                  disabled={filters.page >= findings.data.total_pages}
                  onClick={() => setPage(filters.page + 1)}
                >
                  Next →
                </Button>
              </div>
            </div>
          </>
        )}
      </Card>
    </div>
  )
}
