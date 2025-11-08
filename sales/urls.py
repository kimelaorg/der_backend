from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, StaffSalesViewSet, CustomerLookupView

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='sales-order')
router.register(r'staff-orders', StaffSalesViewSet, basename='staff-sales-order')

urlpatterns = [
    path('customer-lookup/', CustomerLookupView.as_view(), name='customer-lookup'),
    path('', include(router.urls)),
]
