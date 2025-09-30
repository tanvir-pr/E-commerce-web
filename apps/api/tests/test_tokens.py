"""Opaque token hashing."""

from app.security.tokens import generate_opaque_token, hash_token, tokens_match


def test_hash_is_stable() -> None:
    raw = "abc"
    assert hash_token(raw) == hash_token(raw)
    assert len(hash_token(raw)) == 64


def test_tokens_match() -> None:
    raw = generate_opaque_token()
    assert tokens_match(raw, hash_token(raw))
    assert not tokens_match(raw, hash_token("other"))
