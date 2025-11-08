from django.db import models
from django.utils import timezone
from setups.models import Supplier
from products.models import Product
from django.conf import settings

PO_STATUS_CHOICES = (
    ('DRAFT', 'Draft'), ('SENT', 'Sent to Supplier'),
    ('RECEIVED_PARTIAL', 'Partially Received'), ('RECEIVED_FULL', 'Fully Received'),
    ('CANCELLED', 'Cancelled'),
)

class PurchaseOrder(models.Model):
    """The main header for an order placed with a supplier."""
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders')
    po_date = models.DateTimeField(default=timezone.now, help_text="Date the PO was created.")
    expected_delivery_date = models.DateField(null=True, blank=True)
    po_status = models.CharField(max_length=20, choices=PO_STATUS_CHOICES, default='DRAFT')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, help_text="Staff member who created the PO.")
    order_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        verbose_name = "Purchase Order"
        ordering = ['-po_date']

    def __str__(self):
        return f"PO {self.id} for {self.supplier.name} - {self.po_status}"

class PurchaseOrderItem(models.Model):
    """Line item for products ordered on a PO."""
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity_ordered = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_received = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Purchase Order Item"
        unique_together = ('purchase_order', 'product')

    def __str__(self):
        return f"{self.quantity_ordered} x {self.product.name} on PO {self.purchase_order.id}"

class StockReception(models.Model):
    """Records the reception of items from a PO into inventory."""
    purchase_order_item = models.ForeignKey(PurchaseOrderItem, on_delete=models.PROTECT, related_name='receptions')
    quantity_received = models.PositiveIntegerField()
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, help_text="Staff member who recorded the reception.")
    reception_date = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Stock Reception Record"
        ordering = ['-reception_date']

    def __str__(self):
        return f"{self.quantity_received} units of {self.purchase_order_item.product.name} received on {self.reception_date.date()}"
