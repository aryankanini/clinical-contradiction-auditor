import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { endpoints } from '../api/endpoints'
import type { AIExplanation, FindingDetail } from '../api/types'
import {
  Button, Card, ErrorState, Loading, PriorityBadge, SeverityBadge,
  StatusBadge, TypeBadge, Table, Tr, Td, formatDate, humanise,
} from '../components/primitives'

function isExplanation(v: unknown): v is AIExplanation {
  return Boolean(v && typeof v === 'object' && 'rationale_text' in v)
}

const DISPOSITIONS = [
  { key: 'accept', label: 'Accept', desc: 'Confirm this is a real issue' },
  { key: 'escalate', label: 'Escalate', desc: 'Send to a specialist' },
  { key: 'defer', label: 'Defer', desc: 'Review later' },
  { key: 'dispute', label: 'Dispute', desc: 'Mark as incorrect' },
]

export function FindingDetailPage() {
  const { findingId } = useParams()
  const id = Number(findingId)
  const queryClient = useQueryClient()
  const [actionError, setActionError] = useState<string | null>(null)
  const [action, setAction] = useState('')
  const [rationale, setRationale] = useState('')

  const finding = useQuery({ queryKey: ['finding', id], queryFn: () => endpoints.getFinding(id) })
  const queues = useQuery({ queryKey: ['queues'], queryFn: endpoints.listQueues })
  const explanation = useQuery({
    queryKey: ['explanation', id],
    queryFn: () => endpoints.getExplanation(id),
    refetchInterval: (q) => {
      const v = q.state.data
      if (!v || isExplanation(v)) return false
      return v.state === 'pending' || v.state === 'running' ? 2000 : false
    },
  })

  const stored = isExplanation(explanation.data) ? explanation.data : null

  useEffect(() => {
    if (stored?.resolution_draft && !action && !rationale) {
      setAction(stored.resolution_draft.suggested_action)
      setRationale(stored.resolution_draft.rationale)
    }
  }, [stored, action, rationale])

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['finding', id] })
    void queryClient.invalidateQueries({ queryKey: ['findings'] })
    void queryClient.invalidateQueries({ queryKey: ['finding-stats'] })
    void queryClient.invalidateQueries({ queryKey: ['queues'] })
  }

  const onError = (e: unknown) => setActionError(e instanceof Error ? e.message : 'Action failed.')

  const triage = useMutation({
    mutationFn: (d: string) => endpoints.triageFinding(id, d),
    onSuccess: () => { setActionError(null); invalidate() },
    onError,
  })

  const transition = useMutation({
    mutationFn: (s: string) => endpoints.transitionFinding(id, s),
    onSuccess: () => { setActionError(null); invalidate() },
    onError,
  })

  const generate = useMutation({
    mutationFn: () => endpoints.generateExplanation(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['explanation', id] }),
    onError,
  })

  const approve = useMutation({
    mutationFn: () => {
      const draft = stored?.resolution_draft
      const unchanged = draft && draft.suggested_action === action && draft.rationale === rationale
      return endpoints.approveResolution(id, {
        suggested_action: action,
        rationale,
        source: draft ? (unchanged ? 'ai' : 'ai_edited') : 'manual',
      })
    },
    onSuccess: () => { setActionError(null); invalidate() },
    onError,
  })

  const assign = useMutation({
    mutationFn: (queueId?: number) => endpoints.assignFinding(id, queueId),
    onSuccess: () => { setActionError(null); invalidate() },
    onError,
  })

  if (finding.isLoading) return <Loading />
  if (finding.error) return <ErrorState error={finding.error} />
  if (!finding.data) return null
  const data: FindingDetail = finding.data

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <SeverityBadge severity={data.severity} />
          <PriorityBadge priority={data.priority} />
          <StatusBadge status={data.status} />
          <TypeBadge type={data.finding_type} />
        </div>
        <h2 className="mt-3 text-xl font-black text-black">{data.summary}</h2>
        <p className="mt-1 text-xs text-gray-500">
          Rule: <code className="rounded bg-gray-100 px-1.5 py-0.5">{data.rule_id}</code>
          {' · '}Detected {formatDate(data.created_at)}
        </p>
      </div>

      {actionError && <ErrorState error={new Error(actionError)} />}

      <div className="grid gap-8 lg:grid-cols-2">
        {/* Left column */}
        <div className="space-y-6">

          {/* Evidence */}
          <Card title="Supporting Evidence">
            <p className="mb-4 text-sm text-gray-500">
              These are the specific patient records that triggered this issue.
            </p>
            {data.evidence.length ? (
              <Table head={['Record ID', 'Record Type', 'Status', 'Issue Type']}>
                {data.evidence.map((ev) => (
                  <Tr key={ev.id}>
                    <Td className="font-mono text-xs text-gray-600">{ev.record_external_id ?? '—'}</Td>
                    <Td className="font-semibold">{ev.resource_type ?? '—'}</Td>
                    <Td className="text-gray-600">{ev.status_value ?? '—'}</Td>
                    <Td className="text-xs text-gray-500">{humanise(ev.evidence_type)}</Td>
                  </Tr>
                ))}
              </Table>
            ) : (
              <p className="text-sm text-gray-400">No evidence records attached.</p>
            )}
          </Card>

          {/* History */}
          <Card title="Status History">
            <p className="mb-4 text-sm text-gray-500">
              A full audit trail of every action taken on this issue.
            </p>
            {data.status_history?.length ? (
              <ol className="space-y-3">
                {data.status_history.map((row) => (
                  <li key={row.id} className="flex items-start justify-between gap-4 text-sm">
                    <div>
                      <span className="font-semibold text-black">
                        {row.from_status ? `${humanise(row.from_status)} → ` : ''}
                        {humanise(row.to_status)}
                      </span>
                      {row.notes && (
                        <p className="mt-0.5 text-xs text-gray-500">{row.notes}</p>
                      )}
                    </div>
                    <div className="shrink-0 text-right text-xs text-gray-400">
                      <p>{row.changed_by ?? 'system'}</p>
                      <p>{formatDate(row.changed_at)}</p>
                    </div>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-sm text-gray-400">No history yet.</p>
            )}
          </Card>
        </div>

        {/* Right column */}
        <div className="space-y-6">

          {/* AI Explanation */}
          <Card title="AI Explanation">
            {stored ? (
              <div className="space-y-4">
                <div>
                  <p className="mb-1 text-xs font-bold uppercase tracking-widest text-gray-400">What happened</p>
                  <p className="text-sm text-black leading-relaxed">{stored.rationale_text}</p>
                </div>
                {stored.evidence?.narrative && (
                  <div>
                    <p className="mb-1 text-xs font-bold uppercase tracking-widest text-gray-400">Evidence summary</p>
                    <p className="text-sm text-gray-600">{stored.evidence.narrative}</p>
                  </div>
                )}
                {stored.resolution_draft && (
                  <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
                    <p className="mb-1 text-xs font-bold uppercase tracking-widest text-blue-600">AI Suggested Action</p>
                    <p className="text-sm font-semibold text-black">{stored.resolution_draft.suggested_action}</p>
                    <p className="mt-1 text-xs text-blue-700">{stored.resolution_draft.audit_only_note}</p>
                  </div>
                )}
                {stored.low_confidence && (
                  <p className="text-xs font-semibold text-orange-600">
                    ⚠ Low confidence — review carefully before acting.
                  </p>
                )}
                <p className="text-xs text-gray-400">
                  Generated by {stored.model_name} · {formatDate(stored.created_at)}
                </p>
                <Button onClick={() => generate.mutate()} disabled={generate.isPending} variant="ghost">
                  {generate.isPending ? 'Regenerating…' : '↺ Regenerate explanation'}
                </Button>
              </div>
            ) : explanation.data && !isExplanation(explanation.data) ? (
              <div className="space-y-3">
                <div className="flex items-center gap-3 text-sm text-gray-600">
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                  AI is analysing this issue…
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-gray-500">
                  No explanation generated yet. Click below to ask the AI to explain this issue in plain language.
                </p>
                <Button variant="primary" onClick={() => generate.mutate()} disabled={generate.isPending}>
                  {generate.isPending ? 'Generating…' : '✦ Generate AI Explanation'}
                </Button>
              </div>
            )}
          </Card>

          {/* Triage */}
          <Card title="Review Decision">
            <p className="mb-4 text-sm text-gray-500">
              Choose what to do with this issue. Your decision is recorded in the audit trail.
            </p>
            <div className="grid grid-cols-2 gap-2">
              {DISPOSITIONS.map((d) => (
                <button
                  key={d.key}
                  onClick={() => triage.mutate(d.key)}
                  disabled={triage.isPending}
                  className="rounded-xl border border-gray-200 bg-white p-3 text-left transition hover:border-black hover:shadow-sm disabled:opacity-40"
                >
                  <p className="text-sm font-bold text-black">{d.label}</p>
                  <p className="text-xs text-gray-500">{d.desc}</p>
                </button>
              ))}
            </div>
          </Card>

          {/* Resolution */}
          <Card title="Resolution">
            {data.resolution ? (
              <div className="space-y-2 text-sm">
                <p className="font-bold text-black">{data.resolution.suggested_action}</p>
                <p className="text-gray-600">{data.resolution.rationale}</p>
                <p className="text-xs text-gray-400">
                  Approved by {data.resolution.approved_by} ({humanise(data.resolution.source)}) ·{' '}
                  {formatDate(data.resolution.approved_at)}
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-gray-500">
                  Document the agreed resolution. Every resolution requires human approval.
                </p>
                <div>
                  <label className="text-xs font-bold uppercase tracking-widest text-gray-400">
                    Suggested action
                  </label>
                  <textarea
                    value={action}
                    onChange={(e) => setAction(e.target.value)}
                    rows={2}
                    placeholder="What should be done to fix this issue?"
                    className="mt-1 w-full rounded-xl border border-gray-200 p-3 text-sm focus:border-black focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase tracking-widest text-gray-400">
                    Rationale
                  </label>
                  <textarea
                    value={rationale}
                    onChange={(e) => setRationale(e.target.value)}
                    rows={3}
                    placeholder="Why is this the right course of action?"
                    className="mt-1 w-full rounded-xl border border-gray-200 p-3 text-sm focus:border-black focus:outline-none"
                  />
                </div>
                <Button
                  variant="primary"
                  onClick={() => approve.mutate()}
                  disabled={approve.isPending || !action.trim() || !rationale.trim()}
                >
                  {approve.isPending ? 'Saving…' : 'Approve Resolution'}
                </Button>
              </div>
            )}
          </Card>

          {/* Assignment */}
          <Card title="Assign to Team">
            {data.assignment ? (
              <div className="text-sm">
                <p className="font-bold text-black">{data.assignment.queue_name}</p>
                <p className="text-gray-500">
                  {humanise(data.assignment.owner_type)}
                  {data.assignment.assigned_to ? ` · ${data.assignment.assigned_to}` : ''}
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-gray-500">Route this issue to the right team.</p>
                <div className="flex flex-wrap gap-2">
                  <Button onClick={() => assign.mutate(undefined)} disabled={assign.isPending}>
                    Auto-route
                  </Button>
                  {queues.data?.map((q) => (
                    <Button key={q.id} onClick={() => assign.mutate(q.id)} disabled={assign.isPending}>
                      {q.name}
                    </Button>
                  ))}
                </div>
              </div>
            )}
          </Card>

          {/* Status transitions */}
          {data.allowed_transitions?.length > 0 && (
            <Card title="Change Status">
              <div className="flex flex-wrap gap-2">
                {data.allowed_transitions.map((s) => (
                  <Button key={s} onClick={() => transition.mutate(s)} disabled={transition.isPending}>
                    {humanise(s)}
                  </Button>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
