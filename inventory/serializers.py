from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from django.db import transaction
from django.utils import timezone

# NOTE: Assuming these imports are correct based on your previous code
from .models import Inventory, StockMovement, WarehouseLocation
from products.models import ProductSpecification
from setups.serializers import RegionSerializer
# NOTE: Assuming RegionSerializer and related models/imports are accessible

# --- Nested Serializers for Read-Only Data ---

class WarehouseLocationSerializer(serializers.ModelSerializer):
    """Serializer for managing and displaying Warehouse Locations."""
    region_details = RegionSerializer(source='region', read_only=True)

    class Meta:
        model = WarehouseLocation
        fields = (
            'id', 'name', 'code', 'address', 'region', 'region_details',
            'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')
        validators = [
            UniqueTogetherValidator(
                queryset=WarehouseLocation.objects.all(),
                fields=['name', 'code']
            )
        ]

# --- 1. Inventory Status Serializer (R/W) ---
class InventorySerializer(serializers.ModelSerializer):
    """
    Serializer for displaying the current stock status and handling direct updates
    to safety stock and location.
    """
    # OPTIMIZATION: Use ReadOnlyField for simple, non-writable nested attributes
    sku = serializers.ReadOnlyField(source='product.sku')
    product_name = serializers.ReadOnlyField(source='product.product.name')

    # Nested representation of the location
    location_details = WarehouseLocationSerializer(source='location', read_only=True)

    # Note: is_low_stock should be a Property defined on the Inventory model
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Inventory
        fields = (
            'id', 'product', 'sku', 'product_name',
            'quantity_in_stock', 'safety_stock_level',
            'location', 'location_details',
            'last_restock_date', 'is_low_stock',
            'created_at', 'updated_at'
        )
        # quantity_in_stock and last_restock_date are only modified by StockMovement logic
        read_only_fields = ('quantity_in_stock', 'last_restock_date', 'created_at', 'updated_at')


# --- 2. Stock Adjustment Serializer (Write Only for Transactional Logic) ---
class StockAdjustmentSerializer(serializers.Serializer):
    """
    Serializer for validating manual stock adjustments by staff.
    This creates a StockMovement record and updates the Inventory quantity.
    """
    product_sku = serializers.CharField(max_length=50, help_text="The SKU of the product being adjusted.")
    # The absolute number to change the stock by (e.g., 5 to add, -3 to remove)
    adjustment_quantity = serializers.IntegerField(help_text="The quantity change (positive to add, negative to remove).")
    unit_cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        required=False,
        help_text="The unit cost associated with this movement (required for RESTOCK). "
    )
    reason = serializers.CharField(max_length=255, help_text="Reason for manual adjustment (required for audit).")

    # Instance of ProductSpecification found during validation
    product_spec_instance = None

    def validate_product_sku(self, value):
        try:
            # Find the ProductSpecification record via the SKU, pre-fetching the Inventory
            self.product_spec_instance = ProductSpecification.objects.select_related('inventory').get(sku=value)
            return value
        except ProductSpecification.DoesNotExist:
            # Removed reliance on gettext for simpler error message
            raise serializers.ValidationError("Product SKU does not exist.")

    def validate_adjustment_quantity(self, value):
        if value == 0:
            raise serializers.ValidationError("Adjustment quantity must not be zero.")

        # Check for sufficient stock if the movement is a removal (negative value)
        if value < 0:
            current_stock = self.product_spec_instance.inventory.quantity_in_stock if self.product_spec_instance else 0
            if abs(value) > current_stock:
                 # Used f-string for clear error message
                 raise serializers.ValidationError(f"Cannot adjust. Current stock is {current_stock}, but requested removal is {abs(value)}.")
        return value

    @transaction.atomic
    def save(self, **kwargs):
        """
        Custom save method to create a StockMovement record and update the Inventory table.
        """
        validated_data = self.validated_data
        product_spec = self.product_spec_instance
        adjustment_quantity = validated_data['adjustment_quantity']

        # 🔒 SECURITY CHECK: Ensure user is available in context for audit trail
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            # Better to handle this at the View/Permission level, but defensive coding here is good
            raise serializers.ValidationError("Authentication context missing for audit trail.")

        performed_by_user = request.user

        # 1. Create the StockMovement record (ADJUST type)
        movement = StockMovement.objects.create(
            product=product_spec,
            movement_type='ADJUST',
            quantity_change=adjustment_quantity,
            unit_cost=validated_data.get('unit_cost', 0.00),
            reference_id=validated_data['reason'], # Using reason as reference for manual adjustments
            performed_by=performed_by_user,
        )

        # 2. Update the Inventory object atomically
        inventory_item = product_spec.inventory
        inventory_item.quantity_in_stock += adjustment_quantity

        # If stock was added, update the restock date
        if adjustment_quantity > 0:
            inventory_item.last_restock_date = timezone.now()

        inventory_item.save(update_fields=['quantity_in_stock', 'last_restock_date', 'updated_at'])

        return movement

# --- 3. Stock Movement History Serializer (Read Only) ---
class StockMovementSerializer(serializers.ModelSerializer):
    """Serializer for displaying the audit trail of all stock movements."""

    # OPTIMIZATION: Use ReadOnlyField
    product_sku = serializers.ReadOnlyField(source='product.sku')
    product_name = serializers.ReadOnlyField(source='product.product.name')

    # Display the name of the staff member
    # Note: Source is 'performed_by.phone' - Ensure this is the desired audit name
    performed_by_name = serializers.ReadOnlyField(source='performed_by.phone')

    class Meta:
        model = StockMovement
        fields = (
            'id', 'product', 'product_sku', 'product_name',
            'movement_type', 'quantity_change', 'unit_cost',
            'reference_id', 'performed_by', 'performed_by_name',
            'timestamp'
        )
        read_only_fields = '__all__'
