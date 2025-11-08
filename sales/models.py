from django.db import models
from django.utils import timezone
from django.conf import settings
from products.models import DigitalProduct, ProductSpecification
from setups.models import ShippingMethod, ProductCategory
from accounts.models import Address
import uuid


# --- Core Sales Models ---

class WishList(models.Model):
    """Stores product specifications a user wants to purchase."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist_items'
    )
    # Links to the specific variant/specification of the product
    product = models.ForeignKey(ProductSpecification, on_delete=models.CASCADE)
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Wishlist Item"
        # Ensures a user can only add a specific product variant once
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user}'s wish for {self.product.name}"


class ShoppingCart(models.Model):
    """Represents a user's single shopping cart."""
    user = models.OneToOneField( # Use OneToOneField to ensure 1:1 relationship
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shopping_cart'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user}"


class ShoppingCartItem(models.Model):
    """Line items within a shopping cart."""
    cart = models.ForeignKey(
        ShoppingCart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    quantity = models.PositiveIntegerField(default=1)
    # Links to the specific variant/specification of the product
    product_variant = models.ForeignKey(ProductSpecification, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Shopping Cart Item"
        # Ensures only one entry per product variant in a single cart
        unique_together = ('cart', 'product_variant')

    def __str__(self):
        return f"{self.quantity} x {self.product_variant.product.name} ({self.product_variant.name})"


# --- Promotions and Discounts ---

PROMOTION_TYPE_CHOICES = (
    ('PERCENTAGE', 'Percentage Discount'),
    ('FIXED_AMOUNT', 'Fixed Amount Discount'),
)

class Promotion(models.Model):
    """Defines global or targeted sales promotions."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    # Optional coupon code for users to apply
    code = models.CharField(max_length=50, unique=True, blank=True, null=True)

    # New Fields for clear discount definition
    discount_type = models.CharField(max_length=20, choices=PROMOTION_TYPE_CHOICES, default='PERCENTAGE')
    # Use DecimalField for accurate calculations. Max digits set for up to 999.99 or 99.99%
    discount_value = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    announced_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Better to SET_NULL if staff account is deleted
        null=True,
        related_name='announced_promotions'
    )
    announced_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.name} ({self.discount_value}{'%' if self.discount_type == 'PERCENTAGE' else '$'} Off)"


class PromotionCategory(models.Model):
    """Links promotions to specific product categories."""
    category_type = models.ForeignKey(ProductCategory, on_delete=models.CASCADE)
    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.CASCADE,
        related_name='target_categories'
    )

    class Meta:
        verbose_name = "Promotion Category Link"
        # Ensures a promotion targets a category only once
        unique_together = ('promotion', 'category_type')

    def __str__(self):
        return f"{self.promotion.name} applies to {self.category_type.name}"


# --- Orders ---

ORDER_STATUS_CHOICES = (
    ('PENDING', 'Pending Payment'),
    ('PAID', 'Paid, Awaiting Fulfillment'),
    ('FULFILLED', 'Fulfilled/Shipped'),
    ('COMPLETED', 'Completed'),
    ('CANCELLED', 'Cancelled'),
)

class Order(models.Model):
    """The main sales order header."""
    order_id = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        db_index=True,
        help_text="Custom unique ID, e.g., ORD-YYYY-UNIQUE_PART"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='sales_orders'
    )
    order_date = models.DateTimeField(default=timezone.now)
    order_status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='PENDING'
    )
    # Total includes item costs, shipping, and applied taxes/discounts
    order_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    shipping_method = models.ForeignKey(
        ShippingMethod,
        on_delete=models.PROTECT,
        null=True # Orders might not have shipping (e.g., digital)
    )
    shipping_address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    staff_creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_sales_orders'
    )
    is_digital = models.BooleanField(
        default=False,
        help_text="True if the order contains only digital products."
    )

    class Meta:
        verbose_name = "Sales Order"
        ordering = ['-order_date']

    def save(self, *args, **kwargs):
        """
        Overrides save method to generate a unique custom_order_id
        if it doesn't already exist.
        """
        if not self.order_id:
            # Generate a 6-digit number based on a short UUID fragment
            year = timezone.now().strftime("%Y")

            # Function to generate a unique part
            def generate_unique_part():
                return str(uuid.uuid4().int)[:6].zfill(6)

            unique_part = generate_unique_part()
            self.order_id = f"ORD-{year}-{unique_part}"

            # Ensure absolute uniqueness by re-generating if the ID already exists
            while Order.objects.filter(order_id=self.order_id).exists():
                unique_part = generate_unique_part()
                self.order_id = f"ORD-{year}-{unique_part}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_id} ({self.customer}) - {self.order_status}"


class OrderItemPhysical(models.Model):
    """Line item for physical products."""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='physical_items'
    )
    product = models.ForeignKey(ProductSpecification, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    # Capture the price at the time of purchase
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Physical Order Item"
        unique_together = ('order', 'product')
        # Keep track of item cost after discounts/promotions

    def __str__(self):
        return f"{self.quantity} x {self.product.product.name} ({self.product.name})"


class OrderItemDigital(models.Model):
    """Line item for digital products."""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='digital_items'
    )
    product = models.ForeignKey(DigitalProduct, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    # Capture the price at the time of purchase
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Digital Order Item"
        unique_together = ('order', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Digital)"
