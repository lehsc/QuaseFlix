"""
Unit tests for password hashing and access tokens (no database or API needed):
    PYTHONPATH=. pytest tests/test_security.py
"""
import base64
import hashlib
import json

import pytest

from backend import security
from backend.exceptions import InvalidTokenError
from backend.security import (
    ACCESS_TOKEN_TTL_SECONDS,
    burn_password_check,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

PASSWORD = "Senha@12345"


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def forge_token(header: dict, payload: dict) -> str:
    """A token signed with the real key but with the given header and payload."""
    signing_input = f"{security._json_segment(header)}.{security._json_segment(payload)}"
    return f"{signing_input}.{security._sign(signing_input)}"


def token_payload(token: str) -> dict:
    part = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


# ---------------------------------------------------------------- Passwords

def test_hash_does_not_contain_the_password():
    assert PASSWORD not in hash_password(PASSWORD)


def test_hash_has_the_expected_format_and_fits_the_column():
    stored = hash_password(PASSWORD)

    scheme, n, r, p, salt, key = stored.split("$")
    assert scheme == "scrypt"
    assert (int(n), int(r), int(p)) == (2 ** 14, 8, 1)
    assert len(stored) <= 255  # public.account.password_hash is varchar(255)


def test_same_password_gets_a_different_hash_each_time():
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_verify_accepts_the_right_password():
    assert verify_password(PASSWORD, hash_password(PASSWORD)) is True


@pytest.mark.parametrize("wrong", [
    "senha@12345",     # different case
    PASSWORD + " ",    # extra space
    PASSWORD[:-1],     # one character less
    "",
])
def test_verify_rejects_a_wrong_password(wrong):
    assert verify_password(wrong, hash_password(PASSWORD)) is False


def test_verify_handles_non_ascii_passwords():
    stored = hash_password("sênha-ção-ã123")

    assert verify_password("sênha-ção-ã123", stored) is True
    assert verify_password("senha-cao-a123", stored) is False


def test_verify_uses_the_parameters_saved_in_the_hash():
    # A hash made with other (cheaper) parameters still verifies: the parameters
    # can be changed in the future without locking the old accounts out.
    salt = b"0123456789abcdef"
    key = hashlib.scrypt(PASSWORD.encode(), salt = salt, n = 2 ** 12, r = 8, p = 1, dklen = 32)
    stored = f"scrypt$4096$8$1${b64(salt)}${b64(key)}"

    assert verify_password(PASSWORD, stored) is True
    assert verify_password("other", stored) is False


@pytest.mark.parametrize("stored", [
    "",
    PASSWORD,                    # an old account whose password was saved as plain text
    "scrypt$bad",
    "scrypt$16384$8$1$!!!$!!!",
    "bcrypt$16384$8$1$AAAA$AAAA",
    "scrypt$abc$8$1$AAAA$AAAA",
    "scrypt$3$8$1$AAAA$AAAA",    # n is not a power of two
    None,
])
def test_verify_rejects_anything_that_is_not_a_valid_hash(stored):
    assert verify_password(PASSWORD, stored) is False


def test_verify_rejects_a_password_that_is_not_a_string():
    assert verify_password(None, hash_password(PASSWORD)) is False


@pytest.mark.parametrize("password", ["", None, 123])
def test_hash_rejects_an_invalid_password(password):
    with pytest.raises(ValueError, match = "Password"):
        hash_password(password)


def test_burn_password_check_does_not_fail():
    assert burn_password_check(PASSWORD) is None


# ------------------------------------------------------------------- Tokens

def test_token_round_trip():
    assert decode_access_token(create_access_token(42)) == 42


def test_token_is_a_standard_jwt():
    token = create_access_token(42)

    header_part, payload_part, signature_part = token.split(".")
    header = json.loads(base64.urlsafe_b64decode(header_part + "=" * (-len(header_part) % 4)))
    assert header == {"alg": "HS256", "typ": "JWT"}
    assert token_payload(token)["sub"] == "42"
    assert signature_part


def test_token_expires_after_its_time_to_live():
    token = create_access_token(7, now = 1_000)

    assert token_payload(token)["exp"] == 1_000 + ACCESS_TOKEN_TTL_SECONDS
    assert decode_access_token(token, now = 1_000 + ACCESS_TOKEN_TTL_SECONDS - 1) == 7
    with pytest.raises(InvalidTokenError, match = "expired"):
        decode_access_token(token, now = 1_000 + ACCESS_TOKEN_TTL_SECONDS)


def test_token_with_a_changed_payload_is_rejected():
    token = create_access_token(2)
    header_part, _, signature_part = token.split(".")
    other_payload = b64(json.dumps({"sub": "1", "exp": 9_999_999_999}).encode())

    with pytest.raises(InvalidTokenError, match = "signature"):
        decode_access_token(f"{header_part}.{other_payload}.{signature_part}")


def test_token_with_a_changed_signature_is_rejected():
    header_part, payload_part, signature_part = create_access_token(2).split(".")
    changed = ("A" if signature_part[0] != "A" else "B") + signature_part[1:]

    with pytest.raises(InvalidTokenError, match = "signature"):
        decode_access_token(f"{header_part}.{payload_part}.{changed}")


def test_token_without_signature_is_rejected():
    header_part = b64(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    payload_part = b64(json.dumps({"sub": "1", "exp": 9_999_999_999}).encode())

    with pytest.raises(InvalidTokenError):
        decode_access_token(f"{header_part}.{payload_part}.")


def test_token_signed_with_another_key_is_rejected(monkeypatch):
    token = create_access_token(5)

    monkeypatch.setattr(security, "_SECRET_KEY", "another-key")

    with pytest.raises(InvalidTokenError, match = "signature"):
        decode_access_token(token)


def test_token_with_another_algorithm_is_rejected():
    token = forge_token({"alg": "HS512", "typ": "JWT"}, {"sub": "1", "exp": 9_999_999_999})

    with pytest.raises(InvalidTokenError, match = "algorithm"):
        decode_access_token(token)


@pytest.mark.parametrize("payload", [
    {"sub": "1"},                                    # no exp
    {"sub": "1", "exp": "9999999999"},               # exp is not a number
    {"sub": "1", "exp": True},                       # bool is not a timestamp
    {"exp": 9_999_999_999},                          # no sub
    {"sub": 1, "exp": 9_999_999_999},                # sub is not a string
    {"sub": "abc", "exp": 9_999_999_999},
    {"sub": "-1", "exp": 9_999_999_999},
    {"sub": "", "exp": 9_999_999_999},
])
def test_signed_token_with_invalid_claims_is_rejected(payload):
    token = forge_token({"alg": "HS256", "typ": "JWT"}, payload)

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_signed_token_whose_payload_is_not_an_object_is_rejected():
    token = forge_token({"alg": "HS256", "typ": "JWT"}, ["not", "an", "object"])

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


@pytest.mark.parametrize("token", [
    "",
    "abc",
    "a.b",
    "a.b.c",
    "a.b.c.d",
    "é.é.é",
    None,
    123,
])
def test_malformed_tokens_are_rejected(token):
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)
