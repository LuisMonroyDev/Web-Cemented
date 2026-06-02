from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Product, ProductSize, SiteSettings, validate_spotify_embed


class SpotifyValidatorTests(TestCase):
    def test_accepts_embed_url(self):
        # Should not raise.
        validate_spotify_embed("https://open.spotify.com/embed/album/abc123")

    def test_rejects_plain_share_link(self):
        with self.assertRaises(ValidationError):
            validate_spotify_embed("https://open.spotify.com/album/abc123")

    def test_rejects_foreign_domain(self):
        with self.assertRaises(ValidationError):
            validate_spotify_embed("https://evil.example.com/embed/x")


class ProductStatusTests(TestCase):
    def test_status_thresholds(self):
        self.assertEqual(Product(stock=0).status, "Sold out")
        self.assertEqual(Product(stock=5).status, "Low stock")
        self.assertEqual(Product(stock=50).status, "Active")


class ProductSizeTests(TestCase):
    def test_total_stock_sums_sizes_and_ignores_flat_stock(self):
        product = Product.objects.create(name="Tee", price=20, stock=99, is_active=True)
        ProductSize.objects.create(product=product, label="S", stock=2)
        ProductSize.objects.create(product=product, label="M", stock=3)
        self.assertTrue(product.has_sizes)
        self.assertEqual(product.total_stock, 5)  # 2 + 3, not the flat 99
        self.assertEqual(product.status, "Low stock")  # 5 <= threshold (10)

    def test_sizeless_product_falls_back_to_flat_stock(self):
        product = Product.objects.create(name="Vinyl", price=30, stock=50, is_active=True)
        self.assertFalse(product.has_sizes)
        self.assertEqual(product.total_stock, 50)
        self.assertEqual(product.status, "Active")

    def test_all_sizes_out_reads_as_sold_out(self):
        product = Product.objects.create(name="Tee", price=20, stock=99, is_active=True)
        ProductSize.objects.create(product=product, label="S", stock=0)
        self.assertEqual(product.total_stock, 0)
        self.assertEqual(product.status, "Sold out")


class ProductSizeApiTests(TestCase):
    def test_serializer_exposes_sizes_and_size_aware_stock(self):
        product = Product.objects.create(name="Sized Tee", price=20, stock=0, is_active=True)
        ProductSize.objects.create(product=product, label="S", stock=4, order=1)
        ProductSize.objects.create(product=product, label="M", stock=0, order=2)
        res = self.client.get("/api/products/")
        data = next(p for p in res.json() if p["name"] == "Sized Tee")
        # `stock` reports the total across sizes (4), not the flat 0.
        self.assertEqual(data["stock"], 4)
        # Sold-out sizes are still listed (shown disabled on the storefront),
        # ordered by `order`.
        self.assertEqual([s["label"] for s in data["sizes"]], ["S", "M"])
        self.assertEqual(data["sizes"][1]["stock"], 0)


class ProductSizeValidationTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name="Tee", price=20, stock=0, is_active=True)

    def test_whitespace_only_label_rejected(self):
        size = ProductSize(product=self.product, label="   ", stock=3)
        with self.assertRaises(ValidationError):
            size.full_clean()

    def test_label_is_trimmed_on_save(self):
        size = ProductSize.objects.create(product=self.product, label="  M  ", stock=3)
        size.refresh_from_db()
        self.assertEqual(size.label, "M")

    def test_trimming_makes_near_duplicates_collide(self):
        ProductSize.objects.create(product=self.product, label="M", stock=1)
        dupe = ProductSize(product=self.product, label="  M  ", stock=2)
        # After trimming, this is a second "M" — unique_together must reject it.
        with self.assertRaises(ValidationError):
            dupe.full_clean()

    def test_negative_stock_rejected(self):
        size = ProductSize(product=self.product, label="S", stock=-1)
        with self.assertRaises(ValidationError):
            size.full_clean()


class ProductAdminTests(TestCase):
    """Drive the real admin views — the page that 404'd before the migration —
    to confirm the flat-stock field hides for sized products and the changelist
    shows the summed total."""

    def setUp(self):
        admin = get_user_model().objects.create_superuser(
            "boss", "boss@example.com", "pw"
        )
        self.client.force_login(admin)

    def test_flat_stock_hidden_when_product_has_sizes(self):
        product = Product.objects.create(name="Tee", price=20, stock=5, is_active=True)
        ProductSize.objects.create(product=product, label="S", stock=3)
        res = self.client.get(reverse("admin:store_product_change", args=[product.id]))
        self.assertEqual(res.status_code, 200)
        self.assertNotContains(res, 'name="stock"')

    def test_flat_stock_shown_for_sizeless_product(self):
        product = Product.objects.create(name="Vinyl", price=20, stock=5, is_active=True)
        res = self.client.get(reverse("admin:store_product_change", args=[product.id]))
        self.assertContains(res, 'name="stock"')

    def test_changelist_shows_summed_stock_not_flat(self):
        product = Product.objects.create(name="Tee", price=20, stock=99, is_active=True)
        ProductSize.objects.create(product=product, label="S", stock=2)
        ProductSize.objects.create(product=product, label="M", stock=3)
        res = self.client.get(reverse("admin:store_product_changelist"))
        self.assertContains(res, "5 (sizes)")  # summed total, not the flat 99


class SiteSettingsSingletonTests(TestCase):
    def test_load_creates_then_reuses_single_row(self):
        a = SiteSettings.load()
        self.assertEqual(a.pk, 1)
        a.instagram_url = "https://instagram.com/cemented"
        a.save()
        b = SiteSettings.load()
        self.assertEqual(b.pk, 1)
        self.assertEqual(b.instagram_url, "https://instagram.com/cemented")
        self.assertEqual(SiteSettings.objects.count(), 1)


class ProductApiTests(TestCase):
    def test_lists_only_active_products(self):
        Product.objects.create(name="Visible Tee", price=10, stock=5, is_active=True)
        Product.objects.create(name="Hidden Tee", price=10, stock=5, is_active=False)
        res = self.client.get("/api/products/")
        self.assertEqual(res.status_code, 200)
        names = [p["name"] for p in res.json()]
        self.assertIn("Visible Tee", names)
        self.assertNotIn("Hidden Tee", names)


class SettingsApiTests(TestCase):
    def test_returns_settings_object(self):
        res = self.client.get("/api/settings/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("spotify_embed_url", res.json())
