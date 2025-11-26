from django.db import models
from django.utils import timezone
from django.conf import settings
from phonenumber_field.modelfields import PhoneNumberField



class CustomerDetails(models.Model):
    phone_number = PhoneNumberField(region = 'TZ', db_index = True)
    first_name = models.CharField(max_length = 30)
    middle_name = models.CharField(max_length = 100)
    last_name = models.CharField(max_length = 100)
    email = models.EmailField()



# --- Shared Choices for Consistency ---
SALE_STATUS_CHOICES = [
    ('COMPLETED', 'Completed'),
    ('CANCELLED', 'Cancelled'),
    ('REFUNDED', 'Refunded')
]

PAYMENT_METHOD_CHOICES = [
    ('Cash', 'Cash'),
    ('Card', 'Credit/Debit Card'),
    ('MOMO', 'Mobile Money'),
    ('Transfer', 'Bank Transfer'),
    ('Other', 'Other'),
]

PAYMENT_STATUS_CHOICES = [
    ('PENDING', 'Pending Payment'),
    ('PAID', 'Paid'),
    ('FAILED', 'Failed'),
    ('REFUNDED', 'Refunded'),
]


# --- 2. Sale Model (Transaction Header) ---
class Sale(models.Model):
    sale_date = models.DateTimeField(default=timezone.now, db_index=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Audit & Tracking Context
    customer = models.ForeignKey(
        CustomerDetails,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchases',
    )
    sales_outlet = models.ForeignKey(
        'inventory.WarehouseLocation',
        on_delete=models.SET_NULL,
        null=True,
        related_name='office_sales',
    )
    sales_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sales_recorded',
    )

    # Status & Payment
    status = models.CharField(
        max_length=20,
        default='COMPLETED',
        choices=SALE_STATUS_CHOICES,
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES,
        default='CASH',
    )
    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default='PAID',
    )

    class Meta:
        ordering = ['-sale_date']
        verbose_name = "Sale Transaction"
        indexes = [
            models.Index(fields=['sales_outlet', 'sale_date']),
            models.Index(fields=['sales_agent']),
        ]

    def __str__(self):
        return f"Sale #{self.id} - {self.sale_date.date()}"

# --- 3. SaleItem Model (Line Items) ---
class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE)

    # Link to the inventory-tracked product unit (Assuming location is 'products')
    product_specification = models.ForeignKey('products.ProductSpecification', on_delete=models.CASCADE)

    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    unit_measure = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        ordering = ['-sale']
        verbose_name = "Sale Line Item"
        unique_together = ('sale', 'product_specification')

    def __str__(self):
        return f"{self.product_specification} x {self.quantity}"
