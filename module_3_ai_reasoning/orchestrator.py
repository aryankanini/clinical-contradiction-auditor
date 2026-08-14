from __future__ import annotations

from typing import Any, Dict, List

from module_3_ai_reasoning.agents.contradiction_agent import ContradictionAgent
from module_3_ai_reasoning.agents.evidence_agent import EvidenceAgent
from module_3_ai_reasoning.agents.resolution_agent import ResolutionAgent
from module_3_ai_reasoning.llm.provider import BedrockLLMProvider
from shared.models.ai_reasoning_result import AIReasoningResult

PROMPT_VERSION = "v1.0"


class AIReasoningOrchestrator:
	def __init__(self, provider: BedrockLLMProvider | None = None) -> None:
		self._provider = provider or BedrockLLMProvider()
		self._contradiction_agent = ContradictionAgent(self._provider)
		self._evidence_agent = EvidenceAgent(self._provider)
		self._resolution_agent = ResolutionAgent(self._provider)

	async def reason(
		self,
		finding_id: str,
		rule_id: str,
		finding_type: str,
		summary: str,
		severity: str,
		evidence_records: List[Dict[str, Any]],
	) -> AIReasoningResult:
		contradiction_explanation = await self._contradiction_agent.explain(
			rule_id=rule_id,
			finding_type=finding_type,
			summary=summary,
			conflicting_records=evidence_records,
		)

		evidence_synthesis, confidence_context = await self._evidence_agent.synthesize(
			rule_id=rule_id,
			evidence_records=evidence_records,
		)

		resolution_draft = await self._resolution_agent.draft(
			rule_id=rule_id,
			contradiction_explanation=contradiction_explanation,
			evidence_summary=evidence_synthesis.narrative,
			severity=severity,
		)

		return AIReasoningResult(
			finding_id=finding_id,
			rule_id=rule_id,
			contradiction_explanation=contradiction_explanation,
			confidence_context=confidence_context,
			evidence=evidence_synthesis,
			resolution_draft=resolution_draft,
			model_name=self._provider.model_id,
			prompt_version=PROMPT_VERSION,
		)
