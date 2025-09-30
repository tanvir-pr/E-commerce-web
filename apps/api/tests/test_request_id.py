"""Day 1 unit checks. No database."""

from app.middleware import request_id_value


def test_request_id_keeps_a_safe_header() -> None:
    assert request_id_value("abc-123") == "abc-123"


def test_request_id_replaces_an_unsafe_header() -> None:
    generated = request_id_value("not a valid id")
    assert generated != "not a valid id"
    assert request_id_value(None) != ""
