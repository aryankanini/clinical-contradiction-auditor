"""Run a repeatable local timing check for deterministic contradiction rules."""

from time import perf_counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.integration.test_contradiction_detection_pipeline import _contradictory_resources
from tests.unit.test_contradiction_rules import RULE_CLASSES


def main() -> None:
	resources = [resource for patient_number in range(1000) for resource in _contradictory_resources(str(patient_number))]
	start = perf_counter()
	findings = [finding for rule_class in RULE_CLASSES for finding in rule_class().execute(resources)]
	elapsed_ms = (perf_counter() - start) * 1000
	print(f"rules=18 cohort=1000 findings={len(findings)} elapsed_ms={elapsed_ms:.2f}")


if __name__ == "__main__":
	main()