import type { AIExplanation, FindingEvidence, Transparency } from '../api/types'
import { Card, formatDate, humanise } from './primitives'

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[11rem_1fr] gap-3 border-b border-[var(--color-line)] py-2 last:border-0">
      <dt className="text-xs uppercase tracking-wide text-[var(--color-muted)]">{label}</dt>
      <dd className="text-sm break-words">{children}</dd>
    </div>
  )
}

/**
 * Renders the FR-006 transparency payload: rule ID, records evaluated, evidence
 * references, timestamp, and audit outcome — plus which of those are missing.
 */
export function TransparencyPanel({ transparency }: { transparency: Transparency }) {
  return (
    <Card title="Audit transparency (FR-006)">
      {!transparency.complete && (
        <div className="mb-3 rounded-md bg-yellow-50 px-3 py-2 text-sm text-yellow-900 ring-1 ring-inset ring-yellow-200">
          <p className="font-medium">Non-actionable: transparency fields incomplete.</p>
          <p className="mt-1 text-xs">
            Missing {transparency.missing_fields.map(humanise).join(', ')}. This finding cannot be
            accepted until its transparency payload is complete.
          </p>
        </div>
      )}

      <dl>
        <Field label="Rule ID">
          <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">{transparency.rule_id}</code>
        </Field>
        <Field label="Rule pack">{transparency.rule_pack_version ?? '—'}</Field>
        <Field label="Records evaluated">
          {transparency.records_evaluated.length
            ? transparency.records_evaluated.join(', ')
            : '—'}
        </Field>
        <Field label="Evidence references">{transparency.evidence_refs.length}</Field>
        <Field label="Detected at">{formatDate(transparency.detected_at)}</Field>
        <Field label="Audit outcome">{humanise(transparency.audit_outcome)}</Field>
        <Field label="AI rationale">
          {transparency.ai_rationale_present ? 'Present' : 'Not generated'}
        </Field>
        <Field label="Confidence context">{transparency.ai_confidence_context ?? '—'}</Field>
        <Field label="Replay artifact">
          {transparency.replay_artifact_path ? (
            <code className="text-xs">{transparency.replay_artifact_path}</code>
          ) : (
            '—'
          )}
        </Field>
      </dl>
    </Card>
  )
}

export function EvidenceTable({ evidence }: { evidence: FindingEvidence[] }) {
  if (!evidence.length) {
    return (
      <Card title="Evidence">
        <p className="text-sm text-[var(--color-muted)]">No evidence records attached.</p>
      </Card>
    )
  }

  return (
    <Card title={`Evidence (${evidence.length})`}>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs uppercase tracking-wide text-[var(--color-muted)]">
            <tr>
              <th className="py-2 pr-3">Record</th>
              <th className="py-2 pr-3">Type</th>
              <th className="py-2 pr-3">Status</th>
              <th className="py-2 pr-3">State</th>
              <th className="py-2">Kind</th>
            </tr>
          </thead>
          <tbody>
            {evidence.map((item) => (
              <tr key={item.id} className="border-t border-[var(--color-line)]">
                <td className="py-2 pr-3 font-mono text-xs">{item.record_external_id ?? '—'}</td>
                <td className="py-2 pr-3">{item.resource_type ?? '—'}</td>
                <td className="py-2 pr-3">{item.status_value ?? '—'}</td>
                <td className="py-2 pr-3">{item.status_state ?? '—'}</td>
                <td className="py-2 text-xs text-[var(--color-muted)]">
                  {humanise(item.evidence_type)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

/** FR-007 / FR-011: AI text always ships with its disclaimer visible. */
export function AiExplanationCard({
  explanation,
  onGenerate,
  pending,
}: {
  explanation: AIExplanation | null
  onGenerate: () => void
  pending: boolean
}) {
  if (!explanation) {
    return (
      <Card title="AI rationale (FR-007)">
        <p className="text-sm text-[var(--color-muted)]">
          No explanation has been generated for this finding.
        </p>
        <button
          onClick={onGenerate}
          disabled={pending}
          className="mt-3 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:bg-slate-400"
        >
          {pending ? 'Generating…' : 'Generate explanation'}
        </button>
      </Card>
    )
  }

  return (
    <Card title="AI rationale (FR-007)">
      <div className="mb-3 rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-700 ring-1 ring-inset ring-slate-200">
        {explanation.disclaimer}
      </div>

      {explanation.low_confidence && (
        <div className="mb-3 rounded-md bg-yellow-50 px-3 py-2 text-xs text-yellow-900 ring-1 ring-inset ring-yellow-200">
          Low confidence — the model's response could not be fully parsed. A resolution must be
          written or edited manually.
        </div>
      )}

      <p className="text-sm whitespace-pre-wrap">{explanation.rationale_text}</p>

      {explanation.confidence_context && (
        <div className="mt-3">
          <p className="text-xs uppercase tracking-wide text-[var(--color-muted)]">
            Confidence context
          </p>
          <p className="mt-1 text-sm whitespace-pre-wrap">{explanation.confidence_context}</p>
        </div>
      )}

      {explanation.evidence?.narrative && (
        <div className="mt-3">
          <p className="text-xs uppercase tracking-wide text-[var(--color-muted)]">
            Evidence synthesis
          </p>
          <p className="mt-1 text-sm whitespace-pre-wrap">{explanation.evidence.narrative}</p>
        </div>
      )}

      <p className="mt-3 text-xs text-[var(--color-muted)]">
        {explanation.model_name} · prompt {explanation.prompt_version} ·{' '}
        {formatDate(explanation.created_at)}
      </p>
    </Card>
  )
}
