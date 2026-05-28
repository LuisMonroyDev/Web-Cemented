"""Regression tests for the orders admin."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Order, OrderItem


class OrderAdminTests(TestCase):
    def setUp(self):
        admin = get_user_model().objects.create_superuser(
            "boss", "boss@example.com", "Sup3rSecret!"
        )
        self.client.force_login(admin)

    def test_order_change_page_renders(self):
        """The change page must load even though the inline's blank
        'add another' row is an OrderItem with no unit_price (used to 500
        on `None * quantity` in the line_total column)."""
        order = Order.objects.create(email="fan@example.com", total=20)
        OrderItem.objects.create(order=order, name="Tee", unit_price=10, quantity=2)
        url = reverse("admin:orders_order_change", args=[order.id])
        self.assertEqual(self.client.get(url).status_code, 200)
