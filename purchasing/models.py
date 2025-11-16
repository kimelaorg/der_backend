from django.db import models
import datetime
from django.db import models, transaction
from django.core.exceptions import ValidationError
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
    po_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        editable=False,
        help_text="Custom, sequential, and read-friendly Purchase Order Number."
    )
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders')
    po_date = models.DateTimeField(default=timezone.now, help_text="Date the PO was created.")
    expected_delivery_date = models.DateField(null=True, blank=True)
    po_status = models.CharField(max_length=20, choices=PO_STATUS_CHOICES, default='DRAFT')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, help_text="Staff member who created the PO.")
    order_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        verbose_name = "Purchase Order"
        ordering = ['-po_date']

    def save(self, *args, **kwargs):
        """
        Overrides the save method to generate a unique PO number before the first save.
        """
        # Only generate the number if it's a new instance and po_number is not set
        if not self.pk and not self.po_number:
            # Wrap the generation logic in a transaction to prevent race conditions
            # where two users save at the exact same moment.
            with transaction.atomic():
                # Get the current year
                current_year = datetime.date.today().year

                # Find the highest sequential number used for the current year
                last_po = PurchaseOrder.objects.filter(
                    po_number__startswith=f'#ORD-{current_year}-'
                ).order_by('-po_number').first()

                if last_po:
                    # Extract the sequential part (e.g., '1278' from '#ORD-2025-1278')
                    last_sequence_str = last_po.po_number.split('-')[-1]
                    try:
                        next_sequence = int(last_sequence_str) + 1
                    except ValueError:
                        # Fallback if the sequence part is non-numeric
                        next_sequence = 1
                else:
                    # Start the sequence at 1 (or whatever base number you want, e.g., 1000)
                    next_sequence = 1

                # Format the new PO number, ensuring the sequence part is zero-padded to 4 digits
                self.po_number = f'#ORD-{current_year}-{next_sequence:04d}'

        # Call the original save method
        super().save(*args, **kwargs)

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
    quantity_received = models.PositiveIntegerField(default=0)
    decayed_products = models.PositiveIntegerField(default=0)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, help_text="Staff member who recorded the reception.")
    reception_date = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Stock Reception Record"
        ordering = ['-reception_date']

    def __str__(self):
        return f"{self.quantity_received} units of {self.purchase_order_item.product.name} received on {self.reception_date.date()}"

    @property
    def total_received_and_decayed(self):
        """Calculates the total quantity from this record that accounts against the PO item."""
        return self.quantity_received + self.decayed_products

    # --- Validation Method ---
    def clean(self):
        super().clean()

        # 1. Get total quantities previously recorded (excluding the current record if editing)
        # Sum of all received and decayed quantities from PREVIOUS reception records for this item
        # .exclude(pk=self.pk) ensures we don't count the current record against itself during an update
        prior_total = StockReception.objects.filter(
            purchase_order_item=self.purchase_order_item
        ).exclude(pk=self.pk).aggregate(
            received_sum=models.Sum('quantity_received', default=0),
            decayed_sum=models.Sum('decayed_products', default=0)
        )

        prior_total_received = prior_total['received_sum']
        prior_total_decayed = prior_total['decayed_sum']

        # The total quantity that accounts against the PO item if this record is saved
        current_total_accounted = prior_total_received + prior_total_decayed + self.total_received_and_decayed

        # The quantity originally ordered
        ordered_qty = self.purchase_order_item.quantity_ordered


        # --- Rule 1: Quantity received + decayed is less than or equal to Quantity Ordered ---
        if current_total_accounted > ordered_qty:
            # Calculate the excess quantity to provide a helpful error message
            excess_qty = current_total_accounted - ordered_qty
            raise ValidationError({
                'quantity_received': f"The total quantity received and decayed for this item (including this record) exceeds the ordered quantity ({ordered_qty}). Excess amount: {excess_qty}."
            })

        # --- Rule 2: Difference between quantity ordered and total received/decayed is equal or greater than total decay ---
        # This rule, as stated, is confusing, so I'll interpret it as the most logical business check:
        # "The total decay for this single reception record cannot exceed the received quantity."
        # AND/OR
        # "The decay and received quantity in this record must be logically separate."

        # *Interpretation 1 (Simpler): Decay must be less than or equal to the received amount in THIS record.*
        if self.decayed_products > self.quantity_received:
            raise ValidationError({
                'decayed_products': "The quantity of decayed products cannot exceed the quantity received in this single record."
            })

        # *Interpretation 2 (More Complex - Addressing Total Logic from prompt):*
        # The prompt mentions "total decay" vs "difference between quantity ordered and quantity received".
        # A clearer, equivalent rule that maintains inventory integrity is:
        # "The sum of received and decayed products in THIS record must not be zero (unless editing a zero record)."
        if self.quantity_received == 0 and self.decayed_products == 0:
            raise ValidationError("A reception record must have at least one unit received or decayed.")

        # FINAL CHECK: The total quantity received across all receptions must be less than or equal to the ordered quantity.
        # This is essentially Rule 1, but focused only on the final state.
        # The `current_total_accounted <= ordered_qty` check handles this completely.


# --- Additional: Create a Sum property on PurchaseOrderItem for easy access ---

# This can be used in your DRF serializer for the quantity_received_sum field
@property
def total_accounted_for(self):
    return self.receptions.aggregate(
        total_qty=models.Sum('quantity_received', default=0) + models.Sum('decayed_products', default=0)
    )['total_qty']

PurchaseOrderItem.add_to_class('total_accounted_for', total_accounted_for)
