"""
Shopping cart models.

One Cart per customer; CartItem lines reference a Product and a quantity.
Line/Cart totals are computed from the Product price in the DB — the browser
never gets to set prices (that matters once Stripe checkout is wired up).
"""
from django.conf import settings
from django.db import models

from apps.store.models import Product


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart({self.user})"

    @property
    def total(self):
        return sum((item.line_total for item in self.items.all()), 0)


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ["cart", "product"]
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity} x {self.product}"

    @property
    def line_total(self):
        return self.product.price * self.quantity
