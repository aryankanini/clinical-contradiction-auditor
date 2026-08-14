from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from functools import partial
from typing import Any, Dict

import boto3


DEFAULT_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 0.0


@dataclass
class BedrockLLMProvider:
	model_id: str = DEFAULT_MODEL_ID
	max_tokens: int = DEFAULT_MAX_TOKENS
	temperature: float = DEFAULT_TEMPERATURE
	region: str = "us-east-1"
	_client: Any = field(default=None, init=False, repr=False)

	def _get_client(self) -> Any:
		if self._client is None:
			self._client = boto3.client("bedrock-runtime", region_name=self.region)
		return self._client

	def _invoke(self, prompt: str) -> str:
		client = self._get_client()
		response = client.converse(
			modelId=self.model_id,
			messages=[{"role": "user", "content": [{"text": prompt}]}],
			inferenceConfig={
				"maxTokens": self.max_tokens,
				"temperature": self.temperature,
			},
		)
		return response["output"]["message"]["content"][0]["text"]

	async def complete(self, prompt: str) -> str:
		loop = asyncio.get_event_loop()
		return await loop.run_in_executor(None, partial(self._invoke, prompt))
