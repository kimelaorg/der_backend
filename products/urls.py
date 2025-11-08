from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PublicCatalogViewSet, StaffProductManagementViewSet

# Create a router and register our viewsets
router = DefaultRouter()

# Public/Customer Endpoints (Read-only view of active products)
# Accessible via /api/products/catalog/
router.register(r'catalog', PublicCatalogViewSet, basename='public-catalog')

# Staff Management Endpoints (Full CRUD access, secured by DjangoModelPermissions)
# Accessible via /api/products/management/
router.register(r'management', StaffProductManagementViewSet, basename='staff-management')


urlpatterns = [
    # All product catalog endpoints are exposed under /api/products/
    path('', include(router.urls)),
]
