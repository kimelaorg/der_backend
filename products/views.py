from rest_framework import viewsets, generics
from django.db.models import Prefetch, OuterRef, Subquery, Min
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAdminUser
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    Product, ProductSpecification, ProductImage, ProductVideo,
    DigitalProduct
)
from .serializers import (
    ProductSerializer, ProductSpecificationSerializer, ProductImageSerializer, ProductSpecificationImageSerializer,
    ProductVideoSerializer, DigitalProductSerializer, PublicProductDetailSerializer
)
from rest_framework.pagination import PageNumberPagination
from .filter import ProductFilter
from inventory.models import Inventory


class StandardResultsPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size' # Allows user to set page size (e.g., ?page_size=20)
    max_page_size = 100 # Limits the absolute maximum page size

# --- Permissions for Management Endpoints ---
class IsAdminOrReadOnly(IsAuthenticatedOrReadOnly):
    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user and request.user.is_staff

# ====================================================================
# A. MANAGEMENT VIEWSETS (CRUD with Search)
# ===================================================================

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # permission_classes = [IsAdminUser]

    # Add search functionality: search by name, description, brand name, or category name
    filter_backends = [SearchFilter]
    search_fields = ['name', 'description', 'brand__name', 'category__name']

class ProductSpecificationViewSet(viewsets.ModelViewSet):
    queryset = ProductSpecification.objects.all()
    serializer_class = ProductSpecificationSerializer
    # permission_classes = [IsAdminUser]

    # Add search functionality: search by SKU, color, or related product name
    filter_backends = [SearchFilter]
    search_fields = ['sku', 'color', 'product__name']

class ProductImageView(generics.ListAPIView):
    queryset = ProductSpecification.objects.all()
    serializer_class = ProductSpecificationImageSerializer
    # permission_classes = [IsAdminUser]

    # Search by the SKU the image is attached to
    filter_backends = [SearchFilter]
    search_fields = ['product__sku']

class ProductVideoViewSet(viewsets.ModelViewSet):
    queryset = ProductVideo.objects.all()
    serializer_class = ProductVideoSerializer
    # permission_classes = [IsAdminUser]

    # Search by the SKU the video is attached to
    filter_backends = [SearchFilter]
    search_fields = ['product__sku']

class DigitalProductViewSet(viewsets.ModelViewSet):
    queryset = DigitalProduct.objects.all()
    serializer_class = DigitalProductSerializer
    # permission_classes = [IsAdminUser]

    # Search by related product name or license/fulfillment type names
    filter_backends = [SearchFilter]
    search_fields = ['product__name', 'license_type__name', 'fulfillment_method__name']

# ====================================================================
# B. PUBLIC API VIEWSET (Read-Only with Deep Search) 🔎
# ====================================================================

class PublicProductDetailViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides the fully nested, read-only product detail for public viewing,
    with advanced search, filtering (Brand, Screen Size), and pagination.
    """

    serializer_class = PublicProductDetailSerializer
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter

    search_fields = [
        'name', 'description', 'category__name',
        'product_specs__sku', 'product_specs__color',
        'product_specs__screen_size__name', 'product_specs__resolution__name',
        'product_specs__panel_type__name',
        'product_specs__supported_internet_services__name',
        'digital_details__license_type__name',
        'digital_details__fulfillment_method__name',
    ]

    # 'min_sale_price' is now correctly added to this list for ordering.
    ordering_fields = [
        'name',
        'created_at',
        'min_discounted_price',
        'category__name'
    ]
    ordering = ['-created_at']

    def get_queryset(self):
        # 1. Base Query and Sale Price Annotation Fix
        # We find the MINIMUM sale_price across all associated specs to enable ordering.
        queryset = Product.objects.filter(is_active=True).annotate(
            min_sale_price=Min('product_specs__discounted_price')
        )

        # 2. CRITICAL PERFORMANCE OPTIMIZATION & ERROR FIX (Inventory Prefetch)

        # Define Prefetch for Inventory: Solves the "Cannot find 'inventory'" AttributeError
        # 'inventory' is the related_name on the ProductSpecification model.
        inventory_prefetch = Prefetch(
            'inventory',
            # We don't need a custom queryset here, but defining it explicitly is robust
        )

        # Define Prefetch for ProductSpecifications, nesting all related data, including inventory
        product_specs_prefetch = Prefetch(
            'product_specs', # The reverse FK/related name on the Product model
            queryset=ProductSpecification.objects.prefetch_related(
                'productimage_set',
                'productvideo_set',
                'productconnectivity_set',
                'supported_internet_services',
                'electrical_specs',
                inventory_prefetch, # <--- The explicit Prefetch object for Inventory
            )
        )

        # 3. Apply final lookups
        queryset = queryset.prefetch_related(
            product_specs_prefetch, # Apply the nested Prefetch
            'digital_details__digitalproductvideo_set'

        ).select_related(
            'category',
            'digital_details',
            'digital_details__license_type',
            'digital_details__fulfillment_method'
        )

        return queryset


class ProductImageDeleteView(generics.DestroyAPIView):
    serializer_class = ProductImageSerializer
    queryset = ProductImage.objects.all()


class NewProductImageView(generics.CreateAPIView):
    serializer_class = ProductImageSerializer
    queryset = ProductImage.objects.all()
