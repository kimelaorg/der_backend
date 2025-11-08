from django.db import models
from products.models import Product

# Create your models here.

class SalesKPICache(models.Model):
    """
    Cached, aggregated key performance indicators (KPIs) for sales.
    Data is populated periodically by a management command (e.g., cron job).
    """
    date = models.DateField(unique=True, primary_key=True)
    total_net_revenue = models.DecimalField(max_digits=15, decimal_places=2, help_text="Total revenue minus returns and discounts.")
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_count = models.PositiveIntegerField(default=0)
    new_customers_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Sales KPI Cache"
        verbose_name_plural = "Sales KPI Caches"


class InventorySummary(models.Model):
    """
    Summary metrics for inventory health and efficiency.
    """
    month_year = models.CharField(max_length=7, unique=True, primary_key=True, help_text="Format: YYYY-MM")
    turnover_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Inventory turnover rate for the period.")
    total_stock_value_retail = models.DecimalField(max_digits=15, decimal_places=2)
    average_days_supply = models.DecimalField(max_digits=5, decimal_places=1, help_text="Average days of stock on hand (DOH).")

    class Meta:
        verbose_name = "Inventory Summary"
        verbose_name_plural = "Inventory Summaries"


class ProductPerformance(models.Model):
    """
    Tracks top products based on sales volume and revenue.
    """
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING, db_constraint=False)
    sales_volume = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2)
    refund_rate = models.DecimalField(max_digits=5, decimal_places=2)
    ranking = models.PositiveSmallIntegerField(help_text="Current rank by revenue.", unique=True)

    class Meta:
        verbose_name = "Product Performance"
        verbose_name_plural = "Product Performances"
        ordering = ['ranking']
