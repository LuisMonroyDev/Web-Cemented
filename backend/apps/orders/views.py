"""Cart endpoints (login-required) + Stripe checkout and webhook."""
import stripe
from django.conf import settings
from django.db import transaction
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
from .services import cancel_and_refund


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
    """The current customer's real orders, newest first.

    Only pending orders are hidden — those are abandoned/in-flight checkouts
    that were never paid. Everything else stays visible the whole way through
    fulfilment (paid → fulfilling → shipped → delivered) and after a refund
    (canceled), so the customer can always track an in-progress order and see
    that a canceled one was refunded.
    """

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).exclude(
            status=Order.STATUS_PENDING
        )


class OrderCancelView(APIView):
    """Cancel a paid order and refund it through Stripe.

    Refunds we initiate return their result synchronously, so unlike the
    payment flow (which trusts the webhook) we can refund and update the order
    in one request. The row is locked and the status re-checked so a
    double-submit can never issue a second refund.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        if not settings.STRIPE_SECRET_KEY:
            return Response(
                {"detail": "Payments are not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        # A reason is required — the friction discourages frivolous refunds.
        reason = (request.data.get("reason") or "").strip()
        if not reason:
            return Response(
                {"detail": "Please tell us why you're canceling."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Friendly pre-checks for nice error messages; the service re-checks
        # under a row lock, which is the authoritative guard against races.
        order = Order.objects.filter(id=order_id, user=request.user).first()
        if order is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if order.status not in Order.CANCELABLE_STATUSES:
            return Response(
                {"detail": "This order can no longer be canceled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not order.stripe_payment_intent:
            return Response(
                {"detail": "This order has no payment to refund."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            canceled = cancel_and_refund(order, reason)
        except stripe.error.StripeError:
            return Response(
                {"detail": "Refund could not be processed. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        if not canceled:  # lost a race — someone canceled it first
            return Response(
                {"detail": "This order can no longer be canceled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.refresh_from_db()
        return Response(OrderSerializer(order, context={"request": request}).data)


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

        # Resolve the chosen size for products that have them. Size-less
        # products keep a single line per product (size stays None).
        size = None
        if product.has_sizes:
            size_id = request.data.get("size_id")
            if not size_id:
                return Response(
                    {"detail": "Please choose a size."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            size = product.sizes.filter(id=size_id).first()
            if size is None:
                return Response(
                    {"detail": "That size isn't available."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            available = size.stock
        else:
            available = product.stock

        if available <= 0:
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
            size=size,
            defaults={"quantity": min(quantity, available)},
        )
        if not created:
            # never let a line exceed what's actually in stock
            item.quantity = min(item.quantity + quantity, available)
            item.save()
        return _cart_response(cart, request, status.HTTP_201_CREATED)


class CartItemDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, item_id):
        cart = _get_cart(request.user)
        item = CartItem.objects.filter(id=item_id, cart=cart).first()
        if item is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Change this line's size (sized products only — size-less products
        # ignore size_id). Validate the new size belongs to the product and is
        # in stock; if the cart already holds a line for that size, fold this
        # one into it, since (cart, product, size) is unique.
        if "size_id" in request.data and item.product.has_sizes:
            new_size = item.product.sizes.filter(id=request.data.get("size_id")).first()
            if new_size is None:
                return Response(
                    {"detail": "That size isn't available."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if new_size.stock <= 0:
                return Response(
                    {"detail": f"Size {new_size.label} is sold out."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if new_size.id != item.size_id:
                existing = (
                    CartItem.objects.filter(cart=cart, product=item.product, size=new_size)
                    .exclude(id=item.id)
                    .first()
                )
                if existing is not None:
                    existing.quantity = min(
                        existing.quantity + item.quantity, new_size.stock
                    )
                    existing.save()
                    item.delete()
                else:
                    item.size = new_size
                    item.quantity = min(item.quantity, new_size.stock)
                    item.save()
            return _cart_response(cart, request)

        try:
            quantity = int(request.data.get("quantity", item.quantity))
        except (TypeError, ValueError):
            quantity = item.quantity
        if quantity <= 0:
            item.delete()
        else:
            # Clamp to what's in stock for this line's size (or the product).
            item.quantity = min(quantity, item.available_stock)
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
        items = list(cart.items.select_related("product", "size"))
        if not items:
            return Response(
                {"detail": "Your cart is empty."}, status=status.HTTP_400_BAD_REQUEST
            )
        # Re-check stock at checkout — it may have changed since items were added.
        # Per-size when the line has a size, else the product's flat stock.
        for item in items:
            available = item.available_stock
            if item.quantity > available:
                label = f" ({item.size.label})" if item.size_id else ""
                return Response(
                    {
                        "detail": (
                            f"Not enough stock for {item.product.name}{label} "
                            f"(only {available} left)."
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
            # Show the size on the hosted Stripe page + receipt, e.g. "Tee — M".
            display_name = item.product.name
            if item.size_id:
                display_name = f"{item.product.name} — {item.size.label}"
            line_items.append(
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": display_name},
                        "unit_amount": int(unit_price * 100),  # cents
                    },
                    "quantity": item.quantity,
                }
            )
            OrderItem.objects.create(
                order=order,
                product=item.product,
                size=item.size,
                name=item.product.name,
                size_label=item.size.label if item.size_id else "",
                unit_price=unit_price,
                quantity=item.quantity,
            )
        # Flat shipping fee, folded into the order total so our records match
        # exactly what Stripe charges (items + shipping).
        shipping = settings.SHIPPING_FLAT_RATE
        order.shipping_cost = shipping
        order.total = total + shipping
        order.save()

        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=line_items,
            success_url=settings.CHECKOUT_SUCCESS_URL,
            cancel_url=settings.CHECKOUT_CANCEL_URL,
            client_reference_id=str(order.id),
            customer_email=request.user.email or None,
            metadata={"order_id": str(order.id)},
            # Let Stripe collect + validate the shipping address on its own
            # checkout page. We ship to the US only for now.
            shipping_address_collection={
                "allowed_countries": settings.SHIPPING_ALLOWED_COUNTRIES
            },
            # Charge the flat shipping fee as a Stripe shipping option so it
            # shows as its own line on the hosted checkout page.
            shipping_options=[
                {
                    "shipping_rate_data": {
                        "type": "fixed_amount",
                        "fixed_amount": {
                            "amount": int(shipping * 100),  # cents
                            "currency": "usd",
                        },
                        "display_name": "Standard shipping",
                    },
                }
            ],
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


def _shipping(session):
    """Pull the shipping name + address Stripe collected at checkout.

    Stripe moved this field across API versions: newer versions nest it under
    ``collected_information.shipping_details`` while older ones expose
    ``shipping_details`` directly on the session. Read both so we work
    regardless of the account's API version.
    """
    collected = _field(session, "collected_information") or {}
    details = (
        _field(collected, "shipping_details")
        or _field(session, "shipping_details")
        or {}
    )
    address = _field(details, "address") or {}
    return {
        "name": _field(details, "name") or "",
        "line1": _field(address, "line1") or "",
        "line2": _field(address, "line2") or "",
        "city": _field(address, "city") or "",
        "state": _field(address, "state") or "",
        "postal_code": _field(address, "postal_code") or "",
        "country": _field(address, "country") or "",
    }


def _fulfill_checkout(session):
    metadata = _field(session, "metadata") or {}
    order_id = _field(metadata, "order_id") or _field(session, "client_reference_id")
    # Stripe retries deliveries, so fulfilment must be idempotent. Lock the order
    # row and bail if it's already paid — a duplicate delivery is then a no-op.
    with transaction.atomic():
        order = Order.objects.select_for_update().filter(id=order_id).first()
        if order is None or order.status == Order.STATUS_PAID:
            return
        order.status = Order.STATUS_PAID
        order.stripe_payment_intent = _field(session, "payment_intent") or ""
        ship = _shipping(session)
        order.shipping_name = ship["name"]
        order.shipping_line1 = ship["line1"]
        order.shipping_line2 = ship["line2"]
        order.shipping_city = ship["city"]
        order.shipping_state = ship["state"]
        order.shipping_postal_code = ship["postal_code"]
        order.shipping_country = ship["country"]
        order.save()
        # Decrement inventory for what was purchased — the chosen size's stock
        # when the line had a size, otherwise the product's flat stock.
        for line in order.items.select_related("product", "size"):
            if line.size_id:
                line.size.stock = max(0, line.size.stock - line.quantity)
                line.size.save(update_fields=["stock"])
            elif line.product:
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
