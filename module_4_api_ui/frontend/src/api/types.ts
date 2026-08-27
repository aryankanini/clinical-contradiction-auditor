export type Role = 'steward' | 'analyst' | 'compliance'

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface HealthOut {
  status: string
  database_reachable: boolean
  audit_engine: string
  audit_engine_is_placeholder: boolean
  ai_enabled: boolean
}

export interface BatchSummary {
  id: number
  batch_external_id: string
  source_system: string
  status: string
  accepted_count: number
  quarantined_count: number
  received_at: string
}

export interface AuditRunSummary {
  id: number
  rule_pack_version: string | null
  status: string
  started_at: string
}

export interface BatchDetail extends BatchSummary {
  rule_ready_count: number
  governed_signal_count: number
  resource_type_counts: Record<string, number>
  audit_runs: AuditRunSummary[]
}

export interface BatchIngestResponse {
  batch: BatchSummary
  ingest_status: string
  validation_errors: unknown[]
  quarantined_records: unknown[]
}

export interface NormalizedResource {
  id: number
  record_external_id: string
  resource_type: string
  status_value: string | null
  rule_ready: boolean
  incomplete_fields: string[]
  unresolved_links: string[]
}

export interface AuditRun {
  id: number
  batch_id: number
  batch_external_id: string | null
  rule_pack_version: string | null
  status: string
  started_at: string
  completed_at: string | null
  finding_count: number
}

export interface FindingSummary {
  id: number
  audit_run_id: number
  rule_id: string
  finding_type: string
  severity: string
  priority: string
  status: string
  summary: string
  audit_outcome: string
  created_at: string
  evidence_count: number
  has_explanation: boolean
}

export interface FindingEvidence {
  id: number
  evidence_type: string
  record_external_id: string | null
  resource_type: string | null
  status_value: string | null
  evidence_payload: Record<string, unknown>
}

export interface StatusHistoryRow {
  id: number
  from_status: string | null
  to_status: string
  changed_by: string | null
  changed_at: string
  notes: string | null
}

export interface AssignmentOut {
  queue_id: number
  queue_name: string
  owner_type: string
  assigned_to: string | null
  assigned_at: string
}

export interface ResolutionOut {
  suggested_action: string
  rationale: string
  source: string
  approved_by: string
  approved_at: string
}

export interface AIExplanation {
  id: number
  finding_id: number
  model_name: string
  rationale_text: string
  confidence_context: string
  evidence: {
    record_ids: string[]
    resource_types: string[]
    narrative: string
    field_references: string[]
  } | null
  resolution_draft: {
    suggested_action: string
    rationale: string
    requires_human_approval: boolean
    audit_only_note: string
  } | null
  created_at: string
  low_confidence: boolean
}

export interface ExplanationJob {
  finding_id: number
  state: 'pending' | 'running' | 'succeeded' | 'failed'
  started_at: string | null
  completed_at: string | null
  error: string | null
}

export interface FindingDetail extends FindingSummary {
  evidence: FindingEvidence[]
  status_history: StatusHistoryRow[]
  assignment: AssignmentOut | null
  resolution: ResolutionOut | null
  allowed_transitions: string[]
}

export interface FindingStats {
  total: number
  open_total: number
  by_severity: Record<string, number>
  by_status: Record<string, number>
  by_type: Record<string, number>
}

export interface RulePackOut {
  id: number
  version: string
  status: string
  published_at: string | null
  rule_count: number
  is_placeholder: boolean
  metadata: Record<string, unknown>
}

export interface QueueOut {
  id: number
  name: string
  owner_type: string
  config: Record<string, unknown>
  open_count: number
}

export interface Sample {
  sample_id: string
  finding_ids: number[]
  candidate_count: number
}

export interface EvidenceBundleItem {
  finding: FindingSummary
  rule_pack_version: string | null
  replay_snapshots: unknown[]
  reproducibility: { reproducible: boolean; missing_artifacts: string[] }
}

export interface EvidenceBundle {
  export_path: string | null
  items: EvidenceBundleItem[]
}
