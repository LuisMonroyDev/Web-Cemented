"""Regression tests for the auth lifecycle and registration validation."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class RegistrationValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_duplicate_username_rejected(self):
        get_user_model().objects.create_user("fan", "fan@example.com", "Sup3rSecret!")
        res = self.client.post(
            "/api/auth/register/",
            {"username": "fan", "email": "other@example.com", "password": "Sup3rSecret!"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_weak_password_rejected(self):
        res = self.client.post(
            "/api/auth/register/",
            {"username": "newfan", "email": "new@example.com", "password": "123"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_missing_fields_rejected(self):
        res = self.client.post(
            "/api/auth/register/", {"username": "newfan"}, format="json"
        )
        self.assertEqual(res.status_code, 400)

    def test_duplicate_email_rejected(self):
        """Two accounts shouldn't share an email address.

        `RegisterSerializer.validate_email` enforces case-insensitive
        uniqueness since Django's `User.email` has no unique constraint.
        """
        get_user_model().objects.create_user("fan", "dupe@example.com", "Sup3rSecret!")
        res = self.client.post(
            "/api/auth/register/",
            {"username": "fan2", "email": "dupe@example.com", "password": "Sup3rSecret!"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)


class SessionLifecycleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        get_user_model().objects.create_user("fan", "fan@example.com", "Sup3rSecret!")

    def _login(self):
        return self.client.post(
            "/api/auth/login/",
            {"username": "fan", "password": "Sup3rSecret!"},
            format="json",
        )

    def test_login_then_me_returns_user(self):
        self.assertEqual(self._login().status_code, 200)
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["username"], "fan")

    def test_logout_clears_session(self):
        self._login()
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 204)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)
