import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'

import { endpoints } from '../api/endpoints'
import type { AIExplanation, FindingDetail } from '../api/types'
import {
  AiExplanationCard,
  EvidenceTable,
  TransparencyPanel,
} from '../components/TransparencyPanel'
import {
  Button,
  Card,
  ErrorState,
  Loading,
  PriorityBadge,
  SeverityBadge,
  StatusBadge,
  formatDate,
  humanise,
} from '../components/primitives'

const DISPOSITIONS = [
  { key: 'accept', label: 'Accept' },
  { key: 'escalate', label: 'Escalate' },
  { key: 'defer', label: 'Defer' },
  { key: 'dispute', label: 'Dispute' },
]

function isExplanation(value: unknown): value is AIExplanation {
  return Boolean(value && typeof value === 'object' && 'rationale_text' in value)
}

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
    // Generation runs in the background, so poll until a stored explanation appears
    // or the job reports failure.
    refetchInterval: (query) => {
      const value = query.state.data
      if (!value) return false
      if (isExplanation(value)) return false
      return value.state === 'pending' || value.state === 'running' ? 2000 : false
    },
  })

  const stored = isExplanation(explanation.data) ? explanation.data : null

  // Pre-fill the editor from the model's draft; any edit flips the recorded source.
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

  const onError = (error: unknown) => {
    setActionError(error instanceof Error ? error.message : 'Action failed.')
  }

  const triage = useMutation({
    mutationFn: (disposition: string) => endpoints.triageFinding(id, disposition),
    onSuccess: () => {
      setActionError(null)
      invalidate()
    },
    onError,
  })

  const transition = useMutation({
    mutationFn: (status: string) => endpoints.transitionFinding(id, status),
    onSuccess: () => {
      setActionError(null)
      invalidate()
    },
    onError,
  })

  const generate = useMutation({
    mutationFn: () => endpoints.generateExplanation(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['explanation', id] })
    },
    onError,
  })

  const approve = useMutation({
    mutationFn: () => {
      const draft = stored?.resolution_draft
      const unchanged =
        draft && draft.suggested_action === action && draft.rationale === rationale
      const source = draft ? (unchanged ? 'ai' : 'ai_edited') : 'manual'
      return endpoints.approveResolution(id, {
        suggested_action: action,
        rationale,
        source,
      })
    },
    onSuccess: () => {
      setActionError(null)
      invalidate()
    },
    onError,
  })

  const assign = useMutation({
    mutationFn: (queueId?: number) => endpoints.assignFinding(id, queueId),
    onSuccess: () => {
      setActionError(null)
      invalidate()
    },
    onError,
  })

  if (finding.isLoading) return <Loading />
  if (finding.error) return <ErrorState error={finding.error} />
  if (!finding.data) return null

  const data: FindingDetail = finding.data

  return (
    <div className="space-y-6">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <SeverityBadge severity={data.severity} />
          <PriorityBadge priority={data.priority} />
          <StatusBadge status={data.status} />
          <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">{data.rule_id}</code>
          <span className="text-xs text-[var(--color-muted)]">
            {humanise(data.finding_type)}
          </span>
        </div>
        <h2 className="mt-2 text-lg font-semibold">{data.summary}</h2>
        <p className="text-sm text-[var(--color-muted)]">
          Detected {formatDate(data.created_at)} · run #{data.audit_run_id}
        </p>
      </div>

      {actionError && <ErrorState error={new Error(actionError)} />}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <TransparencyPanel transparency={data.transparency} />
          <EvidenceTable evidence={data.evidence} />
        </div>

        <div className="space-y-6">
          <AiExplanationCard
            explanation={stored}
            onGenerate={() => generate.mutate()}
            pending={generate.isPending || explanation.isFetching}
          />

          <Card title="Triage (UC-002)">
            <div className="flex flex-wrap gap-2">
              {DISPOSITIONS.map((item) => (
                <Button
                  key={item.key}
                  onClick={() => triage.mutate(item.key)}
                  disabled={triage.isPending}
                >
                  {item.label}
                </Button>
              ))}
            </div>
            <p className="mt-3 text-xs text-[var(--color-muted)]">
              Accepting requires a complete transparency payload. Disputes route to informatics
              review without altering the deterministic record.
            </p>
          </Card>

          <Card title="Resolution (UC-003)">
            {data.resolution ? (
              <div className="space-y-2 text-sm">
                <p className="font-medium">{data.resolution.suggested_action}</p>
                <p className="text-[var(--color-muted)]">{data.resolution.rationale}</p>
                <p className="text-xs text-[var(--color-muted)]">
                  Approved by {data.resolution.approved_by} ({data.resolution.source}) ·{' '}
                  {formatDate(data.resolution.approved_at)}
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <div>
                  <label className="text-xs uppercase tracking-wide text-[var(--color-muted)]">
                    Suggested action
                  </label>
                  <textarea
                    value={action}
                    onChange={(event) => setAction(event.target.value)}
                    rows={2}
                    className="mt-1 w-full rounded-md border border-[var(--color-line)] p-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs uppercase tracking-wide text-[var(--color-muted)]">
                    Rationale
                  </label>
                  <textarea
                    value={rationale}
                    onChange={(event) => setRationale(event.target.value)}
                    rows={3}
                    className="mt-1 w-full rounded-md border border-[var(--color-line)] p-2 text-sm"
                  />
                </div>
                <Button
                  variant="primary"
                  onClick={() => approve.mutate()}
                  disabled={approve.isPending || !action.trim() || !rationale.trim()}
                >
                  Approve resolution
                </Button>
                <p className="text-xs text-[var(--color-muted)]">
                  Every resolution requires human approval before a finding can enter remediation.
                </p>
              </div>
            )}
          </Card>

          <Card title="Assignment (FR-010)">
            {data.assignment ? (
              <p className="text-sm">
                {data.assignment.queue_name}
                <span className="text-[var(--color-muted)]">
                  {' '}
                  ({data.assignment.owner_type})
                  {data.assignment.assigned_to ? ` · ${data.assignment.assigned_to}` : ''}
                </span>
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => assign.mutate(undefined)} disabled={assign.isPending}>
                  Auto-route
                </Button>
                {queues.data?.map((queue) => (
                  <Button key={queue.id} onClick={() => assign.mutate(queue.id)}>
                    {queue.name}
                  </Button>
                ))}
              </div>
            )}
          </Card>

          {data.allowed_transitions.length > 0 && (
            <Card title="Advance status">
              <div className="flex flex-wrap gap-2">
                {data.allowed_transitions.map((status) => (
                  <Button
                    key={status}
                    onClick={() => transition.mutate(status)}
                    disabled={transition.isPending}
                  >
                    {humanise(status)}
                  </Button>
                ))}
              </div>
            </Card>
          )}

          <Card title="Audit trail (FR-012)">
            <ol className="space-y-2 text-sm">
              {data.status_history.map((row) => (
                <li key={row.id} className="flex items-baseline justify-between gap-3">
                  <span>
                    {row.from_status ? `${humanise(row.from_status)} → ` : ''}
                    <strong>{humanise(row.to_status)}</strong>
                    {row.notes && (
                      <span className="text-[var(--color-muted)]"> — {row.notes}</span>
                    )}
                  </span>
                  <span className="shrink-0 text-xs text-[var(--color-muted)]">
                    {row.changed_by} · {formatDate(row.changed_at)}
                  </span>
                </li>
              ))}
            </ol>
          </Card>
        </div>
      </div>
    </div>
  )
}
