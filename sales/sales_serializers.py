from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from django.db.models import F
from .sales_models import Sale, SaleItem
from products.models import ProductSpecification
from inventory.models import WarehouseLocation, StockMovement
from django.contrib.auth import get_user_model
from .serializers import CustomerDetailSerializer


User = get_user_model()
# --- 1. Nested Serializers (Read-Only) ---

class SaleItemReadSerializer(serializers.ModelSerializer):
    """Used for displaying line item details in a completed Sale."""
    product_sku = serializers.CharField(source='product_specification.sku', read_only=True)
    product_name = serializers.CharField(source='product_specification.product.name', read_only=True)

    class Meta:
        model = SaleItem
        fields = ('id', 'product_specification', 'product_sku', 'product_name',
                  'quantity', 'unit_price', 'unit_measure')
        read_only_fields = fields

class CustomerSerializer(serializers.ModelSerializer):
    """Used for displaying customer details in a completed Sale."""
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'phone_number', 'email')
        

# --- 2. Transactional Serializer (Write-Only) ---

class SaleItemWriteSerializer(serializers.Serializer):
    """Used to validate the incoming item list for a new Sale."""
    product_specification_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductSpecification.objects.all(),
        required=True,
        source='product_specification'
    )
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit_measure = serializers.CharField(max_length=50, required=False, allow_null=True)


class SaleTransactionSerializer(serializers.Serializer):
    """
    Handles the atomic creation of Sale, SaleItem records, StockMovement,
    and updates the Inventory quantity. This is the POS endpoint serializer.
    """
    # Header fields
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    sales_outlet = serializers.PrimaryKeyRelatedField(
        queryset=WarehouseLocation.objects.all(),
        required=False, allow_null=True
    )
    payment_method = serializers.CharField()
    payment_status = serializers.CharField()

    # Line Items (Nested List)
    items = SaleItemWriteSerializer(many=True)

    # Internal cache for inventory instances during validation/creation
    _inventory_updates = {}
    _product_spec_cache = {}

    def validate(self, data):
        total_amount = 0
        items_data = data['items']

        if not items_data:
            raise serializers.ValidationError({"items": "A sale must contain at least one item."})

        # Pre-fetch all necessary ProductSpecification instances with their Inventory link
        product_ids = [item['product_specification'].pk for item in items_data]
        product_specs = ProductSpecification.objects.filter(
            id__in=product_ids
        ).select_related('inventory')

        self._product_spec_cache = {spec.pk: spec for spec in product_specs}

        for item_data in items_data:
            product_spec = item_data['product_specification']
            quantity = item_data['quantity']

            # Check 1: Existence and Inventory Link
            if product_spec.pk not in self._product_spec_cache:
                raise serializers.ValidationError({"items": f"Product ID {product_spec.pk} is invalid or missing."})

            spec_instance = self._product_spec_cache[product_spec.pk]

            # Check 2: Stock Availability (CRITICAL)
            if not hasattr(spec_instance, 'inventory') or quantity > spec_instance.inventory.quantity_in_stock:
                 raise serializers.ValidationError({
                    "items": f"Insufficient stock for SKU {spec_instance.sku}. Requested {quantity}, but only {spec_instance.inventory.quantity_in_stock} available."
                })

            # Check 3: Calculation
            total_amount += quantity * item_data['unit_price']

            # Cache the necessary update data
            self._inventory_updates[spec_instance.pk] = {
                'spec': spec_instance,
                'quantity_sold': quantity,
            }

        data['total_amount'] = total_amount
        return data

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request')
        items_data = validated_data.pop('items')
        total_amount = validated_data.pop('total_amount')

        # 1. Create the Sale Header
        sale = Sale.objects.create(
            sales_agent=request.user,
            total_amount=total_amount,
            sale_date=timezone.now(),
            status='COMPLETED',
            **validated_data
        )

        # 2. Process Line Items and Update Inventory
        for product_id, update_data in self._inventory_updates.items():

            item_payload = next(item for item in items_data if item['product_specification'].pk == product_id)

            product_spec = update_data['spec']
            quantity_sold = update_data['quantity_sold']
            inventory_item = product_spec.inventory

            # A. Create SaleItem Line
            SaleItem.objects.create(
                sale=sale,
                product_specification=product_spec,
                quantity=quantity_sold,
                unit_price=item_payload['unit_price'],
                unit_measure=item_payload.get('unit_measure')
            )

            # B. Create Stock Movement (Audit Trail)
            StockMovement.objects.create(
                product=product_spec,
                movement_type='SALE',
                quantity_change=-quantity_sold,
                reference_id=f"SALE-{sale.pk}",
                performed_by=request.user,
            )

            # C. Update Inventory Quantity (using F() ensures reliable concurrent updates)
            inventory_item.quantity_in_stock = F('quantity_in_stock') - quantity_sold
            inventory_item.save(update_fields=['quantity_in_stock', 'updated_at'])
            inventory_item.refresh_from_db() # Get the true quantity after the atomic update

        return sale

# --- 3. Sale Detail Serializer (Read-Only View) ---

class SaleDetailSerializer(serializers.ModelSerializer):
    """Used to retrieve and display a completed sales invoice."""
    customer = CustomerDetailSerializer(read_only=True)
    items = SaleItemReadSerializer(many=True, read_only=True)
    # Using ReadOnlyField for efficient nested display
    sales_agent_name = serializers.ReadOnlyField(source='sales_agent.get_full_name')
    sales_outlet_name = serializers.ReadOnlyField(source='sales_outlet.name')

    class Meta:
        model = Sale
        fields = (
            'id', 'sale_date', 'total_amount', 'status',
            'payment_method', 'payment_status',
            'sales_outlet', 'sales_outlet_name',
            'sales_agent', 'sales_agent_name',
            'customer', 'items'
        )
        read_only_fields = fields
