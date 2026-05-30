"""Regression tests for the orders admin."""
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import mail
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.store.models import Product

from .admin import OrderAdmin
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


class _FakeForm:
    """Stand-in for the admin ModelForm — save_model only reads changed_data."""

    def __init__(self, changed_data):
        self.changed_data = changed_data


@override_settings(
    STRIPE_SECRET_KEY="sk_test_dummy",
    BAND_NOTIFICATION_EMAIL="band@cemented.band",
    DEFAULT_FROM_EMAIL="orders@cemented.band",
)
class OrderAdminCancelTests(TestCase):
    """Setting an order to 'canceled' in the admin must actually refund it."""

    def _request(self):
        request = RequestFactory().post("/admin/orders/order/")
        # The messages framework save_model uses needs session + storage.
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))
        return request

    @patch("apps.orders.services.stripe.Refund.create")
    def test_admin_status_to_canceled_refunds_restocks_and_emails(self, mock_refund):
        user = get_user_model().objects.create_user(
            "fan", "fan@example.com", "Sup3rSecret!"
        )
        product = Product.objects.create(name="Tee", price=20, stock=1, is_active=True)
        order = Order.objects.create(
            user=user,
            email="fan@example.com",
            status=Order.STATUS_PAID,
            total=20,
            stripe_payment_intent="pi_9",
        )
        OrderItem.objects.create(
            order=order, product=product, name="Tee", unit_price=20, quantity=1
        )

        order_admin = OrderAdmin(Order, AdminSite())
        order.status = Order.STATUS_CANCELED  # simulate the form's edit
        order_admin.save_model(self._request(), order, _FakeForm(["status"]), change=True)

        mock_refund.assert_called_once_with(payment_intent="pi_9")
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CANCELED)
        product.refresh_from_db()
        self.assertEqual(product.stock, 2)  # restocked
        self.assertTrue(
            any("canceled" in m.subject.lower() for m in mail.outbox),
            "customer should get a cancellation email",
        )


class OrderAdminDeleteGuardTests(TestCase):
    """A paid order still has a live, refundable Stripe charge, so deleting it
    from the admin would strand that charge with no way to refund it here.
    Deletion is blocked for such orders, and the bulk delete action is removed
    entirely so it can't bypass the per-order guard."""

    def setUp(self):
        self.admin = OrderAdmin(Order, AdminSite())
        superuser = get_user_model().objects.create_superuser(
            "boss", "boss@example.com", "Sup3rSecret!"
        )
        self.request = RequestFactory().get("/admin/orders/order/")
        self.request.user = superuser

    def _order(self, **kwargs):
        return Order.objects.create(email="fan@example.com", total=20, **kwargs)

    def test_paid_order_cannot_be_deleted(self):
        order = self._order(status=Order.STATUS_PAID, stripe_payment_intent="pi_live")
        self.assertFalse(self.admin.has_delete_permission(self.request, order))

    def test_shipped_order_cannot_be_deleted(self):
        # A fulfilled order has a real charge too — protect it the same way.
        order = self._order(status=Order.STATUS_SHIPPED, stripe_payment_intent="pi_live")
        self.assertFalse(self.admin.has_delete_permission(self.request, order))

    def test_canceled_order_can_be_deleted(self):
        # Already refunded — nothing left to strand, safe to remove.
        order = self._order(status=Order.STATUS_CANCELED, stripe_payment_intent="pi_live")
        self.assertTrue(self.admin.has_delete_permission(self.request, order))

    def test_pending_order_can_be_deleted(self):
        # Abandoned checkout, never charged — safe to remove.
        order = self._order(status=Order.STATUS_PENDING)
        self.assertTrue(self.admin.has_delete_permission(self.request, order))

    def test_bulk_delete_action_is_removed(self):
        self.assertNotIn("delete_selected", self.admin.get_actions(self.request))
