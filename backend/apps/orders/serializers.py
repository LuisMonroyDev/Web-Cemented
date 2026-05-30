from rest_framework import serializers

from apps.store.serializers import ProductSerializer

from .models import Cart, CartItem, Order, OrderItem


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "product", "quantity", "line_total"]


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
        fields = ["id", "name", "unit_price", "quantity", "line_total"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    can_cancel = serializers.SerializerMethodField()
    shipping = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "status_display",
            "total",
            "created_at",
            "items",
            "can_cancel",
            "tracking_number",
            "cancel_reason",
            "shipping",
        ]

    def get_can_cancel(self, order):
        # Cancelable (and refundable) only before it ships. Once shipped,
        # delivered, or already canceled there's nothing to cancel here.
        return order.status in Order.CANCELABLE_STATUSES

    def get_shipping(self, order):
        # Surface the address only when we actually captured one.
        if not order.has_shipping_address:
            return None
        return {"lines": order.shipping_lines}
