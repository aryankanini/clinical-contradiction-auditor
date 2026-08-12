#!/usr/bin/env python3
"""
acquire-knowledge-hook.py
Propel-IQ Knowledge Map — Post-write hook script

Triggered by IDE hook systems after any file write:
  Windsurf    → post_write_code      config: .windsurf/hooks.json
  Claude Code → PostToolUse          config: .claude/settings.json
  Copilot     → postToolUse          config: .github/hooks/knowledge-map.json

Reads JSON payload from stdin.
Checks if the written file is a Propel-IQ artifact or tracked codebase file.
If yes — writes a .pending.json marker to .propel/knowledge/pending/.
The agent picks up pending markers on next /acquire-knowledge (no params) invocation.

Never blocks the IDE agent — always exits 0.
"""

import sys
import json
import os
import re
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _config import load_knowledge_paths

# ─── Configuration ────────────────────────────────────────────────────────────

# Directories that contain Propel-IQ SDLC artifacts
PROPEL_ARTIFACT_DIRS = [
    ".propel/context/",
]

# Codebase indexing — Phase 3
# Set to True when Phase 3 is explicitly enabled for this project
CODEBASE_INDEXING_ENABLED = False

CODEBASE_DIRS = [
    "backend/",
    "src/",
    "ui/",
    "app/",
    "lib/",
]

CODEBASE_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx",
    ".cs", ".java", ".kt",
    ".py", ".rb", ".go",
    ".swift", ".rs",
}

# Never trigger on these extensions
IGNORE_EXTENSIONS = {
    ".json", ".lock", ".log", ".tmp",
    ".png", ".jpg", ".svg", ".ico",
    ".map",
}

# Knowledge map root — must match project-config.json propelDirPath
KNOWLEDGE_ROOT = load_knowledge_paths().get("knowledge_root", ".propel/knowledge")

# ─── Field extraction ─────────────────────────────────────────────────────────

def extract_file_path(payload: dict) -> str:
    """
    Extract the written file path from the IDE hook payload.
    Handles all three IDE formats.
    """
    candidates = [
        payload.get("tool_input", {}).get("file_path", ""),   # Claude Code Write
        payload.get("tool_input", {}).get("path", ""),         # Claude Code Edit
        payload.get("filePath", ""),                            # Windsurf
        payload.get("file_path", ""),                           # Windsurf alt
    ]

    # Copilot — toolArgs may be a JSON string
    tool_args_raw = payload.get("toolArgs", "")
    if isinstance(tool_args_raw, str) and tool_args_raw:
        try:
            parsed = json.loads(tool_args_raw)
            candidates.append(parsed.get("file_path", ""))
            candidates.append(parsed.get("path", ""))
        except json.JSONDecodeError:
            pass
    elif isinstance(tool_args_raw, dict):
        candidates.append(tool_args_raw.get("file_path", ""))
        candidates.append(tool_args_raw.get("path", ""))

    for c in candidates:
        if c and isinstance(c, str) and c.strip():
            return c.strip()
    return ""


def extract_tool_name(payload: dict) -> str:
    return (
        payload.get("tool_name", "")
        or payload.get("toolName", "")
        or payload.get("tool", "")
        or ""
    ).lower()


# ─── Classification ───────────────────────────────────────────────────────────

def is_write_operation(tool_name: str) -> bool:
    write_tools = {
        "write", "edit", "create", "writefile", "write_file",
        "create_file", "str_replace", "overwrite", "str_replace_based_edit"
    }
    return not tool_name or any(w in tool_name for w in write_tools)


def should_trigger(file_path: str) -> tuple:
    if not file_path:
        return False, ""

    normalised = file_path.replace("\\", "/")
    _, ext = os.path.splitext(normalised)

    if ext.lower() in IGNORE_EXTENSIONS:
        return False, ""

    # Propel-IQ SDLC artifact
    for d in PROPEL_ARTIFACT_DIRS:
        if d in normalised:
            return True, "propel-artifact"

    # Codebase (Phase 3 — gated)
    if CODEBASE_INDEXING_ENABLED and ext.lower() in CODEBASE_EXTENSIONS:
        for d in CODEBASE_DIRS:
            if normalised.startswith(d) or f"/{d}" in normalised:
                return True, "codebase"

    return False, ""


# ─── Trigger ──────────────────────────────────────────────────────────────────

def write_pending_marker(file_path: str, source_type: str, project_dir: str):
    pending_dir = os.path.join(project_dir, KNOWLEDGE_ROOT, "pending")
    os.makedirs(pending_dir, exist_ok=True)

    safe_name = re.sub(r"[^\w\-.]", "_", file_path.replace("/", "__"))
    marker_path = os.path.join(pending_dir, f"{safe_name}.pending.json")

    marker = {
        "source": file_path,
        "source_type": source_type,
        "triggered_at": datetime.datetime.utcnow().isoformat() + "Z",
        "triggered_by": "hook",
        "marker_file": marker_path
    }

    try:
        with open(marker_path, "w") as f:
            json.dump(marker, f, indent=2)
        print(f"[acquire-knowledge-hook] Queued: {file_path} ({source_type})", file=sys.stderr)
    except OSError as e:
        print(f"[acquire-knowledge-hook] WARNING: Could not write marker: {e}", file=sys.stderr)
        return  # Do not print stdout instruction if marker write failed

    # Print to stdout — Claude Code, Windsurf, and Copilot feed this back
    # to the agent as context on its next turn. The agent will run
    # /acquire-knowledge immediately rather than waiting for manual sync.
    print(
        f"\nKNOWLEDGE MAP UPDATE REQUIRED\n"
        f"─────────────────────────────────────────────\n"
        f"'{file_path}' was just written.\n"
        f"\n"
        f"Run this before your next step:\n"
        f"  /acquire-knowledge --source \"{file_path}\"\n"
        f"\n"
        f"This updates the knowledge map tree so downstream\n"
        f"workflows navigate the knowledge map instead of\n"
        f"reading the raw file directly.\n"
        f"─────────────────────────────────────────────"
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, Exception):
        sys.exit(0)  # Never block

    tool_name = extract_tool_name(payload)
    if not is_write_operation(tool_name):
        sys.exit(0)

    file_path = extract_file_path(payload)

    project_dir = (
        os.environ.get("CLAUDE_PROJECT_DIR")
        or os.environ.get("WINDSURF_PROJECT_DIR")
        or payload.get("cwd", "")
        or os.getcwd()
    )

    trigger, source_type = should_trigger(file_path)
    if trigger:
        write_pending_marker(file_path, source_type, project_dir)

    sys.exit(0)  # Always 0 — post hook never blocks


if __name__ == "__main__":
    main()
