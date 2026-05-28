"""Order emails, sent when an order is marked paid.

Best-effort: every send is guarded so a mail failure can never break webhook
processing (Stripe must still get a 200, and the order must stay paid).
"""
import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _summary(order):
    lines = "\n".join(
        f"  {item.quantity} x {item.name} — ${item.line_total}"
        for item in order.items.all()
    )
    return f"Order #{order.id}\n\n{lines}\n\nTotal: ${order.total}"


def send_order_emails(order):
    """Email the customer a confirmation and notify the band. Never raises."""
    try:
        summary = _summary(order)
    except Exception:
        logger.exception("Could not build order summary for order %s", order.id)
        return

    if order.email:
        try:
            send_mail(
                f"Your Cemented order #{order.id}",
                f"Thanks for the support!\n\n{summary}",
                None,  # falls back to DEFAULT_FROM_EMAIL
                [order.email],
            )
        except Exception:
            logger.exception("Customer confirmation failed for order %s", order.id)

    if settings.BAND_NOTIFICATION_EMAIL:
        try:
            send_mail(
                f"New order #{order.id} — ${order.total}",
                summary,
                None,
                [settings.BAND_NOTIFICATION_EMAIL],
            )
        except Exception:
            logger.exception("Band notification failed for order %s", order.id)
