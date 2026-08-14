from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from module_3_ai_reasoning.llm.provider import BedrockLLMProvider
from shared.models.ai_reasoning_result import EvidenceSynthesis


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "explanation.txt"


def _format_evidence(records: List[Dict[str, Any]]) -> str:
	lines = []
	for r in records:
		lines.append(
			f"- [{r.get('resource_type', 'Unknown')}] id={r.get('record_id', '?')} "
			f"status={r.get('status', '?')} "
			f"status_state={r.get('status_state', '?')} "
			f"timestamps={r.get('timestamps', {})} "
			f"incomplete_fields={r.get('incomplete_fields', [])} "
			f"unresolved_links={r.get('unresolved_links', [])}"
		)
	return "\n".join(lines) if lines else "No evidence records provided."


class EvidenceAgent:
	def __init__(self, provider: BedrockLLMProvider) -> None:
		self._provider = provider
		self._template = _PROMPT_PATH.read_text(encoding="utf-8")

	async def synthesize(
		self,
		rule_id: str,
		evidence_records: List[Dict[str, Any]],
	) -> Tuple[EvidenceSynthesis, str]:
		prompt = self._template.format(
			rule_id=rule_id,
			evidence_records=_format_evidence(evidence_records),
		)
		narrative = await self._provider.complete(prompt)

		# Split narrative from confidence context on the numbered markers the prompt requests
		parts = narrative.split("2.", maxsplit=1)
		evidence_narrative = parts[0].replace("1.", "").strip()
		confidence_context = parts[1].strip() if len(parts) > 1 else ""

		return EvidenceSynthesis(
			record_ids=[r.get("record_id", "") for r in evidence_records],
			resource_types=list({r.get("resource_type", "") for r in evidence_records}),
			narrative=evidence_narrative,
			field_references=[
				field
				for r in evidence_records
				for field in r.get("incomplete_fields", []) + r.get("unresolved_links", [])
			],
		), confidence_context
