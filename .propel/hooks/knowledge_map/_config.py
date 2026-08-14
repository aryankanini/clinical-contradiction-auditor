"""Shared config loader for knowledge_map hooks. Resolves knowledge paths from project-config.json with safe fallbacks."""
import json
import os
from pathlib import Path

_DEFAULT_KNOWLEDGE_ROOT = ".propel/knowledge"
_DEFAULT_VAULT_PATH = ".propel/knowledge-vault"
_CONFIG_REL = ".propel/project-config.json"


def _normalize(p: str) -> str:
    # Strip leading "./" and normalize separators to forward slashes.
    p = p.replace("\\", "/")
    if p.startswith("./"):
        p = p[2:]
    return p.rstrip("/")


def _resolve_tokens(value: str, config: dict) -> str:
    base = config.get("basePropelPath", "./.propel/context")
    return value.replace("${basePropelPath}", base)


def load_knowledge_paths(project_dir: str | os.PathLike = ".") -> dict:
    """Return {'knowledge_root': str, 'vault_path': str, 'vault_export': bool}. Falls back to defaults on any error."""
    project_dir = Path(project_dir)
    config_path = project_dir / _CONFIG_REL
    knowledge_root = _DEFAULT_KNOWLEDGE_ROOT
    vault_path = _DEFAULT_VAULT_PATH
    vault_export = False
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        k = cfg.get("artifacts", {}).get("knowledge", {})
        if k.get("propelDirPath"):
            knowledge_root = _normalize(_resolve_tokens(k["propelDirPath"], cfg))
        if k.get("vaultPath"):
            vault_path = _normalize(_resolve_tokens(k["vaultPath"], cfg))
        vault_export = bool(k.get("vaultExport", False))
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        pass
    return {"knowledge_root": knowledge_root, "vault_path": vault_path, "vault_export": vault_export}
