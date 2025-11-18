from rest_framework import serializers
from django.db import transaction # For atomic creation
from setups.models import Brand, SupportedInternetService, SupportedResolution, ScreenSize, PanelType
from setups.serializers import BrandSerializer, SupportedInternetServiceSerializer, SupportedResolutionSerializer, ScreenSizeSerializer, PanelTypeSerializer
from products.models import (
    Product, ProductSpecification, ProductImage, ProductVideo,
    ProductConnectivity, ElectricalSpecification
    )

# --- Nested Serializers --

class MegaProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        # Exclude 'product' FK as it's handled by the parent serializer
        fields = ['id', 'image']

class MegaProductVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVideo
        # Exclude 'product' FK as it's handled by the parent serializer
        fields = ['id', 'video']

class MegaProductConnectivitySerializer(serializers.ModelSerializer):
    # connectivity is a FK, you might want to display the name
    connectivity_name = serializers.CharField(source='connectivity.name', read_only=True)

    class Meta:
        model = ProductConnectivity
        fields = ['id', 'connectivity', 'connectivity_name', 'connectivity_count']

class MegaElectricalSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElectricalSpecification
        # This is a OneToOne relationship, so the data is directly nested.
        fields = ['voltage', 'max_wattage', 'frequency']

class MegaProductSpecificationSerializer(serializers.ModelSerializer):
    # Nested related models
    brand = SupportedResolutionSerializer(read_only=True)
    resolution = BrandSerializer(read_only=True)
    screen_size = ScreenSizeSerializer(read_only=True)
    panel_type = PanelTypeSerializer(read_only=True)
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(),  # Queryset needed for validation
        source='brand',                # Map this input ID back to the 'brand' model field
        write_only=True,               # Only used for input (POST/PUT)
        required=True                  # Ensures the input ID is provided
    )
    screen_size_id = serializers.PrimaryKeyRelatedField(
        queryset=ScreenSize.objects.all(),  # Queryset needed for validation
        source='screen_size',                # Map this input ID back to the 'brand' model field
        write_only=True,               # Only used for input (POST/PUT)
        required=True                  # Ensures the input ID is provided
    )
    panel_type_id = serializers.PrimaryKeyRelatedField(
        queryset=PanelType.objects.all(),  # Queryset needed for validation
        source='panel_type',                # Map this input ID back to the 'brand' model field
        write_only=True,               # Only used for input (POST/PUT)
        required=True                  # Ensures the input ID is provided
    )
    resolution_id = serializers.PrimaryKeyRelatedField(
        queryset=SupportedResolution.objects.all(),  # Queryset needed for validation
        source='resolution',                # Map this input ID back to the 'brand' model field
        write_only=True,               # Only used for input (POST/PUT)
        required=True                  # Ensures the input ID is provided
    )
    images = MegaProductImageSerializer(source='productimage_set', many=True, required=False)
    videos = MegaProductVideoSerializer(source='productvideo_set', many=True, required=False)
    connectivity = MegaProductConnectivitySerializer(source='productconnectivity_set', many=True, required=False)
    electrical_specs = MegaElectricalSpecificationSerializer(required=False) # OneToOne, not many=True

    class Meta:
        model = ProductSpecification
        # List all fields needed for specification and nested writes
        fields = [
            'id', 'sku', 'brand', 'screen_size', 'screen_size_id', 'brand_id', 'resolution', 'resolution_id', 'panel_type_id', 'panel_type',
            'original_price', 'sale_price', 'model', 'color',
            'smart_features', 'supported_internet_services',
            'images', 'videos', 'connectivity', 'electrical_specs'
        ]
        read_only_fields = ['sku']

class MegaProductSerializer(serializers.ModelSerializer):
    # ProductSpecification data is nested under 'specification' key
    specification = MegaProductSpecificationSerializer(source='product_specs', many=False)

    # Read-only fields for display
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        # Note: 'product_specs' is the related_name from ProductSpecification
        fields = ['id', 'name', 'description', 'category', 'category_name',
                  'is_active', 'created_at', 'specification']
        read_only_fields = ['created_at']

    def to_representation(self, instance):
        # 1. Get the default representation data
        data = super().to_representation(instance)

        # 2. Manually resolve the 'specification' field (which uses the 'product_specs' accessor)
        try:
            # Access the single ProductSpecification object directly
            specification_instance = instance.product_specs

            # Use the nested serializer to represent the data correctly
            # This ensures the nested serializer is given a model instance, not a Manager.
            data['specification'] = MegaProductSpecificationSerializer(specification_instance).data

        except ProductSpecification.DoesNotExist:
            # Handle case where the specification has not been created yet
            data['specification'] = None

        return data


    @transaction.atomic
    def create(self, validated_data):
        pass
        # 1. Pop the nested specification data
        spec_data = validated_data.pop('product_specs')

        # 2. Create the base Product
        product = Product.objects.create(**validated_data)

        # 3. Handle nested ProductSpecification and its related objects
        self._create_specification(product, spec_data)

        return product

    def _create_specification(self, product, spec_data):
        # Pop nested relationship data before creating the Specification header
        internet_services_data = spec_data.pop('supported_internet_services', [])
        images_data = spec_data.pop('productimage_set', [])
        videos_data = spec_data.pop('productvideo_set', [])
        connectivity_data = spec_data.pop('productconnectivity_set', [])
        electrical_specs_data = spec_data.pop('electrical_specs', None)

        # Create the ProductSpecification instance
        specification = ProductSpecification.objects.create(product=product, **spec_data)

        # Create nested M2M and 1-to-Many relationships
        # Note: M2M must be handled separately after creation
        if internet_services_data:
            specification.supported_internet_services.set(internet_services_data)

        for image_data in images_data:
            ProductImage.objects.create(product=specification, **image_data)

        for video_data in videos_data:
            ProductVideo.objects.create(product=specification, **video_data)

        for conn_data in connectivity_data:
            ProductConnectivity.objects.create(product=specification, **conn_data)

        if electrical_specs_data:
            ElectricalSpecification.objects.create(product=specification, **electrical_specs_data)

        return specification

    # NOTE: update() logic for nested serializers is significantly more complex
    # (handling create/update/delete of nested items) and should be implemented
    # similarly, or use a package like drf-writable-nested.
    # For a simple 'GET' and complex 'POST' (create), this structure is sufficient.
