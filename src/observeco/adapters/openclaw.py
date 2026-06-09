"""OpenClaw adapter — hook registration and configuration."""

import re
from pathlib import Path
from typing import Optional

HOOKS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "hooks"

# Expected hook definitions with validation rules
EXPECTED_HOOKS = {
    "self-healing": {
        "exports": ["beforeToolCall", "afterToolCall"],
        "required": True,
        "purpose": "Tool call retry with exponential backoff",
    },
    "outcome-tracking": {
        "exports": ["afterAssistantResponse", "beforeToolCall"],
        "required": True,
        "purpose": "Task outcome logging and feedback collection",
    },
    "knowledge-graph": {
        "exports": [],
        "required": False,
        "purpose": "Knowledge graph context injection",
    },
    "model-routing": {
        "exports": [],
        "required": False,
        "purpose": "Model/provider routing decisions",
    },
    "waitlist": {
        "exports": [],
        "required": False,
        "purpose": "User waitlist management",
    },
}


def _parse_hook_metadata(hook_path: Path) -> Optional[dict]:
    """Extract name, version, exports from a JS hook file.

    Uses lightweight regex parsing rather than a full JS AST.
    Returns None if the file can't be parsed.
    """
    try:
        text = hook_path.read_text()
    except OSError:
        return None

    name = hook_path.stem
    version = "unknown"
    exports = []

    # Extract module.exports
    m = re.search(r'module\.exports\s*=\s*\{([^}]+)\}', text, re.DOTALL)
    if m:
        exports_block = m.group(1)
        exported_keys = re.findall(r'(\w+)\s*:', exports_block)
        exports = exported_keys

    # Extract name from module.exports
    m = re.search(r"name\s*:\s*'([^']+)'", text)
    if m:
        name = m.group(1)

    # Extract version
    m = re.search(r"version\s*:\s*'([^']+)'", text)
    if m:
        version = m.group(1)

    return {
        "name": name,
        "file": hook_path.name,
        "path": str(hook_path),
        "version": version,
        "exports": exports,
    }


def list_hooks() -> list[dict]:
    """List all available OpenClaw hooks with metadata."""
    if not HOOKS_DIR.is_dir():
        return []

    results = []
    for hook_file in sorted(HOOKS_DIR.glob("*.js")):
        meta = _parse_hook_metadata(hook_file)
        if meta:
            results.append(meta)
    return results


def validate_hooks() -> list[dict]:
    """Validate that required hooks are present and correctly structured.

    Returns a list of validation results, one per expected hook.
    """
    available = {h["name"]: h for h in list_hooks()}
    results = []

    for hook_name, expected in EXPECTED_HOOKS.items():
        result = {
            "name": hook_name,
            "present": hook_name in available,
            "required": expected["required"],
            "purpose": expected["purpose"],
            "status": "missing" if hook_name not in available else "ok",
            "issues": [],
        }

        if hook_name in available:
            meta = available[hook_name]
            # Check required exports
            missing_exports = [e for e in expected["exports"] if e not in meta.get("exports", [])]
            if missing_exports:
                result["status"] = "partial"
                result["issues"].append(f"Missing exports: {', '.join(missing_exports)}")
        else:
            if expected["required"]:
                result["status"] = "critical"
                result["issues"].append("Required hook not found")

        results.append(result)

    return results


def get_hook_config() -> dict:
    """Generate OpenClaw-compatible hook configuration.

    Returns a dict that can be fed directly into OpenClaw's config.
    """
    hooks = list_hooks()
    validation = validate_hooks()

    critical_missing = [v["name"] for v in validation if v["status"] == "critical"]

    config = {
        "hooks_dir": str(HOOKS_DIR),
        "enabled_hooks": {h["name"]: True for h in hooks},
        "hook_files": [h["file"] for h in hooks],
        "validation": {
            "status": "failed" if critical_missing else "ok",
            "missing_required": critical_missing,
        },
    }

    return config


def register_hooks(hooks_dir: Optional[str] = None) -> dict:
    """Validate hooks in the given directory and return config.

    Args:
        hooks_dir: Path to hooks directory. Defaults to hooks/ next to codebase.

    Returns:
        Dict with validation results and generated config.
    """
    global HOOKS_DIR
    if hooks_dir:
        HOOKS_DIR = Path(hooks_dir)

    available = list_hooks()
    validation = validate_hooks()

    return {
        "hooks_found": len(available),
        "hooks": available,
        "validation": validation,
        "config": get_hook_config(),
    }
