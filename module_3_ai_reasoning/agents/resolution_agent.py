from __future__ import annotations

from pathlib import Path

from module_3_ai_reasoning.llm.provider import BedrockLLMProvider
from shared.models.ai_reasoning_result import ResolutionDraft


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "resolution.txt"


class ResolutionAgent:
	def __init__(self, provider: BedrockLLMProvider) -> None:
		self._provider = provider
		self._template = _PROMPT_PATH.read_text(encoding="utf-8")

	async def draft(
		self,
		rule_id: str,
		contradiction_explanation: str,
		evidence_summary: str,
		severity: str,
	) -> ResolutionDraft:
		prompt = self._template.format(
			rule_id=rule_id,
			contradiction_explanation=contradiction_explanation,
			evidence_summary=evidence_summary,
			severity=severity,
		)
		raw = await self._provider.complete(prompt)

		# Split suggested action from rationale on the mandatory closing sentence
		parts = raw.split("This draft requires", maxsplit=1)
		body = parts[0].strip()

		# Further split body into action and rationale on first newline
		body_parts = body.split("\n", maxsplit=1)
		suggested_action = body_parts[0].strip()
		rationale = body_parts[1].strip() if len(body_parts) > 1 else body.strip()

		return ResolutionDraft(
			suggested_action=suggested_action,
			rationale=rationale,
		)
