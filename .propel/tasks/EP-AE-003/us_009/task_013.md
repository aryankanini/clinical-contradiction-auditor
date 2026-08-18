---
taskId: task_013
epicId: EP-AE-003
parentStories: [us_009, us_010]
title: "Database Schema: Timeline Artifacts"
priority: P2-Medium
status: PLANNED
estimatedHours: 3
---

# Task: Database Schema - Timeline Artifacts

## Objective

Implement PostgreSQL schema for timeline findings, stale state detection records, and state transition audit. Support temporal queries and trend analysis.

---

## Acceptance Criteria Mapping

- **us_009-010 AC-5:** Timeline findings persisted with temporal context

---

## Deliverables

| File | Operation | Details |
|------|-----------|---------|
| `shared/database/migrations/003_timeline_artifacts.sql` | CREATE | Schema for timeline_findings, stale_states, state_transitions |
| `shared/database/models.py` | MODIFY | SQLAlchemy ORM models |

---

## Schema Design

### timeline_findings Table
```
id (SERIAL PK)
finding_id (UUID FK → findings.finding_id, not null)
timeline_type (VARCHAR: STALE, TEMPORAL, LIFECYCLE)
temporal_context (JSONB: {date_field, actual_value, expected_value, age_days})
created_at (TIMESTAMP DEFAULT NOW())
```

### stale_states Table
```
id (SERIAL PK)
patient_id (VARCHAR)
resource_type (VARCHAR)
resource_id (VARCHAR)
status (VARCHAR)
last_updated (TIMESTAMP)
age_years (FLOAT)
detected_at (TIMESTAMP DEFAULT NOW())
finding_id (UUID FK → findings.finding_id, nullable)
```

### state_transitions Table
```
id (SERIAL PK)
patient_id (VARCHAR)
resource_type (VARCHAR)
previous_status (VARCHAR)
current_status (VARCHAR)
transition_date (TIMESTAMP)
valid (BOOLEAN DEFAULT TRUE)
finding_id (UUID FK → findings.finding_id, nullable)
created_at (TIMESTAMP DEFAULT NOW())
```

---

## Implementation Checklist

- [ ] Create timeline_findings table
- [ ] Create stale_states table
- [ ] Create state_transitions table
- [ ] Add indexes on patient_id, resource_type, detected_at, transition_date
- [ ] Define foreign key relationships
- [ ] Create SQLAlchemy ORM models
- [ ] Write schema documentation

---

**Effort:** 3 hours  
**Owner:** Database Engineer  
**Review Checklist:** Schema complete, indexes created, ORM models working
