"""Order emails, sent when an order is marked paid.

Best-effort: every send is guarded so a mail failure can never break webhook
processing (Stripe must still get a 200, and the order must stay paid).
"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import Order

logger = logging.getLogger(__name__)


def _summary(order, items):
    lines = "\n".join(
        f"  {item.quantity} x {item.name}"
        f"{f' ({item.size_label})' if item.size_label else ''}"
        f" — ${item.line_total}"
        for item in items
    )
    summary = f"Order #{order.id}\n\n{lines}\n"
    if order.shipping_cost:
        summary += f"\nShipping: ${order.shipping_cost}"
    summary += f"\nTotal: ${order.total}"
    if order.has_shipping_address:
        summary += "\n\nShip to:\n" + "\n".join(
            f"  {line}" for line in order.shipping_lines
        )
    return summary


def _html(order, items, heading, intro, track_url="", track_label=""):
    return render_to_string(
        "orders/order_email.html",
        {
            "order": order,
            "items": items,
            "heading": heading,
            "intro": intro,
            "shipping_lines": order.shipping_lines,
            # Only the shipped/delivered emails pass these; the template hides
            # the button otherwise. track_label tunes the wording ("Track your
            # package" vs. "View delivery confirmation").
            "track_url": track_url,
            "track_label": track_label,
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


def send_shipped_email(order):
    """Tell the customer their order shipped, with the USPS tracking number and
    a link to track it. Never raises — used from the admin save/action paths."""
    if not order.email:
        return
    try:
        items = list(order.items.all())
        summary = _summary(order, items)
    except Exception:
        logger.exception("Could not build shipped summary for order %s", order.id)
        return

    tracking = order.tracking_number
    track_url = Order.usps_tracking_url(tracking) or ""
    heading = "Your order is on its way"
    if tracking:
        intro = (
            f"Order #{order.id} has shipped. Track it with USPS using tracking "
            f"number {tracking}."
        )
    else:
        intro = f"Order #{order.id} has shipped."

    try:
        text = f"{heading}\n\n{intro}\n\n{summary}"
        if track_url:
            text += f"\n\nTrack your package:\n{track_url}"
        send_mail(
            f"Your Cemented order #{order.id} has shipped",
            text,
            None,  # falls back to DEFAULT_FROM_EMAIL
            [order.email],
            html_message=_html(order, items, heading, intro, track_url=track_url),
        )
    except Exception:
        logger.exception("Shipped email failed for order %s", order.id)


def send_delivered_email(order):
    """Tell the customer their order was delivered: the delivered status, their
    shipping address, a USPS link to the delivery record, and a thank-you. Never
    raises — used from the admin save/action paths."""
    if not order.email:
        return
    try:
        items = list(order.items.all())
        summary = _summary(order, items)
    except Exception:
        logger.exception("Could not build delivered summary for order %s", order.id)
        return

    track_url = Order.usps_tracking_url(order.tracking_number) or ""
    heading = "Your order was delivered"
    intro = (
        f"Order #{order.id} has been delivered. Thank you for supporting "
        "Cemented — we hope it was worth the wait."
    )

    try:
        text = f"{heading}\n\n{intro}\n\n{summary}"
        if track_url:
            text += f"\n\nDelivery confirmation:\n{track_url}"
        send_mail(
            f"Your Cemented order #{order.id} was delivered",
            text,
            None,  # falls back to DEFAULT_FROM_EMAIL
            [order.email],
            html_message=_html(
                order,
                items,
                heading,
                intro,
                track_url=track_url,
                track_label="View delivery confirmation",
            ),
        )
    except Exception:
        logger.exception("Delivered email failed for order %s", order.id)
