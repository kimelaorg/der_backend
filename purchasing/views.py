from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch, Sum # Added Prefetch for complex nesting

from .models import PurchaseOrder, PurchaseOrderItem, StockReception
from .serializers import PurchaseOrderSerializer, StockReceptionSerializer
# --- CRITICAL: IMPORT THE CUSTOM PERMISSIONS FROM THE SAME DIRECTORY ---
from .permissions import IsPurchasingManager, IsWarehouseStaff # Assuming these are defined


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Purchase Orders (and their nested items) to be
    viewed, created, edited, and deleted.
    """
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """ Dynamically adjusts permissions based on the action (role-based access). """
        # CRUD operations (create, update, delete) are restricted to Purchasing Managers
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsPurchasingManager]
        # Read-only operations are open to all authenticated staff
        elif self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.IsAuthenticated]
        # Custom action permissions are handled below/via decorator
        else:
            self.permission_classes = [permissions.IsAuthenticated] # Default for custom actions

        return [permission() for permission in self.permission_classes]

    def get_queryset(self):
        """
        Optimizes the queryset by using Prefetch and select_related
        to load all nested data (Supplier, User, Items, and Receptions)
        in a single, efficient query.
        """
        # 1. Define Prefetch for Receptions: Used inside the Item prefetch
        receptions_prefetch = Prefetch(
            'receptions',
            queryset=StockReception.objects.select_related('received_by'), # Select the User model for 'received_by'
            to_attr='receptions_cache' # Use 'receptions_cache' for the serializer to read from
        )

        # 2. Define Prefetch for Items: Used inside the main PO prefetch
        items_prefetch = Prefetch(
            'items',
            queryset=PurchaseOrderItem.objects.select_related('product') # Select the Product model
                                                 .prefetch_related(receptions_prefetch), # Nested prefetch for receptions
            to_attr='items_cache' # Use 'items_cache' for the serializer to read from
        )

        # 3. Apply the Prefetches and Selects to the main queryset
        return PurchaseOrder.objects.all().select_related('supplier', 'created_by') \
                                         .prefetch_related(items_prefetch)

    def perform_create(self, serializer):
        """Inject the creating user from the request context."""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['patch'], url_path='update-status', permission_classes=[permissions.IsAdminUser])
    def update_status(self, request, pk=None):
        # ... (Your existing status update logic remains unchanged)
        po = get_object_or_404(PurchaseOrder, pk=pk)

        new_status = request.data.get('po_status')
        # Correctly accessing PO_STATUS_CHOICES from the model instance's class
        valid_statuses = [choice[0] for choice in po.__class__.PO_STATUS_CHOICES]

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

        serializer = self.get_serializer(po)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StockReceptionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for recording Stock Reception records against PO Items.
    """
    queryset = StockReception.objects.all()
    serializer_class = StockReceptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        # ... (Your existing permission logic remains unchanged)
        if self.action == 'create':
            self.permission_classes = [IsWarehouseStaff]
        elif self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.IsAuthenticated]
        # else:
        #     self.permission_classes = [permissions.DenyAll]

        return [permission() for permission in self.permission_classes]

    def get_queryset(self):
        """
        Optimized queryset for StockReception.
        """
        # Prefetch to avoid multiple lookups for the product name and received_by
        return StockReception.objects.all().select_related('purchase_order_item__product', 'received_by')

    def perform_create(self, serializer):
        """Inject the staff member who performed the reception."""
        serializer.save(received_by=self.request.user)
