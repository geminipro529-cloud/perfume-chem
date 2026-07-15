from __future__ import annotations

from datetime import timedelta

from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


def test_password_hash_round_trip_returns_typed_values():
    password_hash = get_password_hash("correct horse battery staple")

    assert isinstance(password_hash, str)
    assert verify_password("correct horse battery staple", password_hash) is True
    assert verify_password("wrong password", password_hash) is False


def test_long_passwords_are_not_silently_truncated_to_bcrypt_limit():
    password = "x" * 80 + "-correct"
    colliding_prefix = "x" * 80 + "-wrong"
    password_hash = get_password_hash(password)

    assert password_hash.startswith("$bcrypt-sha256$")
    assert verify_password(password, password_hash) is True
    assert verify_password(colliding_prefix, password_hash) is False


def test_existing_legacy_bcrypt_hash_remains_verifiable():
    legacy_hash = "$2b$04$ar/EPsJaJo8.8UUGuNiA.eU3Lx3s.VvpSChwRBsxtled50NMWc5Oy"

    assert verify_password("legacy-password", legacy_hash) is True
    assert verify_password("wrong-password", legacy_hash) is False


def test_access_token_round_trip_returns_claim_mapping():
    token = create_access_token(
        {"sub": "researcher@example.com"},
        expires_delta=timedelta(minutes=5),
    )
    payload = decode_access_token(token)

    assert isinstance(token, str)
    assert payload is not None
    assert payload["sub"] == "researcher@example.com"


def test_invalid_access_token_returns_none():
    assert decode_access_token("not-a-jwt") is None
