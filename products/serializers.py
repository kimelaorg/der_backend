from rest_framework import serializers
from .models import (
    Product, ProductSpecification, ProductImage, ProductVideo,
    ProductConnectivity, ElectricalSpecification, DigitalProduct,
    DigitalProductVideo, SupportedInternetService,
)
from setups.models import Brand, ProductCategory, ScreenSize, SupportedResolution, PanelType



class ElectricalSpecificationSerializer(serializers.ModelSerializer):
    """Used for both CRUD and the nested public API."""
    class Meta:
        model = ElectricalSpecification
        fields = '__all__'
        read_only_fields = ('product',)

# 1. Product Management
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

# 2. Product Specification Management
class ProductSpecificationSerializer(serializers.ModelSerializer):
    supported_internet_services = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=SupportedInternetService.objects.all(),
        required=False
    )
    # Allows for creation/update of Electrical Specs when creating/updating a Spec
    electrical_specs = ElectricalSpecificationSerializer(required=False)

    class Meta:
        model = ProductSpecification
        fields = '__all__'
        read_only_fields = ('sku',)

    # Handles the creation/update of the OneToOne ElectricalSpecification
    def create(self, validated_data):
        electrical_specs_data = validated_data.pop('electrical_specs', None)
        spec = super().create(validated_data)
        if electrical_specs_data:
            ElectricalSpecification.objects.create(product=spec, **electrical_specs_data)
        return spec

    def update(self, instance, validated_data):
        electrical_specs_data = validated_data.pop('electrical_specs', None)
        instance = super().update(instance, validated_data)
        if electrical_specs_data:
            # Update existing or create new
            ElectricalSpecification.objects.update_or_create(
                product=instance,
                defaults=electrical_specs_data
            )
        return instance

# 3. Product Image Management
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = '__all__'

# 4. Product Video Management
class ProductVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVideo
        fields = '__all__'

# 5. Digital Product Management (and its videos)
class DigitalProductVideoManagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = DigitalProductVideo
        fields = '__all__'

class DigitalProductSerializer(serializers.ModelSerializer):
    # Allows videos to be created/managed via the DigitalProduct endpoint
    videos = DigitalProductVideoManagementSerializer(source='digitalproductvideo_set', many=True, required=False)

    class Meta:
        model = DigitalProduct
        fields = '__all__'
        read_only_fields = ('product',)


# ====================================================================
# B. PUBLIC API SERIALIZERS (For Read-Only Catalog)
# Your requested structure is defined here.
# ====================================================================

# Re-use the simple management image/video serializers for read-only purposes
PublicProductImageSerializer = ProductImageSerializer
PublicProductVideoSerializer = ProductVideoSerializer
PublicDigitalProductVideoSerializer = DigitalProductVideoManagementSerializer


# Connectivity Details (Nested in Specification)
class PublicProductConnectivitySerializer(serializers.ModelSerializer):
    connectivity_name = serializers.CharField(source='connectivity.name', read_only=True)

    class Meta:
        model = ProductConnectivity
        fields = ('id', 'connectivity', 'connectivity_name', 'connectivity_count',)


# Digital Details (Nested in Base Product)
class PublicDigitalProductDetailSerializer(serializers.ModelSerializer):
    videos = PublicDigitalProductVideoSerializer(source='digitalproductvideo_set', many=True, read_only=True)
    license_type_name = serializers.CharField(source='license_type.name', read_only=True)
    fulfillment_method_name = serializers.CharField(source='fulfillment_method.name', read_only=True)

    class Meta:
        model = DigitalProduct
        fields = (
            'id', 'videos', 'license_type_name', 'fulfillment_method_name',
            'license_type', 'fulfillment_method'
        )

# Specification (Nested in Base Product)
class PublicProductSpecificationSerializer(serializers.ModelSerializer):
    # OneToOne Relationships
    electrical_specs = ElectricalSpecificationSerializer(read_only=True)

    # Related Sets (M2M/Foreign Keys)
    images = PublicProductImageSerializer(source='productimage_set', many=True, read_only=True)
    videos = PublicProductVideoSerializer(source='productvideo_set', many=True, read_only=True)
    connectivity_details = PublicProductConnectivitySerializer(source='productconnectivity_set', many=True, read_only=True)

    # FK Name Lookups (One-to-many lookups)
    screen_size_name = serializers.CharField(source='screen_size.name', read_only=True)
    resolution_name = serializers.CharField(source='resolution.name', read_only=True)
    panel_type_name = serializers.CharField(source='panel_type.name', read_only=True)

    # Method Fields
    supported_internet_services_names = serializers.SerializerMethodField()
    quantity_in_stock = serializers.SerializerMethodField() # Reads from Inventory table

    def get_supported_internet_services_names(self, obj):
        # Prefetching in the ViewSet makes this efficient
        return [service.name for service in obj.supported_internet_services.all()]

    def get_quantity_in_stock(self, obj):
        """
        Looks up the quantity in stock using the 'inventory' related name.
        Uses a specific check for a missing OneToOne field to prevent general errors.
        """
        try:
            # Access the related Inventory object via the one-to-one field
            # The ._state.adding check isn't typically needed in a read serializer but
            # we rely on the related_name here.
            return obj.inventory.quantity_in_stock
        except ProductSpecification.inventory.RelatedObjectDoesNotExist: # <-- More specific error handling
            # This is the exact exception raised if the OneToOne field is missing
            return 0
        except Exception:
            # Catch all other exceptions (should be rare with proper prefetching)
            return 0


    class Meta:
        model = ProductSpecification
        fields = (
            'id', 'electrical_specs', 'images', 'videos', 'connectivity_details',
            'screen_size_name', 'resolution_name', 'panel_type_name',
            'supported_internet_services_names', 'sku', 'original_price',
            'sale_price', 'color', 'smart_features', 'screen_size',
            'resolution', 'panel_type', 'supported_internet_services', 'quantity_in_stock'
        )


# 6. PUBLIC PRODUCT DETAIL SERIALIZER (The Top Level)
class PublicProductDetailSerializer(serializers.ModelSerializer):
    product_specs = PublicProductSpecificationSerializer(many=True, read_only=True) # uses related_name='product_specs'
    digital_details = PublicDigitalProductDetailSerializer(read_only=True) # uses related_name='digital_details'
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)


    class Meta:
        model = Product
        fields = (
            'id', 'name', 'description', 'brand', 'brand_name', 'category',
            'category_name', 'is_active', 'product_specs', 'digital_details',
            'created_at', 'updated_at'
        )
