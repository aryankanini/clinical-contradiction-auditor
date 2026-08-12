"""
Project Artifact Resolver

Resolves artifact details (propelFilePath, projectFilePath, templates,
contentType, mcpType, references) by artifact name from project-config.json
in the .propel directory.

Usage:
    python resolve_artifact.py --list
    python resolve_artifact.py --artifact spec
    python resolve_artifact.py --all
    python resolve_artifact.py --config-field basePropelPath
    python resolve_artifact.py --config /custom/path/project-config.json --artifact spec
    python resolve_artifact.py --tribal oauth-rfc
    python resolve_artifact.py --derived analysis-security-nfrs
    python resolve_artifact.py --list-tribal
    python resolve_artifact.py --list-derived

Notes:
    - resolve_config_field interpolates string values only. Dict and list values
      are returned as-is; string interpolation is not applied recursively to
      nested structures.
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Tribal freshness defaults — match memory-lint Step 6 freshness rules
TRIBAL_MANUAL_MAX_AGE_DAYS = 90

# Default config: <project-root>/.propel/project-config.json
DEFAULT_CONFIG = Path.cwd() / ".propel" / "project-config.json"

# Knowledge map root: <project-root>/.propel/knowledge
KNOWLEDGE_ROOT = Path.cwd() / ".propel" / "knowledge"


def load_config(config_path: str) -> dict:
    path = Path(config_path)
    if not path.exists():
        print(json.dumps({"error": f"Config file not found: {config_path}"}))
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def interpolate(value: str, config: dict) -> str:
    """Replace ${key} placeholders with top-level config values and normalise slashes."""
    def replacer(match):
        key = match.group(1)
        if key not in config:
            raise ValueError(f"Unresolved variable: ${{{key}}}")
        return str(config[key])
    result = re.sub(r"\$\{(\w+)\}", replacer, value)
    # Normalise double slashes (but preserve protocol prefixes like http://)
    result = re.sub(r"(?<!:)//+", "/", result)
    return result


def list_artifacts(config: dict) -> None:
    artifacts = config.get("artifacts", {})
    if not artifacts:
        print(json.dumps({"error": "No artifacts defined in project config"}))
        sys.exit(1)
    result = {
        "projectName": config.get("projectName", ""),
        "availableArtifacts": list(artifacts.keys()),
    }
    print(json.dumps(result, indent=2))


def normalize_path(path: str) -> str:
    """Normalise double slashes (but preserve protocol prefixes like http://)."""
    return re.sub(r"(?<!:)//+", "/", path)


UML_SUBDIR = "uml-models"


def build_uml_paths(propel_dir: str, project_dir: str) -> tuple:
    """Derive propelUmlPath and projectUmlPath by appending the fixed UML
    subdirectory to the artifact's propel and project directory paths."""
    propel_uml = normalize_path(propel_dir + "/" + UML_SUBDIR)
    project_uml = normalize_path(project_dir + "/" + UML_SUBDIR)
    return propel_uml, project_uml


def _parse_iso8601(value):
    """Parse an ISO-8601 string to an aware datetime; return None on failure."""
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _read_json(path: Path):
    """Read JSON safely; return None on any error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _load_tribal_registry() -> list:
    """Return the list of tribal source entries (empty list if missing)."""
    data = _read_json(KNOWLEDGE_ROOT / "tribal" / "registry.json")
    if not data:
        return []
    return data.get("sources", [])


def _load_derived_registry() -> list:
    """Return the list of derived entries (empty list if missing)."""
    data = _read_json(KNOWLEDGE_ROOT / "derived" / "registry.json")
    if not data:
        return []
    return data.get("entries", [])


def _tree_metadata(tree_file: str) -> dict:
    """Read summary/acquired_at/source_hash from a tree file."""
    if not tree_file:
        return {}
    data = _read_json(Path(tree_file))
    if not data:
        return {}
    return {
        "summary": data.get("summary"),
        "acquired_at": data.get("acquired_at"),
        "source_hash": data.get("source_hash"),
    }


def _hash_file(path: str):
    """SHA-256 of file contents; None if unreadable."""
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def compute_knowledge_status(artifact_key: str, propel_file_path: str) -> dict:
    """Compute knowledge map status for an artifact.

    Returns a dict with knowledgePath, knowledgeLinksPath, knowledgeStatus,
    knowledgeSummary, knowledgeAcquiredAt. knowledgeStatus is one of:
    fresh | stale | missing | not_applicable.
    """
    tree_path = KNOWLEDGE_ROOT / "artifacts" / artifact_key / f"{artifact_key}.tree.json"
    tree_rel = f"./.propel/knowledge/artifacts/{artifact_key}/{artifact_key}.tree.json"
    links_rel = f"./.propel/knowledge/artifacts/{artifact_key}/{artifact_key}.links.json"
    result = {
        "knowledgePath": tree_rel,
        "knowledgeLinksPath": links_rel,
        "knowledgeStatus": "missing",
        "knowledgeSummary": None,
        "knowledgeAcquiredAt": None,
    }
    source = Path(propel_file_path)
    if not source.exists() or not source.is_file():
        result["knowledgeStatus"] = "not_applicable"
        return result
    if not tree_path.exists():
        return result
    meta = _tree_metadata(str(tree_path))
    if not meta:
        return result
    result["knowledgeSummary"] = meta.get("summary")
    result["knowledgeAcquiredAt"] = meta.get("acquired_at")
    current_hash = _hash_file(str(source))
    if current_hash is None:
        return result
    result["knowledgeStatus"] = "fresh" if meta.get("source_hash") == current_hash else "stale"
    return result


def _tribal_status(entry: dict, meta: dict) -> str:
    """Derive knowledgeStatus for a tribal entry per its freshness strategy."""
    tree_file = entry.get("tree_file")
    if not tree_file or not Path(tree_file).exists():
        return "missing"
    if not meta:
        return "missing"

    strategy = entry.get("freshness_strategy", "manual")

    if strategy == "hash_watch":
        source_ref = entry.get("source_ref", "")
        local_source = Path(source_ref) if source_ref else None
        if not local_source or not local_source.exists() or not local_source.is_file():
            # source_ref is a URL or unreadable — fall through to manual rule
            strategy = "manual"
        else:
            current_hash = _hash_file(str(local_source))
            if current_hash is None:
                return "missing"
            return "fresh" if meta.get("source_hash") == current_hash else "stale"

    acquired_at = _parse_iso8601(entry.get("acquired_at"))
    if not acquired_at:
        return "stale"
    age_days = (datetime.now(timezone.utc) - acquired_at).total_seconds() / 86400

    if strategy == "ttl":
        ttl_days = entry.get("ttl_days")
        if not isinstance(ttl_days, (int, float)) or ttl_days <= 0:
            return "stale"
        return "fresh" if age_days <= ttl_days else "stale"

    # manual (default fallback)
    return "fresh" if age_days <= TRIBAL_MANUAL_MAX_AGE_DAYS else "stale"


def _find_node_tree(node_id: str):
    """Find which artifact/tribal tree contains node_id; return (tree_file, acquired_at)."""
    for root in [KNOWLEDGE_ROOT / "artifacts", KNOWLEDGE_ROOT / "tribal"]:
        if not root.exists():
            continue
        for tree_file in root.rglob("*.tree.json"):
            data = _read_json(tree_file)
            if not data:
                continue
            for node in data.get("nodes", []) or []:
                if node.get("id") == node_id:
                    return str(tree_file), data.get("acquired_at")
    return None, None


def _derived_status(entry: dict) -> str:
    """Derived is stale if any upstream node belongs to a tree re-acquired later."""
    tree_file = entry.get("tree_file")
    if not tree_file or not Path(tree_file).exists():
        return "missing"
    derived_acquired = _parse_iso8601(entry.get("acquired_at"))
    if not derived_acquired:
        return "stale"
    upstream = entry.get("upstream_nodes", []) or []
    for node_id in upstream:
        _, upstream_acquired_str = _find_node_tree(node_id)
        upstream_acquired = _parse_iso8601(upstream_acquired_str)
        if upstream_acquired and upstream_acquired > derived_acquired:
            return "stale"
    return "fresh"


def _to_relative(path: str) -> str:
    """Normalize a stored path to project-relative form."""
    if not path:
        return ""
    p = path.replace("\\", "/")
    if p.startswith("./"):
        return p
    if p.startswith(".propel/"):
        return f"./{p}"
    return p


def resolve_tribal(label: str) -> None:
    sources = _load_tribal_registry()
    entry = next((s for s in sources if s.get("label") == label), None)
    if not entry:
        print(json.dumps({
            "error": f"Tribal label '{label}' not found",
            "availableLabels": [s.get("label", "") for s in sources],
        }, indent=2))
        sys.exit(1)
    meta = _tree_metadata(entry.get("tree_file", ""))
    status = _tribal_status(entry, meta)
    result = {
        "label": entry.get("label", ""),
        "sourceType": "tribal",
        "sourceRef": entry.get("source_ref", ""),
        "knowledgePath": _to_relative(entry.get("tree_file", "")),
        "knowledgeLinksPath": _to_relative(entry.get("links_file", "")),
        "knowledgeStatus": status,
        "knowledgeSummary": meta.get("summary") if meta else None,
        "knowledgeAcquiredAt": entry.get("acquired_at"),
        "freshnessStrategy": entry.get("freshness_strategy", "manual"),
        "ttlDays": entry.get("ttl_days"),
        "notes": entry.get("notes", ""),
    }
    print(json.dumps(result, indent=2))


def resolve_derived(label: str) -> None:
    entries = _load_derived_registry()
    entry = next((e for e in entries if e.get("label") == label), None)
    if not entry:
        print(json.dumps({
            "error": f"Derived label '{label}' not found",
            "availableLabels": [e.get("label", "") for e in entries],
        }, indent=2))
        sys.exit(1)
    meta = _tree_metadata(entry.get("tree_file", ""))
    status = _derived_status(entry)
    result = {
        "label": entry.get("label", ""),
        "sourceType": "derived",
        "upstreamNodes": entry.get("upstream_nodes", []),
        "knowledgePath": _to_relative(entry.get("tree_file", "")),
        "knowledgeLinksPath": _to_relative(entry.get("links_file", "")),
        "knowledgeStatus": status,
        "knowledgeSummary": meta.get("summary") if meta else None,
        "knowledgeAcquiredAt": entry.get("acquired_at"),
        "notes": entry.get("notes", ""),
    }
    print(json.dumps(result, indent=2))


def list_tribal() -> None:
    sources = _load_tribal_registry()
    print(json.dumps({
        "availableLabels": [s.get("label", "") for s in sources],
    }, indent=2))


def list_derived() -> None:
    entries = _load_derived_registry()
    print(json.dumps({
        "availableLabels": [e.get("label", "") for e in entries],
    }, indent=2))


def resolve_artifact(config: dict, artifact_key: str) -> None:
    artifacts = config.get("artifacts", {})
    if artifact_key not in artifacts:
        result = {
            "error": f"Artifact '{artifact_key}' not found",
            "availableArtifacts": list(artifacts.keys()),
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)
    entry = artifacts[artifact_key]
    propel_dir = interpolate(entry.get("propelDirPath", ""), config)
    project_dir = interpolate(entry.get("projectDirPath", ""), config)
    propel_file = normalize_path(propel_dir + "/" + entry.get("propelFileName", ""))
    project_file = normalize_path(project_dir + "/" + entry.get("projectFileName", ""))
    propel_uml, project_uml = build_uml_paths(propel_dir, project_dir)
    result = {
        "artifact": artifact_key,
        "propelFileName": entry.get("propelFileName", ""),
        "propelFileNames": entry.get("propelFileNames", {}),
        "propelDirPath": propel_dir,
        "propelFilePath": propel_file,
        "projectFilePath": project_file,
        "propelUmlPath": propel_uml,
        "projectUmlPath": project_uml,
        "templates": entry.get("templates", {}),
        "schema": entry.get("schema", ""),
        "contentType": entry.get("contentType", ""),
        "mcpType": entry.get("mcpType", ""),
        "references": entry.get("references", []),
        "workflow": entry.get("workflow", ""),
    }
    result.update(compute_knowledge_status(artifact_key, propel_file))
    print(json.dumps(result, indent=2))


def resolve_config_field(config: dict, field_name: str) -> None:
    if field_name not in config:
        result = {
            "error": f"Config field '{field_name}' not found",
            "availableFields": [
                k for k in config.keys() if k != "artifacts"
            ],
        }
        print(json.dumps(result, indent=2))
        sys.exit(1)
    value = config[field_name]
    if isinstance(value, str):
        value = interpolate(value, config)
    # Note: dict and list values are returned as-is without recursive interpolation.
    result = {
        "field": field_name,
        "value": value,
    }
    print(json.dumps(result, indent=2))


def resolve_all(config: dict) -> None:
    artifacts = config.get("artifacts", {})
    if not artifacts:
        print(json.dumps({"error": "No artifacts defined in project config"}))
        sys.exit(1)
    resolved = {}
    for key, entry in artifacts.items():
        propel_dir = interpolate(entry.get("propelDirPath", ""), config)
        project_dir = interpolate(entry.get("projectDirPath", ""), config)
        propel_file = normalize_path(propel_dir + "/" + entry.get("propelFileName", ""))
        project_file = normalize_path(project_dir + "/" + entry.get("projectFileName", ""))
        propel_uml, project_uml = build_uml_paths(propel_dir, project_dir)
        resolved[key] = {
            "propelFileName": entry.get("propelFileName", ""),
            "propelFileNames": entry.get("propelFileNames", {}),
            "propelDirPath": propel_dir,
            "propelFilePath": propel_file,
            "projectFilePath": project_file,
            "propelUmlPath": propel_uml,
            "projectUmlPath": project_uml,
            "templates": entry.get("templates", {}),
            "schema": entry.get("schema", ""),
            "contentType": entry.get("contentType", ""),
            "mcpType": entry.get("mcpType", ""),
            "references": entry.get("references", []),
            "workflow": entry.get("workflow", ""),
        }
        resolved[key].update(compute_knowledge_status(key, propel_file))
    result = {
        "projectName": config.get("projectName", ""),
        "description": config.get("description", ""),
        "artifacts": resolved,
    }
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Resolve project artifact details")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help="Path to project-config.json (defaults to .propel/project-config.json in project root)",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List all artifact keys")
    group.add_argument("--artifact", type=str, help="Resolve a specific artifact by key")
    group.add_argument("--all", action="store_true", help="Resolve all artifacts")
    group.add_argument("--config-field", type=str, help="Resolve a top-level config field by name")
    group.add_argument("--tribal", type=str, help="Resolve a tribal entry by label")
    group.add_argument("--derived", type=str, help="Resolve a derived entry by label")
    group.add_argument("--list-tribal", action="store_true", help="List all tribal labels")
    group.add_argument("--list-derived", action="store_true", help="List all derived labels")

    args = parser.parse_args()

    # Tribal/derived modes do not require project-config.json
    if args.list_tribal:
        list_tribal()
        return
    if args.list_derived:
        list_derived()
        return
    if args.tribal:
        resolve_tribal(args.tribal)
        return
    if args.derived:
        resolve_derived(args.derived)
        return

    config = load_config(args.config)

    try:
        if args.list:
            list_artifacts(config)
        elif args.artifact:
            resolve_artifact(config, args.artifact)
        elif args.all:
            resolve_all(config)
        elif args.config_field:
            resolve_config_field(config, args.config_field)
    except ValueError as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
