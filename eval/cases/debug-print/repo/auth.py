"""Authentication helpers."""

import hashlib


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def authenticate(user, token, expected_hash):
    """Return True when the token matches the stored hash."""
    return hash_token(token) == expected_hash and user.is_active
