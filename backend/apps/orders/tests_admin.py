"""Regression tests for the orders admin."""
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
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

    @override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
    def test_change_page_post_blocked_cancel_shows_only_warning(self):
        """End-to-end through the admin change view: POSTing status=canceled on
        a shipped order must surface only the 'can't be canceled' warning, not
        the default 'was changed successfully' message, and leave it shipped."""
        order = Order.objects.create(
            email="fan@example.com",
            status=Order.STATUS_SHIPPED,
            total=20,
            stripe_payment_intent="pi_late",
        )
        item = OrderItem.objects.create(order=order, name="Tee", unit_price=20, quantity=1)
        url = reverse("admin:orders_order_change", args=[order.id])
        resp = self.client.post(
            url,
            {
                "status": Order.STATUS_CANCELED,
                "tracking_number": order.tracking_number,
                # Readonly inline still needs its management form to validate.
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "1",
                "items-MIN_NUM_FORMS": "0",
                "items-MAX_NUM_FORMS": "1000",
                "items-0-id": str(item.id),
                "items-0-order": str(order.id),
                "_save": "Save",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        msgs = [str(m) for m in resp.context["messages"]]
        self.assertTrue(
            any("can't be canceled" in m for m in msgs),
            f"expected a blocked-cancel warning, got {msgs!r}",
        )
        self.assertFalse(
            any("changed successfully" in m.lower() for m in msgs),
            f"should not falsely report success, got {msgs!r}",
        )
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_SHIPPED)


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

    def test_blocked_late_cancel_is_not_reported_as_success(self):
        """Trying to cancel a shipped order is refused. The admin must show the
        'can't be canceled' warning and NOT Django's default 'was changed
        successfully' message — the order was never saved or canceled."""
        staff = get_user_model().objects.create_superuser(
            "boss", "boss@example.com", "Sup3rSecret!"
        )
        order = Order.objects.create(
            email="fan@example.com",
            status=Order.STATUS_SHIPPED,  # past the cancelable window
            total=20,
            stripe_payment_intent="pi_late",
        )
        OrderItem.objects.create(order=order, name="Tee", unit_price=20, quantity=1)

        order_admin = OrderAdmin(Order, AdminSite())
        request = self._request()
        request.user = staff  # response_post_save_change checks permissions
        order.status = Order.STATUS_CANCELED  # simulate the rejected form edit
        order_admin.save_model(request, order, _FakeForm(["status"]), change=True)

        # The order was NOT canceled in the database.
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_SHIPPED)

        # response_change must redirect without posting a success message.
        resp = order_admin.response_change(request, order)
        self.assertEqual(resp.status_code, 302)
        msgs = [str(m) for m in get_messages(request)]
        self.assertTrue(
            any("can't be canceled" in m for m in msgs),
            f"expected a blocked-cancel warning, got {msgs!r}",
        )
        self.assertFalse(
            any("changed successfully" in m.lower() for m in msgs),
            f"should not falsely report success, got {msgs!r}",
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


@override_settings(DEFAULT_FROM_EMAIL="orders@cemented.band")
class OrderAdminShipTests(TestCase):
    """Marking an order shipped — from the change form or the bulk action —
    emails the customer with the tracking number the band just entered, and
    must not re-notify an order that already shipped."""

    def _request(self):
        request = RequestFactory().post("/admin/orders/order/")
        # save_model / actions call message_user, which needs session + storage.
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))
        return request

    def _order(self, **kwargs):
        kwargs.setdefault("email", "fan@example.com")
        kwargs.setdefault("total", 20)
        order = Order.objects.create(**kwargs)
        OrderItem.objects.create(order=order, name="Tee", unit_price=20, quantity=1)
        return order

    def test_save_model_shipped_emails_customer_with_tracking(self):
        order = self._order(
            status=Order.STATUS_FULFILLING, tracking_number="9400111899223333"
        )
        order_admin = OrderAdmin(Order, AdminSite())
        order.status = Order.STATUS_SHIPPED  # simulate the form's edit
        order_admin.save_model(
            self._request(), order, _FakeForm(["status", "tracking_number"]), change=True
        )

        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_SHIPPED)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("shipped", email.subject.lower())
        self.assertEqual(email.to, ["fan@example.com"])
        self.assertIn("9400111899223333", email.body)  # tracking number in the body

    def test_mark_shipped_action_emails_only_newly_shipped(self):
        to_ship = self._order(
            status=Order.STATUS_PAID, tracking_number="9400111899220001"
        )
        already = self._order(
            status=Order.STATUS_SHIPPED, tracking_number="9400111899220002"
        )

        order_admin = OrderAdmin(Order, AdminSite())
        order_admin.mark_shipped(self._request(), Order.objects.all())

        to_ship.refresh_from_db()
        already.refresh_from_db()
        self.assertEqual(to_ship.status, Order.STATUS_SHIPPED)
        self.assertEqual(already.status, Order.STATUS_SHIPPED)  # unchanged
        # Only the order that actually transitioned should be emailed.
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["fan@example.com"])
        self.assertIn("9400111899220001", mail.outbox[0].body)


@override_settings(DEFAULT_FROM_EMAIL="orders@cemented.band")
class OrderAdminDeliverTests(TestCase):
    """Marking an order delivered — from the change form or the bulk action —
    emails the customer a delivery confirmation with their address and the USPS
    link, and must not re-notify an order that was already delivered."""

    def _request(self):
        request = RequestFactory().post("/admin/orders/order/")
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))
        return request

    def _order(self, **kwargs):
        kwargs.setdefault("email", "fan@example.com")
        kwargs.setdefault("total", 20)
        kwargs.setdefault("shipping_line1", "123 Main St")
        kwargs.setdefault("shipping_city", "Austin")
        kwargs.setdefault("shipping_state", "TX")
        kwargs.setdefault("shipping_postal_code", "78701")
        kwargs.setdefault("shipping_country", "US")
        order = Order.objects.create(**kwargs)
        OrderItem.objects.create(order=order, name="Tee", unit_price=20, quantity=1)
        return order

    def test_save_model_delivered_emails_customer_with_address_and_link(self):
        order = self._order(
            status=Order.STATUS_SHIPPED, tracking_number="9400111899223333"
        )
        order_admin = OrderAdmin(Order, AdminSite())
        order.status = Order.STATUS_DELIVERED  # simulate the form's edit
        order_admin.save_model(
            self._request(), order, _FakeForm(["status"]), change=True
        )

        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_DELIVERED)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("delivered", email.subject.lower())
        self.assertEqual(email.to, ["fan@example.com"])
        # Thank-you, the shipping address, and the USPS link are all present.
        self.assertIn("thank you", email.body.lower())
        self.assertIn("123 Main St", email.body)
        self.assertIn("9400111899223333", email.body)

    def test_mark_delivered_action_emails_only_newly_delivered(self):
        to_deliver = self._order(
            status=Order.STATUS_SHIPPED, tracking_number="9400111899220001"
        )
        already = self._order(
            status=Order.STATUS_DELIVERED, tracking_number="9400111899220002"
        )

        order_admin = OrderAdmin(Order, AdminSite())
        order_admin.mark_delivered(self._request(), Order.objects.all())

        to_deliver.refresh_from_db()
        already.refresh_from_db()
        self.assertEqual(to_deliver.status, Order.STATUS_DELIVERED)
        self.assertEqual(already.status, Order.STATUS_DELIVERED)  # unchanged
        # Only the order that actually transitioned should be emailed.
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["fan@example.com"])
        self.assertIn("9400111899220001", mail.outbox[0].body)
