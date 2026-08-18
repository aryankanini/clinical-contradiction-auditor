import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'

import { endpoints } from '../api/endpoints'
import {
  Card,
  EmptyState,
  ErrorState,
  Loading,
  PriorityBadge,
  SeverityBadge,
  StatusBadge,
  formatDate,
  humanise,
} from '../components/primitives'

const SEVERITIES = ['critical', 'high', 'medium', 'low']
const TYPES = ['contradiction', 'stale_state', 'timeline_violation', 'missing_relationship']

/**
 * The prioritised finding queue (UC-002 step 1). Filters live in the URL so a steward
 * can share a link to exactly the slice they are working.
 */
export function FindingsQueuePage() {
  const [params, setParams] = useSearchParams()

  const filters = {
    audit_run_id: params.get('audit_run_id') ? Number(params.get('audit_run_id')) : undefined,
    batch_id: params.get('batch_id') ? Number(params.get('batch_id')) : undefined,
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

  const toggle = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    const current = next.getAll(key)
    next.delete(key)
    const updated = current.includes(value)
      ? current.filter((entry) => entry !== value)
      : [...current, value]
    updated.forEach((entry) => next.append(key, entry))
    next.delete('page')
    setParams(next)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Findings queue</h2>
        <p className="text-sm text-[var(--color-muted)]">
          Ordered by triage priority, then severity. Deterministic rules establish every finding
          shown here.
        </p>
      </div>

      <Card>
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase tracking-wide text-[var(--color-muted)]">
              Severity
            </span>
            {SEVERITIES.map((severity) => (
              <button
                key={severity}
                onClick={() => toggle('severity', severity)}
                className={`rounded-full px-2 py-0.5 text-xs ring-1 ring-inset ${
                  params.getAll('severity').includes(severity)
                    ? 'bg-slate-900 text-white ring-slate-900'
                    : 'bg-white text-slate-700 ring-[var(--color-line)]'
                }`}
              >
                {severity}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs uppercase tracking-wide text-[var(--color-muted)]">Type</span>
            {TYPES.map((type) => (
              <button
                key={type}
                onClick={() => toggle('finding_type', type)}
                className={`rounded-full px-2 py-0.5 text-xs ring-1 ring-inset ${
                  params.getAll('finding_type').includes(type)
                    ? 'bg-slate-900 text-white ring-slate-900'
                    : 'bg-white text-slate-700 ring-[var(--color-line)]'
                }`}
              >
                {humanise(type)}
              </button>
            ))}
          </div>

          {params.toString() && (
            <button
              onClick={() => setParams(new URLSearchParams())}
              className="text-xs text-slate-600 hover:underline"
            >
              Clear filters
            </button>
          )}
        </div>
      </Card>

      <Card>
        {findings.isLoading && <Loading />}
        {findings.error && <ErrorState error={findings.error} />}
        {findings.data && !findings.data.items.length && (
          <EmptyState message="No findings match these filters." />
        )}
        {findings.data && findings.data.items.length > 0 && (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-[var(--color-muted)]">
                  <tr>
                    <th className="py-2 pr-3">Priority</th>
                    <th className="py-2 pr-3">Severity</th>
                    <th className="py-2 pr-3">Rule</th>
                    <th className="py-2 pr-3">Summary</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2 pr-3">Transparency</th>
                    <th className="py-2">Detected</th>
                  </tr>
                </thead>
                <tbody>
                  {findings.data.items.map((finding) => (
                    <tr key={finding.id} className="border-t border-[var(--color-line)]">
                      <td className="py-2 pr-3">
                        <PriorityBadge priority={finding.priority} />
                      </td>
                      <td className="py-2 pr-3">
                        <SeverityBadge severity={finding.severity} />
                      </td>
                      <td className="py-2 pr-3">
                        <code className="text-xs">{finding.rule_id}</code>
                      </td>
                      <td className="py-2 pr-3 max-w-md">
                        <Link
                          to={`/findings/${finding.id}`}
                          className="hover:underline"
                          title={finding.summary}
                        >
                          {finding.summary}
                        </Link>
                      </td>
                      <td className="py-2 pr-3">
                        <StatusBadge status={finding.status} />
                      </td>
                      <td className="py-2 pr-3 text-xs">
                        {finding.transparency_complete ? (
                          <span className="text-[var(--color-good)]">complete</span>
                        ) : (
                          <span className="text-[var(--color-high)]">incomplete</span>
                        )}
                      </td>
                      <td className="py-2 text-xs text-[var(--color-muted)]">
                        {formatDate(finding.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="mt-3 text-xs text-[var(--color-muted)]">
              {findings.data.total} finding(s) · page {findings.data.page} of{' '}
              {findings.data.total_pages}
            </p>
          </>
        )}
      </Card>
    </div>
  )
}
