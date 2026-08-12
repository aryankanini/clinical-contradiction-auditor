#!/usr/bin/env python3
"""
process-pending-acquisitions.py
Propel-IQ Knowledge Map — Pending acquisition processor

Called by the agent at the start of every parameterless /acquire-knowledge run.
Reads marker files written by the IDE hook and returns a JSON list for the
agent to process. The agent invokes /acquire-knowledge --source <source> for
each entry, then deletes the marker file on success.

Output: JSON array of pending acquisitions, or empty array [].
"""

import sys
import json
import os
import glob
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _config import load_knowledge_paths

KNOWLEDGE_ROOT = load_knowledge_paths().get("knowledge_root", ".propel/knowledge")
PENDING_DIR = os.path.join(KNOWLEDGE_ROOT, "pending")
MAX_AGE_HOURS = 24


def main():
    if not os.path.exists(PENDING_DIR):
        print(json.dumps([]))
        sys.exit(0)

    pending = []
    stale = []
    now = datetime.datetime.now(datetime.timezone.utc)

    for marker_path in glob.glob(os.path.join(PENDING_DIR, "*.pending.json")):
        try:
            with open(marker_path) as f:
                marker = json.load(f)

            triggered_at_str = marker.get("triggered_at", "")
            if triggered_at_str:
                try:
                    triggered_at = datetime.datetime.fromisoformat(
                        triggered_at_str.replace("Z", "+00:00")
                    )
                    age_hours = (now - triggered_at).total_seconds() / 3600
                    if age_hours > MAX_AGE_HOURS:
                        stale.append(marker_path)
                        continue
                except ValueError:
                    pass

            # Ensure marker_file is set — agent needs it for cleanup
            if "marker_file" not in marker:
                marker["marker_file"] = marker_path

            pending.append({
                "source": marker.get("source", ""),
                "source_type": marker.get("source_type", "propel-artifact"),
                "triggered_at": triggered_at_str,
                "marker_file": marker["marker_file"]
            })

        except (json.JSONDecodeError, OSError):
            stale.append(marker_path)

    for stale_path in stale:
        try:
            os.remove(stale_path)
        except OSError:
            pass

    print(json.dumps(pending, indent=2))


if __name__ == "__main__":
    main()
