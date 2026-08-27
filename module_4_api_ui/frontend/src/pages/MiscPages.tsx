import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { endpoints } from '../api/endpoints'
import type { EvidenceBundle, Sample } from '../api/types'
import {
  Button, Card, EmptyState, ErrorState, Loading, Table, Tr, Td,
  formatDate, humanise,
} from '../components/primitives'
import { useRole } from '../hooks/useRole'

// ── Work Queues ───────────────────────────────────────────────────────────────

export function QueuesPage() {
  const queues = useQuery({ queryKey: ['queues'], queryFn: endpoints.listQueues })

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-black text-black">Work Queues</h2>
        <p className="mt-1 text-sm text-gray-500">
          Issues are automatically routed to the right team based on their type. Each queue shows how many open issues need attention.
        </p>
      </div>

      {queues.isLoading && <Loading />}
      {queues.error && <ErrorState error={queues.error} />}

      <div className="grid gap-4 lg:grid-cols-2">
        {queues.data?.map((queue) => (
          <div
            key={queue.id}
            className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-gray-400">
                  {humanise(queue.owner_type)}
                </p>
                <h3 className="mt-1 text-lg font-black text-black capitalize">{queue.name}</h3>
              </div>
              <div className="text-right">
                <p className="text-3xl font-black text-black">{queue.open_count}</p>
                <p className="text-xs text-gray-500">open issues</p>
              </div>
            </div>
            <div className="mt-4">
              <Link
                to={`/findings?queue_id=${queue.id}`}
                className="inline-block rounded-xl border border-gray-200 px-4 py-2 text-sm font-semibold text-black transition hover:border-black hover:bg-black hover:text-white"
              >
                View worklist →
              </Link>
            </div>
          </div>
        ))}
      </div>

      {queues.data && !queues.data.length && (
        <EmptyState message="No queues configured." />
      )}
    </div>
  )
}

// ── Audit Rules ───────────────────────────────────────────────────────────────

export function RulePacksPage() {
  const packs = useQuery({ queryKey: ['rule-packs'], queryFn: endpoints.listRulePacks })

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-black text-black">Audit Rules</h2>
        <p className="mt-1 text-sm text-gray-500">
          These are the rules the system uses to detect data quality issues. Each rule pack is a versioned set of checks applied to patient records.
        </p>
      </div>

      {packs.isLoading && <Loading />}
      {packs.error && <ErrorState error={packs.error} />}

      <div className="space-y-4">
        {packs.data?.map((pack) => (
          <Card key={pack.id}>
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-3">
                  <h3 className="text-lg font-black text-black">Version {pack.version}</h3>
                  <span className={`rounded-full border px-2.5 py-0.5 text-xs font-bold ${
                    pack.status === 'ACTIVE'
                      ? 'border-green-200 bg-green-100 text-green-800'
                      : 'border-gray-200 bg-gray-100 text-gray-600'
                  }`}>
                    {pack.status}
                  </span>
                  {pack.is_placeholder && (
                    <span className="rounded-full border border-orange-200 bg-orange-100 px-2.5 py-0.5 text-xs font-bold text-orange-800">
                      Placeholder
                    </span>
                  )}
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  {pack.rule_count} rule{pack.rule_count !== 1 ? 's' : ''} ·{' '}
                  Published {formatDate(pack.published_at)}
                </p>
              </div>
            </div>

            {Array.isArray((pack.metadata as Record<string, unknown>)?.rules) && (
              <div className="mt-4">
                <p className="mb-2 text-xs font-bold uppercase tracking-widest text-gray-400">Rules in this pack</p>
                <div className="flex flex-wrap gap-2">
                  {((pack.metadata as Record<string, unknown>).rules as Array<{ rule_id: string; type: string }>)
                    .slice(0, 12)
                    .map((r) => (
                      <span
                        key={r.rule_id}
                        className="rounded-lg border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs font-mono font-semibold text-gray-700"
                        title={r.type}
                      >
                        {r.rule_id}
                      </span>
                    ))}
                  {((pack.metadata as Record<string, unknown>).rules as unknown[]).length > 12 && (
                    <span className="rounded-lg border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs text-gray-500">
                      +{((pack.metadata as Record<string, unknown>).rules as unknown[]).length - 12} more
                    </span>
                  )}
                </div>
              </div>
            )}
          </Card>
        ))}
      </div>

      {packs.data && !packs.data.length && (
        <EmptyState message="No rule packs published yet." />
      )}
    </div>
  )
}

// ── Compliance ────────────────────────────────────────────────────────────────

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
      <div className="space-y-8">
        <div>
          <h2 className="text-2xl font-black text-black">Compliance</h2>
        </div>
        <Card>
          <div className="py-6 text-center">
            <p className="text-4xl">🔒</p>
            <p className="mt-3 text-sm font-semibold text-black">Compliance role required</p>
            <p className="mt-1 text-sm text-gray-500">
              Switch to the <strong>compliance</strong> role using the selector in the top-right corner to access this section.
            </p>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-black text-black">Compliance Export</h2>
        <p className="mt-1 text-sm text-gray-500">
          Draw a reproducible random sample of findings for external audit review and export a full evidence bundle.
        </p>
      </div>

      <Card title="Select a Sample">
        <p className="mb-4 text-sm text-gray-500">
          Choose how many findings to sample and a seed number. Using the same seed always produces the same sample — useful for reproducible audits.
        </p>
        <div className="flex flex-wrap items-end gap-4">
          <label className="text-sm">
            <span className="block text-xs font-bold uppercase tracking-widest text-gray-400">
              Sample size
            </span>
            <input
              type="number"
              min={1}
              value={size}
              onChange={(e) => setSize(Number(e.target.value))}
              className="mt-1 w-24 rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-black focus:outline-none"
            />
          </label>
          <label className="text-sm">
            <span className="block text-xs font-bold uppercase tracking-widest text-gray-400">
              Seed (for reproducibility)
            </span>
            <input
              type="number"
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value))}
              className="mt-1 w-36 rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-black focus:outline-none"
            />
          </label>
          <Button variant="primary" onClick={() => select.mutate()} disabled={select.isPending}>
            {select.isPending ? 'Drawing…' : 'Draw Sample'}
          </Button>
        </div>
        {select.error && <div className="mt-3"><ErrorState error={select.error} /></div>}
      </Card>

      {sample && (
        <Card
          title={`Sample ${sample.sample_id}`}
          action={
            <Button onClick={() => exportBundle.mutate()} disabled={exportBundle.isPending} variant="primary">
              {exportBundle.isPending ? 'Exporting…' : '↓ Export Evidence Bundle'}
            </Button>
          }
        >
          <p className="mb-4 text-sm text-gray-600">
            {sample.finding_ids.length} finding(s) selected from {sample.candidate_count} candidates.
          </p>
          <div className="flex flex-wrap gap-2">
            {sample.finding_ids.map((fid) => (
              <Link
                key={fid}
                to={`/findings/${fid}`}
                className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-sm font-semibold text-black hover:border-black"
              >
                Finding #{fid}
              </Link>
            ))}
          </div>
        </Card>
      )}

      {bundle && (
        <Card title="Exported Evidence Bundle">
          {bundle.export_path && (
            <p className="mb-4 text-xs text-gray-500">Saved to: {bundle.export_path}</p>
          )}
          <Table head={['Finding', 'Rule Pack', 'Snapshots', 'Reproducible']}>
            {bundle.items.map((item) => (
              <Tr key={item.finding.id}>
                <Td>
                  <Link to={`/findings/${item.finding.id}`} className="font-bold hover:underline">
                    #{item.finding.id}
                  </Link>
                </Td>
                <Td className="text-gray-600">{item.rule_pack_version ?? '—'}</Td>
                <Td className="font-semibold">{item.replay_snapshots.length}</Td>
                <Td>
                  {item.reproducibility.reproducible ? (
                    <span className="text-xs font-bold text-green-700">✓ Yes</span>
                  ) : (
                    <span className="text-xs font-bold text-red-600">
                      ✗ No — {item.reproducibility.missing_artifacts.join(', ')}
                    </span>
                  )}
                </Td>
              </Tr>
            ))}
          </Table>
        </Card>
      )}
    </div>
  )
}

// ── 404 ───────────────────────────────────────────────────────────────────────

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <p className="text-6xl font-black text-gray-200">404</p>
      <p className="mt-4 text-lg font-bold text-black">Page not found</p>
      <p className="mt-1 text-sm text-gray-500">The page you're looking for doesn't exist.</p>
      <Link to="/" className="mt-6 rounded-xl bg-black px-5 py-2.5 text-sm font-bold text-white hover:bg-gray-800">
        Go to Dashboard
      </Link>
    </div>
  )
}
