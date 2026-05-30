"""Order emails, sent when an order is marked paid.

Best-effort: every send is guarded so a mail failure can never break webhook
processing (Stripe must still get a 200, and the order must stay paid).
"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _summary(order, items):
    lines = "\n".join(
        f"  {item.quantity} x {item.name} — ${item.line_total}" for item in items
    )
    summary = f"Order #{order.id}\n\n{lines}\n\nTotal: ${order.total}"
    if order.has_shipping_address:
        summary += "\n\nShip to:\n" + "\n".join(
            f"  {line}" for line in order.shipping_lines
        )
    return summary


def _html(order, items, heading, intro):
    return render_to_string(
        "orders/order_email.html",
        {
            "order": order,
            "items": items,
            "heading": heading,
            "intro": intro,
            "shipping_lines": order.shipping_lines,
        },
    )


def send_order_emails(order):
    """Email the customer a confirmation and notify the band. Never raises."""
    try:
        items = list(order.items.all())
        summary = _summary(order, items)
    except Exception:
        logger.exception("Could not build order summary for order %s", order.id)
        return

    if order.email:
        try:
            heading = "Thanks for the support!"
            intro = "We got your order and we're on it. Here's what's coming your way."
            send_mail(
                f"Your Cemented order #{order.id}",
                f"{heading}\n\n{summary}",
                None,  # falls back to DEFAULT_FROM_EMAIL
                [order.email],
                html_message=_html(order, items, heading, intro),
            )
        except Exception:
            logger.exception("Customer confirmation failed for order %s", order.id)

    if settings.BAND_NOTIFICATION_EMAIL:
        try:
            heading = f"New order #{order.id}"
            intro = "A new order just came through the store."
            send_mail(
                f"New order #{order.id} — ${order.total}",
                summary,
                None,
                [settings.BAND_NOTIFICATION_EMAIL],
                html_message=_html(order, items, heading, intro),
            )
        except Exception:
            logger.exception("Band notification failed for order %s", order.id)


def send_cancellation_email(order):
    """Tell the customer their order was canceled + refunded, and notify the
    band (with the reason). Never raises — used from request/admin paths."""
    try:
        items = list(order.items.all())
        summary = _summary(order, items)
    except Exception:
        logger.exception("Could not build cancellation summary for order %s", order.id)
        return

    if order.email:
        try:
            heading = "Your order was canceled"
            intro = (
                "We've canceled your order and issued a full refund. It can take "
                "a few business days to appear on your statement."
            )
            send_mail(
                f"Your Cemented order #{order.id} was canceled",
                f"{heading}\n\n{summary}",
                None,  # falls back to DEFAULT_FROM_EMAIL
                [order.email],
                html_message=_html(order, items, heading, intro),
            )
        except Exception:
            logger.exception("Cancellation email failed for order %s", order.id)

    if settings.BAND_NOTIFICATION_EMAIL:
        try:
            heading = f"Order #{order.id} canceled"
            reason = order.cancel_reason or "No reason given"
            intro = f"This order was canceled and refunded. Reason: {reason}"
            send_mail(
                f"Canceled order #{order.id} — ${order.total} refunded",
                f"{intro}\n\n{summary}",
                None,
                [settings.BAND_NOTIFICATION_EMAIL],
                html_message=_html(order, items, heading, intro),
            )
        except Exception:
            logger.exception("Band cancellation notice failed for order %s", order.id)
