# Rule Catalog

The audit engine executes deterministic, evidence-backed rules over normalized FHIR mappings. Rule packs are versioned YAML files in `data/rule_packs/`.

## Condition

`RULE-COND-001` checks active conditions with future onset dates. `RULE-COND-002` checks onset/abatement ordering. `RULE-COND-003` checks active conditions carrying abatement dates. `RULE-COND-004` identifies entered-in-error conditions with matching entries.

## Medication

`RULE-MED-001` through `RULE-MED-005` cover effective periods, stopped references, invalid doses, and duplicate medication entries.

## Encounter Family

`RULE-ENC-001` and `RULE-ENC-002` cover encounter periods. `RULE-PROC-001` and `RULE-PROC-002` cover performed dates and periods. `RULE-OBS-001` and `RULE-OBS-002` cover future and missing observation values. `RULE-CARE-001` through `RULE-CARE-003` cover completed and active CarePlans.

## Timeline

`RULE-STALE-001`, `RULE-TEMPORAL-001`, and `RULE-LIFECYCLE-001` validate stale state, temporal ordering, and terminal-to-active transitions.

## Severity

Severity is deterministic: explicit rule weight plus resource impact plus category outcome maps to `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW`. The concrete mapping lives in `module_2_audit_engine/severity.py`.