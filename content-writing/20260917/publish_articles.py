#!/usr/bin/env python3
"""Publish the two 20260917 ObserveCo X Articles via the direct X Articles API.

Self-contained: reads X creds from the local Postiz stack (no secrets in this file).
Handles the media embeds, the markdown->content_state conversion, and the
draft-then-publish race (waits before publishing).

Run:  /usr/bin/python3 publish_articles.py
"""
from __future__ import annotations

import base64
import datetime
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

DIR = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(DIR, 'x-article-publish.log')

# ---------------------------------------------------------------- credentials

def _compose_creds():
    p = os.path.expanduser('~/postiz/docker-compose.yaml')
    t = open(p).read()
    mk = re.search(r'X_API_KEY\s*[:=]\s*(\S+)', t)
    ms = re.search(r'X_API_SECRET\s*[:=]\s*(\S+)', t)
    if not mk or not ms:
        raise RuntimeError('X_API_KEY / X_API_SECRET not found in postiz docker-compose.yaml')
    return mk.group(1).strip('"\''), ms.group(1).strip('"\'')


def _user_token():
    out = subprocess.run(
        ['docker', 'exec', 'postiz-postgres', 'psql', '-U', 'postiz-user',
         '-d', 'postiz-db-local', '-t', '-A', '-c',
         'SELECT "token" FROM "Integration" WHERE "providerIdentifier"=\'x\' LIMIT 1;'],
        capture_output=True, text=True, check=True).stdout.strip()
    tok, sec = out.split(':', 1)
    return tok, sec


def _pct(s):
    return urllib.parse.quote(str(s), safe='~')


def _auth(method, url):
    ck, cs = _compose_creds()
    tok, tsec = _user_token()
    parsed = urllib.parse.urlsplit(url)
    qs = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    base_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, '', ''))
    params = {
        'oauth_consumer_key': ck,
        'oauth_nonce': uuid.uuid4().hex,
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_timestamp': str(int(time.time())),
        'oauth_token': tok,
        'oauth_version': '1.0',
    }
    allp = dict(params)
    allp.update({k: v for k, v in qs.items() if k != 'oauth_signature'})
    enc = sorted((_pct(k), _pct(v)) for k, v in allp.items())
    base = '&'.join([method.upper(), _pct(base_url),
                     _pct('&'.join(f'{k}={v}' for k, v in enc))])
    key = f'{_pct(cs)}&{_pct(tsec)}'
    params['oauth_signature'] = base64.b64encode(
        hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    return 'OAuth ' + ', '.join(f'{_pct(k)}="{_pct(v)}"' for k, v in sorted(params.items()))


def call(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method.upper())
    req.add_header('Authorization', _auth(method, url))
    if data:
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return -1, f'{type(e).__name__}: {e}'


def log(msg):
    line = f'[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {msg}'
    print(line, flush=True)
    with open(LOG, 'a') as f:
        f.write(line + '\n')


# ---------------------------------------------------------------- media

def upload(path):
    boundary = '----x' + uuid.uuid4().hex
    img = open(path, 'rb').read()
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="media"; '
            f'filename="{os.path.basename(path)}"\r\nContent-Type: image/png\r\n\r\n'
            ).encode() + img + b'\r\n'
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="media_category"'
             f'\r\n\r\ntweet_image\r\n').encode()
    body += f'--{boundary}--\r\n'.encode()
    url = 'https://api.x.com/2/media/upload'
    for attempt in range(1, 6):
        req = urllib.request.Request(url, data=body, method='POST')
        req.add_header('Authorization', _auth('POST', url))
        req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                d = json.loads(r.read().decode())['data']
                return d.get('id') or d.get('media_id_string')
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                time.sleep(45 * attempt)
                continue
            log(f'    upload FAILED {e.code}: {e.read().decode()[:160]}')
            return None
    return None


# ---------------------------------------------------------------- payload

def _strip(s):
    spans, out, pos = [], [], 0
    for m in re.finditer(r'\*\*(.+?)\*\*', s):
        out.append(s[pos:m.start()])
        seg = m.group(1)
        out.append(seg)
        spans.append({'offset': sum(len(x) for x in out) - len(seg),
                      'length': len(seg), 'style': 'bold'})
        pos = m.end()
    out.append(s[pos:])
    text = ''.join(out)
    text = re.sub(r'(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)', r'\1', text)
    return text.replace('`', ''), spans


def build(md_path, title, figs, banner=None):
    src = open(md_path).read()
    body = src[src.index('### '):src.index('# PART TWO')]
    entities, blocks = [], []

    cover = None
    if banner:
        mid = upload(os.path.join(DIR, banner))
        if mid:
            cover = {'media_category': 'tweet_image', 'media_id': str(mid)}
            log(f'    cover uploaded ({mid})')

    def add_image(png):
        mid = upload(os.path.join(DIR, png))
        if not mid:
            return
        entities.append({'key': str(len(entities)),
                         'value': {'type': 'image', 'mutability': 'immutable',
                                   'data': {'media_items': [
                                       {'media_category': 'tweet_image', 'media_id': str(mid)}]}}})
        blocks.append({'text': ' ', 'type': 'atomic',
                       'entity_ranges': [{'key': len(entities) - 1, 'offset': 0, 'length': 1}]})
        log(f'    embedded {png} ({mid})')

    lines = body.split('\n')
    i = 0
    while i < len(lines):
        raw = lines[i].rstrip()
        i += 1
        if not raw.strip():
            continue
        m = re.match(r'^!\[[^\]]*\]\(([^)]+)\)\s*$', raw.strip())
        if m:
            add_image(m.group(1))
            continue
        if raw.strip().startswith('|'):
            tbl = []
            while i - 1 < len(lines) and lines[i - 1].strip().startswith('|'):
                tbl.append(lines[i - 1].strip())
                if i < len(lines):
                    i += 1
                else:
                    break
            entities.append({'key': str(len(entities)),
                             'value': {'type': 'markdown', 'mutability': 'mutable',
                                       'data': {'markdown': '\n'.join(tbl)}}})
            blocks.append({'text': ' ', 'type': 'atomic',
                           'entity_ranges': [{'key': len(entities) - 1, 'offset': 0, 'length': 1}]})
            continue
        text, spans = _strip(raw)
        if not text.strip():
            continue
        h = re.match(r'^###\s+(.*)$', text)
        if h:
            blocks.append({'text': h.group(1), 'type': 'header-two'})
            continue
        if text.startswith('> '):
            blocks.append({'text': text[2:], 'type': 'blockquote'})
            continue
        if re.match(r'^[-•]\s+', text):
            blocks.append({'text': re.sub(r'^[-•]\s+', '', text),
                           'type': 'unordered-list-item'})
            continue
        m2 = re.match(r'^(\d+)\.\s+(.*)$', text)
        if m2:
            blocks.append({'text': m2.group(2), 'type': 'ordered-list-item'})
            continue
        b = {'text': text.strip(), 'type': 'unstyled'}
        if spans:
            b['inline_style_ranges'] = spans
        blocks.append(b)

    payload: dict = {'title': title,
                     'content_state': {'blocks': blocks, 'entities': entities}}
    if cover:
        payload['cover_media'] = cover
    return payload


# ---------------------------------------------------------------- publish

ARTICLES = [
    {
        'label': 'Aomorie',
        'md': 'trending-topic-content-aomorie.md',
        'title': "Aomorie Is Genuinely Different. That's Exactly Why It's Still Invisible.",
        'figs': [],
        'banner': 'banner-aomorie.png',
    },
    {
        'label': 'Construction robots',
        'md': 'trending-topic-content-construction-robots.md',
        'title': ("Singapore's Construction Robots Aren't Arriving Because They're Better. "
                  "They're Arriving Because the Biggest Buyer Wrote Them Into the Tender."),
        'figs': [],
        'banner': 'banner-construction-robots.png',
    },
]


def publish_one(spec):
    log(f'--- {spec["label"]} ---')
    payload = build(os.path.join(DIR, spec['md']), spec['title'],
                    spec['figs'], spec['banner'])
    nb = len(payload['content_state']['blocks'])
    ne = len(payload['content_state']['entities'])
    log(f'    payload: {nb} blocks, {ne} entities')

    for attempt in range(1, 25):
        st, txt = call('POST', 'https://api.x.com/2/articles/draft', body=payload)
        if st == 201:
            aid = json.loads(txt)['data']['id']
            log(f'    draft created: {aid}')
            break
        if st in (429, 503):
            wait = min(60 * attempt, 600)
            log(f'    draft {st}; sleeping {wait}s')
            time.sleep(wait)
            continue
        log(f'    draft FATAL {st}: {txt[:300]}')
        return None
    else:
        return None

    # The draft service may not have indexed the new article yet — give it time
    # (a 1-second publish attempt returned 400 "not owned" on 2026-09-17).
    log('    waiting 60s for the draft to settle before publishing')
    time.sleep(60)

    for attempt in range(1, 15):
        st, txt = call('POST', f'https://api.x.com/2/articles/{aid}/publish')
        log(f'    publish {attempt} -> {st} {txt[:200]}')
        if st in (200, 201):
            url = f'https://x.com/i/articles/{aid}'
            log(f'    PUBLISHED: {url}')
            return {'id': aid, 'url': url, 'response': txt[:300]}
        if st in (429, 503):
            time.sleep(min(60 * attempt, 300))
            continue
        # 400 "not owned": retry a couple of times in case it is still settling
        if st == 400 and 'not owned' in txt and attempt <= 3:
            time.sleep(45)
            continue
        break
    log(f'    PUBLISH FAILED for {spec["label"]}')
    return None


def main():
    log('=' * 60)
    log('Publishing 20260917 X Articles')
    results = {}
    for spec in ARTICLES:
        r = publish_one(spec)
        results[spec['label']] = r
        time.sleep(5)

    log('=' * 60)
    print('\n=== RESULT ===')
    ok = 0
    for label, r in results.items():
        if r:
            print(f'PUBLISHED  {label}: {r["url"]}')
            ok += 1
        else:
            print(f'FAILED     {label}')
    print(f'{ok}/{len(results)} published')
    return 0 if ok == len(results) else 1


if __name__ == '__main__':
    sys.exit(main())
