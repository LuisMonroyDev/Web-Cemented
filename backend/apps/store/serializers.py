"""Read-only serializers for the public storefront API."""
from rest_framework import serializers

from .models import GalleryImage, Product, SiteSettings


def _abs_url(filefield, request):
    """Return an absolute media URL the React app (on another port) can load."""
    if not filefield:
        return None
    url = filefield.url
    # Guarantee a leading slash so build_absolute_uri resolves from the host root,
    # regardless of how MEDIA_URL is written.
    if not url.startswith(("http://", "https://", "/")):
        url = "/" + url
    return request.build_absolute_uri(url) if request else url


class ProductSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    status = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = ["id", "name", "price", "description", "image", "stock", "status", "order"]

    def get_image(self, obj):
        return _abs_url(obj.image, self.context.get("request"))


class GalleryImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = GalleryImage
        fields = ["id", "image", "caption", "order"]

    def get_image(self, obj):
        return _abs_url(obj.image, self.context.get("request"))


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = [
            "spotify_embed_url",
            "instagram_url",
            "tiktok_url",
            "youtube_url",
            "spotify_artist_url",
        ]
