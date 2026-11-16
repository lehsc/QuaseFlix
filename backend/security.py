"""
Password hashing and access tokens.

Only the standard library is used (hashlib.scrypt for passwords and HMAC-SHA256
for tokens), so there is no extra package to install. Nothing here touches the
database or FastAPI, which keeps it easy to unit test.
"""
import base64
import functools
import hashlib
import hmac
import json
import os
import secrets
import time

from backend.exceptions import InvalidTokenError

# --------------------------------------------------------------- Passwords
# Stored as: scrypt$<n>$<r>$<p>$<salt>$<hash>. The parameters travel with the
# hash, so they can be raised later without breaking the passwords already
# saved. Memory used per hash is 128 * n * r bytes (16 MiB with these values).

_HASH_SCHEME = "scrypt"
_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SALT_BYTES = 16
_KEY_BYTES = 32


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"), salt = salt, n = n, r = r, p = p, dklen = _KEY_BYTES
    )


def hash_password(password: str) -> str:
    """Returns the salted hash that must be stored instead of the password."""
    if not isinstance(password, str) or not password:
        raise ValueError("Password is required.")
    salt = secrets.token_bytes(_SALT_BYTES)
    key = _scrypt(password, salt, _SCRYPT_N, _SCRYPT_R, _SCRYPT_P)
    return "$".join((
        _HASH_SCHEME, str(_SCRYPT_N), str(_SCRYPT_R), str(_SCRYPT_P),
        _b64encode(salt), _b64encode(key),
    ))


def verify_password(password: str, stored_hash: str) -> bool:
    """
    True if the password matches the stored hash. Anything that is not a valid
    hash (empty value, an old plain text password, ...) simply does not match.
    """
    try:
        scheme, n, r, p, salt, expected = stored_hash.split("$")
        if scheme != _HASH_SCHEME:
            return False
        key = _scrypt(password, _b64decode(salt), int(n), int(r), int(p))
        return hmac.compare_digest(key, _b64decode(expected))
    except (AttributeError, TypeError, ValueError):
        return False


@functools.lru_cache(maxsize = 1)
def _dummy_hash() -> str:
    return hash_password(secrets.token_urlsafe(16))


def burn_password_check(password: str) -> None:
    """
    Does the same work as verify_password. It is called when the e-mail does
    not exist, so the response time does not reveal which e-mails are registered.
    """
    verify_password(password, _dummy_hash())


# ------------------------------------------------------------------ Tokens
# A token is a standard JWT (HS256): base64url(header).base64url(payload).signature
# Whoever has the token is the account in its "sub" claim until "exp".

ACCESS_TOKEN_TTL_SECONDS = 8 * 60 * 60

# Set QUASEFLIX_SECRET_KEY to keep tokens valid across restarts (and across
# several server processes). Without it, a random key is generated on every
# start, so the tokens issued before a restart stop working.
_SECRET_KEY = os.environ.get("QUASEFLIX_SECRET_KEY") or secrets.token_urlsafe(32)

_TOKEN_HEADER = {"alg": "HS256", "typ": "JWT"}


def _json_segment(data: dict) -> str:
    return _b64encode(json.dumps(data, separators = (",", ":"), sort_keys = True).encode("utf-8"))


def _sign(signing_input: str) -> str:
    digest = hmac.new(
        _SECRET_KEY.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256
    ).digest()
    return _b64encode(digest)


def create_access_token(account_id: int, now: float | None = None) -> str:
    """Issues a token for the account that is valid for ACCESS_TOKEN_TTL_SECONDS."""
    issued_at = int(time.time() if now is None else now)
    payload = {
        "sub": str(account_id),
        "iat": issued_at,
        "exp": issued_at + ACCESS_TOKEN_TTL_SECONDS,
    }
    signing_input = f"{_json_segment(_TOKEN_HEADER)}.{_json_segment(payload)}"
    return f"{signing_input}.{_sign(signing_input)}"


def decode_access_token(token: str, now: float | None = None) -> int:
    """
    Returns the account id inside a valid token.

    Raises InvalidTokenError if the token is malformed, was not signed by this
    server, or has expired.
    """
    try:
        header_part, payload_part, signature_part = token.split(".")
        expected_signature = _sign(f"{header_part}.{payload_part}")
        # The signature is checked before anything else is read from the token.
        if not hmac.compare_digest(signature_part.encode("ascii"), expected_signature.encode("ascii")):
            raise InvalidTokenError("Invalid token signature.")
        header = json.loads(_b64decode(header_part))
        payload = json.loads(_b64decode(payload_part))
    except InvalidTokenError:
        raise
    except (AttributeError, TypeError, ValueError) as error:
        raise InvalidTokenError("Malformed token.") from error

    if not isinstance(header, dict) or header.get("alg") != "HS256":
        raise InvalidTokenError("Unsupported token algorithm.")
    if not isinstance(payload, dict):
        raise InvalidTokenError("Malformed token.")

    expires_at = payload.get("exp")
    if isinstance(expires_at, bool) or not isinstance(expires_at, int):
        raise InvalidTokenError("Malformed token.")
    if (time.time() if now is None else now) >= expires_at:
        raise InvalidTokenError("Token expired.")

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.isascii() or not subject.isdigit():
        raise InvalidTokenError("Malformed token.")
    return int(subject)
