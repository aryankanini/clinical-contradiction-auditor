import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { endpoints } from '../api/endpoints'
import {
  Button, Card, EmptyState, ErrorState, Loading, StatusBadge, SuccessState,
  Table, Tr, Td, formatDate,
} from '../components/primitives'

export function BatchesPage() {
  const queryClient = useQueryClient()
  const fileInput = useRef<HTMLInputElement>(null)
  const [message, setMessage] = useState<string | null>(null)

  const batches = useQuery({ queryKey: ['batches'], queryFn: () => endpoints.listBatches() })

  const upload = useMutation({
    mutationFn: (file: File) => endpoints.uploadBatchFile(file),
    onSuccess: (result) => {
      setMessage(
        `"${result.batch.batch_external_id}" uploaded successfully — ` +
        `${result.batch.accepted_count} records accepted, ` +
        `${result.batch.quarantined_count} flagged for review.`,
      )
      void queryClient.invalidateQueries({ queryKey: ['batches'] })
    },
  })

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-black text-black">Patient Records</h2>
        <p className="mt-1 text-sm text-gray-500">
          Upload batches of patient records in FHIR JSON format to check them for data quality issues.
        </p>
      </div>

      <Card title="Upload New Records">
        <p className="mb-4 text-sm text-gray-600">
          Select a JSON file containing patient records. After uploading, open the batch and click{' '}
          <strong>Run Audit</strong> to detect any inconsistencies.
        </p>
        <input
          ref={fileInput}
          type="file"
          accept="application/json"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) upload.mutate(file)
            e.target.value = ''
          }}
        />
        <Button variant="primary" onClick={() => fileInput.current?.click()} disabled={upload.isPending}>
          {upload.isPending ? 'Uploading…' : '↑ Choose file and upload'}
        </Button>
        {message && <div className="mt-4"><SuccessState message={message} /></div>}
        {upload.error && <div className="mt-4"><ErrorState error={upload.error} /></div>}
      </Card>

      <Card title="Previously Uploaded Batches">
        {batches.isLoading && <Loading />}
        {batches.error && <ErrorState error={batches.error} />}
        {batches.data && !batches.data.items.length && (
          <EmptyState message="No batches uploaded yet." />
        )}
        {batches.data && batches.data.items.length > 0 && (
          <Table head={['Batch ID', 'Source System', 'Status', 'Accepted', 'Flagged', 'Received']}>
            {batches.data.items.map((batch) => (
              <Tr key={batch.id}>
                <Td>
                  <Link to={`/batches/${batch.id}`} className="font-bold hover:underline">
                    {batch.batch_external_id}
                  </Link>
                </Td>
                <Td className="text-gray-600">{batch.source_system}</Td>
                <Td><StatusBadge status={batch.status} /></Td>
                <Td className="font-semibold">{batch.accepted_count}</Td>
                <Td className={batch.quarantined_count > 0 ? 'font-semibold text-orange-600' : ''}>
                  {batch.quarantined_count}
                </Td>
                <Td className="text-xs text-gray-500">{formatDate(batch.received_at)}</Td>
              </Tr>
            ))}
          </Table>
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
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-gray-400">Batch</p>
          <h2 className="text-2xl font-black text-black">{data.batch_external_id}</h2>
          <p className="mt-1 text-sm text-gray-500">Source: {data.source_system}</p>
        </div>
        <Button variant="primary" onClick={() => runAudit.mutate()} disabled={runAudit.isPending}>
          {runAudit.isPending ? 'Starting…' : '▶ Run Audit'}
        </Button>
      </div>

      {runAudit.error && <ErrorState error={runAudit.error} />}

      <div className="grid gap-4 lg:grid-cols-4">
        {[
          { label: 'Status', value: <StatusBadge status={data.status} /> },
          { label: 'Records Accepted', value: data.accepted_count },
          { label: 'Flagged for Review', value: data.quarantined_count },
          { label: 'Ready for Audit', value: data.rule_ready_count },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
            <p className="text-xs font-bold uppercase tracking-widest text-gray-500">{label}</p>
            <div className="mt-2 text-xl font-black text-black">{value}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Record Types in This Batch">
          {Object.keys(data.resource_type_counts).length ? (
            <ul className="divide-y divide-gray-100">
              {Object.entries(data.resource_type_counts).map(([type, count]) => (
                <li key={type} className="flex items-center justify-between py-2.5 text-sm">
                  <span className="font-semibold text-black">{type}</span>
                  <span className="font-bold text-black">{count}</span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState message="No records found." />
          )}
        </Card>

        <Card title="Previous Audit Runs">
          {data.audit_runs.length ? (
            <Table head={['Run #', 'Rule Version', 'Status', 'Started', '']}>
              {data.audit_runs.map((run) => (
                <Tr key={run.id}>
                  <Td className="font-bold">#{run.id}</Td>
                  <Td className="text-gray-600">{run.rule_pack_version ?? '—'}</Td>
                  <Td><StatusBadge status={run.status} /></Td>
                  <Td className="text-xs text-gray-500">{formatDate(run.started_at)}</Td>
                  <Td>
                    <Link to={`/findings?audit_run_id=${run.id}`} className="text-sm font-semibold hover:underline">
                      View issues →
                    </Link>
                  </Td>
                </Tr>
              ))}
            </Table>
          ) : (
            <EmptyState message="No audit runs yet. Click 'Run Audit' above." />
          )}
        </Card>
      </div>

      <Card title="Individual Patient Records">
        <p className="mb-4 text-sm text-gray-500">
          Each row is one clinical record (e.g. a diagnosis, medication, or encounter) extracted from the uploaded file.
        </p>
        {resources.isLoading && <Loading />}
        {resources.data?.items.length ? (
          <Table head={['Record ID', 'Type', 'Status', 'Audit Ready', 'Missing Information']}>
            {resources.data.items.map((r) => (
              <Tr key={r.id}>
                <Td className="font-mono text-xs text-gray-600">{r.record_external_id}</Td>
                <Td className="font-semibold">{r.resource_type}</Td>
                <Td className="text-gray-600">{r.status_value ?? '—'}</Td>
                <Td>
                  <span className={`text-xs font-bold ${r.rule_ready ? 'text-green-700' : 'text-orange-600'}`}>
                    {r.rule_ready ? 'Yes' : 'No'}
                  </span>
                </Td>
                <Td className="text-xs text-gray-500">
                  {[...r.incomplete_fields, ...r.unresolved_links].join(', ') || '—'}
                </Td>
              </Tr>
            ))}
          </Table>
        ) : (
          !resources.isLoading && <EmptyState message="No records found." />
        )}
      </Card>
    </div>
  )
}
