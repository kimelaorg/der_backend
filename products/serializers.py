from rest_framework import serializers
from .models import (
    Product, ProductSpecification, ProductImage, ProductVideo,
    ProductConnectivity, ElectricalSpecification, DigitalProduct,
    DigitalProductVideo, SupportedInternetService,
)
from setups.models import Brand, ProductCategory, ScreenSize, SupportedResolution, PanelType, Connectivity



class ElectricalSpecificationSerializer(serializers.ModelSerializer):
    """Used for both CRUD and the nested public API."""
    class Meta:
        model = ElectricalSpecification
        fields = '__all__'
        read_only_fields = ('product',)


class ProductConnectivitySerializer(serializers.ModelSerializer):
    connectivity = serializers.PrimaryKeyRelatedField(
        queryset=Connectivity.objects.all(),
    )

    class Meta:
        model = ProductConnectivity
        fields = ('id', 'connectivity', 'connectivity_count')
        read_only_fields = ('product', 'id')


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
    # Allows for creation/update of Electrical Specs (One-to-One)
    electrical_specs = ElectricalSpecificationSerializer(required=False)

    # CRITICAL CHANGE: Set many=True to handle a list of connections
    product_connectivity = ProductConnectivitySerializer(many=True, required=False)

    class Meta:
        model = ProductSpecification
        fields = '__all__'
        read_only_fields = ('sku',)

    def validate(self, data):
        if data['actual_price'] < data['discounted_price']:
            raise serializer.ValidationError('Discounted price must not exceed actual price')
        return data


    def create(self, validated_data):
        electrical_specs_data = validated_data.pop('electrical_specs', None)
        # 1. POP the list of connectivity items
        product_connectivity_data = validated_data.pop('product_connectivity', None)

        spec = super().create(validated_data)

        if electrical_specs_data:
            ElectricalSpecification.objects.create(product=spec, **electrical_specs_data)

        # 2. CREATE: Iterate over the list and create each ProductConnectivity object
        if product_connectivity_data:
            for conn_data in product_connectivity_data:
                # 📢 FIX APPLIED HERE: Extract the Primary Key (ID) from the validated object.
                # The nested serializer validates the ID and converts it to the model instance object.
                # We need the ID (pk) to set the foreign key (connectivity_id).
                connectivity_instance = conn_data.pop('connectivity')
                connectivity_id = connectivity_instance.pk

                ProductConnectivity.objects.create(
                    product=spec,
                    connectivity_id=connectivity_id, # Set the integer ID
                    **conn_data
                )
        return spec

    def update(self, instance, validated_data):
        electrical_specs_data = validated_data.pop('electrical_specs', None)
        # 3. POP the list of connectivity items
        product_connectivity_data = validated_data.pop('product_connectivity', None)

        # Update the main ProductSpecification instance
        instance = super().update(instance, validated_data)

        # Handle Electrical Specs (One-to-One, update or create)
        if electrical_specs_data:
            ElectricalSpecification.objects.update_or_create(
                product=instance,
                defaults=electrical_specs_data
            )

        # 4. UPDATE: Handle the list of Product Connectivity objects
        if product_connectivity_data is not None:

            # CRITICAL: Delete all existing connections for this specification first
            ProductConnectivity.objects.filter(product=instance).delete()

            # Then, create the new set of connections
            for conn_data in product_connectivity_data:
                # 📢 FIX APPLIED HERE: Extract the Primary Key (ID) from the validated object.
                connectivity_instance = conn_data.pop('connectivity')
                connectivity_id = connectivity_instance.pk

                ProductConnectivity.objects.create(
                    product=instance,
                    connectivity_id=connectivity_id, # Set the integer ID
                    **conn_data
                )

        return instance

# 3. Product Image Management
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('id', 'product', 'image')

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
    brand_name = serializers.CharField(source='brand.name', read_only=True)

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
            'screen_size_name', 'resolution_name', 'panel_type_name', 'model',
            'supported_internet_services_names', 'sku', 'actual_price',
            'discounted_price', 'color', 'smart_features', 'screen_size', 'brand_name',
            'resolution', 'panel_type', 'supported_internet_services', 'quantity_in_stock'
        )


# 6. PUBLIC PRODUCT DETAIL SERIALIZER (The Top Level)
class PublicProductDetailSerializer(serializers.ModelSerializer):
    product_specs = PublicProductSpecificationSerializer(many=True, read_only=True) # uses related_name='product_specs'
    digital_details = PublicDigitalProductDetailSerializer(read_only=True) # uses related_name='digital_details'
    category_name = serializers.CharField(source='category.name', read_only=True)


    class Meta:
        model = Product
        fields = (
            'id', 'name', 'description', 'category',
            'category_name', 'is_active', 'product_specs', 'digital_details',
            'created_at', 'updated_at'
        )


class ProductSpecificationImageSerializer(serializers.ModelSerializer):
    productName = serializers.CharField(source='product.name', read_only=True)
    productDescription = serializers.CharField(source='product.description', read_only=True)
    productDiscountedPrice = serializers.DecimalField(source='discounted_price', read_only=True, max_digits=10, decimal_places=2)
    productActualPrice = serializers.DecimalField(source='actual_price', read_only=True, max_digits=10, decimal_places=2)
    images = PublicProductImageSerializer(source='productimage_set', many=True, read_only=True)

    class Meta:
        model = ProductSpecification
        fields = [
            'id',
            'productName',
            'productDescription',
            'productDiscountedPrice',
            'productActualPrice',
            'images'
        ]
