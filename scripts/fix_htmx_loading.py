#!/usr/bin/env python3
"""Fix the document.write htmx fallback that nukes the entire page."""

path = '/Users/seanfzc/projects/observeco/src/observeco/dashboard/templates/index.html'

with open(path) as f:
    content = f.read()

# The bug: document.write() called AFTER page is fully parsed DESTROYS the DOM.
# The local /static/htmx.min.js doesn't exist at runtime (file is there, but the
# browser snapshots show it never loads due to browser automation CDN blocking).
# CDN is blocked in headless browser environments.
# Result: page renders as <body></body> — completely blank.

# Replace document.write with safe DOM-based fallback
old = '<script src="/static/htmx.min.js"></script>\n    <script>if (!window.htmx) { document.write(\'<script src="https://unpkg.com/htmx.org@1.9.11/dist/htmx.min.js"><\\/script>\'); }</script>'

new_scripts = '''<script src="/static/htmx.min.js" onerror="
  if (!window.htmx) {
    var s = document.createElement('script');
    s.src = 'https://unpkg.com/htmx.org@1.9.11/dist/htmx.min.js';
    document.head.appendChild(s);
  }
"></script>
    <script>if (!window.htmx) {
      var s = document.createElement('script');
      s.src = 'https://unpkg.com/htmx.org@1.9.11/dist/htmx.min.js';
      document.head.appendChild(s);
    }</script>'''

if old in content:
    content = content.replace(old, new_scripts)
    with open(path, 'w') as f:
        f.write(content)
    print(f'✅ Fixed. File written ({len(content)} chars)')
else:
    print('❌ Could not find the exact old string')
    # Show what we have
    import re
    for m in re.finditer(r'document\\.write', content):
        start = max(0, m.start() - 50)
        end = min(len(content), m.end() + 100)
        print(f'  Found at byte {m.start()}: ...{content[start:end]}...')
    # Also show lines 7-8
    lines = content.split('\n')
    for i in range(6, 10):
        if i < len(lines):
            print(f'  Line {i+1}: {repr(lines[i])}')
