from __future__ import annotations

"""Transient state for background work.

Durable state already lives in the database: ``audit_runs.status`` for a run, and the
existence of an ``ai_explanations`` row for a generated explanation. This registry only
holds what has no column — whether a job is in flight right now, and the error text when
one fails.

Scope: per process. Under ``uvicorn --workers N`` the database remains the cross-process
truth; only dedupe and error text are worker-local.
"""

import asyncio
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Tuple


JobKey = Tuple[str, int]


@dataclass
class JobState:
	key: JobKey
	state: str
	started_at: datetime
	completed_at: datetime | None = None
	error: str | None = None


class JobRegistry:
	def __init__(self, max_entries: int = 512) -> None:
		self._entries: "OrderedDict[JobKey, JobState]" = OrderedDict()
		self._max_entries = max_entries
		self._lock = asyncio.Lock()

	def _prune(self) -> None:
		while len(self._entries) > self._max_entries:
			self._entries.popitem(last=False)

	async def claim(self, key: JobKey) -> bool:
		"""Reserve the job. Returns False when one is already in flight."""
		async with self._lock:
			existing = self._entries.get(key)
			if existing is not None and existing.state in {"pending", "running"}:
				return False
			self._entries[key] = JobState(
				key=key, state="pending", started_at=datetime.now(timezone.utc)
			)
			self._entries.move_to_end(key)
			self._prune()
			return True

	async def start(self, key: JobKey) -> None:
		async with self._lock:
			entry = self._entries.get(key)
			if entry is not None:
				entry.state = "running"

	async def succeed(self, key: JobKey) -> None:
		async with self._lock:
			entry = self._entries.get(key)
			if entry is not None:
				entry.state = "succeeded"
				entry.completed_at = datetime.now(timezone.utc)

	async def fail(self, key: JobKey, error: str) -> None:
		async with self._lock:
			entry = self._entries.get(key)
			if entry is None:
				entry = JobState(
					key=key, state="failed", started_at=datetime.now(timezone.utc)
				)
				self._entries[key] = entry
			entry.state = "failed"
			entry.error = error
			entry.completed_at = datetime.now(timezone.utc)

	async def get(self, key: JobKey) -> JobState | None:
		async with self._lock:
			return self._entries.get(key)

	def peek(self, key: JobKey) -> JobState | None:
		"""Lock-free read for sync code paths assembling a response."""
		return self._entries.get(key)

	async def release(self, key: JobKey) -> None:
		async with self._lock:
			self._entries.pop(key, None)
