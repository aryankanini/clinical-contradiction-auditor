# Contradiction Benchmark Report

## Measurement

The local benchmark executed all 18 deterministic contradiction rules against 1,000 patient-shaped inputs on 2026-08-17.

| Rule Set | Cohort | Findings | Elapsed Time | Result |
| --- | ---: | ---: | ---: | --- |
| All 18 rules | 1,000 | 7,000 | 347.28 ms | Pass |

## Result

The complete rule set finished within the current one-second cohort budget. This is equivalent to approximately 0.35 ms per patient-shaped input. Re-run `python tests/performance_benchmarks/benchmark_contradiction_rules.py` on deployment hardware before establishing a production baseline.