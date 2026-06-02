"""Order business logic shared by the API and the admin.

Keeping the cancel/refund flow here — rather than inside a view — means the
customer endpoint and the staff admin cancel an order the *exact same* way:
refund, restock, notify. One implementation, so the two paths can't drift.
"""
import stripe
from django.conf import settings
from django.db import transaction

from .emails import send_cancellation_email
from .models import Order


def cancel_and_refund(order, reason=""):
    """Refund an order's Stripe payment, cancel it, restock, and email.

    Idempotent: the row is locked and its status re-checked inside the
    transaction, so a double-submit — or the customer and staff racing — can
    never issue two refunds.

    Returns True if it canceled the order, False if the order was already past
    a cancelable state (a safe no-op). Raises ``stripe.error.StripeError`` if
    Stripe rejects the refund, so callers can surface that however they like.
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY
    with transaction.atomic():
        locked = Order.objects.select_for_update().filter(pk=order.pk).first()
        if locked is None or locked.status not in Order.CANCELABLE_STATUSES:
            return False
        if not locked.stripe_payment_intent:
            return False

        # Refund first: if Stripe rejects it this raises and the transaction
        # rolls back, so we never mark an order canceled without a refund.
        stripe.Refund.create(payment_intent=locked.stripe_payment_intent)

        locked.status = Order.STATUS_CANCELED
        if reason:
            locked.cancel_reason = reason[:500]
        locked.save(update_fields=["status", "cancel_reason", "updated_at"])

        # Put inventory back — mirrors the decrement at fulfilment (per-size
        # when the line had a size, otherwise the product's flat stock).
        for line in locked.items.select_related("product", "size"):
            if line.size_id:
                line.size.stock += line.quantity
                line.size.save(update_fields=["stock"])
            elif line.product:
                line.product.stock += line.quantity
                line.product.save(update_fields=["stock"])

    # Email after commit so a rolled-back cancel never sends a "canceled" notice.
    send_cancellation_email(locked)
    return True
