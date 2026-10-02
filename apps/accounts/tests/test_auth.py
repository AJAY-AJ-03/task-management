import pytest

LOGIN = "/api/auth/login/"


@pytest.mark.django_db
def test_login_success_returns_tokens_and_user(client, make_user):
    make_user(employee_id="EMP001")
    res = client.post(LOGIN, {"username": "emp1", "password": "Str0ng!Pass123"})
    assert res.status_code == 200
    body = res.data
    assert body["success"] is True
    assert {"access", "refresh", "user"} <= set(body["data"])
    assert body["data"]["user"]["employee_id"] == "EMP001"
    assert body["data"]["user"]["role"] == "EMPLOYEE"


@pytest.mark.django_db
def test_login_wrong_password_is_401(client, make_user):
    make_user()
    res = client.post(LOGIN, {"username": "emp1", "password": "nope"})
    assert res.status_code == 401
    assert res.data["success"] is False


@pytest.mark.django_db
def test_login_inactive_user_rejected(client, make_user):
    u = make_user()
    u.is_active = False
    u.save()
    res = client.post(LOGIN, {"username": "emp1", "password": "Str0ng!Pass123"})
    assert res.status_code == 401


@pytest.mark.django_db
def test_login_missing_fields_is_400(client):
    res = client.post(LOGIN, {})
    assert res.status_code == 400
    assert "username" in res.data["errors"]


@pytest.mark.django_db
def test_me_requires_authentication(client):
    res = client.get("/api/auth/me/")
    assert res.status_code == 401
    assert res.data["success"] is False


@pytest.mark.django_db
def test_me_returns_profile_without_password(auth_client):
    api, user, _ = auth_client()
    res = api.get("/api/auth/me/")
    assert res.status_code == 200
    assert res.data["data"]["username"] == user.username
    assert "password" not in res.data["data"]


@pytest.mark.django_db
def test_refresh_rotates_token(auth_client, client):
    _, _, tokens = auth_client()
    res = client.post("/api/auth/refresh/", {"refresh": tokens["refresh"]})
    assert res.status_code == 200
    assert res.data["data"]["refresh"] != tokens["refresh"]
    # the old refresh token is now blacklisted
    again = client.post("/api/auth/refresh/", {"refresh": tokens["refresh"]})
    assert again.status_code == 401


@pytest.mark.django_db
def test_logout_blacklists_refresh_token(auth_client, client):
    api, _, tokens = auth_client()
    res = api.post("/api/auth/logout/", {"refresh": tokens["refresh"]})
    assert res.status_code == 200
    again = client.post("/api/auth/refresh/", {"refresh": tokens["refresh"]})
    assert again.status_code == 401


@pytest.mark.django_db
def test_logout_with_garbage_token_is_400(auth_client):
    api, _, _ = auth_client()
    res = api.post("/api/auth/logout/", {"refresh": "garbage"})
    assert res.status_code == 400


@pytest.mark.django_db
def test_change_password_flow(auth_client, client):
    api, user, tokens = auth_client()
    res = api.post(
        "/api/auth/change-password/",
        {"old_password": "Str0ng!Pass123", "new_password": "N3w!Password456"},
    )
    assert res.status_code == 200
    user.refresh_from_db()
    assert user.check_password("N3w!Password456")
    # old refresh token revoked
    assert client.post("/api/auth/refresh/", {"refresh": tokens["refresh"]}).status_code == 401


@pytest.mark.django_db
def test_change_password_wrong_old_password_is_400(auth_client):
    api, _, _ = auth_client()
    res = api.post(
        "/api/auth/change-password/",
        {"old_password": "wrong", "new_password": "N3w!Password456"},
    )
    assert res.status_code == 400


@pytest.mark.django_db
def test_email_unique_case_insensitive(make_user):
    from django.db import IntegrityError, transaction
    from apps.accounts.models import User

    make_user("a")
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(username="b", email="A@EXAMPLE.COM", password="x")