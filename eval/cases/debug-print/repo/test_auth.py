from auth import authenticate, hash_token


class FakeUser:
    is_active = True


def test_authenticate_accepts_matching_token():
    user = FakeUser()
    assert authenticate(user, "secret", hash_token("secret"))
