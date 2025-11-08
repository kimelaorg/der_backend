from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StaffLicenseKeyManagementViewSet,
    CustomerLicenseAccessViewSet,
    InternalKeyAssignmentView
)

router = DefaultRouter()

# Staff management endpoints for bulk loading and viewing license keys
router.register(r'management/keys', StaffLicenseKeyManagementViewSet, basename='license-key-management')

# Customer facing endpoint to view their purchased licenses/access
router.register(r'customer/access', CustomerLicenseAccessViewSet, basename='customer-license-access')

urlpatterns = [
    # 1. Internal API endpoint used by the PAYMENTS/SALES app for fulfillment.
    # This must be highly secured, likely via internal API key or RBAC permission check.
    path('internal/assign-key/', InternalKeyAssignmentView.as_view(), name='internal-key-assign'),

    # 2. Router URLs for management and customer views
    path('', include(router.urls)),
]
