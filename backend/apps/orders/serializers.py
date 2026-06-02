from rest_framework import serializers

from apps.store.serializers import ProductSerializer

from .models import Cart, CartItem, Order, OrderItem


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    size = serializers.SerializerMethodField()
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "product", "size", "quantity", "line_total"]

    def get_size(self, item):
        # {id, label} when the line has a size, else null.
        if item.size_id:
            return {"id": item.size_id, "label": item.size.label}
        return None


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ["id", "items", "total"]


class OrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "name", "size_label", "unit_price", "quantity", "line_total"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    can_cancel = serializers.SerializerMethodField()
    shipping = serializers.SerializerMethodField()
    tracking_url = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "status_display",
            "total",
            "shipping_cost",
            "created_at",
            "items",
            "can_cancel",
            "tracking_number",
            "tracking_url",
            "cancel_reason",
            "shipping",
        ]

    def get_can_cancel(self, order):
        # Cancelable (and refundable) only before it ships. Once shipped,
        # delivered, or already canceled there's nothing to cancel here.
        return order.status in Order.CANCELABLE_STATUSES

    def get_tracking_url(self, order):
        # Public USPS tracking page for the number the band entered. The
        # frontend uses this both for the link and the QR code, so the URL
        # format lives here (one source of truth) rather than in the client.
        return Order.usps_tracking_url(order.tracking_number)

    def get_shipping(self, order):
        # Surface the address only when we actually captured one.
        if not order.has_shipping_address:
            return None
        return {"lines": order.shipping_lines}
