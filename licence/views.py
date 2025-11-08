from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, views, status, generics, permissions
from rest_framework.response import Response
from django.db import transaction
from rbac.rbac_permissions import HasPermission
from .models import SoftwareLicense, CustomerDigitalAccess
from .serializers import SoftwareLicenseSerializer, CustomerDigitalAccessSerializer, InternalKeyAssignmentSerializer
from sales.models import Order

# Create your views here.

class StaffLicenseKeyManagementViewSet(viewsets.ModelViewSet):
    """Staff only: CRUD for SoftwareLicense keys (e.g., bulk upload)."""
    queryset = SoftwareLicense.objects.all()
    serializer_class = SoftwareLicenseSerializer
    permission_classes = [HasPermission]
    required_permission = 'licensing:manage_keys'


class CustomerLicenseAccessViewSet(viewsets.ReadOnlyModelViewSet):
    """Customer only: View their granted licenses/access."""
    queryset = CustomerDigitalAccess.objects.all()
    serializer_class = CustomerDigitalAccessSerializer
    permission_classes = [permissions.IsAuthenticated] 

    def get_queryset(self):
        # Assumes request.user is an authenticated User from accounts_app
        qs = super().get_queryset()
        qs = qs.filter(customer_user=self.request.user)
        return qs


class InternalKeyAssignmentView(generics.GenericAPIView):
    """Internal API: Assigns the next available key to a paid order line item."""
    serializer_class = InternalKeyAssignmentSerializer
    permission_classes = [HasPermission]
    required_permission = 'licensing:internal_fulfill'

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        order = get_object_or_404(Order, pk=data['order_id'])

        # 1. Find an available key
        try:
            license = SoftwareLicense.objects.select_for_update().filter(
                product_id=data['digital_product_id'], is_assigned=False
            ).first()
        except SoftwareLicense.DoesNotExist:
            return Response({"detail": "No unassigned license key available."}, status=status.HTTP_404_NOT_FOUND)

        # 2. Assign the key
        license.is_assigned = True
        license.assigned_to_order = order
        license.assigned_at = timezone.now()
        license.save()

        # 3. Grant general digital access (e.g., for a course)
        CustomerDigitalAccess.objects.create(
            product_id=data['digital_product_id'],
            customer_user=order.customer.user,
            granted_via_order=order,
            is_active=True
        )

        return Response({
            "detail": "License successfully assigned and digital access granted.",
            "license_key": license.license_key
        }, status=status.HTTP_200_OK)
