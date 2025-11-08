from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser # Using IsAdminUser as a standard staff replacement
from rest_framework.response import Response
from django.db import models
from django.shortcuts import get_object_or_404
# The rbac_permissions import has been permanently removed.
from .models import Inventory, StockMovement, WarehouseLocation
from products.models import ProductSpecification
from .serializers import (
    InventorySerializer,
    StockAdjustmentSerializer,
    StockMovementSerializer,
    WarehouseLocationSerializer
)


# --- 1. Warehouse Location Management ViewSet ---

class WarehouseLocationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing warehouse locations (CRUD).
    Permissions are set to require standard authenticated staff access.
    """
    queryset = WarehouseLocation.objects.all().order_by('name')
    serializer_class = WarehouseLocationSerializer
    # Using standard DRF permission for staff access
    permission_classes = [IsAuthenticated, IsAdminUser]

    # The dynamic get_permissions method relying on RBAC has been removed.


# --- 2. Inventory and Stock Movement Management ViewSet ---

class InventoryManagementViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin, # Added for updating safety_stock_level/location
    viewsets.GenericViewSet
):
    """
    API endpoints for viewing stock status, low stock alerts, stock history,
    and performing manual stock adjustments.
    Permissions are set to require standard authenticated staff access.
    """
    # Optimized queryset for list/retrieve
    queryset = Inventory.objects.all().select_related('product', 'location')
    serializer_class = InventorySerializer

    # Using standard DRF permission for staff access
    permission_classes = [IsAuthenticated, IsAdminUser]

    # The dynamic get_permissions method relying on RBAC has been removed.

    @action(detail=False, methods=['get'], url_path='low-stock-alerts')
    def low_stock_alerts(self, request):
        """Lists all inventory items where stock is at or below the safety level."""
        low_stock_items = (
            Inventory.objects.filter(quantity_in_stock__lte=models.F('safety_stock_level'))
            .select_related('product', 'location')
        )
        # Use the standard InventorySerializer for output
        serializer = self.get_serializer(low_stock_items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='adjust-stock')
    def adjust_stock(self, request):
        """Performs a manual stock adjustment, logging the movement and updating inventory."""

        # The StockAdjustmentSerializer handles all validation, finding the inventory record,
        # creating the StockMovement record, and updating the Inventory quantity atomically.
        serializer = StockAdjustmentSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        try:
            # The .save() method in the serializer executes the transactional logic
            movement = serializer.save()

            # Fetch the updated inventory record for the response data
            inventory_record = movement.product.inventory

            return Response(
                {
                    "detail": f"Stock for {movement.product.sku} successfully adjusted by {movement.quantity_change}.",
                    "new_quantity": inventory_record.quantity_in_stock
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            # This catch block is mostly for unexpected database/network errors,
            # as validation errors are handled by raise_exception=True
            return Response(
                {"detail": f"Stock adjustment failed due to internal error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @action(detail=False, methods=['get'], url_path='history')
    def history(self, request):
        """Retrieves a paginated list of stock movements, optionally filtered by SKU."""

        sku = request.query_params.get('sku')

        # Base queryset for StockMovement, prefetching related objects
        history_queryset = StockMovement.objects.all().select_related('product', 'performed_by').order_by('-timestamp')

        if sku:
            try:
                # Filter by the product specification instance
                product_spec = ProductSpecification.objects.get(sku=sku)
                history_queryset = history_queryset.filter(product=product_spec)
            except ProductSpecification.DoesNotExist:
                return Response(
                    {"detail": f"Product with SKU '{sku}' not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Utilize the viewset's pagination system if configured, or just serialize the data
        page = self.paginate_queryset(history_queryset)
        if page is not None:
            serializer = StockMovementSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = StockMovementSerializer(history_queryset, many=True)
        return Response(serializer.data)
