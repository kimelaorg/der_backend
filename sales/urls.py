from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, StaffSalesViewSet, CustomerLookupView
from .sales_views import SalesViewSet, SaleAuditViewSet, CustomerGenericView

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='sales-order')
router.register(r'staff-orders', StaffSalesViewSet, basename='staff-sales-order')
router.register(r'sales', SaleAuditViewSet, basename='sale-audit')
router.register(r'sales-records', SalesViewSet, basename='sales-records')

urlpatterns = [
    path('customers/', CustomerGenericView.as_view(), name = 'sales-customers'),
    path('customer-lookup/', CustomerLookupView.as_view(), name='customer-lookup'),
    path('', include(router.urls)),
]
