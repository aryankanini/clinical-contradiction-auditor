"""Validate finding replay hashes against archived audit artifacts."""

from __future__ import annotations

from dataclasses import dataclass

from module_2_audit_engine.models.finding import Finding


@dataclass(frozen=True)
class ReproducibilityReport:
	total_findings: int
	validated_count: int
	unvalidated_count: int
	error_count: int

	@property
	def validation_rate(self) -> float:
		return self.validated_count / self.total_findings if self.total_findings else 1.0

	@property
	def passed(self) -> bool:
		return self.validation_rate >= 0.95 and self.error_count == 0


class ReproducibilityValidator:
	"""Compare archived and replayed immutable findings by their hashes."""

	@staticmethod
	def validate(archived: list[Finding], replayed: list[Finding]) -> ReproducibilityReport:
		replayed_hashes = {finding.finding_id: finding.output_finding_hash for finding in replayed}
		validated = sum(1 for finding in archived if replayed_hashes.get(finding.finding_id) == finding.output_finding_hash)
		unvalidated = len(archived) - validated
		return ReproducibilityReport(len(archived), validated, unvalidated, 0)