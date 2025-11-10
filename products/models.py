from django.db import models
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
    name = models.CharField(max_length=255)
    description = models.TextField()
    # Assuming Brand and ProductCategory are defined in the 'setups' app
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='products')
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT, related_name='products')
    is_active = models.BooleanField(default=True)

    # Use timezone.now without parentheses for call on object creation
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

    # CRITICAL CHANGE: Changed OneToOneField to ForeignKey. This allows a single
    # Product (base model) to have multiple Specifications (variants/SKUs).
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='product_specs',
        verbose_name="Base Product"
    )

    # Specialized Fields (Assumed to be Foreign Keys to models in 'setups' app)
    screen_size = models.ForeignKey(ScreenSize, on_delete=models.PROTECT)
    resolution = models.ForeignKey(SupportedResolution, on_delete=models.PROTECT)
    panel_type = models.ForeignKey(PanelType, on_delete=models.PROTECT)

    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)

    color = models.CharField(max_length=20, blank=True, null=True)
    smart_features = models.BooleanField(default=False)
    supported_internet_services = models.ManyToManyField(SupportedInternetService, blank=True)

    class Meta:
        verbose_name = _("Product Specification (SKU)")
        verbose_name_plural = _("Product Specifications (SKUs)")

    def generate_sku(self):
        """Generates a simple SKU based on attributes."""
        # Note: Added checks for related objects in case they are not yet set
        brand = self.product.brand.name[:3].upper() if (self.product and self.product.brand) else 'PROD'
        category = self.product.category.name[:2].upper() if (self.product and self.product.category) else 'CAT'
        color = self.color[:3].upper() if self.color else 'CLR'
        return f"{brand}-{category}-{color}"

    def save(self, *args, **kwargs):
        """Ensures the SKU is generated before saving if it's missing."""
        if not self.sku:
            self.sku = self.generate_sku()
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
