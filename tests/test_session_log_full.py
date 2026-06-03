"""Additional session log coverage."""

from observeco.session_log import _hash_entry


class TestSessionLog:
    def test_hash_entry_string(self):
        h = _hash_entry({"msg": "hello"}, "prev123")
        assert isinstance(h, str)
        assert len(h) > 0

    def test_hash_entry_diff_data(self):
        h1 = _hash_entry({"msg": "hello"}, "prev123")
        h2 = _hash_entry({"msg": "world"}, "prev123")
        assert h1 != h2

    def test_hash_entry_diff_prev(self):
        h1 = _hash_entry({"msg": "hello"}, "prev123")
        h2 = _hash_entry({"msg": "hello"}, "prev456")
        assert h1 != h2