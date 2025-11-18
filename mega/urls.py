from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MegaProductViewSet


# Create a router instance
router = DefaultRouter()

router.register(r'products', MegaProductViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
