#!/usr/bin/env python3
"""Batch process remaining template extraction chunks.

Usage: .venv/bin/python3 .refactor/batch_process.py [--start c33] [--count 5]

Processes chunks in batches: for each chunk, calls DeepSeek to convert,
writes template + patches route, then compiles and verifies at the end.
"""
import json, os, sys, time, urllib.request, yaml

BASE = "/Users/seanfzc/observeco"
SRC = os.path.join(BASE, "src", "observeco", "dashboard")
TMPL = os.path.join(SRC, "templates", "partials")
BATCH = json.load(open(os.path.join(BASE, ".refactor", "batch_remaining.json")))

# Load DeepSeek config
cfg = yaml.safe_load(open(os.path.join(os.environ["HOME"], ".hermes", "config.yaml")))
def find_prov(d, key):
    if isinstance(d, dict):
        if key in d and isinstance(d[key], dict) and 'api_key' in d[key]: return d[key]
        for v in d.values():
            r = find_prov(v, key)
            if r: return r
prov = find_prov(cfg, 'deepseek')

def call_deepseek(prompt_text):
    body = json.dumps({
        'model': 'deepseek-v4-flash',
        'messages': [{'role': 'user', 'content': prompt_text}],
        'temperature': 0.1,
        'max_tokens': 6000
    }).encode()
    req = urllib.request.Request(
        prov['base_url'].rstrip('/') + '/chat/completions',
        data=body,
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + prov['api_key']}
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        resp = json.load(r)
    content = resp['choices'][0]['message'].get('content') or ''
    return content, resp.get('usage', {})

def extract_blocks(text):
    """Extract TEMPLATE and ROUTE blocks from model output."""
    template = ""
    route = ""
    in_template = False
    in_route = False
    in_code = False
    for line in text.split("\n"):
        if line.strip().startswith("TEMPLATE:"):
            in_template = True
            in_route = False
            in_code = False
            continue
        if line.strip().startswith("ROUTE:"):
            in_route = True
            in_template = False
            in_code = False
            continue
        if line.strip().startswith("```"):
            if in_code:
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            if in_template:
                template += line + "\n"
            elif in_route:
                route += line + "\n"
    return template.strip(), route.strip()

def apply_patch(file_path, old, new):
    """Apply a patch to a file. Returns True on success."""
    src = open(file_path).read()
    if old not in src:
        print(f"  WARN: old_string not found in {file_path}")
        return False
    src = src.replace(old, new, 1)
    open(file_path, "w").write(src)
    return True

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="c33")
    ap.add_argument("--count", type=int, default=5)
    args = ap.parse_args()

    # Find start index
    start_idx = None
    for i, b in enumerate(BATCH):
        if b["chunk_id"] == args.start:
            start_idx = i
            break
    if start_idx is None:
        print(f"Chunk {args.start} not found")
        return

    batch = BATCH[start_idx:start_idx + args.count]
    print(f"Processing {len(batch)} chunks starting from {args.start}")

    for b in batch:
        cid = b["chunk_id"]
        print(f"\n=== {cid} {b['func']} ({b['effective_loc']} LOC) ===")

        # Build prompt
        prompt = f"""You are converting one Python FastAPI route from f-string HTML to a Jinja2 template. Output exactly two code blocks and nothing else — no explanation.

## Source route to convert

```python
{b['source']}
```

## Conversion rules

- Keep ALL Python data-gathering unchanged: the imports, db calls, all computation logic.
- Move ONLY markup into the Jinja2 template.
- The rewritten route must: (1) take `request: Request` as its first parameter (Request is already imported in the file), (2) end with `return templates.TemplateResponse(request, "partials/{cid}.html", context)` where context includes every variable the template references.
- For empty/error branches, keep them as early `return templates.TemplateResponse(...)` with the same template and flags (e.g. pass `empty=True` and use `{{% if empty %}}` in the template).
- Pre-built HTML strings (like eval_html, edits_html, status_badge) should be passed in context and rendered with `{{{{ var|safe }}}}`.
- Jinja2 equivalents: f-string `{{{{var}}}}` → `{{{{{{ var }}}}}}`, the html-accumulation loop → `{{% for x in items %}}...{{% endfor %}}`.
- IMPORTANT: `{{{{ len(x) }}}}` is NOT valid Jinja2. Use `{{{{ x|length }}}}` instead.
- If the template contains JavaScript with `{{{{` or `}}}}` characters, wrap the JS in `{{% raw %}}...{{% endraw %}}`.
- Do NOT rename any variable, CSS class, id, style, or attribute. Do NOT add or remove whitespace inside markup.
- The template file will live at templates/partials/{cid}.html and is rendered with Jinja2 autoescape ON — use `|safe` for pre-built HTML strings.

## Output format (exactly this)

TEMPLATE:
```html
<the template>
```

ROUTE:
```python
<the full replacement function including its @app.get decorator>
```"""

        content, usage = call_deepseek(prompt)
        template, route = extract_blocks(content)

        if not template or not route:
            print(f"  FAIL: could not extract blocks from model output")
            print(f"  Output preview: {content[:200]}")
            continue

        # Write template
        tmpl_path = os.path.join(TMPL, f"{cid}.html")
        open(tmpl_path, "w").write(template + "\n")
        print(f"  Template written: {tmpl_path} ({len(template)} chars)")

        # Find the old function in the source file
        fp = os.path.join(SRC, b["file"])
        src_lines = open(fp).read().split("\n")

        # Extract the old function source (from line_start to line_end)
        old_func = "\n".join(src_lines[b["line_start"]-1:b["line_end"]])

        # Apply the route patch
        if apply_patch(fp, old_func, route):
            print(f"  Route patched in {b['file']}")
        else:
            print(f"  FAIL: could not find old function in {b['file']}")
            print(f"  Looking for: {old_func[:100]}...")
            continue

        print(f"  Cost: {usage.get('total_tokens', '?')} tokens")

    print(f"\n=== Batch complete. Compile and verify ===")

if __name__ == "__main__":
    main()
