from django.db import models
from django.utils import timezone
from sales.models import Order

# Create your models here.

# Statuses for the Payment Attempt
PAYMENT_STATUS_CHOICES = [
    ('PENDING', 'Pending Control Number Generation'),
    ('WAITING_PAYMENT', 'Waiting for Customer Payment'),
    ('SUCCESS', 'Payment Received Successfully'),
    ('FAILED', 'Payment Failed'),
    ('EXPIRED', 'Control Number Expired'),
    ('CANCELLED', 'Order Cancelled')
]

class Payment(models.Model):
    """
    Main payment attempt record, linked to a SalesOrder.
    One order can potentially have multiple payment attempts if the first one fails or expires.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, help_text="The amount expected for this payment attempt.")
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True,
                                      help_text="Transaction ID received from the payment gateway on success.")
    payment_method = models.CharField(max_length=50, help_text="e.g., Bank Transfer, Mobile Money Operator (MNO)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment Transaction"
        verbose_name_plural = "Payment Transactions"
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment for Order {self.order_id} - {self.status}"


class LocalPaymentDetails(models.Model):
    """
    Stores specific details required for local payment systems,
    such as the Control Number and its strict expiry time.
    """
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='local_details')
    control_number = models.CharField(max_length=50, unique=True, null=True, blank=True,
                                      help_text="The unique Namba ya Udhibiti issued by the local gateway.")
    expiry_time = models.DateTimeField(help_text="The time after which the control number is invalid.")

    # Audit fields for gateway communication
    gateway_request_data = models.JSONField(null=True, blank=True)
    gateway_response_data = models.JSONField(null=True, blank=True)

    def is_expired(self):
        """Checks if the control number has passed its expiry time."""
        return self.expiry_time < timezone.now()

    class Meta:
        verbose_name = "Local Payment Detail (Control Number)"
        verbose_name_plural = "Local Payment Details (Control Numbers)"

    def __str__(self):
        return f"CN: {self.control_number} (Expires: {self.expiry_time.strftime('%Y-%m-%d %H:%M')})"
