import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { endpoints } from '../api/endpoints'
import { Card, ErrorState, Loading, StatTile, formatDate, humanise } from '../components/primitives'

export function DashboardPage() {
  const stats = useQuery({ queryKey: ['finding-stats'], queryFn: endpoints.findingStats })
  const runs = useQuery({ queryKey: ['audit-runs'], queryFn: () => endpoints.listAuditRuns() })

  if (stats.isLoading) return <Loading />
  if (stats.error) return <ErrorState error={stats.error} />

  const data = stats.data
  if (!data) return null

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Integrity overview</h2>
        <p className="text-sm text-[var(--color-muted)]">
          Deterministic findings awaiting review across all audited batches.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile label="Open findings" value={data.open_total} />
        <StatTile
          label="Critical"
          value={data.by_severity.critical ?? 0}
          tone="text-[var(--color-critical)]"
        />
        <StatTile label="High" value={data.by_severity.high ?? 0} tone="text-[var(--color-high)]" />
        <StatTile label="Total detected" value={data.total} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="By severity">
          <ul className="space-y-2 text-sm">
            {Object.entries(data.by_severity).map(([key, value]) => (
              <li key={key} className="flex items-center justify-between">
                <Link to={`/findings?severity=${key}`} className="capitalize hover:underline">
                  {key}
                </Link>
                <span className="font-medium">{value}</span>
              </li>
            ))}
            {!Object.keys(data.by_severity).length && (
              <li className="text-[var(--color-muted)]">No findings yet.</li>
            )}
          </ul>
        </Card>

        <Card title="By status">
          <ul className="space-y-2 text-sm">
            {Object.entries(data.by_status).map(([key, value]) => (
              <li key={key} className="flex items-center justify-between">
                <span>{humanise(key)}</span>
                <span className="font-medium">{value}</span>
              </li>
            ))}
            {!Object.keys(data.by_status).length && (
              <li className="text-[var(--color-muted)]">No findings yet.</li>
            )}
          </ul>
        </Card>
      </div>

      <Card title="Recent audit runs">
        {runs.isLoading && <Loading />}
        {runs.data?.items.length ? (
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-[var(--color-muted)]">
              <tr>
                <th className="py-2">Run</th>
                <th className="py-2">Batch</th>
                <th className="py-2">Status</th>
                <th className="py-2">Started</th>
              </tr>
            </thead>
            <tbody>
              {runs.data.items.map((run) => (
                <tr key={run.id} className="border-t border-[var(--color-line)]">
                  <td className="py-2">
                    <Link to={`/findings?audit_run_id=${run.id}`} className="hover:underline">
                      #{run.id}
                    </Link>
                  </td>
                  <td className="py-2">{run.batch_external_id ?? run.batch_id}</td>
                  <td className="py-2">{humanise(run.status)}</td>
                  <td className="py-2">{formatDate(run.started_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          !runs.isLoading && (
            <p className="text-sm text-[var(--color-muted)]">
              No audit runs yet — ingest a batch and run an audit to begin.
            </p>
          )
        )}
      </Card>
    </div>
  )
}
