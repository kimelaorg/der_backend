from django.urls import path, include
from rest_framework import routers
from products.views import PublicCatalogViewSet
from .views import ReviewViewSet

# Nested routing setup: /api/products/1/reviews/
router = routers.SimpleRouter()
router.register(r'reviews', PublicCatalogViewSet, basename='review')


urlpatterns = [
    path('', include(router.urls)),
]
