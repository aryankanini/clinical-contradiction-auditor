#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from module_4_api_ui.backend.main import create_app
from module_4_api_ui.backend.dependencies import get_session_factory
from module_4_api_ui.backend.config import ApiConfig
from starlette.testclient import TestClient

# Create test app
app = create_app()
client = TestClient(app)

# Call health endpoint
response = client.get("/api/v1/health")
data = response.json()

print("Response status:", response.status_code)
print("Response JSON:")
import json
print(json.dumps(data, indent=2))
print("\nAudit notice value:")
print(repr(data.get("audit_only_notice")))
