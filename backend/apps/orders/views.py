"""Cart endpoints — all require a logged-in customer."""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.store.models import Product

from .models import Cart, CartItem
from .serializers import CartSerializer


def _get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def _cart_response(cart, request, status_code=status.HTTP_200_OK):
    return Response(
        CartSerializer(cart, context={"request": request}).data, status=status_code
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
        try:
            quantity = max(1, int(request.data.get("quantity", 1)))
        except (TypeError, ValueError):
            quantity = 1

        cart = _get_cart(request.user)
        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product, defaults={"quantity": quantity}
        )
        if not created:
            item.quantity += quantity
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
