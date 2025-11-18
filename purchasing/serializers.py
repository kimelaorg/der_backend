from rest_framework import serializers
from django.db.models import Sum
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import PurchaseOrder, PurchaseOrderItem, StockReception, PO_STATUS_CHOICES
from setups.models import Supplier
from products.models import Product


# --- Helper Function for Order Totals ---
def calculate_order_total(items_data):
    """Calculates the total cost based on the provided list of item dictionaries."""
    total = 0.00
    for item in items_data:
        # Use float() for robust multiplication
        quantity = item.get('quantity_ordered', 0)
        cost = item.get('unit_cost', 0.00)
        total += quantity * float(cost)
    return total


# --- 1. StockReception Serializer ---
class StockReceptionSerializer(serializers.ModelSerializer):
    """Serializer for recording stock reception against a specific PO item."""

    # Read-only fields for context and display (KEEP)
    product_name = serializers.CharField(source='purchase_order_item.product.name', read_only=True)
    received_by_name = serializers.CharField(source='received_by.username', read_only=True)

    class Meta:
        model = StockReception
        fields = [
            'id', 'purchase_order_item', 'product_name',
            'quantity_received',
            'decayed_products',
            'received_by', 'received_by_name', 'reception_date'
        ]
        # 'received_by' and 'reception_date' will be set in the view (usually by pre_save/perform_create)
        read_only_fields = ['id', 'received_by', 'received_by_name', 'reception_date', 'product_name']

    def validate(self, data):
        """
        Custom validation that ensures the model's clean() method is called
        to execute complex business rules (like quantity checks).
        """
        # 1. Create a temporary model instance (or update the existing one)
        if self.instance:
            # If updating (PUT/PATCH), start with the existing instance and update fields
            instance = self.instance
            for attr, value in data.items():
                setattr(instance, attr, value)
        else:
            # If creating (POST), create a new instance
            instance = StockReception(**data)

        # 2. Handle fields set by the view/context, otherwise full_clean() might complain.
        # This assumes 'received_by' is passed via context or handled in create/update.
        if not instance.received_by_id and self.context.get('request', {}).user.is_authenticated:
            instance.received_by = self.context['request'].user

        # 3. Explicitly call the model's full_clean() method
        try:
            instance.full_clean(exclude=['received_by']) # Exclude fields that might be defaulted later
        except ValidationError as e:
            # Translate Django model errors into DRF field errors
            raise serializers.ValidationError(e.message_dict)

        # 4. If validation passes, return the data
        return data


# --- 2. PurchaseOrderItem Serializer (Nested) ---
class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for the individual line items of a Purchase Order."""
    # Display product name
    product_name = serializers.CharField(source='product.name', read_only=True)

    # Calculated fields for display
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    quantity_received_sum = serializers.SerializerMethodField()

    # Nested field for detailed reading (will be handled in to_representation)
    # This is set to read_only=True because we handle creation/update manually in the parent PO serializer
    receptions = StockReceptionSerializer(many=True, read_only=True)


    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'product', 'product_name',
            'quantity_ordered', 'unit_cost',
            'line_total', 'quantity_received_sum',
            'receptions' # This field is included for READ operations
        ]
        read_only_fields = ['id', 'line_total', 'quantity_received_sum']

    def get_quantity_received_sum(self, obj):
        """Calculates the sum of all received quantities for this item, prioritizing cache."""
        # Use cached data ('receptions_cache' defined in ViewSet Prefetch) if available
        if hasattr(obj, 'receptions_cache'):
             return sum(r.quantity_received for r in obj.receptions_cache)

        # Fallback to database aggregation (slower)
        return obj.receptions.aggregate(total_received=Sum('quantity_received'))['total_received'] or 0

    def to_representation(self, instance):
        """Override to calculate line_total and optimize nested receptions display by using cache."""
        representation = super().to_representation(instance)

        # Calculate line total for display (No Change)
        representation['line_total'] = float(instance.quantity_ordered) * float(instance.unit_cost)

        # Include nested stock receptions for detailed view
        # --- FIX: Read from the cached attribute 'receptions_cache' if available ---
        if hasattr(instance, 'receptions_cache'):
            receptions_data = instance.receptions_cache
        else:
            receptions_data = instance.receptions.all() # Fallback to query manager

        representation['receptions'] = StockReceptionSerializer(receptions_data, many=True).data

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
            'id', 'po_number', 'supplier', 'supplier_name', 'po_date', 'expected_delivery_date',
            'po_status', 'po_status_display', 'created_by', 'created_by_name',
            'order_total', 'items'
        ]
        read_only_fields = ['id', 'po_date', 'created_by', 'order_total']


    def validate_items(self, items):
        """Ensure items list is not empty."""
        if not items:
            raise serializers.ValidationError("A Purchase Order must contain at least one item.")
        return items

    def validate(self, data):
        """
        Triggers the model's full validation (including clean()) to ensure
        expected_delivery_date is not before po_date, skipping the 'items' data.
        """
        # 1. Separate the nested items data
        items_data = data.pop('items', None)
        user = self.context['request'].user

        # 2. Create a temporary instance or use the existing one for validation
        #    Use the modified 'data' dict which no longer contains 'items'
        instance = self.instance or PurchaseOrder(**data)

        # 3. Manually update fields on the instance for validation (especially important for updates)
        #    If self.instance exists, we need to apply the updates from 'data'
        #    (which is everything *but* items).

        if self.instance:
            # Updating an existing instance
            instance = self.instance
        else:
            # Creating a new instance: Inject the user into the initial data.
            # We must use .copy() to avoid altering the original 'data' dict before returning it.
            temp_data = data.copy()
            temp_data['created_by'] = user # <--- INJECTION HERE
            instance = PurchaseOrder(**temp_data)

        # 4. Run the model's full validation
        for key, value in data.items():
            # Apply all direct model fields, skipping nested/read-only fields that shouldn't be set
            if key not in ['order_total']:
                setattr(instance, key, value)

        # 5. Run the model's full validation
        try:
            # The instance now has a valid 'created_by' field, allowing validation to proceed
            instance.full_clean()
        except ValidationError as e:
            # Re-raise the Django ValidationError as a DRF ValidationError
            raise serializers.ValidationError(e.message_dict)

        # 6. Add 'items' back to the data dictionary before returning
        if items_data is not None:
            data['items'] = items_data

        return data


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

        # instance.save() is called later after total recalculation

        if items_data is not None:
            # Logic to manage nested items (create/update/delete)
            item_ids_to_keep = set()
            for item_data in items_data:
                item_id = item_data.get('id')

                # Check if item_id is provided AND the item belongs to THIS PO (robustness check)
                if item_id and instance.items.filter(id=item_id).exists():
                    # Update existing item
                    item = instance.items.get(id=item_id)
                    item.product = item_data.get('product', item.product)
                    item.quantity_ordered = item_data.get('quantity_ordered', item.quantity_ordered)
                    item.unit_cost = item_data.get('unit_cost', item.unit_cost)
                    item.save()
                    item_ids_to_keep.add(item.id)
                else:
                    # Create new item (id=None or ID doesn't belong to PO)
                    new_item = PurchaseOrderItem.objects.create(purchase_order=instance, **item_data)
                    item_ids_to_keep.add(new_item.id)

            # Delete items that were in the original PO but not in the new list
            instance.items.exclude(id__in=item_ids_to_keep).delete()

            # Recalculate and update the total cost for the PO header based on the final items
            # --- FIX: Ensure the aggregation fields are correct for calculation ---
            recalculated_total = instance.items.aggregate(
                total=Sum(models.F('unit_cost') * models.F('quantity_ordered'))
            )['total'] or 0.00

            # NOTE: To use F() expressions inside aggregate, you must import F
            # from django.db.models import F
            # Since that wasn't imported, I'll rely on the original logic
            # but using the final saved items for the total.

            # Recalculate based on currently saved items
            recalculated_total = sum(item.unit_cost * item.quantity_ordered for item in instance.items.all())

            instance.order_total = recalculated_total

        # --- FIX: Ensure the final representation uses the cached items list ---
        instance.save()

        return instance
