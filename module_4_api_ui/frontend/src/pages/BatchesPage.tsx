import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { endpoints } from '../api/endpoints'
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  Loading,
  StatusBadge,
  formatDate,
  humanise,
} from '../components/primitives'

export function BatchesPage() {
  const queryClient = useQueryClient()
  const fileInput = useRef<HTMLInputElement>(null)
  const [message, setMessage] = useState<string | null>(null)

  const batches = useQuery({ queryKey: ['batches'], queryFn: () => endpoints.listBatches() })

  const upload = useMutation({
    mutationFn: (file: File) => endpoints.uploadBatch(file),
    onSuccess: (result) => {
      setMessage(
        `Ingested ${result.batch.batch_external_id}: ${result.batch.accepted_count} accepted, ` +
          `${result.batch.quarantined_count} quarantined (${humanise(result.ingest_status)}).`,
      )
      void queryClient.invalidateQueries({ queryKey: ['batches'] })
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Batches</h2>
          <p className="text-sm text-[var(--color-muted)]">
            FHIR batches ingested for cross-resource auditing.
          </p>
        </div>
        <div>
          <input
            ref={fileInput}
            type="file"
            accept="application/json"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) upload.mutate(file)
              event.target.value = ''
            }}
          />
          <Button variant="primary" onClick={() => fileInput.current?.click()}>
            {upload.isPending ? 'Uploading…' : 'Upload batch JSON'}
          </Button>
        </div>
      </div>

      {message && (
        <div className="rounded-md bg-emerald-50 px-4 py-3 text-sm text-emerald-900 ring-1 ring-inset ring-emerald-200">
          {message}
        </div>
      )}
      {upload.error && <ErrorState error={upload.error} />}

      <Card>
        {batches.isLoading && <Loading />}
        {batches.error && <ErrorState error={batches.error} />}
        {batches.data && !batches.data.items.length && (
          <EmptyState message="No batches ingested yet." />
        )}
        {batches.data && batches.data.items.length > 0 && (
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-[var(--color-muted)]">
              <tr>
                <th className="py-2">Batch</th>
                <th className="py-2">Source</th>
                <th className="py-2">Status</th>
                <th className="py-2">Accepted</th>
                <th className="py-2">Quarantined</th>
                <th className="py-2">Received</th>
              </tr>
            </thead>
            <tbody>
              {batches.data.items.map((batch) => (
                <tr key={batch.id} className="border-t border-[var(--color-line)]">
                  <td className="py-2">
                    <Link to={`/batches/${batch.id}`} className="font-medium hover:underline">
                      {batch.batch_external_id}
                    </Link>
                  </td>
                  <td className="py-2">{batch.source_system}</td>
                  <td className="py-2">
                    <StatusBadge status={batch.status} />
                  </td>
                  <td className="py-2">{batch.accepted_count}</td>
                  <td className="py-2">{batch.quarantined_count}</td>
                  <td className="py-2">{formatDate(batch.received_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}

export function BatchDetailPage() {
  const { batchId } = useParams()
  const id = Number(batchId)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const batch = useQuery({ queryKey: ['batch', id], queryFn: () => endpoints.getBatch(id) })
  const resources = useQuery({
    queryKey: ['batch-resources', id],
    queryFn: () => endpoints.listBatchResources(id),
  })

  const runAudit = useMutation({
    mutationFn: () => endpoints.createAuditRun(id),
    onSuccess: (run) => {
      void queryClient.invalidateQueries({ queryKey: ['batch', id] })
      navigate(`/findings?audit_run_id=${run.id}`)
    },
  })

  if (batch.isLoading) return <Loading />
  if (batch.error) return <ErrorState error={batch.error} />
  if (!batch.data) return null

  const data = batch.data

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">{data.batch_external_id}</h2>
          <p className="text-sm text-[var(--color-muted)]">
            {data.source_system} · received {formatDate(data.received_at)}
          </p>
        </div>
        <Button variant="primary" onClick={() => runAudit.mutate()} disabled={runAudit.isPending}>
          {runAudit.isPending ? 'Starting…' : 'Run deterministic audit'}
        </Button>
      </div>

      {runAudit.error && <ErrorState error={runAudit.error} />}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Ingest outcome">
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-[var(--color-muted)]">Status</dt>
              <dd>
                <StatusBadge status={data.status} />
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[var(--color-muted)]">Accepted</dt>
              <dd>{data.accepted_count}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[var(--color-muted)]">Quarantined</dt>
              <dd>{data.quarantined_count}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[var(--color-muted)]">Rule-ready resources</dt>
              <dd>{data.rule_ready_count}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[var(--color-muted)]">Governed relationship signals</dt>
              <dd>{data.governed_signal_count}</dd>
            </div>
          </dl>
        </Card>

        <Card title="Resource mix">
          <ul className="space-y-2 text-sm">
            {Object.entries(data.resource_type_counts).map(([type, count]) => (
              <li key={type} className="flex justify-between">
                <span>{type}</span>
                <span className="font-medium">{count}</span>
              </li>
            ))}
            {!Object.keys(data.resource_type_counts).length && (
              <li className="text-[var(--color-muted)]">No normalized resources.</li>
            )}
          </ul>
        </Card>
      </div>

      <Card title="Audit runs">
        {data.audit_runs.length ? (
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-[var(--color-muted)]">
              <tr>
                <th className="py-2">Run</th>
                <th className="py-2">Rule pack</th>
                <th className="py-2">Status</th>
                <th className="py-2">Started</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {data.audit_runs.map((run) => (
                <tr key={run.id} className="border-t border-[var(--color-line)]">
                  <td className="py-2">#{run.id}</td>
                  <td className="py-2">{run.rule_pack_version ?? '—'}</td>
                  <td className="py-2">{humanise(run.status)}</td>
                  <td className="py-2">{formatDate(run.started_at)}</td>
                  <td className="py-2 text-right">
                    <Link
                      to={`/findings?audit_run_id=${run.id}`}
                      className="text-sm hover:underline"
                    >
                      View findings
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState message="No audit runs for this batch yet." />
        )}
      </Card>

      <Card title="Normalized resources">
        {resources.isLoading && <Loading />}
        {resources.data?.items.length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-[var(--color-muted)]">
                <tr>
                  <th className="py-2 pr-3">Record</th>
                  <th className="py-2 pr-3">Type</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Rule ready</th>
                  <th className="py-2">Gaps</th>
                </tr>
              </thead>
              <tbody>
                {resources.data.items.map((resource) => (
                  <tr key={resource.id} className="border-t border-[var(--color-line)]">
                    <td className="py-2 pr-3 font-mono text-xs">{resource.record_external_id}</td>
                    <td className="py-2 pr-3">{resource.resource_type}</td>
                    <td className="py-2 pr-3">{resource.status_value ?? '—'}</td>
                    <td className="py-2 pr-3">{resource.rule_ready ? 'yes' : 'no'}</td>
                    <td className="py-2 text-xs text-[var(--color-muted)]">
                      {[...resource.incomplete_fields, ...resource.unresolved_links].join(', ') ||
                        '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          !resources.isLoading && <EmptyState message="No normalized resources." />
        )}
      </Card>
    </div>
  )
}
