#!/usr/bin/env python3
"""
Direct test: construct HealthOut and see what gets serialized
"""
from module_4_api_ui.backend.schemas.common import HealthOut

# Build a HealthOut instance like the router does
health = HealthOut(
    status="ok",
    database_reachable=True,
    audit_engine="ContradictionDetector",
    audit_engine_is_placeholder=False,
    ai_enabled=True,
)

print("Instance fields:")
print(f"  status: {health.status}")
print(f"  audit_only_notice: {health.audit_only_notice}")
print()
print("Serialized to dict:")
print(health.model_dump())
print()
print("Serialized to JSON:")
import json
print(json.dumps(health.model_dump(), indent=2))
