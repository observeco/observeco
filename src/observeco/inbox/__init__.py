"""Anomalies Inbox — cross-detector deduplication, correlation, and triage.

Architecture:
  store.py        Persistence layer (inbox_items CRUD, upsert-by-id, occurrence folding)
  registry.py     Detector adapters (9 sources → normalized inbox items)
  correlate.py    Correlation pass (fold ≥3 agents/window into parent items)

Obs-Spec: obs-spec-092 (§3)
Design: DPA §2-A (UNKNOWN ≠ CRITICAL), §2-B (verdict = sentence)
"""
