from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BrandViewSet, ProductCategoryViewSet, SupplierViewSet, PaymentMethodViewSet,
    ShippingMethodViewSet, SupportedInternetServiceViewSet, SupportedResolutionViewSet,
    ScreenSizeViewSet, PanelTypeViewSet, ConnectivityViewSet, LicenceTypeViewSet,
    SoftwareFulfillmentMethodViewSet, RegionViewSet, DistrictViewSet, WardViewSet,
    StreetViewSet
)

# Create a router and register our viewsets
router = DefaultRouter()

# --- Core Setup Models ---
router.register(r'brands', BrandViewSet)
router.register(r'categories', ProductCategoryViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'payment-methods', PaymentMethodViewSet)
router.register(r'shipping-methods', ShippingMethodViewSet)

# --- Product Attribute Lookups ---
router.register(r'internet-services', SupportedInternetServiceViewSet)
router.register(r'resolutions', SupportedResolutionViewSet)
router.register(r'screen-sizes', ScreenSizeViewSet)
router.register(r'panel-types', PanelTypeViewSet)
router.register(r'connectivity', ConnectivityViewSet)
router.register(r'licence-types', LicenceTypeViewSet)
router.register(r'fulfillment-methods', SoftwareFulfillmentMethodViewSet)

# --- Geographical Lookups (Nested) ---
router.register(r'regions', RegionViewSet)
router.register(r'districts', DistrictViewSet)
router.register(r'wards', WardViewSet)
router.register(r'streets', StreetViewSet)

urlpatterns = [
    # All setup/lookup endpoints are exposed under /api/setups/ or /api/settings/
    path('', include(router.urls)),
]
