from rest_framework import serializers
from django.db import transaction
from .models import ShipmentRequest, Shipment, ShipmentLineItem, ShippingMethod
from sales.models import Order, OrderItemPhysical


class ShippingMethodSerializer(serializers.ModelSerializer):
    """
    Serializer for the ShippingMethod model.
    """
    # Custom field to display the estimated delivery timeframe clearly
    estimated_delivery = serializers.SerializerMethodField()

    class Meta:
        model = ShippingMethod
        fields = [
            'id',
            'name',
            'description',
            'base_cost',
            'estimated_delivery',
            'carrier_name',
            'service_type'
        ]
        # We explicitly exclude 'is_active', 'min_delivery_days', and 'max_delivery_days'
        # as they are used internally or combined into 'estimated_delivery'.

    def get_estimated_delivery(self, obj: ShippingMethod) -> str:
        """
        Formats the delivery days into a readable string (e.g., '1-3 business days').
        """
        if obj.min_delivery_days == obj.max_delivery_days:
            return f"{obj.min_delivery_days} business days"
        return f"{obj.min_delivery_days}-{obj.max_delivery_days} business days"


class ShipmentLineItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='order_item.product.name')
    class Meta:
        model = ShipmentLineItem
        fields = ['id', 'order_item', 'product_name', 'quantity']
        read_only_fields = ['id']

class ShipmentSerializer(serializers.ModelSerializer):
    """Staff serializer for managing shipments (dispatch, delivery updates)."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    line_items = ShipmentLineItemSerializer(many=True, read_only=True)
    shipping_method_details = ShippingMethodSerializer(source='shipping_method', read_only=True)

    class Meta:
        model = Shipment
        fields = ['id', 'request', 'shipping_method', 'shipping_method_details', 'tracking_number', 'status', 'status_display', 'assigned_to_staff', 'dispatched_at', 'delivered_at', 'line_items']
        read_only_fields = ['request', 'dispatched_at', 'delivered_at']

class ShipmentRequestSerializer(serializers.ModelSerializer):
    """Internal/Staff serializer to display pending requests."""
    order_id = serializers.ReadOnlyField(source='order.id')
    customer_phone = serializers.ReadOnlyField(source='order.customer.phone_number')

    class Meta:
        model = ShipmentRequest
        fields = ['id', 'order', 'order_id', 'customer_phone', 'requested_at', 'is_fulfilled']
        read_only_fields = fields

class InternalShipmentRequestSerializer(serializers.Serializer):
    """Serializer for the internal API call to create a shipment request."""
    order_id = serializers.IntegerField(help_text="ID of the SalesOrder whose physical items need fulfillment.")

    @transaction.atomic
    def create(self, validated_data):
        order_id = validated_data['order_id']
        order = Order.objects.get(pk=order_id)

        if order.physical_items.count() == 0:
            raise serializers.ValidationError("Order contains no physical items to ship.")

        if ShipmentRequest.objects.filter(order=order).exists():
            # Idempotency check: prevent duplicate requests
            return ShipmentRequest.objects.get(order=order)

        # Create the request
        request = ShipmentRequest.objects.create(order=order)

        # Auto-create the initial Shipment object for this request
        # NOTE: Assumes a default ShippingMethod (ID=1) for automatic creation
        default_shipping_method_id = 1
        shipment = Shipment.objects.create(request=request, shipping_method_id=default_shipping_method_id, status='PENDING')

        # Add all physical order items to the shipment line items
        for item in order.physical_items.all():
            ShipmentLineItem.objects.create(shipment=shipment, order_item=item, quantity=item.quantity)

        return shipment # Return the created shipment for immediate action
