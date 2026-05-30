import stripe
from django.conf import settings
from django.contrib import admin, messages

from .emails import send_delivered_email, send_shipped_email
from .models import Order, OrderItem
from .services import cancel_and_refund


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("product", "name", "unit_price", "quantity", "line_total")

    @admin.display(description="Line total")
    def line_total(self, obj):
        # The inline's blank "add another" template row is an unsaved OrderItem
        # with no unit_price, so guard against computing None * quantity.
        if obj.unit_price is None:
            return "—"
        return obj.line_total


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "email", "status", "total", "tracking_number", "created_at")
    list_filter = ("status",)
    search_fields = (
        "email",
        "stripe_session_id",
        "stripe_payment_intent",
        "tracking_number",
    )
    # status + tracking_number stay editable so the band can advance an order
    # and record its tracking number; everything else is set by checkout.
    readonly_fields = (
        "user",
        "email",
        "total",
        "shipping_cost",
        "stripe_session_id",
        "stripe_payment_intent",
        "shipping_address",
        "cancel_reason",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (None, {"fields": ("status", "tracking_number")}),
        ("Customer", {"fields": ("user", "email", "shipping_address")}),
        (
            "Payment",
            {"fields": ("total", "shipping_cost", "stripe_session_id", "stripe_payment_intent")},
        ),
        ("Cancellation", {"fields": ("cancel_reason",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    inlines = [OrderItemInline]
    actions = (
        "mark_fulfilling",
        "mark_shipped",
        "mark_delivered",
        "cancel_and_refund_orders",
    )

    @admin.display(description="Shipping address")
    def shipping_address(self, obj):
        # Multi-line address block from the snapshot captured at checkout.
        lines = obj.shipping_lines
        return "\n".join(lines) if lines else "—"

    def has_add_permission(self, request):
        # Orders are created by checkout, never by hand.
        return False

    def has_delete_permission(self, request, obj=None):
        # Deleting a paid order is destructive: the Stripe charge lives on, but
        # we lose the row (and its payment_intent) that lets us refund it from
        # here — leaving a real charge with no way to refund it through the admin.
        # Block deletion of any order that still has a live, un-refunded charge.
        # Pending (never paid) and canceled (already refunded) orders are safe.
        if obj is not None and obj.stripe_payment_intent and obj.status != Order.STATUS_CANCELED:
            return False
        return super().has_delete_permission(request, obj)

    def get_actions(self, request):
        # Drop the bulk "delete selected" action entirely: it checks only the
        # model-level delete permission (obj=None), so it would bypass the
        # per-order guard above and could wipe paid orders with live charges.
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def save_model(self, request, obj, form, change):
        # Setting status to "canceled" from the change form must actually
        # refund the customer (and restock + email), not just flip the label.
        # Route that through the shared service instead of a plain save.
        if change and "status" in form.changed_data and obj.status == Order.STATUS_CANCELED:
            # Each branch below posts its own precise message and may leave the
            # order unsaved (blocked or refund-failed). Flag the request so
            # response_change skips Django's default "was changed successfully"
            # — redundant on success, and outright wrong when we blocked it.
            request._cancellation_handled = True
            if not settings.STRIPE_SECRET_KEY:
                self.message_user(
                    request, "Stripe isn't configured — can't refund.", messages.ERROR
                )
                return
            try:
                canceled = cancel_and_refund(obj, reason="Canceled by staff")
            except stripe.error.StripeError:
                self.message_user(
                    request,
                    "Stripe refund failed — order left unchanged.",
                    messages.ERROR,
                )
                return
            if canceled:
                self.message_user(
                    request,
                    f"Order #{obj.pk} refunded, canceled, and customer emailed.",
                )
            else:
                self.message_user(
                    request,
                    f"Order #{obj.pk} can't be canceled at its current stage.",
                    messages.WARNING,
                )
            return
        super().save_model(request, obj, form, change)
        # Notify the customer when the order transitions to shipped, including
        # the tracking number/link the band just entered on the same form.
        if change and "status" in form.changed_data and obj.status == Order.STATUS_SHIPPED:
            send_shipped_email(obj)
            self.message_user(
                request, f"Order #{obj.pk} marked shipped — customer notified."
            )
        # Likewise, confirm delivery with a thank-you when it transitions to
        # delivered (the email reuses the captured address + tracking link).
        if change and "status" in form.changed_data and obj.status == Order.STATUS_DELIVERED:
            send_delivered_email(obj)
            self.message_user(
                request, f"Order #{obj.pk} marked delivered — customer notified."
            )

    def response_change(self, request, obj):
        # When save_model handled a cancellation it already posted a precise
        # message — and on a blocked/failed cancel it never saved the order.
        # Skip Django's default success message (a lie in that case) and just
        # run the normal post-save redirect back to the changelist.
        if getattr(request, "_cancellation_handled", False):
            return self.response_post_save_change(request, obj)
        return super().response_change(request, obj)

    @admin.action(description="Mark selected orders as fulfilling")
    def mark_fulfilling(self, request, queryset):
        updated = queryset.update(status=Order.STATUS_FULFILLING)
        self.message_user(request, f"{updated} order(s) marked fulfilling.")

    @admin.action(description="Mark selected orders as shipped")
    def mark_shipped(self, request, queryset):
        # Iterate (not bulk update) so each order saves through the model and
        # gets a shipped email with its tracking number/link. Skip orders that
        # are already shipped so we don't re-notify the customer.
        sent = 0
        for order in queryset.exclude(status=Order.STATUS_SHIPPED):
            order.status = Order.STATUS_SHIPPED
            order.save(update_fields=["status", "updated_at"])
            send_shipped_email(order)
            sent += 1
        self.message_user(request, f"{sent} order(s) marked shipped and emailed.")

    @admin.action(description="Mark selected orders as delivered")
    def mark_delivered(self, request, queryset):
        # Iterate (not bulk update) so each order saves through the model and
        # gets a delivery confirmation + thank-you email. Skip orders already
        # delivered so we don't re-notify the customer.
        sent = 0
        for order in queryset.exclude(status=Order.STATUS_DELIVERED):
            order.status = Order.STATUS_DELIVERED
            order.save(update_fields=["status", "updated_at"])
            send_delivered_email(order)
            sent += 1
        self.message_user(request, f"{sent} order(s) marked delivered and emailed.")

    @admin.action(description="Cancel & refund selected orders")
    def cancel_and_refund_orders(self, request, queryset):
        done = skipped = failed = 0
        for order in queryset:
            try:
                if cancel_and_refund(order, reason="Canceled by staff"):
                    done += 1
                else:
                    skipped += 1  # already shipped/canceled — not refundable here
            except stripe.error.StripeError:
                failed += 1
        level = messages.ERROR if failed else messages.INFO
        self.message_user(
            request,
            f"Refunded & canceled {done}; skipped {skipped}; failed {failed}.",
            level,
        )
