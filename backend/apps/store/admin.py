from django.contrib import admin
from django.utils.html import format_html

from .models import GalleryImage, Product, ProductSize, SiteSettings


def _thumb(image, height=40):
    if not image:
        return "—"
    return format_html(
        '<img src="{}" style="height:{}px;border-radius:4px;object-fit:cover;" />',
        image.url,
        height,
    )


class ProductSizeInline(admin.TabularInline):
    """The "enter sizes by stock" flow: add a row per size (S/M/L/…) with its
    own stock. Leave it empty and the product just uses its flat stock above."""

    model = ProductSize
    extra = 0
    fields = ("label", "stock", "order")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("thumbnail", "name", "price", "stock_display", "status", "is_active", "order")
    list_display_links = ("name",)
    list_editable = ("price", "is_active", "order")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    readonly_fields = ("preview", "created_at", "updated_at")
    inlines = [ProductSizeInline]

    def get_exclude(self, request, obj=None):
        """Hide the flat ``stock`` field once a product has sizes.

        With sizes, stock is tracked per size and the flat field is ignored, so
        showing an editable box that does nothing is just a trap. New products
        and size-less products still show it (it's their real stock).
        """
        if obj and obj.has_sizes:
            return ("stock",)
        return super().get_exclude(request, obj)

    @admin.display(description="")
    def thumbnail(self, obj):
        return _thumb(obj.image)

    @admin.display(description="Stock")
    def stock_display(self, obj):
        """Show the real sellable count so the number always matches Status.

        For sized products that's the sum across sizes (the flat field is
        ignored); the "(sizes)" tag signals stock is managed per size.
        """
        if obj.has_sizes:
            return f"{obj.total_stock} (sizes)"
        return obj.total_stock

    @admin.display(description="Status")
    def status(self, obj):
        return obj.status

    @admin.display(description="Current image")
    def preview(self, obj):
        return _thumb(obj.image, height=180)


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ("thumbnail", "caption", "order", "is_active", "created_at")
    list_display_links = ("thumbnail", "caption")
    list_editable = ("order", "is_active")
    readonly_fields = ("preview", "created_at")

    @admin.display(description="")
    def thumbnail(self, obj):
        return _thumb(obj.image)

    @admin.display(description="Preview")
    def preview(self, obj):
        return _thumb(obj.image, height=220)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("__str__", "updated_at")

    def has_add_permission(self, request):
        # Singleton — allow creating the first (and only) row.
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
