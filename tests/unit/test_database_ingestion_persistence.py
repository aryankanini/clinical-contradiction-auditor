from __future__ import annotations

import tempfile
import unittest

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from module_1_data.pipeline import ingest_batch
from shared.database.base import Base
from shared.database.models import (
	GovernedRelationshipSignalRow,
	IngestBatchRow,
	IngestRecordRow,
	NormalizedResourceRow,
	ValidationStateRow,
)


class DatabaseIngestionPersistenceTests(unittest.TestCase):
	def test_ingest_batch_database_persistence_writes_relational_state(self) -> None:
		payload = {
			"batch_id": "batch-db-1",
			"source": "ehr-a",
			"records": [
				{"id": "cond-1", "resourceType": "Condition", "clinicalStatus": {"text": "active"}, "recordedDate": "2026-08-12T10:00:00Z"},
				{"id": "obs-1", "resourceType": "Observation", "status": "final"},
			],
		}

		with tempfile.TemporaryDirectory() as temp_dir:
			database_url = f"sqlite+pysqlite:///{temp_dir}/clinical_auditor.db"
			result = ingest_batch(payload, artifact_dir=temp_dir, database_url=database_url)

			self.assertIn("database_batch_id", result.metadata)

			engine = create_engine(database_url)
			try:
				with Session(engine) as session:
					batch_count = session.scalar(select(func.count()).select_from(IngestBatchRow))
					record_count = session.scalar(select(func.count()).select_from(IngestRecordRow))
					normalized_count = session.scalar(select(func.count()).select_from(NormalizedResourceRow))
					validation_count = session.scalar(select(func.count()).select_from(ValidationStateRow))
					signal_count = session.scalar(select(func.count()).select_from(GovernedRelationshipSignalRow))

					self.assertEqual(batch_count, 1)
					self.assertEqual(record_count, 2)
					self.assertEqual(normalized_count, 2)
					self.assertEqual(validation_count, 2)
					self.assertEqual(signal_count, 1)
			finally:
				engine.dispose()

	def test_ingest_batch_database_persistence_tracks_quarantined_records(self) -> None:
		payload = {
			"batch_id": "batch-db-2",
			"source": "ehr-a",
			"records": [
				{"id": "enc-1", "resourceType": "Encounter", "status": "finished", "period": {"start": "2026-08-12T10:00:00Z"}},
				{"resourceType": "Observation"},
			],
		}

		with tempfile.TemporaryDirectory() as temp_dir:
			database_url = f"sqlite+pysqlite:///{temp_dir}/clinical_auditor.db"
			ingest_batch(payload, artifact_dir=temp_dir, database_url=database_url)

			engine = create_engine(database_url)
			try:
				with Session(engine) as session:
					quarantined_count = session.scalar(
						select(func.count()).select_from(IngestRecordRow).where(IngestRecordRow.quarantined.is_(True))
					)
					self.assertEqual(quarantined_count, 1)
			finally:
				engine.dispose()


if __name__ == "__main__":
	unittest.main()