"""Chisel trim + drift tests."""

import os
import tempfile

from observeco.chisel.drift import run_drift
from observeco.chisel.trim import compress_guidance_block, run_compress


class TestCompress:
    def test_compress_empty_block(self):
        result = compress_guidance_block("")
        assert isinstance(result, str)

    def test_compress_short_block(self):
        result = compress_guidance_block("Keep this brief.")
        assert isinstance(result, str)

    def test_run_compress_with_file(self):
        """Run compress against a real temp file."""
        soul_content = "---\nname: test-agent\nmodel: test-model\nguidance: This is a test guidance block with enough content to compress.\n---\nHello world"
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
        tmp.write(soul_content)
        tmp.close()
        try:
            result = run_compress(agent_name="test-agent", filepath=tmp.name)
            assert isinstance(result, dict)
        finally:
            os.unlink(tmp.name)

    def test_run_compress_nonexistent_file(self):
        """Run compress with nonexistent file raises FileNotFoundError."""
        import pytest
        with pytest.raises(FileNotFoundError):
            run_compress(agent_name="ghost", filepath="/tmp/nonexistent_soul_xyz123.md")


class TestDrift:
    def test_run_drift_no_crash(self):
        result = run_drift()
        assert result is None
