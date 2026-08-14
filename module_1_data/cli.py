from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from module_1_data.pipeline import ingest_batch


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Run the clinical auditor ingestion pipeline on a JSON batch file.")
	parser.add_argument("input_json", help="Path to the batch JSON payload to ingest")
	parser.add_argument(
		"--artifact-dir",
		default="data/processed/ingest-artifacts",
		help="Directory where provenance and replay artifacts will be written",
	)
	parser.add_argument(
		"--database-url",
		default=None,
		help="Optional SQLAlchemy database URL for relational persistence",
	)
	parser.add_argument(
		"--pretty",
		action="store_true",
		help="Pretty-print the full pipeline result as JSON",
	)
	return parser


def _load_payload(input_path: Path) -> dict[str, Any]:
	return json.loads(input_path.read_text(encoding="utf-8"))


def _build_summary(result: Any) -> dict[str, Any]:
	return {
		"status": result.status,
		"metadata": result.metadata,
		"staged_resource_count": len(result.staged_resources),
		"normalized_resource_count": len(result.normalized_resources),
		"validation_state_count": len(result.validation_states),
		"governed_signal_count": len(result.governed_signals),
		"provenance_path": result.provenance.storage_path if result.provenance else None,
		"replay_artifact_path": result.replay_artifact.storage_path if result.replay_artifact else None,
	}


def main() -> int:
	parser = build_parser()
	args = parser.parse_args()
	input_path = Path(args.input_json)
	payload = _load_payload(input_path)
	result = ingest_batch(
		payload,
		artifact_dir=args.artifact_dir,
		database_url=args.database_url,
	)

	if args.pretty:
		print(json.dumps(_build_summary(result), indent=2))
	else:
		summary = _build_summary(result)
		for key, value in summary.items():
			print(f"{key}: {value}")

	return 0


if __name__ == "__main__":
	raise SystemExit(main())