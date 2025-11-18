from django.db import models
import datetime
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.db.models import Sum, F
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
    expected_delivery_date = models.DateTimeField(null=True, blank=True)
    po_status = models.CharField(max_length=20, choices=PO_STATUS_CHOICES, default='DRAFT')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, help_text="Staff member who created the PO.")
    order_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        verbose_name = "Purchase Order"
        ordering = ['-po_date']

    def clean(self):
        """
        Validation to ensure expected_delivery_date is not before po_date.
        """
        super().clean()

        # We can compare the two DateTimeField objects directly
        if self.expected_delivery_date and self.po_date:
            if self.expected_delivery_date < self.po_date:
                raise ValidationError({
                    'expected_delivery_date':
                    'The expected delivery date cannot be before the Purchase Order date(Today).'
                })

    def save(self, *args, **kwargs):

        self.full_clean()

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

    # --- Calculated Properties (for Read/Display in DRF) ---

    @property
    def quantity_remained_for_sale(self):
        """Calculates the quantity that is immediately available for sale from this batch."""
        return self.quantity_received - self.decayed_products

    @property
    def quantity_remained_unreceived(self):
        """Calculates the total quantity still expected from the PO item after all receptions."""
        ordered_qty = self.purchase_order_item.quantity_ordered

        # Calculate total accounted for (received + decayed) across ALL receptions for this item
        total_accounted = self.purchase_order_item.receptions.aggregate(
            sum_accounted=Sum(F('quantity_received') + F('decayed_products'), default=0)
        )['sum_accounted']

        # Ensure we don't return a negative number (though validation should prevent this)
        return max(0, ordered_qty - total_accounted)


    # --- Validation Method ---
    def clean(self):
        super().clean()

        # Rule 0: Basic check that data is present
        if self.quantity_received is None or self.decayed_products is None:
            raise ValidationError("Quantity received and decayed products fields must be filled.")

        ordered_qty = self.purchase_order_item.quantity_ordered

        # --- Rule 1, 3: Decayed products cannot exceed quantity received in this batch ---
        if self.decayed_products > self.quantity_received:
            raise ValidationError({
                'decayed_products': "Decayed products cannot exceed the quantity physically received in this batch."
            })

        # --- Rule 5: Quantity Remained For Sale check (Self-validation) ---
        # The quantity_remained_for_sale calculation (quantity_received - decayed_products)
        # must be non-negative. This is implicitly enforced by Rule 1.
        if self.quantity_remained_for_sale < 0: # Should not happen due to Rule 1
             raise ValidationError("Internal error: Quantity for sale cannot be negative.")


        # --- Calculate Prior Totals (Received + Decayed) ---

        qs = StockReception.objects.filter(
            purchase_order_item=self.purchase_order_item
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)

        prior_totals = qs.aggregate(
            prior_accounted_sum=Sum(F('quantity_received') + F('decayed_products'))
        )
        prior_accounted = prior_totals['prior_accounted_sum'] or 0

        current_record_accounted = self.quantity_received + self.decayed_products
        grand_total_accounted = prior_accounted + current_record_accounted


        # --- Rule 2, 4: Grand Total Accounted cannot exceed Quantity Ordered ---
        if grand_total_accounted > ordered_qty:
            excess_qty = grand_total_accounted - ordered_qty
            raise ValidationError({
                'quantity_received': f"The total accounted quantity (Received + Decayed) for this item ({grand_total_accounted}) exceeds the ordered quantity ({ordered_qty}). Over by {excess_qty} units."
            })

        # --- Rule 6: Quantity Remained Unreceived check (Internal Check) ---
        # Since we just verified that grand_total_accounted <= ordered_qty,
        # the remaining unreceived quantity (ordered_qty - grand_total_accounted)
        # will always be >= 0. This ensures the quantity unreceived never exceeds quantity ordered.

    def save(self, *args, **kwargs):
        # Always call full_clean() to ensure business rules are enforced
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity_received} units of {self.purchase_order_item.product.name} received on {self.reception_date.date()}"
