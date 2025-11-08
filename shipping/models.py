from django.db import models
from django.utils import timezone
from sales.models import Order, OrderItemPhysical
from django.conf import settings
from setups.models import ShippingMethod

# Create your models here.


SHIPMENT_STATUS_CHOICES = (
    ('PENDING', 'Pending Assignment'), ('PACKING', 'In Packaging'),
    ('DISPATCHED', 'Dispatched'), ('DELIVERED', 'Delivered'),
    ('FAILED', 'Delivery Failed'),
)

class ShipmentRequest(models.Model):
    """A request to fulfill all physical items from a Sales Order."""
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='shipment_request', help_text="The associated SalesOrder.")
    requested_at = models.DateTimeField(default=timezone.now)
    is_fulfilled = models.BooleanField(default=False)

    class Meta:
        db_table = 'shipment_request'
        verbose_name = "Shipment Request"
        ordering = ['requested_at']

    def __str__(self):
        return f"Request for Order {self.order.id}"


class Shipment(models.Model):
    """Tracks the physical shipment process."""
    request = models.ForeignKey(ShipmentRequest, on_delete=models.CASCADE, related_name='shipments')
    shipping_method = models.ForeignKey(ShippingMethod, on_delete=models.PROTECT)
    tracking_number = models.CharField(max_length=100, unique=True, null=True, blank=True, db_index = True)
    status = models.CharField(max_length=20, choices=SHIPMENT_STATUS_CHOICES, default='PENDING')
    assigned_to_staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_shipments')
    dispatched_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Shipment"
        ordering = ['-dispatched_at']

    def __str__(self):
        return f"Shipment {self.tracking_number or self.id} - {self.get_status_display()}"


class ShipmentLineItem(models.Model):
    """Links physical order items to a specific shipment."""
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='line_items')
    order_item = models.ForeignKey(OrderItemPhysical, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(help_text="Quantity of this item included in the shipment.")
    weight = models.CharField(max_length = 10, null = True, blank = True)

    class Meta:
        verbose_name = "Shipment Line Item"
        unique_together = ('shipment', 'order_item')

    def __str__(self):
        return f"{self.quantity} x {self.order_item.product.name} in Shipment {self.shipment.id}"
