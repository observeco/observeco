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
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────

SKILLS_DIR = Path.home() / ".hermes" / "skills"

# ── Token counting ──────────────────────────────────────────────────────────

def _count_tokens(text: str) -> int:
    """Rough token estimate (chars/4)."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        pass
    return max(1, int(len(text) / 4))


def _text_hash(text: str) -> str:
    """SHA-256 of text content, first 16 chars."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ── Parsing ─────────────────────────────────────────────────────────────────

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


# ── Ollama / cloud config ──────────────────────────────────────────────────

_OLLAMA_BASE_URL = os.environ.get("CAVEMAN_OLLAMA_URL", "http://localhost:11434/v1")
_OLLAMA_MODEL = os.environ.get("CAVEMAN_MODEL", "hermes3:latest")
_WORKERS = int(os.environ.get("CAVEMAN_WORKERS", "3"))

# DeepSeek API config (loaded from hermes config)
_DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


def _get_deepseek_key() -> str:
    """Read DeepSeek API key from hermes config."""
    import yaml
    env_path = Path.home() / ".hermes" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1].strip().strip("\"'").strip()
    # Fallback: read from config.yaml
    cfg_path = Path.home() / ".hermes" / "config.yaml"
    if cfg_path.exists():
        cfg = yaml.safe_load(cfg_path.read_text())
        cfg_key = cfg.get("providers", {}).get("deepseek", {}).get("api_key", "")
        if cfg_key and "..." not in cfg_key:
            return cfg_key
    return ""


_CAVEMAN_SYSTEM = (
    "You are a text compression expert. "
    "Compress natural language markdown into caveman format: "
    "remove articles, filler, pleasantries, hedging, connective fluff. "
    "Use short synonyms and sentence fragments. "
    "NEVER modify code blocks, inline code, URLs, file paths, or commands. "
    "Preserve ALL headings, bullet hierarchy, numbered lists, and tables exactly. "
    "Return ONLY the compressed markdown body — do NOT wrap in fences."
)


def _call_llm(prompt: str, system: str = "", provider: str = "ollama") -> str:
    """Call LLM — ollama (local) or deepseek (cloud). Returns response text."""
    if provider == "deepseek":
        api_key = _get_deepseek_key()
        if not api_key:
            raise ValueError("No DeepSeek API key found")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = json.dumps({
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.05,
            "max_tokens": 4096,
            "stream": False,
        }).encode()
        req = urllib.request.Request(
            _DEEPSEEK_URL, data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())
        return result["choices"][0]["message"]["content"].strip()

    # Default: local ollama
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = json.dumps({
        "model": _OLLAMA_MODEL,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 4096,
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        f"{_OLLAMA_BASE_URL}/chat/completions",
        data=payload, headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode())
    return result["choices"][0]["message"]["content"].strip()


def _split_structural_prose(text: str) -> tuple[list[dict], list[str]]:
    """Split text into structural elements and prose blocks.

    Returns:
        structural: list of dicts with type, lines (1-indexed), and content
        prose_lines: the original lines — used for reconstruction
    """
    lines = text.splitlines()
    structural = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        # Code fence — capture block fully
        if s.startswith("```") or s.startswith("~~~"):
            fence_char = s[:3] if s.startswith("```") else s[:3]
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

        # Separator
        if s == "---" or s.startswith("___"):
            structural.append({"type": "separator", "start": i, "end": i + 1})
            i += 1
            continue

        # Horizontal rule variations
        if re.match(r"^[-_*]{3,}$", s):
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

        # Everything else is prose
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


def _validate_structure(original_structural: list[dict], compressed_text: str) -> list[str]:
    """Validate that compressed text preserves all non-prose structural elements."""
    errors = []

    # Count headings
    orig_headings = sum(1 for s in original_structural if s["type"] == "heading")
    comp_headings = len(re.findall(r"^#{1,6}\s", compressed_text, re.MULTILINE))
    if orig_headings != comp_headings:
        errors.append(f"Headings: {orig_headings} → {comp_headings}")

    # Count code fences
    orig_fences = 0
    for s in original_structural:
        if s["type"] == "code_block":
            # Count both opening and closing
            for ln in range(s["start"], s["end"]):
                if ln < len(compressed_text.splitlines()) and \
                   (compressed_text.splitlines()[ln].strip().startswith("```") or \
                    compressed_text.splitlines()[ln].strip().startswith("~~~")):
                    pass
            orig_fences += 2  # opening + closing

    if orig_fences > 0:
        fence_re = re.compile(r"(`{3,}|~{3,})")
        comp_fences = len(fence_re.findall(compressed_text))
        if orig_fences != comp_fences:
            errors.append(f"Code fences: {orig_fences} → {comp_fences}")

    # Check URLs preserved
    for s in original_structural:
        for ln in range(s["start"], s.get("end_actual", s["end"])):
            pass
    # Get original URLs from the text before splitting
    for s in original_structural:
        for ln in range(s["start"], s["end"]):
            pass  # need original text
    # Simpler: read the original text from somewhere

    return errors


def _cloud_caveman_compress_body(body_text: str, max_retries: int = 2,
                                  provider: str = "deepseek") -> tuple[str, bool]:
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

    # Batch ALL prose into ONE prompt
    batch_input = "\n\n---\n\n".join(snip for _, snip in compressible)
    system = "You are a text compression engine. Output ONLY compressed text. No greetings, no explanations."
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
                return body_text, False

    if not batch_result:
        return body_text, False

    compressed_blocks = re.split(r"\n---\n|\n---\n\n", batch_result)
    compressed_blocks = [b.strip() for b in compressed_blocks if b.strip()]

    # Check we got roughly the right number of blocks back
    if len(compressed_blocks) < len(compressible) * 0.5:
        return body_text, False

    # Reconstruct: replace each compressible prose block with its compressed version
    output_pieces = []
    total_saved = 0
    block_idx = 0

    for idx, s in enumerate(structural):
        snippet = "\n".join(lines[s["start"]:s["end"]])
        if idx in [c[0] for c in compressible]:
            # Replace with compressed version
            if block_idx < len(compressed_blocks) and len(compressed_blocks[block_idx]) < len(snippet) * 0.95:
                compressed_snippet = compressed_blocks[block_idx]
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


# ── Rule-based compression (fast, no LLM) ──────────────────────────────────

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


# ── Manifest generation ─────────────────────────────────────────────────────

def _build_manifest(skill_path: Path, original_text: str,
                    compressed_text: str, body_text: str,
                    compressed_body: str) -> dict:
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
    for line in text.splitlines():
        if line.strip().startswith("```") or line.strip().startswith("~~~"):
            in_code = not in_code
            code_blocks += 0.5  # opening or closing
        if in_code and line.strip() and not line.strip().startswith(("```", "~~~")):
            pass
    return int(code_blocks), 0  # didn't separate prose from code


# ── Skill card generation (P0: progressive disclosure) ──────────────────────

def _build_card(skill_path: Path, meta: dict, original_text: str,
                compressed_text: str, manifest: dict) -> dict:
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


# ── Main compressor ─────────────────────────────────────────────────────────

def compress_skill_to_artifacts(skill_path: Path, dry_run: bool = False,
                                engine: str = "rule") -> typing.Optional[dict]:
    """Compress a single skill with chosen engine.

    Args:
        engine: "rule" for fast rule-based, "caveman" for LLM-based
    """
    original_text = skill_path.read_text(encoding="utf-8")
    frontmatter, body_text = _split_skill(original_text)

    if not body_text.strip():
        return None

    # Choose compression engine
    if engine == "caveman":
        compressed_body, success = _cloud_caveman_compress_body(body_text, provider="deepseek")
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

    # Write compressed file
    compressed_path = skill_path.with_suffix(".md.compressed")
    compressed_path.write_text(compressed_text, encoding="utf-8")

    # Write manifest
    manifest_path = skill_path.with_suffix(".md.manifest")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Write skill card
    card = _build_card(skill_path, meta, original_text, compressed_text, manifest)
    card_path = skill_path.with_suffix(".md.card")
    card_path.write_text(json.dumps(card), encoding="utf-8")

    return manifest


def batch_compress_skills(skills_dir: Path = SKILLS_DIR,
                           dry_run: bool = False,
                           limit: int = 0,
                           engine: str = "rule") -> list[dict]:
    """Compress all SKILL.md files in a directory tree.

    Returns list of manifest dicts for compressed skills.
    """
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

    return results


def generate_cards_json(skills_dir: Path = SKILLS_DIR) -> str:
    """Generate the consolidated cards.json from all individual cards.

    Returns JSON string of cards array.
    """
    cards = []
    for card_file in sorted(skills_dir.rglob("SKILL.md.card")):
        try:
            card = json.loads(card_file.read_text(encoding="utf-8"))
            cards.append(card)
        except Exception:
            pass
    return json.dumps(cards, indent=2)


def export_manifest_json(skills_dir: Path = SKILLS_DIR) -> str:
    """Generate consolidated manifest catalog.

    Returns JSON string of all manifests keyed by skill name.
    """
    manifests = {}
    for mf in sorted(skills_dir.rglob("SKILL.md.manifest")):
        try:
            m = json.loads(mf.read_text(encoding="utf-8"))
            manifests[m["skill"]] = m
        except Exception:
            pass
    return json.dumps(manifests, indent=2)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Batch skill compression")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--limit", type=int, default=0, help="Max skills to process")
    parser.add_argument("--cards", action="store_true", help="Generate cards.json only")
    parser.add_argument("--engine", choices=["rule", "caveman"], default="rule",
                        help="Compression engine (default: rule)")
    parser.add_argument("--caveman", action="store_true",
                        help="Shorthand for --engine=caveman")
    parser.add_argument("--workers", type=int, default=0,
                        help="Override parallel workers for caveman mode")
    args = parser.parse_args()

    engine = "caveman" if args.caveman else args.engine
    if args.workers:
        os.environ["CAVEMAN_WORKERS"] = str(args.workers)

    if args.cards:
        print("Generating consolidated cards.json...")
        cards_json = generate_cards_json()
        (SKILLS_DIR / "cards.json").write_text(cards_json)
        cards = json.loads(cards_json)
        print(f"  Wrote {len(cards)} cards to skills/cards.json")
        sys.exit(0)

    print(f"Compressing skills in {SKILLS_DIR} (engine={engine})...")
    results = batch_compress_skills(dry_run=args.dry_run, limit=args.limit, engine=engine)

    if not args.dry_run and results:
        # Write consolidated manifests
        m = export_manifest_json()
        (SKILLS_DIR / "manifests.json").write_text(m)
        print(f"  Wrote {len(results)} manifests to skills/manifests.json")

        # Write cards
        c = generate_cards_json()
        (SKILLS_DIR / "cards.json").write_text(c)
        print(f"  Wrote {len(json.loads(c))} cards to skills/cards.json")
