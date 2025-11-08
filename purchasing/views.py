from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import PurchaseOrder, StockReception # Note: Assuming PurchaseOrderItem is handled via serializer
from .serializers import PurchaseOrderSerializer, StockReceptionSerializer
from django.db.models import Sum

# --- CRITICAL: IMPORT THE CUSTOM PERMISSIONS FROM THE SAME DIRECTORY ---
from .permissions import IsPurchasingManager, IsWarehouseStaff


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Purchase Orders (and their nested items) to be
    viewed, created, edited, and deleted.
    """
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    # This is just a placeholder; permissions are handled by get_permissions
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """
        Dynamically adjusts permissions based on the action (role-based access).
        Read access is for all authenticated staff. Write access is for Purchasing Managers.
        """
        # CRUD operations (create, update, delete) are restricted to Purchasing Managers
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsPurchasingManager]
        # Read-only operations are open to all authenticated staff
        elif self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.IsAuthenticated]
        else:
            # Handle other specific actions below
            pass

        return [permission() for permission in self.permission_classes]

    def get_queryset(self):
        # Prefetch related items for performance
        return PurchaseOrder.objects.all().select_related('supplier', 'created_by').prefetch_related('items__product')

    def perform_create(self, serializer):
        """Inject the creating user from the request context."""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['patch'], url_path='update-status', permission_classes=[permissions.IsAdminUser])
    def update_status(self, request, pk=None):
        """
        Custom action to quickly update the status of a Purchase Order.
        Restricted to Superusers only for critical state changes.
        """
        po = get_object_or_404(PurchaseOrder, pk=pk)

        # Check if the new status is valid
        new_status = request.data.get('po_status')
        valid_statuses = [choice[0] for choice in po.PO_STATUS_CHOICES]

        if new_status not in valid_statuses:
            return Response(
                {"detail": f"Invalid status provided. Must be one of: {valid_statuses}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_status == po.po_status:
            return Response(
                {"detail": f"Status is already {new_status}"},
                status=status.HTTP_200_OK
            )

        po.po_status = new_status
        po.save()

        # Return the updated PO data
        serializer = self.get_serializer(po)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StockReceptionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for recording Stock Reception records against PO Items.
    """
    queryset = StockReception.objects.all()
    serializer_class = StockReceptionSerializer

    # This is just a placeholder; permissions are handled by get_permissions
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """
        Dynamically adjusts permissions based on the action (role-based access).
        Read access is for all authenticated staff. Create access is for Warehouse Staff.
        """
        if self.action == 'create':
            # Creation is restricted to Warehouse Staff
            self.permission_classes = [IsWarehouseStaff]
        elif self.action in ['list', 'retrieve']:
            # Read-only operations are open to all authenticated staff
            self.permission_classes = [permissions.IsAuthenticated]
        else:
            # Deny updates or deletions to maintain transactional integrity
            self.permission_classes = [permissions.DenyAll]

        return [permission() for permission in self.permission_classes]


    def get_queryset(self):
        # Prefetch to avoid multiple lookups for the product name
        return StockReception.objects.all().select_related('purchase_order_item__product', 'received_by')

    def perform_create(self, serializer):
        """Inject the staff member who performed the reception."""
        # The serializer's create method handles all the inventory and PO logic.
        serializer.save(received_by=self.request.user)
