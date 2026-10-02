import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()  # resets throttle counters between tests


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def make_user(db):
    def _make(username="emp1", role="EMPLOYEE", password="Str0ng!Pass123", **extra):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password=password,
            role=role,
            first_name=username.title(),
            **extra,
        )
    return _make


@pytest.fixture
def auth_client(make_user):
    def _auth(user=None, password="Str0ng!Pass123"):
        user = user or make_user()
        api_client = APIClient()
        res = api_client.post("/api/auth/login/", {"username": user.username, "password": password})
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['data']['access']}")
        return api_client, user, res.data["data"]
    return _auth