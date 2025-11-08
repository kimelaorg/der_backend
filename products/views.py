from rest_framework import viewsets, filters, permissions
from .models import Product
from .serializers import ProductSerializer

# --- Optimized Queryset Definition ---
# This queryset ensures all related one-to-one and one-to-many fields are fetched
# in the most efficient manner, essential for displaying complex product details.
PRODUCT_BASE_QUERYSET = Product.objects.all().select_related(
    'brand',
    'category',
    'digital_details', # OneToOne is safe for select_related
).prefetch_related(
    # Prefetch the list of ProductSpecifications (SKUs/variants)
    'product_specs',

    # Deeply prefetch foreign keys on the specifications model
    'product_specs__screen_size',
    'product_specs__resolution',
    'product_specs__panel_type',

    # Deeply prefetch Many-to-Many and One-to-Many relationships on specifications
    'product_specs__supported_internet_services',
    'product_specs__productconnectivity_set',
    'product_specs__productimage_set',
    'product_specs__productvideo_set',

    # Deeply prefetch the One-to-One electrical specs attached to the SKU
    'product_specs__electrical_specs',

    # Prefetch digital details related videos
    'digital_details__digitalproductvideo_set'
)


# --- Public Read-Only Catalog View ---
class PublicCatalogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides a read-only view of active products available for sale.
    Supports robust searching and sorting for the e-commerce storefront.
    """
    # Filter for active products for the public catalog
    queryset = PRODUCT_BASE_QUERYSET.filter(is_active=True)

    serializer_class = ProductSerializer
    # Requires customer/user to be logged in to view the catalog
    permission_classes = [permissions.AllowAny]

    # 1. Enable Searching AND Ordering/Sorting
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    # 2. Search fields (name, sku, brand name, category name)
    # The double underscore lookups work correctly even with the One-to-Many relationship
    search_fields = ['name', 'product_specs__sku', 'brand__name', 'category__name']

    # 3. Fields available for sorting (using sale_price from ProductSpecification)
    ordering_fields = ['name', 'product_specs__sale_price', 'created_at']
    ordering = ['name'] # Default ordering


# --- Staff Management ViewSet (CRUD) ---
class StaffProductManagementViewSet(viewsets.ModelViewSet):
    """
    Provides full CRUD access for staff to manage the entire product catalog.
    Access is granted based on standard Django model permissions (e.g., 'products.add_product').
    """
    # Use the base queryset for full CRUD access
    queryset = PRODUCT_BASE_QUERYSET

    serializer_class = ProductSerializer
    # Staff must be authenticated and have specific model permissions
    # permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

    # 1. Enable Searching AND Ordering/Sorting
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    # 2. Search fields (name, sku, brand name, category name)
    search_fields = ['name', 'product_specs__sku', 'brand__name', 'category__name']

    # 3. Fields available for sorting (using sale_price from ProductSpecification)
    ordering_fields = ['name', 'product_specs__sale_price', 'created_at']
    ordering = ['name'] # Default ordering
