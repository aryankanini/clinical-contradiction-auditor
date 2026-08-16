// Hand-written mirrors of the backend's pydantic schemas.

export type Role = 'steward' | 'analyst' | 'compliance'

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ApiErrorBody {
  error: string
  detail: string
  context: Record<string, unknown>
}

export interface Health {
  status: string
  database_reachable: boolean
  audit_engine: string
  audit_engine_is_placeholder: boolean
  ai_enabled: boolean
  audit_only_notice: string
}

export interface AuditRunSummary {
  id: number
  status: string
  started_at: string
  completed_at: string | null
  rule_pack_version: string | null
}

export interface BatchSummary {
  id: number
  batch_external_id: string
  source_system: string
  status: string
  received_at: string
  accepted_count: number
  quarantined_count: number
  loader_success_count: number
  loader_failure_count: number
  latest_audit_run: AuditRunSummary | null
}

export interface BatchDetail extends BatchSummary {
  provenance_artifact_path: string | null
  replay_artifact_path: string | null
  resource_type_counts: Record<string, number>
  rule_ready_count: number
  governed_signal_count: number
  audit_runs: AuditRunSummary[]
}

export interface BatchIngestResponse {
  batch: BatchDetail
  ingest_status: string
  validation_errors: Record<string, unknown>[]
  quarantined_records: Record<string, unknown>[]
  loader_failures: Record<string, unknown>[]
  provenance_id: string | null
  replay_artifact_id: string | null
}

export interface GovernedSignal {
  rule_id: string
  relationship_field: string
  reason: string
  audit_only_note: string
}

export interface NormalizedResource {
  id: number
  resource_type: string
  record_external_id: string
  status_value: string | null
  status_state: string
  primary_timestamp: string | null
  timestamps: Record<string, unknown>
  references: Record<string, unknown>
  provenance: Record<string, unknown>
  rule_ready: boolean
  incomplete_fields: string[]
  unresolved_links: string[]
  governed_signals: GovernedSignal[]
}

export interface AuditRun {
  id: number
  batch_id: number
  batch_external_id: string | null
  rule_pack_id: number
  rule_pack_version: string | null
  status: string
  started_at: string
  completed_at: string | null
}

export interface AuditRunDetail extends AuditRun {
  finding_count: number
  severity_counts: Record<string, number>
  priority_counts: Record<string, number>
  finding_type_counts: Record<string, number>
  outcome_counts: Record<string, number>
  error_message: string | null
}

export interface Transparency {
  rule_id: string
  rule_pack_version: string | null
  audit_run_id: number
  records_evaluated: string[]
  evidence_refs: string[]
  detected_at: string
  audit_outcome: string
  ai_rationale_present: boolean
  ai_confidence_context: string | null
  ai_model_name: string | null
  ai_prompt_version: string | null
  replay_artifact_path: string | null
  complete: boolean
  missing_fields: string[]
}

export interface FindingEvidence {
  id: number
  evidence_type: string
  normalized_resource_id: number | null
  record_external_id: string | null
  resource_type: string | null
  status_value: string | null
  status_state: string | null
  primary_timestamp: string | null
  evidence_payload: Record<string, unknown>
}

export interface StatusHistory {
  id: number
  from_status: string | null
  to_status: string
  changed_at: string
  changed_by: string | null
  notes: string | null
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
  transparency_complete: boolean
  assigned_queue_name: string | null
  assigned_to: string | null
}

export interface EvidenceSynthesis {
  record_ids: string[]
  resource_types: string[]
  narrative: string
  field_references: string[]
}

export interface ResolutionDraft {
  suggested_action: string
  rationale: string
  requires_human_approval: boolean
  audit_only_note: string
  low_confidence: boolean
}

export interface AIExplanation {
  id: number
  finding_id: number
  model_name: string
  prompt_version: string
  rationale_text: string
  confidence_context: string
  evidence: EvidenceSynthesis | null
  resolution_draft: ResolutionDraft | null
  created_at: string
  low_confidence: boolean
  disclaimer: string
}

export interface ExplanationJob {
  finding_id: number
  state: 'pending' | 'running' | 'succeeded' | 'failed'
  started_at: string | null
  completed_at: string | null
  error: string | null
}

export interface Resolution {
  evidence_id: number
  suggested_action: string
  rationale: string
  source: string
  approved_by: string
  approved_at: string
  notes: string | null
  audit_only_note: string
}

export interface Assignment {
  id: number
  queue_id: number
  queue_name: string
  owner_type: string
  assigned_to: string | null
  assigned_at: string
  auto_routed: boolean
  escalated: boolean
}

export interface FindingDetail extends FindingSummary {
  transparency: Transparency
  evidence: FindingEvidence[]
  explanation: AIExplanation | null
  resolution: Resolution | null
  assignment: Assignment | null
  status_history: StatusHistory[]
  allowed_transitions: string[]
  audit_only_notice: string
}

export interface FindingStats {
  total: number
  open_total: number
  by_severity: Record<string, number>
  by_status: Record<string, number>
  by_priority: Record<string, number>
  by_finding_type: Record<string, number>
  transparency_complete_count: number
}

export interface RulePack {
  id: number
  version: string
  status: string
  published_at: string | null
  metadata: Record<string, unknown>
  rule_count: number
  is_placeholder: boolean
}

export interface Queue {
  id: number
  name: string
  owner_type: string
  config: Record<string, unknown>
  open_count: number
}

export interface ReproducibilityCheck {
  name: string
  passed: boolean
  detail: string
}

export interface Reproducibility {
  finding_id: number
  reproducible: boolean
  checks: ReproducibilityCheck[]
  missing_artifacts: string[]
  verified_at: string
}

export interface Sample {
  sample_id: string
  criteria: Record<string, unknown>
  finding_ids: number[]
  candidate_count: number
  selected_at: string
}

export interface EvidenceBundleItem {
  finding: FindingDetail
  batch_external_id: string | null
  rule_pack_version: string | null
  replay_snapshots: Record<string, unknown>[]
  reproducibility: Reproducibility
}

export interface EvidenceBundle {
  sample_id: string
  generated_at: string
  generated_by: string
  items: EvidenceBundleItem[]
  export_path: string | null
  audit_only_notice: string
}
