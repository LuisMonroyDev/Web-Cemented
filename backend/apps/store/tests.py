from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Product, SiteSettings, validate_spotify_embed


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
