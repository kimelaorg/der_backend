from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PurchaseOrderViewSet, StockReceptionViewSet

# Create a router and register our viewsets
router = DefaultRouter()
# /purchase-orders/orders/ (list/create) and /purchase-orders/orders/{pk}/ (detail/update/delete)
router.register(r'orders', PurchaseOrderViewSet, basename='purchaseorder')
# /purchase-orders/receptions/ (list/create) and /purchase-orders/receptions/{pk}/ (detail/read)
router.register(r'receptions', StockReceptionViewSet, basename='stockreception')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
]
