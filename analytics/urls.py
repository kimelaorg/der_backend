from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SalesSummaryViewSet, InventoryTurnoverViewSet, TopProductsViewSet

# Create a router and register our read-only viewsets
router = DefaultRouter()

# 1. Sales KPI Cache (e.g., /api/analytics/sales-kpis/)
router.register(r'sales-kpis', SalesSummaryViewSet, basename='sales-kpis')

# 2. Inventory Health Summary (e.g., /api/analytics/inventory-health/)
router.register(r'inventory-health', InventoryTurnoverViewSet, basename='inventory-health')

# 3. Product Performance Ranking (e.g., /api/analytics/top-products/)
router.register(r'top-products', TopProductsViewSet, basename='top-products')

urlpatterns = [
    # All analytics endpoints are exposed under /api/analytics/
    path('', include(router.urls)),
]
