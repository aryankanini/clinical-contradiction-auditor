from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class DatabaseConfig:
	url: str
	echo: bool = False
	pool_pre_ping: bool = True

	@classmethod
	def from_env(cls) -> "DatabaseConfig":
		return cls(
			url=os.getenv(
				"DATABASE_URL",
				"postgresql+psycopg://postgres:postgres@localhost:5432/clinical_auditor",
			),
			echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
		)
