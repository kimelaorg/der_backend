from rest_framework import serializers
from .models import Payment, LocalPaymentDetails, PAYMENT_STATUS_CHOICES
from django.utils import timezone

class ControlNumberRequestSerializer(serializers.Serializer):
    """Input serializer for a customer requesting a control number for an order."""
    order_id = serializers.IntegerField(help_text="The ID of the SalesOrder to pay for.")
    payment_method_id = serializers.IntegerField(help_text="The ID of the Payment Method (from settings_app).")

class PaymentStatusSerializer(serializers.ModelSerializer):
    """Output serializer for displaying the status of a payment attempt."""
    order_id = serializers.IntegerField(source='order.id')
    control_number = serializers.CharField(source='local_details.control_number', read_only=True)
    expiry_time = serializers.DateTimeField(source='local_details.expiry_time', read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'order_id', 'amount_due', 'status', 'transaction_id',
                  'payment_method', 'created_at', 'control_number', 'expiry_time']
