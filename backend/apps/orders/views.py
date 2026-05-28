"""Cart endpoints (login-required) + Stripe checkout and webhook."""
import stripe
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.store.models import Product

from .emails import send_order_emails
from .models import Cart, CartItem, Order, OrderItem
from .serializers import CartSerializer, OrderSerializer


def _get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def _cart_response(cart, request, status_code=status.HTTP_200_OK):
    return Response(
        CartSerializer(cart, context={"request": request}).data, status=status_code
    )


# --------------------------------------------------------------------------- #
# Cart
# --------------------------------------------------------------------------- #
class OrderListView(generics.ListAPIView):
    """The current customer's paid orders, newest first."""

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(
            user=self.request.user, status=Order.STATUS_PAID
        )


class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return _cart_response(_get_cart(request.user), request)


class CartItemsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        product = Product.objects.filter(
            id=request.data.get("product_id"), is_active=True
        ).first()
        if product is None:
            return Response(
                {"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND
            )
        if product.stock <= 0:
            return Response(
                {"detail": "This item is out of stock."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            quantity = max(1, int(request.data.get("quantity", 1)))
        except (TypeError, ValueError):
            quantity = 1

        cart = _get_cart(request.user)
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": min(quantity, product.stock)},
        )
        if not created:
            # never let a line exceed what's actually in stock
            item.quantity = min(item.quantity + quantity, product.stock)
            item.save()
        return _cart_response(cart, request, status.HTTP_201_CREATED)


class CartItemDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, item_id):
        cart = _get_cart(request.user)
        item = CartItem.objects.filter(id=item_id, cart=cart).first()
        if item is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            quantity = int(request.data.get("quantity", item.quantity))
        except (TypeError, ValueError):
            quantity = item.quantity
        if quantity <= 0:
            item.delete()
        else:
            item.quantity = quantity
            item.save()
        return _cart_response(cart, request)

    def delete(self, request, item_id):
        cart = _get_cart(request.user)
        CartItem.objects.filter(id=item_id, cart=cart).delete()
        return _cart_response(cart, request)


# --------------------------------------------------------------------------- #
# Checkout (Stripe hosted Checkout Session)
# --------------------------------------------------------------------------- #
class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cart = _get_cart(request.user)
        items = list(cart.items.select_related("product"))
        if not items:
            return Response(
                {"detail": "Your cart is empty."}, status=status.HTTP_400_BAD_REQUEST
            )
        # Re-check stock at checkout — it may have changed since items were added.
        for item in items:
            if item.quantity > item.product.stock:
                return Response(
                    {
                        "detail": (
                            f"Not enough stock for {item.product.name} "
                            f"(only {item.product.stock} left)."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if not settings.STRIPE_SECRET_KEY:
            return Response(
                {"detail": "Payments are not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        stripe.api_key = settings.STRIPE_SECRET_KEY

        order = Order.objects.create(
            user=request.user,
            email=request.user.email.lower(),
            status=Order.STATUS_PENDING,
        )
        line_items = []
        total = 0
        for item in items:
            unit_price = item.product.price  # priced from the DB, never the client
            total += unit_price * item.quantity
            line_items.append(
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": item.product.name},
                        "unit_amount": int(unit_price * 100),  # cents
                    },
                    "quantity": item.quantity,
                }
            )
            OrderItem.objects.create(
                order=order,
                product=item.product,
                name=item.product.name,
                unit_price=unit_price,
                quantity=item.quantity,
            )
        order.total = total
        order.save()

        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=line_items,
            success_url=settings.CHECKOUT_SUCCESS_URL,
            cancel_url=settings.CHECKOUT_CANCEL_URL,
            client_reference_id=str(order.id),
            customer_email=request.user.email or None,
            metadata={"order_id": str(order.id)},
        )
        order.stripe_session_id = session.id
        order.save(update_fields=["stripe_session_id"])
        return Response({"checkout_url": session.url})


# --------------------------------------------------------------------------- #
# Stripe webhook — the source of truth for payment (NOT the redirect)
# --------------------------------------------------------------------------- #
def _field(obj, key, default=None):
    """Read a key from a Stripe object or a plain dict.

    Stripe objects support subscripting (obj[key]) but NOT dict.get() or
    dict(obj), so subscript-with-fallback is the only access that works for both.
    """
    try:
        return obj[key]
    except (KeyError, TypeError):
        return default


def _fulfill_checkout(session):
    metadata = _field(session, "metadata") or {}
    order_id = _field(metadata, "order_id") or _field(session, "client_reference_id")
    order = Order.objects.filter(id=order_id).first()
    if order is None:
        return
    order.status = Order.STATUS_PAID
    order.stripe_payment_intent = _field(session, "payment_intent") or ""
    order.save()
    # Decrement inventory for what was purchased.
    for line in order.items.all():
        if line.product:
            line.product.stock = max(0, line.product.stock - line.quantity)
            line.product.save(update_fields=["stock"])
    if order.user_id:  # empty the cart now that they've paid
        CartItem.objects.filter(cart__user_id=order.user_id).delete()
    send_order_emails(order)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse(status=503)
    try:
        event = stripe.Webhook.construct_event(
            request.body,
            request.META.get("HTTP_STRIPE_SIGNATURE", ""),
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        return HttpResponseBadRequest("Invalid payload")
    except stripe.error.SignatureVerificationError:
        return HttpResponseBadRequest("Invalid signature")

    if event["type"] == "checkout.session.completed":
        _fulfill_checkout(event["data"]["object"])
    return HttpResponse(status=200)
