from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Tuple

from shared.database.config import DatabaseConfig


DEFAULT_ARTIFACT_DIR = "data/processed/ingest-artifacts"
DEFAULT_EXPORT_DIR = "data/processed/compliance-exports"
DEFAULT_CORS_ORIGINS: Tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")


def _env_bool(name: str, default: bool) -> bool:
	raw = os.getenv(name)
	if raw is None:
		return default
	return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
	raw = os.getenv(name)
	if raw is None or not raw.strip():
		return default
	try:
		return int(raw)
	except ValueError:
		return default


def _env_tuple(name: str, default: Tuple[str, ...]) -> Tuple[str, ...]:
	raw = os.getenv(name)
	if raw is None or not raw.strip():
		return default
	return tuple(item.strip() for item in raw.split(",") if item.strip())


@dataclass(frozen=True)
class ApiConfig:
	"""Runtime configuration for the module 4 API.

	Wraps DatabaseConfig rather than replacing it so module 1 and the API always
	resolve DATABASE_URL the same way.
	"""

	database_url: str
	database_echo: bool = False
	artifact_dir: str = DEFAULT_ARTIFACT_DIR
	export_dir: str = DEFAULT_EXPORT_DIR
	auto_create_tables: bool = True
	max_batch_records: int = 5000
	cors_origins: Tuple[str, ...] = DEFAULT_CORS_ORIGINS
	audit_engine: str = "auto"
	ai_enabled: bool = True
	ai_timeout_seconds: float = 60.0
	bedrock_model_id: str | None = None
	aws_region: str | None = None

	@property
	def database_config(self) -> DatabaseConfig:
		return DatabaseConfig(url=self.database_url, echo=self.database_echo)

	@classmethod
	def from_env(cls) -> "ApiConfig":
		database = DatabaseConfig.from_env()
		return cls(
			database_url=database.url,
			database_echo=database.echo,
			artifact_dir=os.getenv("API_ARTIFACT_DIR", DEFAULT_ARTIFACT_DIR),
			export_dir=os.getenv("API_EXPORT_DIR", DEFAULT_EXPORT_DIR),
			auto_create_tables=_env_bool("API_AUTO_CREATE_TABLES", True),
			max_batch_records=_env_int("API_MAX_BATCH_RECORDS", 5000),
			cors_origins=_env_tuple("API_CORS_ORIGINS", DEFAULT_CORS_ORIGINS),
			audit_engine=os.getenv("AUDIT_ENGINE", "auto"),
			ai_enabled=_env_bool("AI_ENABLED", True),
			ai_timeout_seconds=float(_env_int("AI_TIMEOUT_SECONDS", 60)),
			bedrock_model_id=os.getenv("BEDROCK_MODEL_ID"),
			aws_region=os.getenv("AWS_REGION"),
		)
