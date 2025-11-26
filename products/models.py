from django.db import models
import uuid
from django.db.models import Max
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from setups.models import (
    Brand, ProductCategory, SupportedInternetService, SupportedResolution,
    Connectivity, LicenceType, SoftwareFulfillmentMethod, ScreenSize, PanelType
)
from django.utils import timezone

# --- 1. Base Product Model ---

class Product(models.Model):
    """
    The base definition of a commercial product (e.g., 'Samsung 4K TV Series 8').
    """
    name = models.CharField(max_length=300)
    description = models.TextField()
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT, related_name='products')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null = True)

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ('name',)

    def __str__(self):
        return self.name

# --- 2. Product Specification / Variant Model (The SKU) ---

class ProductSpecification(models.Model):
    """
    Represents a specific variant or SKU of a product (e.g., 'Samsung 4K TV 55-inch').
    This is the unit of measure for Inventory, Sales, and Purchasing.
    """
    sku = models.CharField(max_length=50, unique=True, verbose_name="SKU")
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='product_specs',
        verbose_name="Base Product"
    )

    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='products')
    screen_size = models.ForeignKey(ScreenSize, on_delete=models.PROTECT, null = True)
    resolution = models.ForeignKey(SupportedResolution, on_delete=models.PROTECT, null = True)
    panel_type = models.ForeignKey(PanelType, on_delete=models.PROTECT, null = True, blank=True,)
    actual_price = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2)
    model = models.CharField(max_length = 255, unique = True)

    color = models.CharField(max_length=20, blank=True, null=True)
    smart_features = models.BooleanField(default=False)
    supported_internet_services = models.ManyToManyField(SupportedInternetService, blank=True)

    class Meta:
        verbose_name = _("Product Specification (SKU)")
        verbose_name_plural = _("Product Specifications (SKUs)")

    def _generate_base_sku(self):
        """Generates the base portion of the SKU."""
        try:
            brand = self.brand.name[:3].upper()
            category = self.product.category.name[:2].upper()
            color = self.color[:3].upper() if self.color else 'GEN'
            return f"{brand}-{category}-{color}"
        except AttributeError:
            # Fallback if related objects are unexpectedly missing during save
            return "SKU-ERROR"

    def save(self, *args, **kwargs):
        """
        Ensures the SKU is unique by appending a counter if a conflict is found.
        """
        # Only generate SKU if it's a new object or the SKU is explicitly empty
        if not self.pk or not self.sku:
            base_sku = self._generate_base_sku()

            # Use the base_sku as the initial check
            new_sku = base_sku
            counter = 0

            # Loop until a unique SKU is found
            while ProductSpecification.objects.filter(sku=new_sku).exists():
                counter += 1
                # Append a sequential counter (e.g., BASE-01, BASE-02)
                new_sku = f"{base_sku}-{counter:02d}"

                # Safety break to prevent infinite loop (e.g., if database is massive and slow)
                if counter > 99:
                    # Consider raising a hard error or switching to a hash
                    new_sku = f"{base_sku}-{uuid.uuid4().hex[:4].upper()}"
                    if ProductSpecification.objects.filter(sku=new_sku).exists():
                         raise ValidationError("Could not generate a unique SKU after 100 attempts and hash fallback.")
                    break

            self.sku = new_sku

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Specs for {self.product.name} ({self.sku})"

# --- 3. Related Models (Keeping the original structure) ---

class ProductImage(models.Model):
    product = models.ForeignKey(ProductSpecification, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='Media/Images')

class ProductVideo(models.Model):
    product = models.ForeignKey(ProductSpecification, on_delete=models.CASCADE)
    video = models.FileField(upload_to='Media/Electronics/Videos')

class ProductConnectivity(models.Model):
    product = models.ForeignKey(ProductSpecification, on_delete=models.CASCADE)
    connectivity = models.ForeignKey(Connectivity, on_delete=models.CASCADE)
    connectivity_count = models.PositiveIntegerField(default=0, null=True, blank=True)

class ElectricalSpecification(models.Model):
    product = models.OneToOneField(ProductSpecification, on_delete=models.CASCADE, related_name='electrical_specs')
    voltage = models.CharField(max_length=50, blank=True)
    max_wattage = models.CharField(max_length=50, null=True, blank=True)
    frequency = models.CharField(max_length=20, default='50/60 Hz')

# --- 4. Digital Product Models ---

class DigitalProduct(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='digital_details')
    license_type = models.ForeignKey(LicenceType, on_delete=models.RESTRICT)
    fulfillment_method = models.ForeignKey(SoftwareFulfillmentMethod, on_delete=models.RESTRICT)

    class Meta:
        verbose_name = _("Digital Product Detail")
        verbose_name_plural = _("Digital Product Details")

    def __str__(self):
        return f"Digital Detail for {self.product.name}"

class DigitalProductVideo(models.Model):
    product = models.ForeignKey(DigitalProduct, on_delete=models.CASCADE)
    video = models.FileField(upload_to='Media/Digital/Videos')
