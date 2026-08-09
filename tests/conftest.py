"""Test configuration and fixtures for observeco."""
import os
import shutil
import sqlite3
import sys

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _isolate_test_db(tmp_path_factory):
    """Point every Database() at a WAL-safe fixture copy, never the live DB.

    The live pulse.db must not be opened from tests: opening it through
    Database() silently applies pending migrations to production (observed:
    schema advanced 73->74 during a pytest run). We copy the live DB with
    the SQLite backup API (shutil.copy2 produces torn WAL copies) into a
    session temp dir and export OBSERVECO_TEST_DB so Database() redirects.

    Tests that mutate the copy get isolated state; the live DB is untouched.
    """
    live = os.path.expanduser("~/Library/Application Support/observeco/pulse.db")
    if not os.path.exists(live):
        # No live DB (fresh checkout / CI) — use an empty fixture DB path;
        # Database() will create it lazily under the temp dir.
        fixture = str(tmp_path_factory.mktemp("observeco_test") / "pulse.db")
        os.environ["OBSERVECO_TEST_DB"] = fixture
        yield fixture
        return

    fixture = str(tmp_path_factory.mktemp("observeco_test") / "pulse.db")
    src = sqlite3.connect(live)
    dst = sqlite3.connect(fixture)
    src.backup(dst)
    dst.commit()
    dst.close()
    src.close()
    os.environ["OBSERVECO_TEST_DB"] = fixture
    yield fixture
