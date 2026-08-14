#!/usr/bin/env python3
"""
detect-raw-read.py
Knowledge Map — PreToolUse informational hook

Fires on any Read, web_fetch, or MCP tool call.
Checks if the file, URL, or remote source has a tree in the knowledge map.
Prints an informational message if found — never blocks, never modifies anything.

Three outcomes:
  1. Found in knowledge map, fresh  → INFO: suggest using the tree
  2. Found in knowledge map, stale  → INFO: suggest running sync
  3. Not found anywhere             → Silent. No message.

Exit codes:
  0 = always. This hook never blocks (never exits 2).

Configured in .claude/settings.json under PreToolUse with matchers:
  Read | web_fetch | WebFetch | mcp.*
"""

import sys
import json
import os
import hashlib
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _config import load_knowledge_paths

# ─── Configuration ────────────────────────────────────────────────────────────

KNOWLEDGE_ROOT = load_knowledge_paths().get("knowledge_root", ".propel/knowledge")
INDEX_PATH = os.path.join(KNOWLEDGE_ROOT, "index.json")
TRIBAL_REGISTRY_PATH = os.path.join(KNOWLEDGE_ROOT, "tribal", "registry.json")

# ─── Payload extraction ───────────────────────────────────────────────────────

def extract_source_ref(payload: dict) -> tuple:
    """
    Extract the source reference from the tool payload.
    Returns (source_ref: str, source_type: str)

    source_type: "file" | "url" | "mcp"
    """
    tool_name = (
        payload.get("tool_name", "")
        or payload.get("toolName", "")
        or ""
    ).lower()

    tool_input = payload.get("tool_input", {})
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except json.JSONDecodeError:
            tool_input = {}

    # File read
    if any(t in tool_name for t in ["read", "view"]):
        path = (
            tool_input.get("file_path", "")
            or tool_input.get("path", "")
            or ""
        ).strip()
        if path:
            return path, "file"

    # Web fetch
    if any(t in tool_name for t in ["web_fetch", "webfetch", "fetch", "browse"]):
        url = (
            tool_input.get("url", "")
            or tool_input.get("uri", "")
            or ""
        ).strip()
        if url:
            return url, "url"

    # MCP tool calls — Confluence, SharePoint, Notion etc.
    if "mcp" in tool_name or tool_name.startswith("confluence") \
            or tool_name.startswith("sharepoint") or tool_name.startswith("notion"):
        ref = (
            tool_input.get("url", "")
            or tool_input.get("page_id", "")
            or tool_input.get("page_url", "")
            or tool_input.get("document_url", "")
            or tool_input.get("id", "")
            or ""
        ).strip()
        if ref:
            return ref, "mcp"

    return "", ""


# ─── Knowledge map lookup ─────────────────────────────────────────────────────

def load_json_file(path: str) -> dict | list | None:
    """Safely load a JSON file. Returns None on any error."""
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def is_file_fresh(source_path: str, stored_hash: str, project_dir: str) -> bool:
    """Compare current file hash against stored hash."""
    if not stored_hash:
        return False
    full_path = os.path.join(project_dir, source_path) \
        if not os.path.isabs(source_path) else source_path
    try:
        with open(full_path, "rb") as f:
            current_hash = hashlib.md5(f.read()).hexdigest()
        return current_hash == stored_hash
    except OSError:
        return False


def is_tribal_fresh(source: dict) -> bool:
    """
    Check tribal source freshness based on its strategy.
    hash_watch → compare file hash
    manual     → always considered stale (needs user re-acquisition)
    ttl        → check if TTL has expired
    """
    strategy = source.get("freshness_strategy", "manual")
    acquired_at_str = source.get("acquired_at", "")

    if strategy == "manual":
        # Manual sources are always flagged as needing review
        return False

    if strategy == "ttl":
        ttl_days = source.get("ttl_days", 0)
        if not ttl_days or not acquired_at_str:
            return False
        try:
            acquired_at = datetime.datetime.fromisoformat(
                acquired_at_str.replace("Z", "+00:00")
            )
            age_seconds = (
                datetime.datetime.now(datetime.timezone.utc) - acquired_at
            ).total_seconds()
            return age_seconds < (ttl_days * 86400)
        except ValueError:
            return False

    if strategy == "hash_watch":
        # For remote sources with hash_watch — compare stored hash
        # Source ref is a local file path in this case
        stored_hash = source.get("source_hash", "")
        source_ref = source.get("source_ref", "")
        if not stored_hash or not source_ref:
            return False
        try:
            with open(source_ref, "rb") as f:
                current_hash = hashlib.md5(f.read()).hexdigest()
            return current_hash == stored_hash
        except OSError:
            return False

    return False


def has_complete_nodes(tree_file_path: str, project_dir: str) -> bool:
    """Check if the tree has at least one complete node."""
    full_path = os.path.join(project_dir, tree_file_path) \
        if not os.path.isabs(tree_file_path) else tree_file_path
    tree = load_json_file(full_path)
    if not tree:
        return False
    nodes = tree.get("nodes", [])
    return any(n.get("state") == "complete" for n in nodes)


def check_index(source_ref: str, project_dir: str) -> dict | None:
    """
    Check index.json for a matching artifact by source path.
    Returns the artifact entry if found, None otherwise.
    """
    index_path = os.path.join(project_dir, INDEX_PATH)
    index = load_json_file(index_path)
    if not index:
        return None

    normalised = source_ref.replace("\\", "/")

    for artifact in index.get("artifacts", []):
        artifact_source = artifact.get("source", "").replace("\\", "/")
        if artifact_source and (
            artifact_source == normalised
            or normalised.endswith(artifact_source)
            or artifact_source.endswith(normalised)
        ):
            return artifact

    return None


def check_tribal_registry(source_ref: str, project_dir: str) -> dict | None:
    """
    Check tribal/registry.json for a matching source by source_ref.
    Matches URLs, file paths, and cloud references.
    Returns the registry entry if found, None otherwise.
    """
    registry_path = os.path.join(project_dir, TRIBAL_REGISTRY_PATH)
    registry = load_json_file(registry_path)
    if not registry:
        return None

    normalised = source_ref.strip().rstrip("/")

    for source in registry.get("sources", []):
        registered_ref = source.get("source_ref", "").strip().rstrip("/")
        if registered_ref and (
            registered_ref == normalised
            or normalised in registered_ref
            or registered_ref in normalised
        ):
            return source

    return None


# ─── Message formatting ───────────────────────────────────────────────────────

def format_index_message(artifact: dict, is_fresh: bool,
                         has_complete: bool, source_ref: str) -> str:
    """Format the informational message for an indexed artifact."""
    tree_file = artifact.get("tree_file", "")
    artifact_key = artifact.get("artifact", "")
    node_count = artifact.get("node_count", 0)

    if is_fresh and has_complete:
        return (
            f"\nINFO [Knowledge Map]: Fresh tree available for '{artifact_key}'.\n"
            f"  Instead of reading '{source_ref}' directly:\n"
            f"  → Navigate: {tree_file}\n"
            f"  → {node_count} nodes available with full content preserved.\n"
            f"  → Rule 7: .propel/rules/knowledge-protocol.md\n"
        )

    if is_fresh and not has_complete:
        return (
            f"\nINFO [Knowledge Map]: Tree for '{artifact_key}' exists but "
            f"nodes are skeleton only (content pending).\n"
            f"  Run: /acquire-knowledge --source {source_ref}\n"
            f"  Proceeding with raw file read for now.\n"
        )

    # Stale
    return (
        f"\nINFO [Knowledge Map]: Tree for '{artifact_key}' is stale "
        f"(source has changed since last acquisition).\n"
        f"  Run: /acquire-knowledge to sync.\n"
        f"  Proceeding with raw file read for now.\n"
    )


def format_tribal_message(source: dict, is_fresh: bool, source_ref: str) -> str:
    """Format the informational message for a tribal source."""
    label = source.get("label", source_ref)
    tree_file = source.get("tree_file", "")
    strategy = source.get("freshness_strategy", "manual")

    if is_fresh:
        return (
            f"\nINFO [Knowledge Map]: Fresh tree available for tribal source "
            f"'{label}'.\n"
            f"  Instead of fetching '{source_ref}' directly:\n"
            f"  → Navigate: {tree_file}\n"
            f"  → Rule 7: .propel/rules/knowledge-protocol.md\n"
        )

    if strategy == "manual":
        acquired_at = source.get("acquired_at", "unknown")
        return (
            f"\nINFO [Knowledge Map]: Tribal source '{label}' requires "
            f"manual re-acquisition (last acquired: {acquired_at}).\n"
            f"  Run: /acquire-knowledge --source \"{source_ref}\" "
            f"--label \"{label}\" --freshness manual\n"
            f"  Proceeding with live fetch for now.\n"
        )

    return (
        f"\nINFO [Knowledge Map]: Tribal source '{label}' tree is stale.\n"
        f"  Run: /acquire-knowledge --source \"{source_ref}\" to sync.\n"
        f"  Proceeding with live fetch for now.\n"
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    # Read payload from stdin
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, Exception):
        sys.exit(0)  # Parse error → allow silently

    # Extract source reference
    source_ref, source_type = extract_source_ref(payload)
    if not source_ref:
        sys.exit(0)  # Nothing to check

    # Determine project root
    project_dir = (
        os.environ.get("CLAUDE_PROJECT_DIR")
        or os.getcwd()
    )

    # ── Check 1: Is this in the artifact index? ──────────────────────────────
    artifact = check_index(source_ref, project_dir)
    if artifact:
        stored_hash = artifact.get("source_hash", "")
        tree_file = artifact.get("tree_file", "")

        fresh = is_file_fresh(source_ref, stored_hash, project_dir)
        complete = has_complete_nodes(tree_file, project_dir) if fresh else False

        msg = format_index_message(artifact, fresh, complete, source_ref)
        print(msg)
        sys.exit(0)

    # ── Check 2: Is this in the tribal registry? ─────────────────────────────
    tribal_source = check_tribal_registry(source_ref, project_dir)
    if tribal_source:
        fresh = is_tribal_fresh(tribal_source)
        msg = format_tribal_message(tribal_source, fresh, source_ref)
        print(msg)
        sys.exit(0)

    # ── Not found in either index ─────────────────────────────────────────────
    # Silent. No message. Allow the read.
    sys.exit(0)


if __name__ == "__main__":
    main()
