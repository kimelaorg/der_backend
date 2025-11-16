from django.db import models
from django.utils.translation import gettext_lazy as _
from products.models import ProductSpecification
from django.conf import settings
from django.utils import timezone
from setups.models import Region # To track geographical location of warehouse

# --- 1. Warehouse Location Model (New) ---
class WarehouseLocation(models.Model):
    """
    Stores physical locations (warehouses, stores, staging areas) where
    products are stocked.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Location Name"))
    code = models.CharField(max_length=20, unique=True, help_text=_("Short code for quick reference (e.g., WA, SCL, MZ)"))
    address = models.TextField(blank=True, verbose_name=_("Full Address"))
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Geographic Region")
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Warehouse Location")
        verbose_name_plural = _("Warehouse Locations")
        ordering = ('name',)

    def __str__(self):
        return self.name


# --- 2. Inventory Stock Model ---
class Inventory(models.Model):
    """
    The main table tracking real-time stock levels for each product (SKU) at a specific location.

    NOTE: Using ProductSpecification as the FK target ensures we track stock by SKU, not just Product name.
    """
    product = models.OneToOneField(
        ProductSpecification,
        on_delete=models.CASCADE,
        related_name='inventory',
        verbose_name=_("Product (SKU)")
    )
    quantity_in_stock = models.IntegerField(default=0)
    safety_stock_level = models.IntegerField(default=5)

    # Location tracking - Now a ForeignKey for better management
    location = models.ForeignKey(
        WarehouseLocation,
        on_delete=models.PROTECT,
        verbose_name=_("Storage Location"),
        related_name='stock_items',
        # Default to a primary warehouse if one exists
        null=True
    )

    last_restock_date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Inventory Stock")
        verbose_name_plural = _("Inventory Stock")
        ordering = ('quantity_in_stock',)

    def __str__(self):
        return f"{self.product.sku}: {self.quantity_in_stock} units at {self.location.code if self.location else 'Unknown'}"

    # Custom property to check if stock is dangerously low
    @property
    def is_low_stock(self):
        return self.quantity_in_stock <= self.safety_stock_level


# --- 3. Stock Movement History Model ---
class StockMovement(models.Model):
    """
    Tracks every transaction that modifies the Inventory quantity, providing an auditable trail.
    """
    MOVEMENT_TYPES = [
        ('SALE', 'Sale (Decrement)'),
        ('RETURN', 'Return (Increment)'),
        ('RESTOCK', 'Restock (Increment)'),
        ('ADJUST', 'Manual Adjustment (Staff)'),
        ('TRANSFER', 'Transfer (Internal Move)'), # Added transfer type
    ]

    product = models.ForeignKey(
        ProductSpecification,
        on_delete=models.PROTECT,
        related_name='stock_movements', # Renamed for clarity
        verbose_name=_("Product")
    )
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPES, verbose_name=_("Movement Type"))
    quantity_change = models.IntegerField(verbose_name=_("Quantity Change (+ or -)"))

    # Crucial for COGS calculation (Cost of Goods Sold)
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Unit Cost at time of movement")
    )

    # Reference ID from the initiating app (e.g., Sales Order ID, Purchase Order ID)
    reference_id = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("Reference ID"))

    # Staff who performed the manual action or the system user if automated
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Performed By"))

    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = _("Stock Movement")
        verbose_name_plural = _("Stock Movements")
        ordering = ('-timestamp',)

    def __str__(self):
        return f"{self.product.sku} | {self.movement_type} | Change: {self.quantity_change}"
