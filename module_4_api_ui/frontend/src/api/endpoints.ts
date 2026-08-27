import { api } from './client'
import type {
  AIExplanation,
  AssignmentOut,
  AuditRun,
  BatchDetail,
  BatchIngestResponse,
  BatchSummary,
  EvidenceBundle,
  ExplanationJob,
  FindingDetail,
  FindingStats,
  FindingSummary,
  HealthOut,
  NormalizedResource,
  Page,
  QueueOut,
  ResolutionOut,
  RulePackOut,
  Sample,
} from './types'

export const endpoints = {
  // Health
  health: () => api.get<HealthOut>('/health'),

  // Batches
  uploadBatchFile: (file: File) => api.upload<BatchIngestResponse>('/batches/upload', file),
  listBatches: (page = 1) => api.get<Page<BatchSummary>>(`/batches?page=${page}&page_size=25`),
  getBatch: (id: number) => api.get<BatchDetail>(`/batches/${id}`),
  listBatchResources: (batchId: number, page = 1) =>
    api.get<Page<NormalizedResource>>(`/batches/${batchId}/resources?page=${page}&page_size=50`),

  // Audit runs
  createAuditRun: (batchId: number) =>
    api.post<AuditRun>('/audit-runs', { batch_id: batchId, rule_pack_version: null }),
  listAuditRuns: (page = 1) =>
    api.get<Page<AuditRun>>(`/audit-runs?page=${page}&page_size=25`),

  // Findings
  listFindings: (filters: {
    audit_run_id?: number
    batch_id?: number
    severity?: string[]
    finding_type?: string[]
    status?: string[]
    open_only?: boolean
    search?: string
    queue_id?: number
    page?: number
  }) => {
    const p = new URLSearchParams()
    if (filters.audit_run_id != null) p.set('audit_run_id', String(filters.audit_run_id))
    if (filters.batch_id != null) p.set('batch_id', String(filters.batch_id))
    if (filters.queue_id != null) p.set('queue_id', String(filters.queue_id))
    if (filters.open_only) p.set('open_only', 'true')
    if (filters.search) p.set('search', filters.search)
    filters.severity?.forEach((s) => p.append('severity', s))
    filters.finding_type?.forEach((t) => p.append('finding_type', t))
    filters.status?.forEach((s) => p.append('status', s))
    p.set('page', String(filters.page ?? 1))
    p.set('page_size', '25')
    return api.get<Page<FindingSummary>>(`/findings?${p.toString()}`)
  },
  findingStats: () => api.get<FindingStats>('/findings/stats'),
  getFinding: (id: number) => api.get<FindingDetail>(`/findings/${id}`),
  triageFinding: (id: number, disposition: string, notes?: string) =>
    api.post<FindingDetail>(`/findings/${id}/triage`, { disposition, notes }),
  transitionFinding: (id: number, toStatus: string, notes?: string) =>
    api.post<FindingDetail>(`/findings/${id}/status`, { to_status: toStatus, notes }),

  // AI Explanations
  generateExplanation: (id: number, forceRefresh = false) =>
    api.post<AIExplanation | ExplanationJob>(`/findings/${id}/explanation`, {
      force_refresh: forceRefresh,
    }),
  getExplanation: (id: number) =>
    api.get<AIExplanation | ExplanationJob | null>(`/findings/${id}/explanation`),

  // Resolution
  approveResolution: (
    id: number,
    payload: { suggested_action: string; rationale: string; source: string },
  ) => api.put<ResolutionOut>(`/findings/${id}/resolution`, payload),
  assignFinding: (id: number, queueId?: number, assignedTo?: string) =>
    api.post<AssignmentOut>(`/findings/${id}/assignment`, {
      queue_id: queueId ?? null,
      assigned_to: assignedTo ?? null,
    }),

  // Catalog
  listRulePacks: () => api.get<RulePackOut[]>('/rule-packs'),
  listQueues: () => api.get<QueueOut[]>('/queues'),

  // Compliance
  selectSample: (payload: { sample_size: number; seed: number }) =>
    api.post<Sample>('/compliance/samples', payload),
  exportBundle: (findingIds: number[], includeSnapshots = true) =>
    api.post<EvidenceBundle>('/compliance/exports', {
      finding_ids: findingIds,
      include_replay_snapshots: includeSnapshots,
    }),
}
