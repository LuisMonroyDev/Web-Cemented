from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_logs_in_and_me_returns_user(self):
        res = self.client.post(
            "/api/auth/register/",
            {"username": "fan", "email": "fan@example.com", "password": "Sup3rSecret!"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["username"], "fan")

    def test_me_requires_auth(self):
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_login_rejects_bad_credentials(self):
        get_user_model().objects.create_user("fan", "fan@example.com", "Sup3rSecret!")
        res = self.client.post(
            "/api/auth/login/",
            {"username": "fan", "password": "wrong"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
