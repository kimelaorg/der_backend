from rest_framework import serializers
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from decimal import Decimal
from setups.models import ShippingMethod # Added Address and ShippingMethod for order serialization
from accounts.models import Address as UserAddress # Imported Address model correctly
from products.models import DigitalProduct, ProductSpecification # Ensure ProductSpecification is imported
from inventory.models import Inventory # Assuming Inventory links to ProductSpecification

from .models import (
    WishList, ShoppingCart, ShoppingCartItem, Promotion, PromotionCategory,
    Order, OrderItemPhysical, OrderItemDigital
)

User = get_user_model()


# --- User/Customer Details ---

class CustomerDetailSerializer(serializers.ModelSerializer):
    """Minimal serializer for displaying customer info within an Order."""
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email']
        read_only_fields = fields


# --- WishList Serializers ---

class WishListSerializer(serializers.ModelSerializer):
    """Serializer for managing user WishList items."""
    product_name = serializers.CharField(source='product.product.name', read_only=True)
    product_variant_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = WishList
        fields = ['id', 'user', 'product', 'product_name', 'product_variant_name', 'added_at']
        read_only_fields = ['user', 'product_name', 'product_variant_name', 'added_at']
        extra_kwargs = {
            'product': {'write_only': True}
        }


# --- Shopping Cart Serializers ---

class CartItemWriteSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating cart items (write-only)."""
    class Meta:
        model = ShoppingCartItem
        fields = ['product_variant', 'quantity']

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be positive.")
        return value

class CartItemReadSerializer(serializers.ModelSerializer):
    """Serializer for displaying cart items (read-only)."""
    product_name = serializers.CharField(source='product_variant.product.name', read_only=True)
    product_variant_name = serializers.CharField(source='product_variant.name', read_only=True)
    sku = serializers.CharField(source='product_variant.sku', read_only=True)

    class Meta:
        model = ShoppingCartItem
        fields = ['id', 'product_variant', 'product_name', 'product_variant_name', 'sku', 'quantity']
        read_only_fields = fields


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Serializer for the main ShoppingCart, including its items."""
    items = CartItemReadSerializer(many=True, read_only=True)

    class Meta:
        model = ShoppingCart
        fields = ['id', 'user', 'created_at', 'updated_at', 'items']
        read_only_fields = ['user', 'created_at', 'updated_at']


# --- Promotion Serializers ---

class PromotionCategorySerializer(serializers.ModelSerializer):
    """Serializer for linking promotions to categories."""
    category_name = serializers.CharField(source='category_type.name', read_only=True)

    class Meta:
        model = PromotionCategory
        fields = ['id', 'category_type', 'category_name']
        read_only_fields = ['category_name']

class PromotionSerializer(serializers.ModelSerializer):
    """Serializer for managing Promotions."""
    target_categories = PromotionCategorySerializer(many=True, read_only=True)
    announced_by_name = serializers.CharField(source='announced_by.get_full_name', read_only=True)

    class Meta:
        model = Promotion
        fields = [
            'id', 'name', 'description', 'code', 'discount_type', 'discount_value',
            'is_active', 'start_date', 'end_date', 'announced_by',
            'announced_by_name', 'announced_at', 'target_categories'
        ]
        read_only_fields = ['announced_by_name', 'announced_at']


# --- Order Line Item Serializers (Read & Write for Order creation) ---

class OrderItemPhysicalSerializer(serializers.ModelSerializer):
    """Handles Physical product line items (writeable for order creation)."""
    # Read-only fields for display
    sku = serializers.CharField(source='product.sku', read_only=True)
    product_name = serializers.CharField(source='product.product.name', read_only=True)

    class Meta:
        model = OrderItemPhysical
        # 'product' field here refers to ProductSpecification FK
        fields = ['product', 'sku', 'product_name', 'quantity', 'unit_price', 'line_total']
        read_only_fields = ['unit_price', 'line_total', 'sku', 'product_name']


class OrderItemDigitalSerializer(serializers.ModelSerializer):
    """Handles Digital product line items (writeable for order creation)."""
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = OrderItemDigital
        # 'product' field here refers to DigitalProduct FK
        fields = ['product', 'product_name', 'quantity', 'unit_price', 'line_total']
        read_only_fields = ['unit_price', 'line_total', 'product_name']


# --- Main Order Serializer (Read & Write) ---

class SalesOrderSerializer(serializers.ModelSerializer):
    """
    Handles read operations for Orders and the complex write/create operations
    for customers checking out.
    """
    customer_details = CustomerDetailSerializer(source='customer', read_only=True)
    status_display = serializers.CharField(source='get_order_status_display', read_only=True)

    # Read/Display for existing items
    physical_items = OrderItemPhysicalSerializer(many=True, read_only=True)
    digital_items = OrderItemDigitalSerializer(many=True, read_only=True)

    # Writeable fields for nested creation
    new_physical_items = OrderItemPhysicalSerializer(many=True, write_only=True, required=False)
    new_digital_items = OrderItemDigitalSerializer(many=True, write_only=True, required=False)

    # Read-only display of shipping/address names
    shipping_method_name = serializers.CharField(source='shipping_method.name', read_only=True)
    shipping_address_line = serializers.CharField(source='shipping_address.street_address', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'customer', 'customer_details', 'order_date',
            'order_status', 'status_display', 'order_total', 'is_digital',
            'shipping_method', 'shipping_method_name', 'shipping_address',
            'shipping_address_line', 'staff_creator',
            'physical_items', 'digital_items',
            'new_physical_items', 'new_digital_items'
        ]
        # These fields are set during creation/managed by staff
        read_only_fields = [
            'id', 'order_id', 'customer', 'customer_details', 'order_date',
            'order_status', 'order_total', 'is_digital', 'staff_creator'
        ]

    def validate(self, data):
        """Validate that the order has at least one item."""
        if not data.get('new_physical_items') and not data.get('new_digital_items'):
            raise serializers.ValidationError("Order must contain at least one item.")

        # Check if shipping is provided for physical goods
        if data.get('new_physical_items') and (not data.get('shipping_method') or not data.get('shipping_address')):
             raise serializers.ValidationError("Physical items require both a shipping method and a shipping address.")

        return data

    @transaction.atomic
    def create(self, validated_data):
        """Custom create method to handle line item creation and stock management."""

        # 1. Separate nested item data (using 'new_' prefix for write-only fields)
        physical_data = validated_data.pop('new_physical_items', [])
        digital_data = validated_data.pop('new_digital_items', [])

        # 2. Set the customer to the currently authenticated user
        customer = self.context['request'].user

        # 3. Create the main Order header
        order = Order.objects.create(customer=customer, **validated_data)

        total_price = Decimal('0.00')
        is_digital_only = True # Assume true until a physical item is found

        # 4. Handle Physical Items (Requires Stock Check/Decrement)
        for item_data in physical_data:
            product_spec = item_data['product']
            quantity = item_data['quantity']

            # Stock Check
            try:
                # Assuming Inventory links to ProductSpecification via FK 'product'
                inventory_item = Inventory.objects.get(product=product_spec)
            except Inventory.DoesNotExist:
                raise serializers.ValidationError(f"Inventory record not found for {product_spec.product.name}.")

            if inventory_item.quantity_in_stock < quantity:
                raise serializers.ValidationError(f"Insufficient stock ({inventory_item.quantity_in_stock} available) for {product_spec.product.name} ({product_spec.name}).")

            # Decrement stock (atomic operation)
            inventory_item.quantity_in_stock -= quantity
            inventory_item.save()

            # Price calculation (assuming price is on ProductSpecification)
            # NOTE: We assume ProductSpecification has a 'price' attribute
            unit_price = Decimal(str(product_spec.price))
            line_total = unit_price * quantity
            total_price += line_total
            is_digital_only = False

            OrderItemPhysical.objects.create(
                order=order,
                unit_price=unit_price,
                line_total=line_total,
                **item_data
            )

        # 5. Handle Digital Items (No Stock Check required)
        for item_data in digital_data:
            digital_product = item_data['product']
            quantity = item_data['quantity']

            # Price calculation (assuming price is on DigitalProduct)
            # NOTE: We assume DigitalProduct has a 'price' attribute
            unit_price = Decimal(str(digital_product.price))
            line_total = unit_price * quantity
            total_price += line_total

            OrderItemDigital.objects.create(
                order=order,
                unit_price=unit_price,
                line_total=line_total,
                **item_data
            )

        # 6. Finalize order header
        order.order_total = total_price
        # Set is_digital flag based on what items were processed
        order.is_digital = is_digital_only and len(digital_data) > 0
        order.save()

        return order
