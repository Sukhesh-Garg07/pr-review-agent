"""Session management built on the auth helpers."""

from auth import authenticate


class SessionManager:
    def __init__(self, user_store):
        self._users = user_store

    def login(self, user, token):
        record = self._users[user.username]
        if authenticate(user, token, record["token_hash"]):
            return f"session-{user.username}"
        return None
