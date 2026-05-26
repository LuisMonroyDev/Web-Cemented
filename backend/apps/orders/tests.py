from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.store.models import Product


class CartTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "fan", "fan@example.com", "Sup3rSecret!"
        )
        self.product = Product.objects.create(
            name="Tour Tee", price=20, stock=10, is_active=True
        )

    def test_cart_requires_auth(self):
        self.assertIn(self.client.get("/api/cart/").status_code, (401, 403))

    def test_add_item_and_total(self):
        self.client.force_authenticate(self.user)
        added = self.client.post(
            "/api/cart/items/",
            {"product_id": self.product.id, "quantity": 2},
            format="json",
        )
        self.assertEqual(added.status_code, 201)

        cart = self.client.get("/api/cart/")
        self.assertEqual(len(cart.data["items"]), 1)
        self.assertEqual(str(cart.data["total"]), "40.00")

    def test_adding_same_product_increments(self):
        self.client.force_authenticate(self.user)
        for _ in range(2):
            self.client.post(
                "/api/cart/items/",
                {"product_id": self.product.id, "quantity": 1},
                format="json",
            )
        cart = self.client.get("/api/cart/")
        self.assertEqual(len(cart.data["items"]), 1)
        self.assertEqual(cart.data["items"][0]["quantity"], 2)
