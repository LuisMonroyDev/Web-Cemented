from unittest.mock import patch

import stripe
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.store.models import Product

from .models import Cart, CartItem, Order, OrderItem
from .services import cancel_and_refund


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

    def test_cannot_add_out_of_stock(self):
        self.client.force_authenticate(self.user)
        sold_out = Product.objects.create(name="Gone", price=10, stock=0, is_active=True)
        res = self.client.post(
            "/api/cart/items/",
            {"product_id": sold_out.id, "quantity": 1},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_quantity_capped_at_stock(self):
        self.client.force_authenticate(self.user)  # self.product has stock 10
        res = self.client.post(
            "/api/cart/items/",
            {"product_id": self.product.id, "quantity": 50},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["items"][0]["quantity"], 10)


@override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
class CheckoutTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "fan", "fan@example.com", "Sup3rSecret!"
        )
        self.product = Product.objects.create(
            name="Tour Tee", price=20, stock=10, is_active=True
        )

    def test_checkout_requires_auth(self):
        self.assertIn(self.client.post("/api/checkout/").status_code, (401, 403))

    def test_empty_cart_rejected(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post("/api/checkout/").status_code, 400)

    @patch("apps.orders.views.stripe.checkout.Session.create")
    def test_creates_order_and_returns_url(self, mock_create):
        mock_create.return_value = type(
            "Session", (), {"id": "cs_test_123", "url": "https://stripe.test/cs_test_123"}
        )()
        self.client.force_authenticate(self.user)
        self.client.post(
            "/api/cart/items/",
            {"product_id": self.product.id, "quantity": 2},
            format="json",
        )
        res = self.client.post("/api/checkout/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["checkout_url"], "https://stripe.test/cs_test_123")

        order = Order.objects.get()
        self.assertEqual(str(order.total), "40.00")
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.stripe_session_id, "cs_test_123")
        # Stripe was asked to charge 2000 cents/unit, qty 2.
        kwargs = mock_create.call_args.kwargs
        self.assertEqual(kwargs["line_items"][0]["price_data"]["unit_amount"], 2000)
        # ...and to collect a shipping address on its checkout page.
        self.assertIn("US", kwargs["shipping_address_collection"]["allowed_countries"])


@override_settings(STRIPE_WEBHOOK_SECRET="whsec_dummy")
class WebhookTests(TestCase):
    @patch("apps.orders.views.stripe.Webhook.construct_event")
    def test_completed_session_marks_paid_and_clears_cart(self, mock_construct):
        user = get_user_model().objects.create_user(
            "fan", "fan@example.com", "Sup3rSecret!"
        )
        product = Product.objects.create(name="Tee", price=20, stock=5, is_active=True)
        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, product=product, quantity=2)
        order = Order.objects.create(user=user, status=Order.STATUS_PENDING, total=40)
        OrderItem.objects.create(
            order=order, product=product, name="Tee", unit_price=20, quantity=2
        )

        # A real Stripe object — it supports [] but not .get() or dict(), which
        # is exactly the shape that broke the live webhook. A plain dict here
        # would hide the bug.
        session_obj = stripe.checkout.Session.construct_from(
            {
                "metadata": {"order_id": str(order.id)},
                "payment_intent": "pi_123",
                "client_reference_id": str(order.id),
                "shipping_details": {
                    "name": "Jane Fan",
                    "address": {
                        "line1": "123 Riff St",
                        "line2": "Apt 4",
                        "city": "Austin",
                        "state": "TX",
                        "postal_code": "78701",
                        "country": "US",
                    },
                },
            },
            "sk_test_dummy",
        )
        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {"object": session_obj},
        }
        res = self.client.post(
            "/api/webhooks/stripe/",
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=sig",
        )
        self.assertEqual(res.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_PAID)
        self.assertEqual(order.stripe_payment_intent, "pi_123")
        self.assertEqual(CartItem.objects.filter(cart=cart).count(), 0)
        product.refresh_from_db()
        self.assertEqual(product.stock, 3)  # 5 - 2 sold
        # The shipping address Stripe collected is snapshotted onto the order.
        self.assertEqual(order.shipping_name, "Jane Fan")
        self.assertEqual(order.shipping_line1, "123 Riff St")
        self.assertEqual(order.shipping_city, "Austin")
        self.assertEqual(order.shipping_postal_code, "78701")
        self.assertTrue(order.has_shipping_address)


class OrdersApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "fan", "fan@example.com", "Sup3rSecret!"
        )

    def test_orders_require_auth(self):
        self.assertIn(self.client.get("/api/orders/").status_code, (401, 403))

    def test_lists_users_paid_and_canceled_orders(self):
        other = get_user_model().objects.create_user(
            "other", "other@example.com", "Sup3rSecret!"
        )
        paid = Order.objects.create(user=self.user, status=Order.STATUS_PAID, total=40)
        canceled = Order.objects.create(
            user=self.user, status=Order.STATUS_CANCELED, total=15
        )
        Order.objects.create(user=self.user, status=Order.STATUS_PENDING, total=10)
        Order.objects.create(user=other, status=Order.STATUS_PAID, total=99)

        self.client.force_authenticate(self.user)
        res = self.client.get("/api/orders/")
        self.assertEqual(res.status_code, 200)
        # Paid + canceled (newest first), but not pending and not other users'.
        self.assertEqual({o["id"] for o in res.data}, {paid.id, canceled.id})

    def test_can_cancel_flag_reflects_status(self):
        paid = Order.objects.create(user=self.user, status=Order.STATUS_PAID, total=40)
        canceled = Order.objects.create(
            user=self.user, status=Order.STATUS_CANCELED, total=15
        )
        self.client.force_authenticate(self.user)
        res = self.client.get("/api/orders/")
        flags = {o["id"]: o["can_cancel"] for o in res.data}
        self.assertTrue(flags[paid.id])
        self.assertFalse(flags[canceled.id])


@override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
class OrderCancelTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "fan", "fan@example.com", "Sup3rSecret!"
        )
        self.product = Product.objects.create(
            name="Tour Tee", price=20, stock=3, is_active=True
        )
        self.order = Order.objects.create(
            user=self.user,
            status=Order.STATUS_PAID,
            total=40,
            stripe_payment_intent="pi_123",
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            name="Tour Tee",
            unit_price=20,
            quantity=2,
        )

    def _cancel(self, order_id, reason="Changed my mind"):
        return self.client.post(
            f"/api/orders/{order_id}/cancel/", {"reason": reason}, format="json"
        )

    def test_cancel_requires_auth(self):
        res = self.client.post(f"/api/orders/{self.order.id}/cancel/")
        self.assertIn(res.status_code, (401, 403))

    @patch("apps.orders.services.stripe.Refund.create")
    def test_cancel_refunds_restocks_and_stores_reason(self, mock_refund):
        self.client.force_authenticate(self.user)
        res = self._cancel(self.order.id, reason="Ordered the wrong size")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], Order.STATUS_CANCELED)
        self.assertFalse(res.data["can_cancel"])
        mock_refund.assert_called_once_with(payment_intent="pi_123")

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_CANCELED)
        self.assertEqual(self.order.cancel_reason, "Ordered the wrong size")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)  # 3 + 2 returned

    @patch("apps.orders.services.stripe.Refund.create")
    def test_cancel_requires_a_reason(self, mock_refund):
        self.client.force_authenticate(self.user)
        res = self.client.post(f"/api/orders/{self.order.id}/cancel/", {}, format="json")
        self.assertEqual(res.status_code, 400)
        mock_refund.assert_not_called()

    @patch("apps.orders.services.stripe.Refund.create")
    def test_fulfilling_order_can_still_cancel(self, mock_refund):
        self.order.status = Order.STATUS_FULFILLING
        self.order.save(update_fields=["status"])
        self.client.force_authenticate(self.user)
        res = self._cancel(self.order.id)
        self.assertEqual(res.status_code, 200)
        mock_refund.assert_called_once()

    @patch("apps.orders.services.stripe.Refund.create")
    def test_shipped_order_cannot_cancel(self, mock_refund):
        self.order.status = Order.STATUS_SHIPPED
        self.order.save(update_fields=["status"])
        self.client.force_authenticate(self.user)
        res = self._cancel(self.order.id)
        self.assertEqual(res.status_code, 400)
        mock_refund.assert_not_called()

    @patch("apps.orders.services.stripe.Refund.create")
    def test_cannot_cancel_someone_elses_order(self, mock_refund):
        other = get_user_model().objects.create_user(
            "other", "other@example.com", "Sup3rSecret!"
        )
        self.client.force_authenticate(other)
        res = self._cancel(self.order.id)
        self.assertEqual(res.status_code, 404)
        mock_refund.assert_not_called()

    @patch("apps.orders.services.stripe.Refund.create")
    def test_cannot_cancel_twice(self, mock_refund):
        self.order.status = Order.STATUS_CANCELED
        self.order.save(update_fields=["status"])
        self.client.force_authenticate(self.user)
        res = self._cancel(self.order.id)
        self.assertEqual(res.status_code, 400)
        mock_refund.assert_not_called()


@override_settings(
    STRIPE_SECRET_KEY="sk_test_dummy",
    BAND_NOTIFICATION_EMAIL="band@cemented.band",
    DEFAULT_FROM_EMAIL="orders@cemented.band",
)
class CancelServiceTests(TestCase):
    """The shared cancel/refund service used by both the API and the admin."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "fan", "fan@example.com", "Sup3rSecret!"
        )
        self.product = Product.objects.create(
            name="Tour Tee", price=20, stock=3, is_active=True
        )
        self.order = Order.objects.create(
            user=self.user,
            email="fan@example.com",
            status=Order.STATUS_PAID,
            total=40,
            stripe_payment_intent="pi_123",
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            name="Tour Tee",
            unit_price=20,
            quantity=2,
        )

    @patch("apps.orders.services.stripe.Refund.create")
    def test_refunds_restocks_emails_and_cancels(self, mock_refund):
        self.assertTrue(cancel_and_refund(self.order, reason="Defective print"))
        mock_refund.assert_called_once_with(payment_intent="pi_123")

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_CANCELED)
        self.assertEqual(self.order.cancel_reason, "Defective print")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)  # 3 + 2 returned
        # Customer confirmation + band notice.
        self.assertEqual(len(mail.outbox), 2)
        recipients = {addr for m in mail.outbox for addr in m.to}
        self.assertIn("fan@example.com", recipients)
        self.assertIn("band@cemented.band", recipients)

    @patch("apps.orders.services.stripe.Refund.create")
    def test_is_idempotent(self, mock_refund):
        self.assertTrue(cancel_and_refund(self.order, reason="One"))
        # A second call must not refund again or restock twice.
        self.assertFalse(cancel_and_refund(self.order, reason="Two"))
        mock_refund.assert_called_once()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    @patch("apps.orders.services.stripe.Refund.create")
    def test_noop_once_shipped(self, mock_refund):
        self.order.status = Order.STATUS_SHIPPED
        self.order.save(update_fields=["status"])
        self.assertFalse(cancel_and_refund(self.order, reason="Too late"))
        mock_refund.assert_not_called()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    BAND_NOTIFICATION_EMAIL="band@cemented.band",
    DEFAULT_FROM_EMAIL="orders@cemented.band",
)
class OrderEmailTests(TestCase):
    def test_paid_order_emails_customer_and_band(self):
        from apps.orders.emails import send_order_emails

        user = get_user_model().objects.create_user(
            "fan", "fan@example.com", "Sup3rSecret!"
        )
        order = Order.objects.create(
            user=user, email="fan@example.com", status=Order.STATUS_PAID, total=25
        )
        OrderItem.objects.create(order=order, name="Tee", unit_price=25, quantity=1)

        send_order_emails(order)

        self.assertEqual(len(mail.outbox), 2)
        recipients = {addr for message in mail.outbox for addr in message.to}
        self.assertIn("fan@example.com", recipients)
        self.assertIn("band@cemented.band", recipients)


class OrderEmailNormalizationTests(TestCase):
    """order.email is stored canonically (trimmed + lowercased). A stray
    capital had made a customer email silently fail in Resend's test mode,
    which compares the recipient case-sensitively against the account address."""

    def test_email_is_lowercased_and_trimmed_on_save(self):
        order = Order.objects.create(email="  Fan.Name@Example.COM ", total=10)
        order.refresh_from_db()
        self.assertEqual(order.email, "fan.name@example.com")

    def test_blank_email_stays_blank(self):
        order = Order.objects.create(email="", total=10)
        order.refresh_from_db()
        self.assertEqual(order.email, "")
