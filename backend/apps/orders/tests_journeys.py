"""End-to-end regression tests for the customer purchase pipeline.

These drive full journeys through the real API + test DB, mocking only the
external boundaries (Stripe + email). They guard the highest-risk paths:
the full purchase flow, cart ownership, stock handling, checkout, and the
Stripe webhook.
"""
from unittest.mock import patch

import stripe
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.store.models import Product

from .models import Order, OrderItem


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def make_user(username="fan", email="fan@example.com", password="Sup3rSecret!"):
    return get_user_model().objects.create_user(username, email, password)


def stripe_session(order_id, payment_intent="pi_test_123"):
    """A real Stripe object (supports [] but not .get()), matching live shape.

    A plain dict would hide the access-pattern bug that broke the live webhook.
    """
    return stripe.checkout.Session.construct_from(
        {
            "metadata": {"order_id": str(order_id)},
            "payment_intent": payment_intent,
            "client_reference_id": str(order_id),
        },
        "sk_test_dummy",
    )


def fire_webhook(client, order, payment_intent="pi_test_123"):
    """POST a checkout.session.completed webhook for an order (signature mocked)."""
    with patch("apps.orders.views.stripe.Webhook.construct_event") as mock_construct:
        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {"object": stripe_session(order.id, payment_intent)},
        }
        return client.post(
            "/api/webhooks/stripe/",
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=sig",
        )


# --------------------------------------------------------------------------- #
# Headline end-to-end journey
# --------------------------------------------------------------------------- #
@override_settings(
    STRIPE_SECRET_KEY="sk_test_dummy",
    STRIPE_WEBHOOK_SECRET="whsec_dummy",
    BAND_NOTIFICATION_EMAIL="band@cemented.band",
    DEFAULT_FROM_EMAIL="orders@cemented.band",
)
class FullPurchaseJourneyTests(TestCase):
    """Register -> browse -> cart -> checkout -> webhook -> fulfilled order."""

    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(
            name="Tour Tee", price=20, stock=5, is_active=True
        )

    @patch("apps.orders.views.stripe.checkout.Session.create")
    def test_register_through_to_paid_order(self, mock_session):
        mock_session.return_value = type(
            "S", (), {"id": "cs_1", "url": "https://stripe.test/cs_1"}
        )()

        # 1. Register (auto-logs in via session cookie). Mixed-case email on
        #    purpose — the order must store it lowercased.
        reg = self.client.post(
            "/api/auth/register/",
            {"username": "fan", "email": "Fan@Example.com", "password": "Sup3rSecret!"},
            format="json",
        )
        self.assertEqual(reg.status_code, 201)

        # 2. Browse the storefront.
        products = self.client.get("/api/products/")
        self.assertEqual(products.status_code, 200)
        self.assertEqual(len(products.json()), 1)

        # 3. Add to cart.
        added = self.client.post(
            "/api/cart/items/",
            {"product_id": self.product.id, "quantity": 2},
            format="json",
        )
        self.assertEqual(added.status_code, 201)

        # 4. Checkout creates a pending order + Stripe session.
        checkout = self.client.post("/api/checkout/")
        self.assertEqual(checkout.status_code, 200)
        self.assertEqual(checkout.data["checkout_url"], "https://stripe.test/cs_1")
        order = Order.objects.get()
        self.assertEqual(order.status, Order.STATUS_PENDING)
        self.assertEqual(order.email, "fan@example.com")  # normalized

        # 5. Stripe confirms payment via webhook (the source of truth).
        self.assertEqual(fire_webhook(self.client, order).status_code, 200)

        # 6. Order is fulfilled end to end.
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_PAID)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)  # 5 - 2 sold
        self.assertEqual(self.client.get("/api/cart/").data["items"], [])

        self.assertEqual(len(mail.outbox), 2)
        recipients = {addr for m in mail.outbox for addr in m.to}
        self.assertIn("fan@example.com", recipients)
        self.assertIn("band@cemented.band", recipients)

        # 7. Order is visible in the customer's account.
        orders = self.client.get("/api/orders/")
        self.assertEqual([o["id"] for o in orders.data], [order.id])


# --------------------------------------------------------------------------- #
# Cart ownership + isolation (security)
# --------------------------------------------------------------------------- #
class CartOwnershipTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.alice = make_user("alice", "alice@example.com")
        self.bob = make_user("bob", "bob@example.com")
        self.product = Product.objects.create(
            name="Tee", price=10, stock=10, is_active=True
        )

    def _alice_adds_item(self):
        self.client.force_authenticate(self.alice)
        self.client.post(
            "/api/cart/items/",
            {"product_id": self.product.id, "quantity": 1},
            format="json",
        )
        from .models import CartItem

        return CartItem.objects.get()

    def test_user_cannot_modify_another_users_cart_item(self):
        item = self._alice_adds_item()
        self.client.force_authenticate(self.bob)
        self.assertEqual(
            self.client.patch(
                f"/api/cart/items/{item.id}/", {"quantity": 99}, format="json"
            ).status_code,
            404,
        )

    def test_user_cannot_delete_another_users_cart_item(self):
        item = self._alice_adds_item()
        self.client.force_authenticate(self.bob)
        self.client.delete(f"/api/cart/items/{item.id}/")
        item.refresh_from_db()  # must still exist
        self.assertEqual(item.quantity, 1)

    def test_carts_are_isolated_per_user(self):
        self._alice_adds_item()
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.get("/api/cart/").data["items"], [])


# --------------------------------------------------------------------------- #
# Cart mutations
# --------------------------------------------------------------------------- #
class CartMutationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(self.user)
        self.product = Product.objects.create(
            name="Tee", price=10, stock=10, is_active=True
        )

    def _add(self, qty=1):
        from .models import CartItem

        self.client.post(
            "/api/cart/items/",
            {"product_id": self.product.id, "quantity": qty},
            format="json",
        )
        return CartItem.objects.get(cart__user=self.user, product=self.product)

    def test_patch_updates_quantity(self):
        item = self._add(1)
        res = self.client.patch(
            f"/api/cart/items/{item.id}/", {"quantity": 4}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 4)

    def test_patch_zero_quantity_removes_item(self):
        from .models import CartItem

        item = self._add(2)
        res = self.client.patch(
            f"/api/cart/items/{item.id}/", {"quantity": 0}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(CartItem.objects.filter(id=item.id).exists())

    def test_delete_removes_item(self):
        from .models import CartItem

        item = self._add(1)
        res = self.client.delete(f"/api/cart/items/{item.id}/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(CartItem.objects.filter(id=item.id).exists())

    def test_add_nonexistent_product_returns_404(self):
        res = self.client.post(
            "/api/cart/items/", {"product_id": 999999, "quantity": 1}, format="json"
        )
        self.assertEqual(res.status_code, 404)

    def test_add_inactive_product_returns_404(self):
        hidden = Product.objects.create(
            name="Hidden", price=10, stock=5, is_active=False
        )
        res = self.client.post(
            "/api/cart/items/", {"product_id": hidden.id, "quantity": 1}, format="json"
        )
        self.assertEqual(res.status_code, 404)

    def test_garbage_quantity_defaults_to_one(self):
        res = self.client.post(
            "/api/cart/items/",
            {"product_id": self.product.id, "quantity": "abc"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["items"][0]["quantity"], 1)


# --------------------------------------------------------------------------- #
# Checkout edges
# --------------------------------------------------------------------------- #
@override_settings(STRIPE_SECRET_KEY="sk_test_dummy")
class CheckoutEdgeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user(email="Buyer@Example.com")
        self.client.force_authenticate(self.user)
        self.product = Product.objects.create(
            name="Tee", price=20, stock=10, is_active=True
        )

    def _add(self, qty):
        self.client.post(
            "/api/cart/items/",
            {"product_id": self.product.id, "quantity": qty},
            format="json",
        )

    @patch("apps.orders.views.stripe.checkout.Session.create")
    def test_checkout_rejected_when_stock_dropped_below_cart(self, mock_session):
        self._add(5)
        self.product.stock = 2  # someone else bought most of it
        self.product.save(update_fields=["stock"])
        res = self.client.post("/api/checkout/")
        self.assertEqual(res.status_code, 400)
        mock_session.assert_not_called()
        self.assertEqual(Order.objects.count(), 0)

    @override_settings(STRIPE_SECRET_KEY="")
    def test_checkout_503_when_stripe_unconfigured(self):
        self._add(1)
        self.assertEqual(self.client.post("/api/checkout/").status_code, 503)

    @patch("apps.orders.views.stripe.checkout.Session.create")
    def test_total_and_unit_price_snapshot_from_db(self, mock_session):
        mock_session.return_value = type("S", (), {"id": "cs_1", "url": "u"})()
        self._add(3)
        self.client.post("/api/checkout/")
        order = Order.objects.get()
        # Items come straight from the DB (3 × $20 = $60); checkout adds the
        # flat $5 shipping fee on top, so the charged total is $65.
        self.assertEqual(str(order.items.get().unit_price), "20.00")
        self.assertEqual(str(order.shipping_cost), "5.00")
        self.assertEqual(str(order.total), "65.00")

    @patch("apps.orders.views.stripe.checkout.Session.create")
    def test_order_email_normalized_to_lowercase(self, mock_session):
        mock_session.return_value = type("S", (), {"id": "cs_1", "url": "u"})()
        self._add(1)
        self.client.post("/api/checkout/")
        self.assertEqual(Order.objects.get().email, "buyer@example.com")


# --------------------------------------------------------------------------- #
# Webhook robustness
# --------------------------------------------------------------------------- #
@override_settings(STRIPE_WEBHOOK_SECRET="whsec_dummy")
class WebhookRobustnessTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.product = Product.objects.create(
            name="Tee", price=20, stock=5, is_active=True
        )

    def _pending_order(self, qty=2):
        order = Order.objects.create(
            user=self.user,
            email="fan@example.com",
            status=Order.STATUS_PENDING,
            total=20 * qty,
        )
        OrderItem.objects.create(
            order=order, product=self.product, name="Tee", unit_price=20, quantity=qty
        )
        return order

    @patch(
        "apps.orders.views.stripe.Webhook.construct_event",
        side_effect=stripe.error.SignatureVerificationError("bad", "sig"),
    )
    def test_bad_signature_returns_400(self, _mock):
        res = self.client.post(
            "/api/webhooks/stripe/",
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="bad",
        )
        self.assertEqual(res.status_code, 400)

    @patch(
        "apps.orders.views.stripe.Webhook.construct_event",
        side_effect=ValueError("bad payload"),
    )
    def test_bad_payload_returns_400(self, _mock):
        res = self.client.post(
            "/api/webhooks/stripe/",
            data="not json",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="x",
        )
        self.assertEqual(res.status_code, 400)

    @override_settings(STRIPE_WEBHOOK_SECRET="")
    def test_missing_secret_returns_503(self):
        res = self.client.post(
            "/api/webhooks/stripe/", data="{}", content_type="application/json"
        )
        self.assertEqual(res.status_code, 503)

    @patch("apps.orders.views.stripe.Webhook.construct_event")
    def test_unknown_event_type_is_noop_200(self, mock_construct):
        mock_construct.return_value = {
            "type": "payment_intent.created",
            "data": {"object": {}},
        }
        res = self.client.post(
            "/api/webhooks/stripe/",
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="x",
        )
        self.assertEqual(res.status_code, 200)

    @patch("apps.orders.views.stripe.Webhook.construct_event")
    def test_unknown_order_id_does_not_crash(self, mock_construct):
        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {"object": stripe_session(999999)},
        }
        res = self.client.post(
            "/api/webhooks/stripe/",
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="x",
        )
        self.assertEqual(res.status_code, 200)

    def test_stock_never_goes_negative(self):
        order = self._pending_order(qty=2)
        self.product.stock = 1  # less than the quantity ordered
        self.product.save(update_fields=["stock"])
        fire_webhook(self.client, order)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)  # max(0, 1 - 2)


# --------------------------------------------------------------------------- #
# Webhook idempotency — KNOWN GAP (expected failures)
# --------------------------------------------------------------------------- #
@override_settings(
    STRIPE_WEBHOOK_SECRET="whsec_dummy",
    BAND_NOTIFICATION_EMAIL="band@cemented.band",
    DEFAULT_FROM_EMAIL="orders@cemented.band",
)
class WebhookIdempotencyTests(TestCase):
    """Stripe retries deliveries; processing the same event twice is a no-op.

    `_fulfill_checkout` locks the order row and bails if it's already paid, so a
    duplicate delivery neither re-decrements stock nor re-sends emails.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.product = Product.objects.create(
            name="Tee", price=20, stock=5, is_active=True
        )

    def _pending_order(self, qty=2):
        order = Order.objects.create(
            user=self.user,
            email="fan@example.com",
            status=Order.STATUS_PENDING,
            total=20 * qty,
        )
        OrderItem.objects.create(
            order=order, product=self.product, name="Tee", unit_price=20, quantity=qty
        )
        return order

    def test_duplicate_delivery_decrements_stock_once(self):
        order = self._pending_order(qty=2)
        fire_webhook(self.client, order)
        fire_webhook(self.client, order)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)  # 5 - 2, not 5 - 4

    def test_duplicate_delivery_does_not_resend_emails(self):
        order = self._pending_order(qty=1)
        fire_webhook(self.client, order)
        mail.outbox.clear()
        fire_webhook(self.client, order)  # duplicate
        self.assertEqual(len(mail.outbox), 0)
