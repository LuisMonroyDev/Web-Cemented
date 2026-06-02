"""Regression tests for the public storefront API (products, gallery, settings)."""
from django.test import TestCase
from rest_framework.test import APIClient

from .models import GalleryImage, Product, SiteSettings


class ProductListingTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_only_active_products_listed(self):
        Product.objects.create(name="Visible", price=10, stock=5, is_active=True)
        Product.objects.create(name="Hidden", price=10, stock=5, is_active=False)
        names = [p["name"] for p in self.client.get("/api/products/").json()]
        self.assertEqual(names, ["Visible"])

    def test_sold_out_product_still_listed_with_status(self):
        Product.objects.create(name="Gone", price=10, stock=0, is_active=True)
        data = self.client.get("/api/products/").json()
        self.assertEqual(data[0]["status"], "Sold out")
        self.assertEqual(data[0]["stock"], 0)

    def test_product_payload_shape(self):
        Product.objects.create(name="Tee", price=25, stock=50, is_active=True)
        product = self.client.get("/api/products/").json()[0]
        self.assertEqual(
            set(product),
            {"id", "name", "price", "description", "image", "stock", "status", "order", "sizes"},
        )
        self.assertEqual(product["status"], "Active")


class GalleryListingTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_only_active_gallery_images_listed(self):
        GalleryImage.objects.create(caption="Shown", is_active=True)
        GalleryImage.objects.create(caption="Hidden", is_active=False)
        captions = [g["caption"] for g in self.client.get("/api/gallery/").json()]
        self.assertEqual(captions, ["Shown"])


class SettingsEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_settings_returns_singleton_fields(self):
        res = self.client.get("/api/settings/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            set(res.json()),
            {
                "spotify_embed_url",
                "instagram_url",
                "tiktok_url",
                "youtube_url",
                "spotify_artist_url",
            },
        )
        self.assertEqual(SiteSettings.objects.count(), 1)
