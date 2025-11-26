
import django_filters
from .models import Product

class ProductFilter(django_filters.FilterSet):
    """
    A filter class for the Product model, allowing filtering
    by Brand and Screen Size (from the Specification model).
    """
    # Filter by Brand ID
    brand = django_filters.NumberFilter(field_name='brand__id')

    # Filter by Screen Size ID (Uses 'in' lookup to check all specifications)
    screen_size = django_filters.NumberFilter(
        field_name='product_specs__screen_size__id',
        distinct=True # Ensures products aren't duplicated if they have multiple specs matching the filter
    )

    class Meta:
        model = Product
        fields = ['name', 'screen_size'] # Define the fields available in the URL
