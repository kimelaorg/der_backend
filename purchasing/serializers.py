from rest_framework import serializers
from django.db.models import Sum
from .models import PurchaseOrder, PurchaseOrderItem, StockReception, PO_STATUS_CHOICES
# Assuming Supplier and Product are correctly imported from other apps
from setups.models import Supplier
from products.models import Product


# --- Helper Function for Order Totals ---
def calculate_order_total(items_data):
    """Calculates the total cost based on the provided list of item dictionaries."""
    total = 0.00
    for item in items_data:
        # We ensure quantity_ordered and unit_cost are available
        quantity = item.get('quantity_ordered', 0)
        # Use float() for robust multiplication
        cost = item.get('unit_cost', 0.00)
        total += quantity * float(cost)
    return total


# --- 1. StockReception Serializer ---
class StockReceptionSerializer(serializers.ModelSerializer):
    """Serializer for recording stock reception against a specific PO item."""
    # Read-only fields for context and display
    product_name = serializers.CharField(source='purchase_order_item.product.name', read_only=True)
    received_by_name = serializers.CharField(source='received_by.username', read_only=True)

    class Meta:
        model = StockReception
        fields = [
            'id', 'purchase_order_item', 'product_name',
            'quantity_received', 'decayed_products',
            'received_by', 'received_by_name', 'reception_date'
        ]
        read_only_fields = ['id', 'received_by', 'reception_date']


# --- 2. PurchaseOrderItem Serializer (Nested) ---
class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for the individual line items of a Purchase Order."""
    # Display product name and supplier name for context
    product_name = serializers.CharField(source='product.name', read_only=True)

    # Calculate line total and received quantity for display
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    quantity_received_sum = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrderItem
        # Including reception data only in the detailed PO view
        fields = [
            'id', 'product', 'product_name',
            'quantity_ordered', 'unit_cost',
            'line_total', 'quantity_received_sum',
            'receptions'
        ]
        read_only_fields = ['id', 'line_total', 'quantity_received_sum']

    def get_quantity_received_sum(self, obj):
        """Calculates the sum of all received quantities for this item."""
        return obj.receptions.aggregate(total_received=Sum('quantity_received'))['total_received'] or 0

    def to_representation(self, instance):
        """Override to calculate line_total and include nested receptions."""
        representation = super().to_representation(instance)

        # Calculate line total for display
        representation['line_total'] = float(instance.quantity_ordered) * float(instance.unit_cost)

        # Include nested stock receptions for detailed view
        # Exclude this from update/create payload (it's only for read)
        representation['receptions'] = StockReceptionSerializer(instance.receptions.all(), many=True).data

        return representation


# --- 3. PurchaseOrder Serializer (Main Header) ---
class PurchaseOrderSerializer(serializers.ModelSerializer):
    """
    Main serializer for Purchase Orders, supporting nested creation and updates
    of Purchase Order Items.
    """
    # Nested serializer for handling line items
    items = PurchaseOrderItemSerializer(many=True)

    # Read-only fields for display
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    po_status_display = serializers.CharField(source='get_po_status_display', read_only=True)

    # The order_total is calculated by the logic below
    order_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'supplier', 'supplier_name', 'po_date', 'expected_delivery_date',
            'po_status', 'po_status_display', 'created_by', 'created_by_name',
            'order_total', 'items'
        ]
        # po_date is defaulted to timezone.now, and created_by is set in the view/create method
        read_only_fields = ['id', 'po_date', 'created_by']

    def validate_items(self, items):
        """Ensure items list is not empty."""
        if not items:
            raise serializers.ValidationError("A Purchase Order must contain at least one item.")
        return items

    def create(self, validated_data):
        """Create a PurchaseOrder and its nested PurchaseOrderItem instances."""
        items_data = validated_data.pop('items')

        # 1. Calculate total and set created_by
        validated_data['order_total'] = calculate_order_total(items_data)
        validated_data['created_by'] = self.context['request'].user

        # 2. Create the PurchaseOrder header
        purchase_order = PurchaseOrder.objects.create(**validated_data)

        # 3. Create nested items
        for item_data in items_data:
            PurchaseOrderItem.objects.create(purchase_order=purchase_order, **item_data)

        return purchase_order

    def update(self, instance, validated_data):
        """Update a PurchaseOrder and handle nested PurchaseOrderItem updates/deletions."""
        items_data = validated_data.pop('items', None)

        # Update PurchaseOrder header fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            # Logic to manage nested items (create/update/delete)
            item_ids_to_keep = set()
            for item_data in items_data:
                item_id = item_data.get('id')

                if item_id:
                    # Update existing item
                    try:
                        item = instance.items.get(id=item_id)
                        item.product = item_data.get('product', item.product)
                        item.quantity_ordered = item_data.get('quantity_ordered', item.quantity_ordered)
                        item.unit_cost = item_data.get('unit_cost', item.unit_cost)
                        item.save()
                        item_ids_to_keep.add(item.id)
                    except PurchaseOrderItem.DoesNotExist:
                        # Skip if the item ID provided doesn't belong to this PO
                        continue
                else:
                    # Create new item
                    new_item = PurchaseOrderItem.objects.create(purchase_order=instance, **item_data)
                    item_ids_to_keep.add(new_item.id)

            # Delete items that were in the original PO but not in the new list
            instance.items.exclude(id__in=item_ids_to_keep).delete()

            # Recalculate and update the total cost for the PO header
            updated_total = calculate_order_total(items_data)
            instance.order_total = updated_total
            instance.save()

        return instance
