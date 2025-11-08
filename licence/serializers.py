from rest_framework import serializers
from .models import SoftwareLicense, CustomerDigitalAccess
from products.models import DigitalProduct


class SoftwareLicenseSerializer(serializers.ModelSerializer):
    """Serializer for managing SoftwareLicense keys (Staff CRUD)."""
    product_name = serializers.ReadOnlyField(source='product.name')

    class Meta:
        model = SoftwareLicense
        fields = ['id', 'product', 'product_name', 'license_key', 'is_assigned', 'assigned_to_order', 'assigned_at', 'created_at']
        read_only_fields = ['is_assigned', 'assigned_to_order', 'assigned_at', 'created_at']

class CustomerDigitalAccessSerializer(serializers.ModelSerializer):
    """Serializer for customer-facing read-only view of their access."""
    product_name = serializers.ReadOnlyField(source='product.name')
    order_id = serializers.ReadOnlyField(source='granted_via_order.id')

    class Meta:
        model = CustomerDigitalAccess
        fields = ['product_name', 'order_id', 'access_granted_at', 'access_expires_at', 'is_active']
        read_only_fields = fields

class InternalKeyAssignmentSerializer(serializers.Serializer):
    """Internal serializer used for assigning a key to a completed order."""
    order_id = serializers.IntegerField(help_text="The SalesOrder ID to fulfill.")
    digital_product_id = serializers.IntegerField(help_text="The DigitalProduct ID being assigned.")

    def validate(self, data):
        try:
            DigitalProduct.objects.get(pk=data['digital_product_id'])
        except DigitalProduct.DoesNotExist:
            raise serializers.ValidationError("Digital Product ID not found.")
        return data
