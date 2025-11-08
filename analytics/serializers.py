from rest_framework import serializers
from .models import SalesKPICache, InventorySummary, ProductPerformance

class SalesKPICacheSerializer(serializers.ModelSerializer):
    """Serializer for daily/monthly sales metrics cache."""
    class Meta:
        model = SalesKPICache
        fields = '__all__'

class InventorySummarySerializer(serializers.ModelSerializer):
    """Serializer for inventory health metrics (turnover, stock value)."""
    class Meta:
        model = InventorySummary
        fields = '__all__'

class ProductPerformanceSerializer(serializers.ModelSerializer):
    """Serializer for product ranking and performance data."""
    # Assuming 'product' is a ForeignKey, we can represent it by its name/SKU
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = ProductPerformance
        # Include product name/sku for readability in the report
        fields = ['ranking', 'product_sku', 'product_name', 'sales_volume', 'total_revenue', 'refund_rate']
