from django.urls import path

from . import views

urlpatterns = [
    path("cart/", views.CartView.as_view(), name="cart"),
    path("cart/items/", views.CartItemsView.as_view(), name="cart-items"),
    path("cart/items/<int:item_id>/", views.CartItemDetailView.as_view(), name="cart-item-detail"),
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
    path("webhooks/stripe/", views.stripe_webhook, name="stripe-webhook"),
]
