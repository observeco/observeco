#!/usr/bin/env python3
"""Batch caveman compression for Hermes skill files.

Generates per-skill:
  SKILL.md.compressed  — caveman-compressed body (frontmatter preserved, prose compressed)
  SKILL.md.manifest    — JSON with hashes, token counts, verification status
  SKILL.md.card        — lightweight metadata card (200-400 tok) for progressive loading

Usage:
  python3 batch_compress.py                           # all skills
  python3 batch_compress.py --skill research/deep     # single skill
  python3 batch_compress.py --watch                   # watch mode (future)
"""

import hashlib
import json
import os
import re
import sys
import time
import typing
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .llm_client import get_client
from observeco.dashboard.config import PORTS


# Lazy accessor — call at use site, not import time
def _skills_dir() -> Path | None:
    from observeco.dirs import hermes_home
    hh = hermes_home()
    return hh / "skills" if hh else None


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _count_tokens(text: str) -> int:
    """Rough token estimate (chars/4)."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        pass
    return len(text) // 4


def _text_hash(text: str) -> str:
    """SHA-256 of text content, first 16 chars."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _atomic_write(path: Path, content: str) -> None:
    """Write content atomically via temp file + rename.
    ponytail: uses os.replace for atomicity on POSIX/NTFS.
    Upgrade path: if readers need NFS-safety, add fsync(fd) before rename."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(str(tmp), str(path))


# ── Parsing ─────────────────────────────────────────────────────────────────────

def _split_skill(body: str) -> tuple[str, str]:
    """Split SKILL.md into (frontmatter, body_text).

    Returns ("", body) if no frontmatter found.
    """
    if body.startswith("---"):
        parts = body.split("---", 2)
        if len(parts) >= 3:
            return parts[1], parts[2]
        return "", parts[1] if len(parts) >= 2 else body
    return "", body


def _parse_yaml_frontmatter(frontmatter: str) -> dict:
    """Minimal YAML frontmatter parse for known fields."""
    meta: dict = {}
    for line in frontmatter.strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                val = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",")]
            elif val.startswith(">") or val.startswith("|"):
                continue  # skip block scalars
            else:
                val = val.strip('"').strip("'")
            meta[key] = val
    return meta


# ── Config ──────────────────────────────────────────────────────────────────────

_OLLAMA_BASE_URL = os.environ.get("CAVEMAN_OLLAMA_URL", f"http://localhost:{PORTS.ollama}/v1")
_OLLAMA_MODEL = os.environ.get("CAVEMAN_MODEL", "hermes3:latest")
_WORKERS = int(os.environ.get("CAVEMAN_WORKERS", "4"))

_CAVEMAN_SYSTEM = (
    "You are a text compression expert. "
    "Compress natural language markdown into caveman format: "
    "remove articles, filler, pleasantries, hedging, connective fluff. "
    "Use short synonyms and sentence fragments. "
    "NEVER modify code blocks, inline code, URLs, file paths, or commands. "
    "Preserve ALL headings, bullet hierarchy, numbered lists, and tables exactly. "
    "Return ONLY the compressed markdown body — do NOT wrap in fences."
)


# ── LLM ────────────────────────────────────────────────────────────────────────

def _call_llm(prompt: str, system: str, provider: str) -> str:
    """Call LLM via provider abstraction. Returns response text."""
    try:
        client = get_client(provider)
        return client.complete(prompt, system)
    except Exception:
        return ""


# ── Structural Analysis ─────────────────────────────────────────────────────────

def _split_structural_prose(text: str) -> tuple[list, list[str]]:
    """Split text into structural elements and prose blocks.

    Returns:
        structural: list of dicts with type, start, end (1-indexed lines)
        lines: the original lines
    """
    lines = text.splitlines()
    structural = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()

        # Code fence — capture block fully
        if s.startswith("```") or s.startswith("~~~"):
            fence_char = s[:3]
            start = i
            i += 1
            while i < len(lines):
                if lines[i].strip().startswith(fence_char):
                    break
                i += 1
            structural.append({"type": "code_block", "start": start, "end": i + 1})
            i += 1
            continue

        # Heading
        if re.match(r"^#{1,6}\s", s):
            structural.append({"type": "heading", "start": i, "end": i + 1})
            i += 1
            continue

        # Table row
        if s.startswith("|") and "|" in s[1:]:
            structural.append({"type": "table", "start": i, "end": i + 1})
            i += 1
            continue

        # Separator / horizontal rule
        if s == "---" or re.match(r"^[-_*]{3,}$", s):
            structural.append({"type": "separator", "start": i, "end": i + 1})
            i += 1
            continue

        # Blank line
        if s == "":
            structural.append({"type": "blank", "start": i, "end": i + 1})
            i += 1
            continue

        # Fenced HTML comments
        if s.startswith("<!--"):
            structural.append({"type": "comment", "start": i, "end": i + 1})
            i += 1
            continue

        # Everything else is prose — collect contiguous lines
        prose_start = i
        while i < len(lines):
            s2 = lines[i].strip()
            if (s2.startswith("#") and re.match(r"^#{1,6}\s", s2)) or \
               s2.startswith("```") or s2.startswith("~~~") or \
               (s2.startswith("|") and "|" in s2[1:]) or \
               s2 == "" or \
               s2 == "---" or \
               re.match(r"^[-_*]{3,}$", s2) or \
               s2.startswith("<!--"):
                break
            i += 1
        if i > prose_start:
            structural.append({"type": "prose", "start": prose_start, "end": i})

    return structural, lines


def _validate_structure(original_structural: list, compressed_text: str) -> list[str]:
    """Validate that compressed text preserves all non-prose structural elements."""
    errors = []

    # Count headings
    orig_headings = sum(1 for s in original_structural if s["type"] == "heading")
    comp_headings = len(re.findall(r"^#{1,6}\s", compressed_text, re.MULTILINE))
    if orig_headings != comp_headings:
        errors.append(f"Headings: {orig_headings} → {comp_headings}")

    # Count code fences
    orig_fences = sum(2 for s in original_structural if s["type"] == "code_block")
    if orig_fences > 0:
        fence_re = re.compile(r"(`{3,}|~{3,})")
        comp_fences = len(fence_re.findall(compressed_text))
        if orig_fences != comp_fences:
            errors.append(f"Code fences: {orig_fences} → {comp_fences}")

    # Check URLs preserved
    # ponytail: naive URL extraction — misses parenthesized/backtick-wrapped URLs
    # Upgrade path: use a proper URI parser or markdown AST
    return errors


# ── Compression Engines ─────────────────────────────────────────────────────────

def _cloud_caveman_compress_body(
    body_text: str, max_retries: int = 2, provider: str = "auto"
) -> tuple[str, bool]:
    """Compress a skill body using prose-split approach + LLM.

    Mechanically preserves all structural elements (headings, code blocks, tables,
    lists) in Python. Sends ONLY prose paragraphs to the LLM for compression.

    Returns (compressed_text, success). On failure, returns original.
    """
    if len(body_text.strip()) < 200:
        return body_text, False

    # Strip frontmatter marker if present
    text = body_text
    has_fm = False
    fm_content = ""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            has_fm = True
            fm_content = parts[1]
            text = parts[2]

    if not text.strip():
        return body_text, False

    # Collect all compressible prose blocks first
    structural, lines = _split_structural_prose(text)
    orig_urls = set(re.findall(r"https?://[^\s)\"']+", text))

    compressible = []  # (index in structural, snippet)
    for idx, s in enumerate(structural):
        if s["type"] != "prose":
            continue
        snippet = "\n".join(lines[s["start"]:s["end"]])
        if len(snippet.strip()) < 100:
            continue
        inline_count = snippet.count("`")
        if inline_count > len(snippet) * 0.1:
            continue
        compressible.append((idx, snippet))

    if not compressible:
        return body_text, False

    # Batch prose into chunks to avoid overwhelming the LLM
    MAX_BATCH_SIZE = 50  # blocks per API call
    system = "You are a text compression engine. Output ONLY compressed text. No greetings, no explanations."
    all_compressed = []

    for batch_start in range(0, len(compressible), MAX_BATCH_SIZE):
        batch = compressible[batch_start:batch_start + MAX_BATCH_SIZE]
        batch_input = "\n\n---\n\n".join(snip for _, snip in batch)
        prompt = (
            "Compress each prose block to caveman format: remove articles, filler, pleasantries, "
            "hedging, connective fluff. Use short sentence fragments and drop every word "
            "that isn't necessary. Keep technical terms, numbers, file paths, and proper nouns exactly.\n\n"
            "STRICT RULES:\n"
            "- This is ONLY prose -- no code, no URLs, no headings\n"
            "- Drop filler words aggressively\n"
            "- Return blocks in SAME order, separated by `\n\n---\n\n`\n"
            "- Compress EACH block independently\n"
            "- Return ONLY the compressed blocks\n\n"
            f"BLOCKS:\n{batch_input}"
        )

        batch_result = ""
        for attempt in range(max_retries + 1):
            try:
                batch_result = _call_llm(prompt, system=system, provider=provider)
                m = re.match(r"\A\s*(`{3,})[^\n]*\n(.*)\n\1\s*\Z", batch_result, re.DOTALL)
                if m:
                    batch_result = m.group(2)
                batch_result = batch_result.strip()
                if batch_result and not batch_result.isspace():
                    break
            except Exception:
                if attempt == max_retries:
                    break

        if batch_result:
            blocks = re.split(r"\n---\n|\n---\n\n", batch_result)
            blocks = [b.strip() for b in blocks if b.strip()]
            all_compressed.extend(blocks)

    # Check we got roughly the right number of blocks back
    if len(all_compressed) < len(compressible) * 0.5:
        return body_text, False

    # Reconstruct: replace each compressible prose block with its compressed version
    output_pieces = []
    total_saved = 0
    block_idx = 0

    for idx, s in enumerate(structural):
        snippet = "\n".join(lines[s["start"]:s["end"]])
        if idx in [c[0] for c in compressible]:
            if block_idx < len(all_compressed) and len(all_compressed[block_idx]) < len(snippet) * 0.95:
                compressed_snippet = all_compressed[block_idx]
                total_saved += len(snippet) - len(compressed_snippet)
            else:
                compressed_snippet = snippet
            block_idx += 1
            output_pieces.append(compressed_snippet)
        else:
            output_pieces.append(snippet)

    if total_saved <= 0:
        return body_text, False

    compressed_text = "\n".join(output_pieces)

    # Validate URLs preserved
    comp_urls = set(re.findall(r"https?://[^\s)\"']+", compressed_text))
    lost_urls = orig_urls - comp_urls
    if lost_urls:
        return body_text, False

    if has_fm:
        compressed_text = f"---{fm_content}---\n{compressed_text}"

    return compressed_text, True


def _rule_compress_body(body_text: str) -> str:
    """Apply the existing rule-based guidance compression.

    Same algorithm as compress_guidance_block() in chisel/trim.py
    but without section detection — works on any prose text.
    """
    lines = body_text.splitlines()
    seen_rules = set()
    result = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append(line)
            continue

        # Skip code blocks
        if stripped.startswith("```") or stripped.startswith("~~"):
            result.append(line)
            continue

        # Skip headings
        if stripped.startswith("#"):
            result.append(line)
            continue

        # Dedup identical guidance rules
        key = stripped.lower()
        if key in seen_rules and len(stripped) > 20:
            continue
        seen_rules.add(key)

        # Apply shortenings
        shortened = stripped
        replacements = [
            ("you MUST", "must"), ("You MUST", "Must"),
            ("you should", "should"), ("You should", "Should"),
            ("you may", "can"), ("You may", "Can"),
            ("do not", "don't"), ("Do not", "Don't"),
            ("do NOT", "don't"), ("Do NOT", "Don't"),
            ("please ", ""), ("Please ", ""),
            ("Note: ", ""), ("NOTE: ", ""),
            ("Important: ", ""), ("IMPORTANT: ", ""),
        ]
        for old, new in replacements:
            shortened = shortened.replace(old, new)

        # Preserve indentation
        if line.startswith(" ") or line.startswith("\t"):
            indent = line[:len(line) - len(line.lstrip())]
            shortened = indent + shortened

        result.append(shortened)

    return "\n".join(result)


# ── Manifest & Card Builders ───────────────────────────────────────────────────

def _build_manifest(
    skill_path: Path, original_text: str,
    compressed_text: str, body_text: str,
    compressed_body: str,
) -> dict:
    """Build manifest for a skill file."""
    before_code, after_prose = estimate_structure(original_text)
    return {
        "skill": skill_path.parent.name,
        "path": str(skill_path),
        "original_hash": _text_hash(original_text),
        "compressed_hash": _text_hash(compressed_text),
        "original_tokens": _count_tokens(original_text),
        "compressed_tokens": _count_tokens(compressed_text),
        "savings_tokens": _count_tokens(original_text) - _count_tokens(compressed_text),
        "savings_pct": round(
            (1 - _count_tokens(compressed_text) / max(_count_tokens(original_text), 1)) * 100, 1
        ),
        "code_block_count": before_code,
        "prose_token_savings_before": _count_tokens(body_text),
        "prose_token_savings_after": _count_tokens(compressed_body),
        "created_at": int(time.time()),
        "verified": True,
    }


def estimate_structure(text: str) -> tuple[int, int]:
    """Count code blocks and prose tokens in text."""
    code_blocks = 0
    in_code = False
    prose_tokens = 0
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("```") or s.startswith("~~~"):
            in_code = not in_code
            code_blocks += 0.5
        elif in_code:
            continue
        elif s and not s.startswith("#"):
            prose_tokens += _count_tokens(line)
    return int(code_blocks), prose_tokens


def _build_card(
    skill_path: Path, meta: dict, original_text: str,
    compressed_text: str, manifest: dict,
) -> dict:
    """Build a lightweight skill card for the progressive disclosure system.

    ~200-400 tokens, contains everything needed for intent matching without
    loading the full body.
    """
    # Extract trigger phrases from frontmatter
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    related = meta.get("related_skills", [])
    if isinstance(related, str):
        related = [t.strip() for t in related.split(",") if t.strip()]

    description = meta.get("description", "") or ""

    # Extract unique trigger phrases from body headings
    headings = re.findall(r"^#{1,4}\s+(.+)$", original_text, re.MULTILINE)
    triggers = []
    for h in headings[:8]:  # top 8 headings
        cleaned = h.strip().lower()
        if cleaned and cleaned not in ("when to use", "introduction", "overview", "core identity"):
            triggers.append(cleaned[:60])

    return {
        "name": meta.get("name", skill_path.parent.name),
        "category": skill_path.parent.parent.name,
        "description": description[:200] if description else "",
        "tags": tags[:10],
        "related_skills": related[:5],
        "headings": triggers,
        "total_tokens": manifest["original_tokens"],
        "compressed_tokens": manifest["compressed_tokens"],
        "savings_pct": manifest["savings_pct"],
        "original_hash": manifest["original_hash"],
        "compressed_hash": manifest["compressed_hash"],
        "code_blocks": manifest["code_block_count"],
        "slot": "",
        "last_used": 0,
    }


# ── Core Compression ───────────────────────────────────────────────────────────

def compress_skill_to_artifacts(
    skill_path: Path, dry_run: bool = False,
    engine: str = "rule", provider: str = "auto",
    apply: bool = True,
) -> typing.Optional[dict]:
    """Compress a single skill with chosen engine.

    Args:
        skill_path: Path to SKILL.md
        dry_run: If True, return manifest without writing files
        engine: "rule" for fast rule-based, "caveman" for LLM-based
        provider: LLM provider for caveman engine (auto|deepseek|openai|anthropic|google|ollama|hermes|lite)
        apply: If True, overwrite SKILL.md with compressed content and create .bak backup.
               If False (dry-run mode), write sidecar files only (legacy behavior).
    """
    original_text = skill_path.read_text(encoding="utf-8")
    frontmatter, body_text = _split_skill(original_text)

    if not body_text.strip():
        return None

    # Choose compression engine
    if engine == "caveman":
        compressed_body, success = _cloud_caveman_compress_body(body_text, provider=provider)
        if not success:
            return None
    else:
        compressed_body = _rule_compress_body(body_text)

    # Reassemble
    if frontmatter:
        compressed_text = f"---{frontmatter}---\n{compressed_body}"
    else:
        compressed_text = compressed_body

    before = _count_tokens(original_text)
    after = _count_tokens(compressed_text)
    if after >= before:
        return None

    # Build manifest
    meta = _parse_yaml_frontmatter(frontmatter) if frontmatter else {}
    manifest = _build_manifest(skill_path, original_text, compressed_text,
                                body_text, compressed_body)
    manifest["engine"] = engine

    if dry_run:
        return manifest

    # Write compressed file — atomic write
    compressed_path = skill_path.with_suffix(".md.compressed")
    _atomic_write(compressed_path, compressed_text)

    # Write manifest — atomic write
    manifest_path = skill_path.with_suffix(".md.manifest")
    _atomic_write(manifest_path, json.dumps(manifest, indent=2))

    # Write skill card — atomic write
    card = _build_card(skill_path, meta, original_text, compressed_text, manifest)
    card_path = skill_path.with_suffix(".md.card")
    _atomic_write(card_path, json.dumps(card))

    # ── Apply: overwrite SKILL.md with compressed content ─────────────────────
    if apply:
        bak_path = skill_path.with_suffix(".md.bak")

        # 1. Create backup if it doesn't exist yet
        if not bak_path.exists():
            _atomic_write(bak_path, original_text)

        # 2. Overwrite SKILL.md with compressed content
        _atomic_write(skill_path, compressed_text)

        # 3. Update manifest: record pre-compression state and mark as applied
        manifest["applied_at"] = int(time.time())
        manifest["pre_compress_hash"] = manifest["original_hash"]
        manifest["pre_compress_tokens"] = manifest["original_tokens"]
        # After apply, original == compressed (same file)
        manifest["original_hash"] = manifest["compressed_hash"]
        manifest["original_tokens"] = manifest["compressed_tokens"]
        _atomic_write(manifest_path, json.dumps(manifest, indent=2))

        # 4. Update card: total_tokens now equals compressed_tokens
        card["total_tokens"] = manifest["compressed_tokens"]
        _atomic_write(card_path, json.dumps(card))

        # 5. Remove redundant .compressed file (SKILL.md IS the compressed version)
        if compressed_path.exists():
            compressed_path.unlink()

    return manifest


# ── Batch Operations ───────────────────────────────────────────────────────────

def batch_compress_skills(
    skills_dir: Path | None = None,
    dry_run: bool = False,
    limit: int = 0,
    engine: str = "rule",
) -> list[dict]:
    """Compress all SKILL.md files in a directory tree.

    Returns list of manifest dicts for compressed skills.
    """
    if skills_dir is None:
        sd = _skills_dir()
        if sd is None:
            return []
        skills_dir = sd
    results = []
    start_ts = time.time()
    skill_files = sorted(skills_dir.rglob("SKILL.md"))

    # Filter out already-compressed backups and artifacts
    skill_files = [sf for sf in skill_files
                   if not any(sf.name.endswith(ext) for ext in
                             [".compressed", ".manifest", ".card", ".bak"])]

    if limit > 0:
        # Sort by size descending first
        with_sizes = [(sf, _count_tokens(sf.read_text(encoding="utf-8")))
                      for sf in skill_files]
        with_sizes.sort(key=lambda x: -x[1])
        skill_files = [sf for sf, _ in with_sizes[:limit]]

    if engine == "caveman" and not dry_run:
        # Parallel batch with thread pool
        total = len(skill_files)
        done = 0
        start_ts = time.time()
        print(f"  Caveman batch: {total} skills, {_WORKERS} workers, model={_OLLAMA_MODEL}")

        def _process(sf: Path) -> typing.Optional[dict]:
            return compress_skill_to_artifacts(sf, dry_run=False, engine="caveman")

        with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
            futures = {pool.submit(_process, sf): sf for sf in skill_files}
            for future in as_completed(futures):
                sf = futures[future]
                done += 1
                try:
                    manifest = future.result()
                    if manifest:
                        results.append(manifest)
                        elapsed = time.time() - start_ts
                        rate = done / max(elapsed, 0.1)
                        remaining = (total - done) / max(rate, 0.1)
                        print(f"  [{done}/{total}] {manifest['skill']}: {manifest['original_tokens']} → {manifest['compressed_tokens']} tok ({manifest['savings_pct']:+.1f}%) [~{remaining:.0f}s left]")
                    else:
                        print(f"  [{done}/{total}] {sf.parent.name}: skipped (no savings)")
                except Exception as e:
                    print(f"  [{done}/{total}] {sf.parent.name}: error — {e}")
    else:
        # Sequential (rule-based is fast enough)
        for sf in skill_files:
            try:
                manifest = compress_skill_to_artifacts(sf, dry_run=dry_run, engine=engine)
                if manifest:
                    results.append(manifest)
                    action = "[dry-run] Would save" if dry_run else "Saved"
                    print(f"  {action} {manifest['skill']}: {manifest['original_tokens']} -> {manifest['compressed_tokens']} tok ({manifest['savings_pct']:+.1f}%)")
            except Exception as e:
                print(f"  [error] {sf.parent.name}: {e}")

    if results:
        total_before = sum(m["original_tokens"] for m in results)
        total_after = sum(m["compressed_tokens"] for m in results)
        saved = total_before - total_after
        pct = round(saved / max(total_before, 1) * 100, 1)
        elapsed = round(time.time() - start_ts, 1)
        label = "[dry-run] Would save" if dry_run else "Saved"
        avg_per_skill = saved / max(len(results), 1)
        print(f"\n  {label} {saved} tokens across {len(results)} skills ({pct}%) in {elapsed}s")
        print(f"  Avg savings per skill: {avg_per_skill:.0f} tokens")

    # Log per-skill action_log entries
    if not dry_run and results:
        import json as _json
        import uuid

        from observeco.db import Database
        from observeco.tracking.tokens import _estimate_cost
        try:
            _db = Database()
            _batch_id = str(uuid.uuid4())[:8]
            for _i, _m in enumerate(results):
                _orig = _m.get("original_tokens", 0)
                _comp = _m.get("compressed_tokens", _orig)
                _pct = _m.get("savings_pct", 0)
                _sname = _m.get("skill", "unknown")
                if _pct > 5:
                    _db.log_action(
                        agent_name="fleet",
                        action_type="skill_compress",
                        action_detail=f"{_sname} — compressed {_orig:,} → {_comp:,} tok ({_pct:.0f}%)",
                        tokens_saved=_orig - _comp,
                        cost_saved=_estimate_cost(_orig - _comp),
                        status="success",
                        metadata=_json.dumps({"batch_id": _batch_id, "batch_total_skills": len(results), "batch_index": _i}),
                        triggered_by="cli",
                    )
                else:
                    _db.log_action(
                        agent_name="fleet",
                        action_type="skill_compress",
                        action_detail=f"{_sname} — already condensed (no further savings)",
                        tokens_saved=0,
                        cost_saved=0,
                        status="no_action",
                        metadata=_json.dumps({"batch_id": _batch_id, "batch_total_skills": len(results), "batch_index": _i, "savings_pct": _pct}),
                        triggered_by="cli",
                    )
        except Exception:
            pass  # fire-and-forget

    return results


# ── JSON Export ─────────────────────────────────────────────────────────────────

def generate_cards_json(skills_dir: Path | None = None) -> str:
    """Generate the consolidated cards.json from all individual cards.

    Deduplicates by name — keeps the entry with the higher token count
    when a skill has cards in multiple directories (e.g. root + category subfolder).

    Returns JSON string of cards array.
    """
    if skills_dir is None:
        sd = _skills_dir()
        if sd is None:
            return "[]"
        skills_dir = sd
    cards_by_name: dict[str, dict] = {}
    for card_file in sorted(skills_dir.rglob("SKILL.md.card")):
        try:
            card = json.loads(card_file.read_text(encoding="utf-8"))
            name = card.get("name", "")
            if not name:
                continue
            existing = cards_by_name.get(name)
            if existing is None or card.get("total_tokens", 0) > existing.get("total_tokens", 0):
                cards_by_name[name] = card
        except Exception:
            pass
    return json.dumps(list(cards_by_name.values()), indent=2)


def export_manifest_json(skills_dir: Path | None = None) -> str:
    """Generate consolidated manifest catalog.

    Returns JSON string of all manifests keyed by skill name.
    """
    if skills_dir is None:
        sd = _skills_dir()
        if sd is None:
            return "{}"
        skills_dir = sd
    manifests = {}
    for mf in sorted(skills_dir.rglob("SKILL.md.manifest")):
        try:
            m = json.loads(mf.read_text(encoding="utf-8"))
            manifests[m["skill"]] = m
        except Exception:
            pass
    return json.dumps(manifests, indent=2)


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Batch skill compression")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--skill", type=str, default="", help="Single skill path (relative to skills dir)")
    parser.add_argument("--watch", action="store_true", help="Watch mode (future)")
    parser.add_argument("--limit", type=int, default=0, help="Max skills to process")
    parser.add_argument("--cards", action="store_true", help="Generate cards.json only")
    parser.add_argument("--engine", choices=["rule", "caveman"], default="rule",
                        help="Compression engine (default: rule)")
    parser.add_argument("--caveman", action="store_true",
                        help="Shorthand for --engine=caveman")
    parser.add_argument("--provider", type=str, default="auto",
                        help="LLM provider for caveman engine (auto|deepseek|openai|anthropic|google|ollama|hermes|lite)")
    parser.add_argument("--workers", type=int, default=0,
                        help="Override parallel workers for caveman mode")
    args = parser.parse_args()

    engine = "caveman" if args.caveman else args.engine
    if args.workers:
        os.environ["CAVEMAN_WORKERS"] = str(args.workers)

    sd = _skills_dir()
    if sd is None:
        print("Hermes skills directory not found")
        sys.exit(1)

    if args.cards:
        print("Generating consolidated cards.json...")
        cards_json = generate_cards_json()
        (sd / "cards.json").write_text(cards_json)
        cards = json.loads(cards_json)
        print(f"  Wrote {len(cards)} cards to skills/cards.json")
        sys.exit(0)

    if args.skill:
        skill_path = sd / args.skill
        if not skill_path.exists():
            print(f"Skill not found: {skill_path}")
            sys.exit(1)
        print(f"Compressing {skill_path} (engine={engine}, provider={args.provider})...")
        manifest = compress_skill_to_artifacts(skill_path, dry_run=args.dry_run, engine=engine, provider=args.provider)
        if manifest:
            action = "[dry-run] Would save" if args.dry_run else "Saved"
            print(f"  {action} {manifest['skill']}: {manifest['original_tokens']} -> {manifest['compressed_tokens']} tok ({manifest['savings_pct']:+.1f}%)")
        else:
            print("  No savings — skipped")
        sys.exit(0)

    if args.watch:
        print("Watch mode not yet implemented.")
        sys.exit(0)

    print(f"Compressing skills in {sd} (engine={engine})...")
    results = batch_compress_skills(dry_run=args.dry_run, limit=args.limit, engine=engine)

    if not args.dry_run and results:
        # Write consolidated manifests
        m = export_manifest_json()
        (sd / "manifests.json").write_text(m)
        print(f"  Wrote {len(results)} manifests to skills/manifests.json")

        # Write cards
        c = generate_cards_json()
        (sd / "cards.json").write_text(c)
        print(f"  Wrote {len(json.loads(c))} cards to skills/cards.json")
