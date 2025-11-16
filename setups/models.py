from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField


# --- 1. Brands Model ---
class Brand(models.Model):
    """
    Stores the manufacturers and brands of products (e.g., Samsung, Hisense, etc.).
    Used as a lookup for the 'products' app.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Brand Name"))
    created_at = models.DateTimeField(default = timezone.now)

    class Meta:
        verbose_name = _("Brand")
        verbose_name_plural = _("Brands")
        ordering = ('name',)

        # Custom Permission: Prevent deletion of critical setup data by non-superusers
        permissions = [
            ("cannot_delete_brand", "Can only mark a brand as inactive, not delete it"),
        ]

    def __str__(self):
        return self.name


# --- 2. Product Categories Model ---
class ProductCategory(models.Model):
    """
    Stores the high-level categories for organizing the product catalog
    (e.g., Televisions, Home Appliances, Software).
    """
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Category Name"))
    parent_category = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subcategories',
        verbose_name=_("Parent Category")
    )
    is_digital = models.BooleanField(default=False, verbose_name=_("Is Digital Product Category"))
    description = models.TextField()
    created_at = models.DateTimeField(default = timezone.now)
    updated_at = models.DateTimeField(null = True)
    status = models.BooleanField(default = True)

    class Meta:
        verbose_name = _("Product Category")
        verbose_name_plural = _("Product Categories")
        ordering = ('-created_at',)

        # Custom Permission: Prevent deletion of critical setup data by non-superusers
        permissions = [
            ("cannot_delete_productcategory", "Can only mark a category as inactive, not delete it"),
        ]

    def __str__(self):
        return self.name


class Supplier(models.Model):
    """
    Stores details of external vendors from whom SSEAMS purchases inventory.
    Used by the 'purchasing' app.
    """
    name = models.CharField(max_length=150, unique=True, verbose_name=_("Supplier Name"))
    contact_person = models.CharField(max_length=100, blank=True, verbose_name=_("Contact Person"))
    phone = PhoneNumberField(unique=True, verbose_name=_("Phone Number"))
    email = models.EmailField(blank=True, null=True, verbose_name=_("Email Address"))
    address = models.TextField(blank=True, verbose_name=_("Address Details"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    created_at = models.DateTimeField(default = timezone.now)
    updated_at = models.DateTimeField(null = True)

    class Meta:
        verbose_name = _("Supplier")
        verbose_name_plural = _("Suppliers")
        ordering = ('name',)

    def __str__(self):
        return self.name


class SupportedInternetService(models.Model):
    CHOICES = [
        ('Netflix', 'Netflix'),
        ('Browser', 'Browser'),
        ('YouTube', 'YouTube'),
        ('HBO Max', 'HBO Max'),
        ('Google TV', 'Google TV'),
        ('Disney Plus', 'Disney Plus'),
    ]
    name = models.CharField(max_length = 200, choices = CHOICES, unique=True)

    def __str__(self):
        return self.name


class SupportedResolution(models.Model):
    CHOICES = [
        ('4K', '4K UHD'),
        ('8K', '8K UHD'),
        ('HD', 'HD Ready'),
        ('FHD', 'Full HD')
    ]
    name = models.CharField(max_length = 50, choices = CHOICES, unique=True)

    def __str__(self):
        return self.get_name_display()


class ScreenSize(models.Model):
    name = models.CharField(max_length = 50, unique=True, help_text="e.g., 55 inch, 65 inch")

    class Meta:
        verbose_name = _("Screen Size (Inches)")
        verbose_name_plural = _("Screen Sizes (Inches)")

    def __str__(self):
        return self.name


class PanelType(models.Model):
    CHOICES=[
        ('LED', 'LED'),
        ('OLED', 'OLED'),
        ('QLED', 'QLED')
    ]
    name = models.CharField(max_length = 50, choices = CHOICES, unique=True)

    def __str__(self):
        return self.get_name_display()


class Connectivity(models.Model):
    CHOICES = [
        ('HDMI', 'HDMI'),
        ('Wi-Fi', 'Wi-Fi'),
        ('Bluetooth', 'Bluetooth'),
        ('Ethernet', 'Ethernet'),
        ('USB', 'USB'),
        ('RF', 'RF'),
        ('Coaxial', 'Coaxial'),
        ('Screen Mirroring', 'Screen Mirroring')
    ]
    name = models.CharField(max_length = 50, choices = CHOICES, unique=True)

    class Meta:
        verbose_name_plural = "Connectivity Options"

    def __str__(self):
        return self.get_name_display()


class LicenceType(models.Model):
    CHOICES = [
        ('SUBS', 'Subscription'),
        ('PERM', 'Permanent License'),
        ('TEMP', 'Temporary Access')
    ]
    name = models.CharField(max_length = 50, choices = CHOICES, unique=True)
    description = models.TextField(blank=True) # Added blank=True for consistency

    class Meta:
        verbose_name_plural = "License Types"

    def __str__(self):
        return self.get_name_display()


class SoftwareFulfillmentMethod(models.Model):
    CHOICES = [
        ('KEY', 'Issue License Key'),
        ('ACCESS', 'Grant Video Access')
    ]
    name = models.CharField(max_length = 50, choices = CHOICES, unique=True)
    description = models.TextField(blank=True) # Added blank=True for consistency

    class Meta:
        verbose_name_plural = "Software Fulfillment Methods"

    def __str__(self):
        return self.get_name_display()


# --- 4. Payment Methods Model ---
class PaymentMethod(models.Model):
    """
    Stores details about payment channels (e.g., M-Pesa, Tigo Pesa, Bank Transfer, PayPal).
    Used by the 'payments' app.
    """
    name = models.CharField(max_length=50, unique=True, verbose_name=_("Method Name"))
    code = models.CharField(max_length=20, unique=True, verbose_name=_("Short Code"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    # FIX: Removed parentheses from timezone.now()
    created_at = models.DateTimeField(default = timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Payment Method")
        verbose_name_plural = _("Payment Methods")
        ordering = ('name',)

    def __str__(self):
        return self.name


class ShippingMethod(models.Model):
    """
    Defines the available methods for shipping goods to customers.
    """

    # --- Identification & Description ---
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="The internal and customer-facing name of the method (e.g., 'Standard Shipping', 'Express 24-Hour')."
    )
    description = models.TextField(
        blank=True,
        help_text="A detailed description of the service and its restrictions."
    )

    # --- Cost and Availability ---
    base_cost = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        help_text="The minimum or flat cost of this shipping method, before any weight or distance surcharges."
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Only active methods can be selected by customers at checkout."
    )

    min_delivery_time = models.PositiveSmallIntegerField(
        help_text="Minimum estimated delivery time in business days."
    )
    max_delivery_time = models.PositiveSmallIntegerField(
        help_text="Maximum estimated delivery time in business days."
    )
    carrier_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Optional: Name of the external carrier (e.g., 'DHL')."
    )

    # Useful for sorting or filtering by service type in the frontend
    SERVICE_CHOICES = [
        ('S', 'Standard'),
        ('E', 'Express'),
        ('P', 'Priority'),
        ('L', 'Local Pickup'),
    ]
    service_type = models.CharField(
        max_length=1,
        choices=SERVICE_CHOICES,
        default='S',
        help_text="Categorization of the speed/level of service."
    )

    class Meta:
        db_table = 'shipment_method'
        verbose_name = "Shipping Method"
        verbose_name_plural = "Shipping Methods"
        ordering = ['base_cost', 'name']
        # FIX: The original __str__ used non-existent fields, removed and simplified

    def __str__(self):
        return f"{self.name} (Cost: {self.base_cost})"


class Region(models.Model):
    """
    Geographical region data, used for customer addresses and shipping zone definitions.
    """
    name = models.CharField(max_length=45, unique=True)

    class Meta:
        verbose_name = _("Region")
        verbose_name_plural = _("Regions")
        # Custom Permission: Critical data must be protected
        permissions = [
            ("cannot_delete_region", "Can only mark a region as inactive, not delete it"),
        ]

    def __str__(self):
        return self.name

# --- Uncommented/Fixed Nested Location Models (Recommended for detailed shipping) ---

class District(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    name = models.CharField(max_length=45)

    class Meta:
        unique_together = ('region', 'name')
        verbose_name = _("District")
        verbose_name_plural = _("Districts")

    def __str__(self):
        return f"{self.name} ({self.region.name})"

class Ward(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE)
    name = models.CharField(max_length=45)

    class Meta:
        unique_together = ('district', 'name')
        verbose_name = _("Ward")
        verbose_name_plural = _("Wards")

    def __str__(self):
        return f"{self.name} ({self.district.name})"

class Street(models.Model):
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE)
    name = models.CharField(max_length=45)

    class Meta:
        unique_together = ('ward', 'name')
        verbose_name = _("Street")
        verbose_name_plural = _("Streets")

    def __str__(self):
        return self.name
