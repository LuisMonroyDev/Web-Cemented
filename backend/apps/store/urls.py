from django.urls import path

from . import views

urlpatterns = [
    path("products/", views.ProductListView.as_view(), name="product-list"),
    path("gallery/", views.GalleryListView.as_view(), name="gallery-list"),
    path("settings/", views.SiteSettingsView.as_view(), name="site-settings"),
]
