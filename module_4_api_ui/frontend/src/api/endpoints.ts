import { api, buildQuery } from './client'
import type {
  AIExplanation,
  AuditRun,
  AuditRunDetail,
  BatchDetail,
  BatchIngestResponse,
  BatchSummary,
  EvidenceBundle,
  ExplanationJob,
  FindingDetail,
  FindingStats,
  FindingSummary,
  Health,
  NormalizedResource,
  Page,
  Queue,
  Reproducibility,
  Resolution,
  RulePack,
  Sample,
} from './types'

export interface FindingFilters {
  audit_run_id?: number
  batch_id?: number
  status?: string[]
  severity?: string[]
  priority?: string[]
  finding_type?: string[]
  rule_id?: string
  queue_id?: number
  open_only?: boolean
  search?: string
  page?: number
  page_size?: number
}

export const endpoints = {
  health: () => api.get<Health>('/health'),

  listBatches: (params: { page?: number; page_size?: number; source?: string } = {}) =>
    api.get<Page<BatchSummary>>(`/batches${buildQuery(params)}`),
  getBatch: (id: number) => api.get<BatchDetail>(`/batches/${id}`),
  listBatchResources: (id: number, params: { page?: number; resource_type?: string } = {}) =>
    api.get<Page<NormalizedResource>>(`/batches/${id}/resources${buildQuery(params)}`),
  ingestBatch: (payload: unknown) => api.post<BatchIngestResponse>('/batches', payload),
  uploadBatch: (file: File) => api.upload<BatchIngestResponse>('/batches/upload', file),

  listAuditRuns: (params: { batch_id?: number; page?: number } = {}) =>
    api.get<Page<AuditRun>>(`/audit-runs${buildQuery(params)}`),
  getAuditRun: (id: number) => api.get<AuditRunDetail>(`/audit-runs/${id}`),
  createAuditRun: (batchId: number, rulePackVersion?: string) =>
    api.post<AuditRun>('/audit-runs', {
      batch_id: batchId,
      rule_pack_version: rulePackVersion ?? null,
    }),

  listFindings: (filters: FindingFilters = {}) =>
    api.get<Page<FindingSummary>>(`/findings${buildQuery(filters as Record<string, unknown>)}`),
  getFinding: (id: number) => api.get<FindingDetail>(`/findings/${id}`),
  findingStats: () => api.get<FindingStats>('/findings/stats'),
  triageFinding: (id: number, disposition: string, notes?: string) =>
    api.post<FindingDetail>(`/findings/${id}/triage`, { disposition, notes: notes ?? null }),
  transitionFinding: (id: number, toStatus: string, notes?: string) =>
    api.post<FindingDetail>(`/findings/${id}/status`, { to_status: toStatus, notes: notes ?? null }),

  generateExplanation: (id: number, forceRefresh = false) =>
    api.post<AIExplanation | ExplanationJob>(`/findings/${id}/explanation`, {
      force_refresh: forceRefresh,
    }),
  getExplanation: (id: number) =>
    api.get<AIExplanation | ExplanationJob | null>(`/findings/${id}/explanation`),

  getResolution: (id: number) => api.get<Resolution | null>(`/findings/${id}/resolution`),
  getResolutionDraft: (id: number) =>
    api.get<Record<string, unknown> | null>(`/findings/${id}/resolution/draft`),
  approveResolution: (
    id: number,
    payload: { suggested_action: string; rationale: string; source: string; notes?: string },
  ) => api.put<Resolution>(`/findings/${id}/resolution`, payload),
  assignFinding: (id: number, queueId?: number, assignedTo?: string) =>
    api.post(`/findings/${id}/assignment`, {
      queue_id: queueId ?? null,
      assigned_to: assignedTo ?? null,
    }),

  listQueues: () => api.get<Queue[]>('/queues'),
  listQueueFindings: (queueId: number) =>
    api.get<Page<FindingSummary>>(`/queues/${queueId}/findings`),
  listRulePacks: () => api.get<RulePack[]>('/rule-packs'),

  selectSample: (payload: Record<string, unknown>) =>
    api.post<Sample>('/compliance/samples', payload),
  checkReproducibility: (id: number) =>
    api.get<Reproducibility>(`/compliance/findings/${id}/reproducibility`),
  recordVerification: (id: number, outcome: string, notes?: string) =>
    api.post(`/compliance/findings/${id}/verification`, { outcome, notes: notes ?? null }),
  exportBundle: (findingIds: number[]) =>
    api.post<EvidenceBundle>('/compliance/exports', {
      finding_ids: findingIds,
      include_replay_snapshots: true,
    }),
}
