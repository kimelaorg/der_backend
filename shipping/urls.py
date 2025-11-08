from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StaffShipmentManagementViewSet, StaffShipmentRequestViewSet, InternalShipmentRequestView,
    ActiveShippingMethodListView
    )

router = DefaultRouter()
router.register(r'management', StaffShipmentManagementViewSet, basename='shipment-management')
router.register(r'requests', StaffShipmentRequestViewSet, basename='shipment-requests')

urlpatterns = [
    path('', include(router.urls)),
    path('methods/', ActiveShippingMethodListView.as_view(), name='shipping-method-list'),
    path('internal-request/', InternalShipmentRequestView.as_view(), name='internal-shipment-request'),

]
