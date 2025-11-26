from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet, ProductSpecificationViewSet, ProductImageView, NewProductImageView,
    ProductVideoViewSet, DigitalProductViewSet, PublicProductDetailViewSet, ProductImageDeleteView
)

# Create a router instance
router = DefaultRouter()

router.register(r'products', ProductViewSet)
router.register(r'specs', ProductSpecificationViewSet)
router.register(r'videos', ProductVideoViewSet)
router.register(r'digital-products', DigitalProductViewSet)
router.register(r'public-catalog', PublicProductDetailViewSet, basename='public-product')


urlpatterns = [
    path('', include(router.urls)),
    path('images/', NewProductImageView.as_view()),
    path('images-list/', ProductImageView.as_view()),
    path('images-delete/<int:pk>', ProductImageDeleteView.as_view())
]
