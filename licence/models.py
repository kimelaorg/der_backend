from django.db import models
from django.utils import timezone
from products.models import DigitalProduct
from sales.models import Order
from django.conf import settings

# Create your models here.

class SoftwareLicense(models.Model):
    """Stores pre-generated license keys for software products."""
    product = models.ForeignKey(
        DigitalProduct, on_delete=models.CASCADE, related_name='licenses',
        help_text="The digital product this key is for."
    )
    license_key = models.CharField(
        max_length=255, unique=True,
        help_text="The unique software license key."
    )
    is_assigned = models.BooleanField(
        default=False, help_text="True if the key has been assigned."
    )
    assigned_to_order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="The order this key was assigned to."
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default = timezone.now())

    class Meta:
        verbose_name = "Software License Key"
        verbose_name_plural = "Software License Keys"
        ordering = ['created_at']
        indexes = [models.Index(fields=['product', 'is_assigned'])]

    def __str__(self):
        return f"Key for {self.product.name} ({'Assigned' if self.is_assigned else 'Available'})"


class CustomerDigitalAccess(models.Model):
    """Grants a customer access to a digital product (e.g., course, download)."""
    product = models.ForeignKey(
        DigitalProduct, on_delete=models.CASCADE,
        help_text="The digital product the customer has access to."
    )
    customer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='digital_accesses',
        help_text="The user/customer who has access."
    )
    granted_via_order = models.ForeignKey(
        Order, on_delete=models.PROTECT,
        help_text="The order that granted this access."
    )
    access_granted_at = models.DateTimeField(default = timezone.now())
    access_expires_at = models.DateTimeField(
        null=True, blank=True, help_text="Expiry date for timed access."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Customer Digital Access"
        verbose_name_plural = "Customer Digital Accesses"
        unique_together = ('customer_user', 'product', 'granted_via_order')
        ordering = ['-access_granted_at']

    def __str__(self):
        return f"Access for {self.customer_user.phone} to {self.product.name} ({'Active' if self.is_active else 'Inactive'})"
