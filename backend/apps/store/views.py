"""Public, read-only API the storefront consumes. No auth — GET only."""
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import GalleryImage, Product, SiteSettings
from .serializers import (
    GalleryImageSerializer,
    ProductSerializer,
    SiteSettingsSerializer,
)


class ProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        # Prefetch sizes so serializing each product's size list (and its
        # size-aware stock total) doesn't fire a query per product.
        return Product.objects.filter(is_active=True).prefetch_related("sizes")


class GalleryListView(generics.ListAPIView):
    serializer_class = GalleryImageSerializer

    def get_queryset(self):
        return GalleryImage.objects.filter(is_active=True)


class SiteSettingsView(APIView):
    def get(self, request):
        serializer = SiteSettingsSerializer(
            SiteSettings.load(), context={"request": request}
        )
        return Response(serializer.data)
