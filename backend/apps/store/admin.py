from django.contrib import admin
from django.utils.html import format_html

from .models import GalleryImage, Product, SiteSettings


def _thumb(image, height=40):
    if not image:
        return "—"
    return format_html(
        '<img src="{}" style="height:{}px;border-radius:4px;object-fit:cover;" />',
        image.url,
        height,
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("thumbnail", "name", "price", "stock", "status", "is_active", "order")
    list_display_links = ("name",)
    list_editable = ("price", "stock", "is_active", "order")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    readonly_fields = ("preview", "created_at", "updated_at")

    @admin.display(description="")
    def thumbnail(self, obj):
        return _thumb(obj.image)

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
