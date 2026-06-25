"""Atomic config writer for proxy base_url management.

All config mutations go through atomic_write_base_url().
The file is always fully old or fully new — never partial.
Only base_url is modified; all other user fields are preserved.
"""

from __future__ import annotations

import logging
import os
import re

from observeco.proxy.snapshot_store import set_last_write_hash, sha256_file

logger = logging.getLogger(__name__)

# Reject values that look like masked/display API keys (e.g. sk-68e...724a)
_TRUNCATED_KEY_RE = re.compile(r"\.\.\.")


def validate_no_truncated_keys(doc: dict) -> None:
    """Raise ValueError if any string value in the doc contains '...' (truncated key).

    Prevents masked display values from being persisted to disk.
    Walks the full document recursively.
    """
    _walk(doc)


def _walk(node: object) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(k, str) and _TRUNCATED_KEY_RE.search(k):
                raise ValueError(f"Truncated key detected in config key: {k!r}")
            _walk(v)
    elif isinstance(node, list):
        for item in node:
            _walk(item)
    elif isinstance(node, str):
        if _TRUNCATED_KEY_RE.search(node):
            raise ValueError(f"Truncated value detected in config: {node!r}")


def atomic_write_base_url(
    path: str,
    provider: str,
    url: str,
    adapter: type,
) -> None:
    """Write provider base_url to config atomically.

    Steps:
      1. Load the current config via the adapter (version-agnostic).
      2. Set base_url for the provider.
      3. Validate no truncated keys are present (rejects masked values).
      4. Write to a temp file, fsync, then atomic rename.
      5. Record the sha256 of the resulting file (clobber guard).
    """
    doc = adapter.load(path)
    adapter.set_base_url(doc, provider, url)
    validate_no_truncated_keys(doc)

    tmp_path = f"{path}.observeco.tmp"
    try:
        with open(tmp_path, "w") as fh:
            adapter.dump(doc, fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)  # atomic: file is always old-or-new, never partial
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    file_hash = sha256_file(path)
    set_last_write_hash(path, provider, file_hash)
    logger.debug("atomic_write_base_url: %s provider=%s url=%s hash=%s", path, provider, url, file_hash[:8])
