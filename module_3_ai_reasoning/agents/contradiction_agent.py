from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from module_3_ai_reasoning.llm.provider import BedrockLLMProvider


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "contradiction.txt"


def _format_records(records: List[Dict[str, Any]]) -> str:
	lines = []
	for r in records:
		lines.append(
			f"- [{r.get('resource_type', 'Unknown')}] id={r.get('record_id', '?')} "
			f"status={r.get('status', '?')} timestamps={r.get('timestamps', {})}"
		)
	return "\n".join(lines) if lines else "No records provided."


class ContradictionAgent:
	def __init__(self, provider: BedrockLLMProvider) -> None:
		self._provider = provider
		self._template = _PROMPT_PATH.read_text(encoding="utf-8")

	async def explain(
		self,
		rule_id: str,
		finding_type: str,
		summary: str,
		conflicting_records: List[Dict[str, Any]],
	) -> str:
		prompt = self._template.format(
			rule_id=rule_id,
			finding_type=finding_type,
			summary=summary,
			conflicting_records=_format_records(conflicting_records),
		)
		return await self._provider.complete(prompt)
