from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import SalesKPICache, InventorySummary, ProductPerformance
from .serializers import (
    SalesKPICacheSerializer,
    InventorySummarySerializer,
    ProductPerformanceSerializer
)

# Create your views here.

class SalesSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API view for retrieving cached Sales KPIs (e.g., daily revenue, AOV).
    Endpoint: /api/analytics/sales-summary/
    """
    queryset = SalesKPICache.objects.all().order_by('-date')
    serializer_class = SalesKPICacheSerializer
    permission_classes = [IsAuthenticated]


class InventoryTurnoverViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API view for retrieving cached Inventory Health metrics (e.g., turnover rate).
    Endpoint: /api/analytics/inventory-turnover/
    """
    queryset = InventorySummary.objects.all().order_by('-month_year')
    serializer_class = InventorySummarySerializer
    permission_classes = [IsAuthenticated]
    

class TopProductsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API view for retrieving the product ranking report.
    Endpoint: /api/analytics/top-products/
    """
    # Ordering is already set in the model Meta, but reinforce fetching the top ones
    queryset = ProductPerformance.objects.all().order_by('ranking')
    serializer_class = ProductPerformanceSerializer
    permission_classes = [IsAuthenticated]
