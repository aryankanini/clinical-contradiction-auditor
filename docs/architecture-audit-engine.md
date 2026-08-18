# Audit Engine Architecture

The engine uses immutable contracts at each audit boundary.

1. `RulePackLoader` validates a versioned YAML pack.
2. `RuleOrchestrator` constructs a canonical, rule-ID-sorted execution plan.
3. Rules return raw evidence mappings without changing input resources.
4. `extract_evidence` creates an immutable `Finding` with stable SHA-256 hashes.
5. `SafetyValidator` rejects restricted diagnostic or treatment language.
6. `FindingHydrator` assigns a deterministic severity tier.
7. Append-only audit storage retains execution facts and reproducibility records.

Reproducibility compares archived finding IDs and output hashes from the same input snapshot and rule version. A validation report passes at or above 95% matching findings.