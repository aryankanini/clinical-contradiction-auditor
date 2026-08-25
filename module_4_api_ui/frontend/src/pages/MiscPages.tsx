import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { endpoints } from '../api/endpoints'
import type { EvidenceBundle, Sample } from '../api/types'
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  Loading,
  formatDate,
  humanise,
} from '../components/primitives'
import { useRole } from '../hooks/useRole'

export function QueuesPage() {
  const queues = useQuery({ queryKey: ['queues'], queryFn: endpoints.listQueues })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Resolution queues</h2>
        <p className="text-sm text-[var(--color-muted)]">
          Mixed-ownership routing across stewardship, informatics, operations, and governance.
        </p>
      </div>

      {queues.isLoading && <Loading />}
      {queues.error && <ErrorState error={queues.error} />}
      <div className="grid gap-4 lg:grid-cols-2">
        {queues.data?.map((queue) => (
          <Card key={queue.id} title={queue.name}>
            <p className="text-sm text-[var(--color-muted)]">Owner: {queue.owner_type}</p>
            <p className="mt-2 text-2xl font-semibold">{queue.open_count}</p>
            <p className="text-xs text-[var(--color-muted)]">open findings</p>
            <Link
              to={`/findings?queue_id=${queue.id}`}
              className="mt-3 inline-block text-sm hover:underline"
            >
              View worklist
            </Link>
          </Card>
        ))}
      </div>
      {queues.data && !queues.data.length && <EmptyState message="No queues configured." />}
    </div>
  )
}

export function RulePacksPage() {
  const packs = useQuery({ queryKey: ['rule-packs'], queryFn: endpoints.listRulePacks })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Rule packs</h2>
        <p className="text-sm text-[var(--color-muted)]">
          Read-only. Authoring and publishing rule versions belongs to the audit-engine module.
        </p>
      </div>

      {packs.isLoading && <Loading />}
      {packs.data?.map((pack) => (
        <Card key={pack.id} title={pack.version}>
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <span>{humanise(pack.status)}</span>
            <span className="text-[var(--color-muted)]">
              published {formatDate(pack.published_at)}
            </span>
            <span className="text-[var(--color-muted)]">{pack.rule_count} rule(s)</span>
            {pack.is_placeholder && (
              <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">
                placeholder metadata
              </span>
            )}
          </div>
        </Card>
      ))}
      {packs.data && !packs.data.length && <EmptyState message="No rule packs published." />}
    </div>
  )
}

export function CompliancePage() {
  const { role } = useRole()
  const [sample, setSample] = useState<Sample | null>(null)
  const [bundle, setBundle] = useState<EvidenceBundle | null>(null)
  const [seed, setSeed] = useState(20260816)
  const [size, setSize] = useState(5)

  const select = useMutation({
    mutationFn: () => endpoints.selectSample({ sample_size: size, seed }),
    onSuccess: setSample,
  })

  const exportBundle = useMutation({
    mutationFn: () => endpoints.exportBundle(sample?.finding_ids ?? []),
    onSuccess: setBundle,
  })

  if (role !== 'compliance') {
    return (
      <Card title="Compliance export">
        <p className="text-sm text-[var(--color-muted)]">
          Switch to the <strong>compliance</strong> role to select samples and export evidence
          bundles.
        </p>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Compliance evidence</h2>
        <p className="text-sm text-[var(--color-muted)]">
          Sampling is seeded, so the same criteria always reproduce the same set of findings.
        </p>
      </div>

      <Card title="Select sample">
        <div className="flex flex-wrap items-end gap-4">
          <label className="text-sm">
            <span className="block text-xs uppercase tracking-wide text-[var(--color-muted)]">
              Sample size
            </span>
            <input
              type="number"
              min={1}
              value={size}
              onChange={(event) => setSize(Number(event.target.value))}
              className="mt-1 w-24 rounded-md border border-[var(--color-line)] px-2 py-1"
            />
          </label>
          <label className="text-sm">
            <span className="block text-xs uppercase tracking-wide text-[var(--color-muted)]">
              Seed
            </span>
            <input
              type="number"
              value={seed}
              onChange={(event) => setSeed(Number(event.target.value))}
              className="mt-1 w-36 rounded-md border border-[var(--color-line)] px-2 py-1"
            />
          </label>
          <Button variant="primary" onClick={() => select.mutate()} disabled={select.isPending}>
            Draw sample
          </Button>
        </div>
        {select.error && (
          <div className="mt-3">
            <ErrorState error={select.error} />
          </div>
        )}
      </Card>

      {sample && (
        <Card
          title={`Sample ${sample.sample_id}`}
          action={
            <Button onClick={() => exportBundle.mutate()} disabled={exportBundle.isPending}>
              {exportBundle.isPending ? 'Exporting…' : 'Export evidence bundle'}
            </Button>
          }
        >
          <p className="text-sm">
            {sample.finding_ids.length} of {sample.candidate_count} candidate finding(s) selected.
          </p>
          <ul className="mt-3 space-y-1 text-sm">
            {sample.finding_ids.map((id) => (
              <li key={id}>
                <Link to={`/findings/${id}`} className="hover:underline">
                  Finding #{id}
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {bundle && (
        <Card title="Reproducibility (FR-012)">
          <p className="mb-3 text-xs text-[var(--color-muted)]">
            Written to {bundle.export_path ?? 'response only'}
          </p>
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-[var(--color-muted)]">
              <tr>
                <th className="py-2">Finding</th>
                <th className="py-2">Rule pack</th>
                <th className="py-2">Snapshots</th>
                <th className="py-2">Reproducible</th>
              </tr>
            </thead>
            <tbody>
              {bundle.items.map((item) => (
                <tr key={item.finding.id} className="border-t border-[var(--color-line)]">
                  <td className="py-2">#{item.finding.id}</td>
                  <td className="py-2">{item.rule_pack_version ?? '—'}</td>
                  <td className="py-2">{item.replay_snapshots.length}</td>
                  <td className="py-2">
                    {item.reproducibility.reproducible ? (
                      <span className="text-[var(--color-good)]">yes</span>
                    ) : (
                      <span className="text-[var(--color-critical)]">
                        no — {item.reproducibility.missing_artifacts.join(', ')}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}

export function NotFoundPage() {
  return <EmptyState message="Page not found." />
}
