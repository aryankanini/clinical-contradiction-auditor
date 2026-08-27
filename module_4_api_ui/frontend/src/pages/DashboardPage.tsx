import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { endpoints } from '../api/endpoints'
import {
  Card, EmptyState, ErrorState, Loading, StatTile,
  Table, Tr, Td, StatusBadge, SeverityBadge, formatDate, humanise,
} from '../components/primitives'

const TYPE_LABELS: Record<string, string> = {
  contradiction: 'Contradictions',
  stale_state: 'Stale Records',
  timeline_violation: 'Timeline Issues',
  missing_relationship: 'Missing Links',
}

const TYPE_DESC: Record<string, string> = {
  contradiction: 'Two records say opposite things about the same patient.',
  stale_state: 'A record has been left open or unchanged for too long.',
  timeline_violation: 'Events are recorded in an impossible order.',
  missing_relationship: 'A required link between records is absent.',
}

export function DashboardPage() {
  const stats = useQuery({ queryKey: ['finding-stats'], queryFn: endpoints.findingStats })
  const runs = useQuery({ queryKey: ['audit-runs'], queryFn: () => endpoints.listAuditRuns() })

  if (stats.isLoading) return <Loading />
  if (stats.error) return <ErrorState error={stats.error} />
  const data = stats.data

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-black text-black">Overview</h2>
        <p className="mt-1 text-sm text-gray-500">
          A summary of all data quality issues found across patient records.
        </p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile label="Open Issues" value={data?.open_total ?? 0} accent />
        <StatTile
          label="Critical"
          value={data?.by_severity.critical ?? 0}
          sub="Needs immediate attention"
        />
        <StatTile
          label="High"
          value={data?.by_severity.high ?? 0}
          sub="Review soon"
        />
        <StatTile
          label="Total Detected"
          value={data?.total ?? 0}
          sub="All time"
        />
      </div>

      {/* Issue type explainer */}
      <div>
        <h3 className="mb-3 text-xs font-black uppercase tracking-widest text-gray-500">
          What kind of issues were found?
        </h3>
        <div className="grid gap-4 lg:grid-cols-4">
          {Object.entries(TYPE_LABELS).map(([key, label]) => (
            <Link
              key={key}
              to={`/findings?finding_type=${key}`}
              className="group rounded-2xl border border-gray-200 bg-white p-5 shadow-sm transition hover:border-black hover:shadow-md"
            >
              <p className="text-2xl font-black text-black">
                {data?.by_type?.[key] ?? 0}
              </p>
              <p className="mt-1 text-sm font-bold text-black">{label}</p>
              <p className="mt-1 text-xs text-gray-500">{TYPE_DESC[key]}</p>
            </Link>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* By severity */}
        <Card title="Issues by Severity">
          {!data || !Object.keys(data.by_severity).length ? (
            <EmptyState message="No issues detected yet." />
          ) : (
            <ul className="space-y-3">
              {['critical', 'high', 'medium', 'low'].map((sev) => {
                const count = data.by_severity[sev] ?? 0
                const total = data.total || 1
                return (
                  <li key={sev}>
                    <div className="mb-1 flex items-center justify-between text-sm">
                      <Link to={`/findings?severity=${sev}`} className="font-semibold capitalize hover:underline">
                        {sev}
                      </Link>
                      <span className="font-bold">{count}</span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
                      <div
                        className={`h-2 rounded-full ${sev === 'critical' ? 'bg-red-500' : sev === 'high' ? 'bg-orange-400' : sev === 'medium' ? 'bg-yellow-400' : 'bg-blue-400'}`}
                        style={{ width: `${(count / total) * 100}%` }}
                      />
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </Card>

        {/* By status */}
        <Card title="Issues by Status">
          {!data || !Object.keys(data.by_status).length ? (
            <EmptyState message="No issues detected yet." />
          ) : (
            <ul className="divide-y divide-gray-100">
              {Object.entries(data.by_status).map(([key, value]) => (
                <li key={key} className="flex items-center justify-between py-2.5 text-sm">
                  <StatusBadge status={key} />
                  <span className="font-bold text-black">{value}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {/* Recent audit runs */}
      <Card title="Recent Audit Checks">
        {runs.isLoading && <Loading />}
        {runs.data && !runs.data.items.length && (
          <EmptyState message="No checks run yet — upload a patient record batch to begin." />
        )}
        {runs.data && runs.data.items.length > 0 && (
          <Table head={['Check #', 'Record Batch', 'Rule Version', 'Status', 'Issues Found', 'Started']}>
            {runs.data.items.map((run) => (
              <Tr key={run.id}>
                <Td>
                  <Link to={`/findings?audit_run_id=${run.id}`} className="font-bold hover:underline">
                    #{run.id}
                  </Link>
                </Td>
                <Td className="text-gray-600">{run.batch_external_id ?? `Batch ${run.batch_id}`}</Td>
                <Td className="text-gray-600">{run.rule_pack_version ?? '—'}</Td>
                <Td><StatusBadge status={run.status} /></Td>
                <Td className="font-bold">{run.finding_count ?? '—'}</Td>
                <Td className="text-gray-500 text-xs">{formatDate(run.started_at)}</Td>
              </Tr>
            ))}
          </Table>
        )}
      </Card>
    </div>
  )
}
