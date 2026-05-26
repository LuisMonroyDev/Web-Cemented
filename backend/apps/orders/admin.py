from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("product", "name", "unit_price", "quantity", "line_total")

    @admin.display(description="Line total")
    def line_total(self, obj):
        return obj.line_total


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "email", "status", "total", "created_at")
    list_filter = ("status",)
    search_fields = ("email", "stripe_session_id", "stripe_payment_intent")
    readonly_fields = (
        "user",
        "email",
        "total",
        "stripe_session_id",
        "stripe_payment_intent",
        "created_at",
        "updated_at",
    )
    inlines = [OrderItemInline]

    def has_add_permission(self, request):
        # Orders are created by checkout, never by hand.
        return False
