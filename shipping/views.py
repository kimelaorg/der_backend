from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, views, status, generics
from rest_framework.response import Response
from rbac.rbac_permissions import HasPermission
from .models import Shipment, ShipmentRequest, ShippingMethod
from .serializers import (
    ShipmentSerializer, ShipmentRequestSerializer, InternalShipmentRequestSerializer,
    ShippingMethodSerializer
    )


# Create your views here.
class ActiveShippingMethodListView(generics.ListAPIView):
    """
    A public-facing endpoint to list all currently active shipping methods.
    Used by the customer during the checkout process.
    """
    serializer_class = ShippingMethodSerializer

    # Override get_queryset to ensure only active methods are retrieved
    def get_queryset(self):
        # We only return methods that are marked as active
        return ShippingMethod.objects.filter(is_active=True).order_by('base_cost')


class StaffShipmentManagementViewSet(viewsets.ModelViewSet):
    """Staff only: Manage (CRUD) shipments and update status/tracking."""
    queryset = Shipment.objects.select_related('request__order__customer', 'shipping_method').all()
    serializer_class = ShipmentSerializer
    permission_classes = [HasPermission]
    required_permission = 'shipping:manage_shipments'

    def get_queryset(self):
        # Filter out shipments that are already delivered/failed unless explicitly requested
        return self.queryset.exclude(status__in=['DELIVERED', 'FAILED'])

class StaffShipmentRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """Staff only: View all pending and fulfilled shipment requests."""
    queryset = ShipmentRequest.objects.select_related('order__customer').all()
    serializer_class = ShipmentRequestSerializer
    permission_classes = [HasPermission]
    required_permission = 'shipping:view_requests'

class InternalShipmentRequestView(generics.GenericAPIView):
    """Internal API: Triggers the creation of a ShipmentRequest after payment confirmation."""
    serializer_class = InternalShipmentRequestSerializer
    permission_classes = [HasPermission]
    required_permission = 'shipping:internal_request'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # The serializer handles the creation of ShipmentRequest and initial Shipment object
        shipment = serializer.save()

        return Response({
            "detail": "Shipment request created and initial shipment assigned.",
            "shipment_id": shipment.id,
            "order_id": shipment.request.order.id
        }, status=status.HTTP_201_CREATED)
