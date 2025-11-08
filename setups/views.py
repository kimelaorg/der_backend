from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework.pagination import PageNumberPagination
# from rbac.rbac_permissions import IsStaffUser, required_permission # REMOVED: Relying on Django's built-in staff/permissions
from .models import (
    Brand, ProductCategory, Supplier, PaymentMethod, ShippingMethod,
    SupportedInternetService, SupportedResolution, ScreenSize, PanelType,
    Connectivity, LicenceType, SoftwareFulfillmentMethod,
    Region, District, Ward, Street
)
from .serializers import (
    BrandSerializer, ProductCategorySerializer, SupplierSerializer, PaymentMethodSerializer,
    ShippingMethodSerializer, SupportedInternetServiceSerializer, SupportedResolutionSerializer,
    ScreenSizeSerializer, PanelTypeSerializer, ConnectivitySerializer, LicenceTypeSerializer,
    SoftwareFulfillmentMethodSerializer, RegionSerializer, DistrictSerializer, WardSerializer,
    StreetSerializer
)

User = get_user_model()


class CustomPageNumberPagination(PageNumberPagination):
    """
    Custom pagination class that sets the default page size to 5.
    Allows clients to override using the 'page_size' query parameter.
    """
    # page_size = 5
    # page_size_query_param = 'page_size'
    # max_page_size = 50


class StaffConfigBaseViewSet(viewsets.ModelViewSet):
    """
    Base class for all setup models.
    Requires the user to be staff, authenticated, and have the necessary Django model permissions (e.g., add_brand).

    The SETUP_MANAGER group will be assigned all model permissions for the setups app.
    """
    # Using DjangoModelPermissions for CRUD control and IsStaffUser for base access control

    # permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser, permissions.DjangoModelPermissions]


    # def get_permissions(self):
    #     if self.action in ['list', 'retrieve']:
    #         return [permissions.IsAuthenticated()]
    #     return [permissions.IsAuthenticated(), permissions.DjangoModelPermissions()]


# --- 2. ViewSets with Custom Delete Prevention Logic (Critical Models) ---

class CriticalSetupViewSet(StaffConfigBaseViewSet):
    """
    Base class for critical setup models (Brand, Category, Region) where
    we prevent accidental deletion by regular staff/managers, even if they have
    Django delete permission. Only superusers should be able to hard delete.
    """
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Superuser check: If the user is a superuser, allow deletion
        if request.user.is_superuser:
            return super().destroy(request, *args, **kwargs)

        # Permission check: Check for the custom permission defined in models.py (e.g., cannot_delete_brand)
        # Note: We rely on the model's custom permission checks defined in the Meta class
        # (e.g., 'cannot_delete_brand') to enforce this security layer.

        # If the user is staff (and thus has DjangoModelPermissions check pass) but is NOT a superuser,
        # we prevent the hard delete and return a custom message.
        return Response(
            {"detail": f"Deletion of critical setup record '{instance}' is only permitted for Superusers to prevent system breaks. Please mark it as 'inactive' instead."},
            status=status.HTTP_403_FORBIDDEN
        )

        # The original DRF permission check will prevent non-staff from reaching this point.
        # return super().destroy(request, *args, **kwargs) # This line is unreachable due to the explicit Response above

# --- Re-implementing destroy for CriticalSetupViewSet without the redundant perm check ---
class CriticalSetupViewSet(StaffConfigBaseViewSet):
    """
    Base class for critical setup models (Brand, Category, Region) where
    we prevent accidental deletion by regular staff/managers, even if they have
    Django delete permission. Only superusers should be able to hard delete.
    """
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Superuser check: If the user is a superuser, allow deletion
        if request.user.is_superuser:
            return super().destroy(request, *args, **kwargs)

        # All non-superusers, even if they have the 'delete' permission granted
        # via a group (like SETUP_MANAGER), are explicitly blocked from deleting
        # critical setup records and are told to use the 'is_active' flag instead.
        return Response(
            {"detail": f"Deletion of critical setup record '{instance}' is only permitted for Superusers to prevent system breaks. Please mark it as 'inactive' instead."},
            status=status.HTTP_403_FORBIDDEN
        )


class BrandViewSet(CriticalSetupViewSet):
    """Provides CRUD access to Brand data, preventing deletion by non-superusers."""
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer


class ProductCategoryViewSet(CriticalSetupViewSet):
    """Provides CRUD access to Product Category data, preventing deletion by non-superusers."""
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    serializer_class = ProductCategorySerializer
    pagination_class = CustomPageNumberPagination


# --- 3. Supplier and Payment/Shipping ViewSets ---

class SupplierViewSet(StaffConfigBaseViewSet):
    """Provides CRUD access to Supplier data."""
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer

# This ViewSet requires modification for public read access
class PaymentMethodViewSet(viewsets.ModelViewSet):
    """
    Publicly accessible list of active payment methods (Read-Only).
    Staff with 'delete_paymentmethod' permission can manage the list.
    """
    queryset = PaymentMethod.objects.filter(is_active=True)
    serializer_class = PaymentMethodSerializer

    def get_permissions(self):
        """Allows GET (read) to all authenticated users, but CRUD only to staff (with DjangoModelPermissions)."""
        if self.action in ['list', 'retrieve']:
            # Anyone logged in (customer or staff) can see the list
            return [permissions.IsAuthenticated()]
        # Create, Update, Destroy operations require staff status and Django Model Permissions
        # return [permissions.IsAuthenticated(), permissions.IsStaff(), permissions.DjangoModelPermissions()]
        return [permissions.IsAuthenticated(), permissions.DjangoModelPermissions()]

    # Staff can see all (active/inactive) methods, non-staff see only active
    def get_queryset(self):
        # Check if the user is staff (and thus likely a SETUP_MANAGER)
        if self.request.user.is_authenticated and self.request.user.is_staff:
             # If the staff user has change permission for this model, they see all records
             if self.request.user.has_perm('setups.change_paymentmethod'):
                return PaymentMethod.objects.all()
        # Default: Return only active methods for public/customer access
        return PaymentMethod.objects.filter(is_active=True)

class ShippingMethodViewSet(StaffConfigBaseViewSet):
    """Provides CRUD access to Shipping Method data, publicly readable."""
    queryset = ShippingMethod.objects.all()
    serializer_class = ShippingMethodSerializer


# --- 4. Product Attribute ViewSets (Simple CRUD) ---

class SupportedInternetServiceViewSet(StaffConfigBaseViewSet):
    queryset = SupportedInternetService.objects.all()
    serializer_class = SupportedInternetServiceSerializer

class SupportedResolutionViewSet(StaffConfigBaseViewSet):
    queryset = SupportedResolution.objects.all()
    serializer_class = SupportedResolutionSerializer

class ScreenSizeViewSet(StaffConfigBaseViewSet):
    queryset = ScreenSize.objects.all()
    serializer_class = ScreenSizeSerializer

class PanelTypeViewSet(StaffConfigBaseViewSet):
    queryset = PanelType.objects.all()
    serializer_class = PanelTypeSerializer

class ConnectivityViewSet(StaffConfigBaseViewSet):
    queryset = Connectivity.objects.all()
    serializer_class = ConnectivitySerializer

class LicenceTypeViewSet(StaffConfigBaseViewSet):
    queryset = LicenceType.objects.all()
    serializer_class = LicenceTypeSerializer

class SoftwareFulfillmentMethodViewSet(StaffConfigBaseViewSet):
    queryset = SoftwareFulfillmentMethod.objects.all()
    serializer_class = SoftwareFulfillmentMethodSerializer


# --- 5. Geographical Location ViewSets (Critical and Nested) ---

class RegionViewSet(CriticalSetupViewSet):
    """Provides CRUD access to Region data, preventing deletion by non-superusers."""
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    # Note: Delete prevention is handled by CriticalSetupViewSet.destroy

class DistrictViewSet(StaffConfigBaseViewSet):
    """Provides CRUD access to District data."""
    queryset = District.objects.all()
    serializer_class = DistrictSerializer

class WardViewSet(StaffConfigBaseViewSet):
    """Provides CRUD access to Ward data."""
    queryset = Ward.objects.all()
    serializer_class = WardSerializer

class StreetViewSet(StaffConfigBaseViewSet):
    """Provides CRUD access to Street data."""
    queryset = Street.objects.all()
    serializer_class = StreetSerializer
