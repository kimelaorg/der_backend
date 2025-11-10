from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet, ProductSpecificationViewSet, ProductImageViewSet,
    ProductVideoViewSet, DigitalProductViewSet, PublicProductDetailViewSet
)

# Create a router instance
router = DefaultRouter()

router.register(r'products', ProductViewSet)
router.register(r'specs', ProductSpecificationViewSet)
router.register(r'images', ProductImageViewSet)
router.register(r'videos', ProductVideoViewSet)
router.register(r'digital-products', DigitalProductViewSet)
router.register(r'public-catalog', PublicProductDetailViewSet, basename='public-product')


urlpatterns = [
    path('', include(router.urls)),
]
