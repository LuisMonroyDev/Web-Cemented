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
    # Lifecycle: pending → paid → fulfilling → shipped → delivered.
    # canceled is a terminal off-ramp from paid/fulfilling (refunded).
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_FULFILLING = "fulfilling"
    STATUS_SHIPPED = "shipped"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELED = "canceled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_FULFILLING, "Fulfilling"),
        (STATUS_SHIPPED, "Shipped"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_CANCELED, "Canceled"),
    ]
    # Statuses from which a customer may still cancel for a refund — only
    # before the order ships. After that it's a return, not a cancellation.
    CANCELABLE_STATUSES = (STATUS_PAID, STATUS_FULFILLING)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    email = models.EmailField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    # `total` is the full charged amount (items + shipping); `shipping_cost` is
    # broken out so it can be shown as its own line and so `total` stays
    # explainable (the items always add up to total minus shipping).
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    stripe_session_id = models.CharField(max_length=255, blank=True)
    stripe_payment_intent = models.CharField(max_length=255, blank=True)

    # Shipping address — captured from Stripe Checkout at fulfilment time.
    shipping_name = models.CharField(max_length=120, blank=True)
    shipping_line1 = models.CharField(max_length=200, blank=True)
    shipping_line2 = models.CharField(max_length=200, blank=True)
    shipping_city = models.CharField(max_length=120, blank=True)
    shipping_state = models.CharField(max_length=120, blank=True)
    shipping_postal_code = models.CharField(max_length=20, blank=True)
    shipping_country = models.CharField(max_length=2, blank=True)

    # Fulfilment — the band enters this from the admin once the order ships.
    tracking_number = models.CharField(max_length=120, blank=True)
    # Why a customer canceled — collected to discourage frivolous refunds.
    cancel_reason = models.CharField(max_length=500, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} ({self.status})"

    def save(self, *args, **kwargs):
        # Store the contact email canonically (trimmed + lowercased). Some
        # providers (e.g. Resend in sandbox/test mode) compare the recipient
        # case-sensitively, so a stray capital can make a send silently fail.
        # Normalizing here keeps every order consistent however it was created
        # — checkout, admin, shell, or a fixture.
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    @staticmethod
    def usps_tracking_url(tracking_number):
        """Public USPS tracking page for a tracking number, or None if unset.

        The number is entered by hand in the admin; this just wraps it in the
        USPS tracking URL so the API and emails can link/QR to it consistently.
        """
        if not tracking_number:
            return None
        return f"https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_number}"

    @property
    def has_shipping_address(self):
        return bool(self.shipping_line1)

    @property
    def shipping_lines(self):
        """Address as a list of display lines (skips empty parts)."""
        if not self.has_shipping_address:
            return []
        city_line = ", ".join(p for p in [self.shipping_city, self.shipping_state] if p)
        if self.shipping_postal_code:
            city_line = f"{city_line} {self.shipping_postal_code}".strip()
        return [
            line
            for line in [
                self.shipping_name,
                self.shipping_line1,
                self.shipping_line2,
                city_line,
                self.shipping_country,
            ]
            if line
        ]


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
