#!/usr/bin/env python3
"""
Test the live health endpoint
"""
import urllib.request
import json

try:
    with urllib.request.urlopen("http://127.0.0.1:18080/api/v1/health", timeout=5) as response:
        data = json.loads(response.read())
        print("Health endpoint response:")
        print(json.dumps(data, indent=2))
        print()
        print("audit_only_notice value:")
        print(repr(data.get("audit_only_notice")))
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
