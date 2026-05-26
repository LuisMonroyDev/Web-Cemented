"""
Cart + order models.

Cart/CartItem: one cart per customer; lines reference a Product + quantity.
Order/OrderItem: created at checkout. Order items snapshot the name and price
at purchase time so history stays correct even if a product changes later.

All money is computed from Product prices in the DB — the browser never sets
amounts. That's what makes the Stripe checkout safe.
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


class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_CANCELED = "canceled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_CANCELED, "Canceled"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    email = models.EmailField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stripe_session_id = models.CharField(max_length=255, blank=True)
    stripe_payment_intent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} ({self.status})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=120)  # snapshot at purchase time
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)  # snapshot
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.name}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity
