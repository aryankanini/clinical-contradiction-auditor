#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from module_4_api_ui.backend.schemas.common import HealthOut
from module_4_api_ui.backend.disclaimers import AUDIT_ONLY_NOTICE

print("AUDIT_ONLY_NOTICE constant:", repr(AUDIT_ONLY_NOTICE))
print("\nHealthOut schema:")
for field_name, field_info in HealthOut.model_fields.items():
    default = field_info.default
    if field_name == 'audit_only_notice':
        print(f"  {field_name}: default = {repr(default)}")

health = HealthOut(
    status="ok",
    database_reachable=True,
    audit_engine="test",
    audit_engine_is_placeholder=False,
    ai_enabled=True,
)
print("\nHealthOut instance json:")
import json
print(json.dumps(json.loads(health.model_dump_json()), indent=2))
