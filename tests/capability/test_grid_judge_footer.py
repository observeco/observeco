"""Tests for the grid footer judge line (_judge_footer_html).

Regression test: the persistent-judge feature (migration 68) surfaces which
LLM judge scored a grid run in the table footer. The helper must tolerate
sqlite3.Row (no .get()), plain dicts, missing `judge` column (pre-migration
runs / older DBs), and empty values without 500ing the grid table.
"""

import sqlite3

from observeco.dashboard.routes.capability import _judge_footer_html


def _row(**cols):
    """Build a sqlite3.Row with the given column->value pairs."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn.execute(
        f"SELECT {', '.join(f':{k} AS {k}' for k in cols)}",
        {k: v for k, v in cols.items()},
    ).fetchone()


def test_row_with_judge_renders_escaped():
    html = _judge_footer_html(_row(judge="ollama-cloud/glm-5.2"))
    assert "Judge:" in html
    assert "ollama-cloud/glm-5.2" in html


def test_row_without_judge_column_returns_empty():
    # Pre-migration DBs / older runs lack the judge column entirely.
    assert _judge_footer_html(_row(models="[]")) == ""


def test_row_with_null_judge_returns_empty():
    assert _judge_footer_html(_row(judge=None)) == ""


def test_dict_with_judge_renders():
    html = _judge_footer_html({"judge": "deepseek/deepseek-v4-pro"})
    assert "deepseek/deepseek-v4-pro" in html


def test_none_returns_empty():
    assert _judge_footer_html(None) == ""


def test_judge_value_is_escaped():
    html = _judge_footer_html({"judge": "<script>alert(1)</script>"})
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
