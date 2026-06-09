#!/usr/bin/env python3
"""Compile check + fix the glossary emoji issue in server.py."""
import os

path = os.path.expanduser('~/projects/observeco/src/observeco/dashboard/server.py')

with open(path, 'rb') as f:
    raw = f.read()

# Find line 1578 (the f-string start)
lines = raw.split(b'\n')

# Check line 1578 (0-indexed = 1577)
l1577 = lines[1577]
print(f'Line 1578 ({len(l1577)} bytes)')
# Find all 'f' characters and check context
for i, byte in enumerate(l1577):
    if byte == 0x66:  # 'f'
        ctx = l1577[i:i+15]
        try:
            print(f'  f at byte {i}: {ctx.decode("ascii", errors="replace")}')
        except:
            print(f'  f at byte {i}: {ctx.hex()}')

# Check for the ❓ line
l1578 = lines[1578]  # 0-indexed line 1579
print(f'\nLine 1579 ({len(l1578)} bytes)')
# Check if the ❓ is properly inside the f-string
# Find ❓ bytes
heart_idx = l1578.find(b'\xe2\x9d\x93')
if heart_idx >= 0:
    # Check whether it's inside a string context
    before = l1578[max(0,heart_idx-30):heart_idx]
    after = l1578[heart_idx:heart_idx+30]
    print(f'  Before ❓: {repr(before)}')
    print(f'  After ❓: {repr(after)}')

# Now compile
import py_compile

try:
    py_compile.compile(path, doraise=True)
    print('\n✅ Compile OK')
except py_compile.PyCompileError as e:
    print(f'\n❌ Compile error: {e}')
