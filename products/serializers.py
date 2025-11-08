from rest_framework import serializers
from django.db import transaction
from .models import (
    Product, ProductSpecification, DigitalProduct, ElectricalSpecification,
    ProductImage, ProductVideo, ProductConnectivity, DigitalProductVideo
)
from setups.models import Brand, ProductCategory, SupportedInternetService, LicenceType, SoftwareFulfillmentMethod


# --- 1. Nested Serializers for Media and Connectivity ---

class ProductImageSerializer(serializers.ModelSerializer):
    """Handles images related to a specific ProductSpecification (SKU)."""
    class Meta:
        model = ProductImage
        fields = ('id', 'image')
        extra_kwargs = {'id': {'required': False, 'allow_null': True}} # For partial updates/deletes

class ProductVideoSerializer(serializers.ModelSerializer):
    """Handles videos related to a specific ProductSpecification (SKU)."""
    class Meta:
        model = ProductVideo
        fields = ('id', 'video')
        extra_kwargs = {'id': {'required': False, 'allow_null': True}}

class ProductConnectivitySerializer(serializers.ModelSerializer):
    """Handles M2M connections (e.g., 3x HDMI, 2x USB) related to a SKU."""
    connectivity_name = serializers.CharField(source='connectivity.name', read_only=True)

    class Meta:
        model = ProductConnectivity
        fields = ('id', 'connectivity', 'connectivity_name', 'connectivity_count')
        extra_kwargs = {'id': {'required': False, 'allow_null': True}}

class DigitalProductVideoSerializer(serializers.ModelSerializer):
    """Handles videos specific to a Digital Product."""
    class Meta:
        model = DigitalProductVideo
        fields = ('id', 'video')
        extra_kwargs = {'id': {'required': False, 'allow_null': True}}

# --- 2. Nested Serializers for Specifications (OneToOne/ManyToOne) ---

class ElectricalSpecificationSerializer(serializers.ModelSerializer):
    """Handles the OneToOne electrical specs (Power, Voltage, etc.) for a SKU."""
    class Meta:
        model = ElectricalSpecification
        # Exclude the FK field 'product' as it's handled by the parent serializer
        exclude = ('product',)

class ProductSpecificationSerializer(serializers.ModelSerializer):
    """
    Serializer for a single Product Specification (SKU).
    This includes all physical product details and media/connectivity.
    """
    # Nested fields for related specs/details (OneToOne)
    electrical_specs = ElectricalSpecificationSerializer(required=False, allow_null=True)

    # Nested Media
    images = ProductImageSerializer(many=True, required=False)
    videos = ProductVideoSerializer(many=True, required=False)

    # Nested Connectivity (M2M through ProductConnectivity)
    connectivity_details = ProductConnectivitySerializer(source='productconnectivity_set', many=True, required=False)

    # Read-only fields for displaying FK names
    screen_size_name = serializers.CharField(source='screen_size.name', read_only=True)
    resolution_name = serializers.CharField(source='resolution.name', read_only=True)
    panel_type_name = serializers.CharField(source='panel_type.name', read_only=True)

    # Read-only field for displaying M2M names (SupportedInternetService)
    supported_internet_services_names = serializers.SlugRelatedField(
        source='supported_internet_services',
        many=True,
        read_only=True,
        slug_field='name'
    )

    class Meta:
        model = ProductSpecification
        # Exclude the product FK field as it is set by the parent (ProductSerializer)
        exclude = ('product',)

class DigitalProductSerializer(serializers.ModelSerializer):
    """Handles the OneToOne digital details for a base Product."""
    videos = DigitalProductVideoSerializer(source='digitalproductvideo_set', many=True, required=False)

    # Read-only fields for displaying FK names
    license_type_name = serializers.CharField(source='license_type.name', read_only=True)
    fulfillment_method_name = serializers.CharField(source='fulfillment_method.name', read_only=True)

    class Meta:
        model = DigitalProduct
        # Exclude the product FK field as it is set by the parent (ProductSerializer)
        exclude = ('product',)

# --- 3. Main Product Catalog Serializer ---

class ProductSerializer(serializers.ModelSerializer):
    """
    The main serializer for a base Product, capable of handling multiple
    ProductSpecification (SKUs) instances and their nested data.
    """
    # CRITICAL CHANGE: ProductSpecification is now a ForeignKey, so we use many=True
    # The source is the reverse accessor from the ProductSpecification FK to Product.
    product_specs = ProductSpecificationSerializer('product_specs', many=True, required=False)

    # Digital Details remain OneToOne
    digital_details = DigitalProductSerializer(required=False, allow_null=True)

    # Read-only fields for displaying related names instead of IDs
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'description',
            'brand', 'brand_name', 'category', 'category_name', 'is_active',
            'product_specs', 'digital_details',
            'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')

    # --- Helper methods for nested creation/update ---

    def create_single_specification(self, product, specs_data):
        """Creates a single ProductSpecification instance and its related nested objects."""
        # 1. Pop nested OneToMany (images, videos, connectivity) and OneToOne (electrical) data
        internet_services_data = specs_data.pop('supported_internet_services', [])
        connectivity_details_data = specs_data.pop('productconnectivity_set', [])
        images_data = specs_data.pop('images', [])
        videos_data = specs_data.pop('videos', [])
        electrical_specs_data = specs_data.pop('electrical_specs', None)

        # 2. Create ProductSpecification (Physical Product Detail)
        specs_instance = ProductSpecification.objects.create(product=product, **specs_data)

        # 3. Handle M2M
        specs_instance.supported_internet_services.set(internet_services_data)

        # 4. Handle nested OneToMany fields
        for conn_data in connectivity_details_data:
            ProductConnectivity.objects.create(product=specs_instance, **conn_data)
        for img_data in images_data:
            ProductImage.objects.create(product=specs_instance, **img_data)
        for vid_data in videos_data:
            ProductVideo.objects.create(product=specs_instance, **vid_data)

        # 5. Handle OneToOne
        if electrical_specs_data:
            ElectricalSpecification.objects.create(product=specs_instance, **electrical_specs_data)

        return specs_instance

    def update_single_specification(self, specs_instance, specs_data):
        """Updates a single ProductSpecification instance and its related nested objects."""

        internet_services_data = specs_data.pop('supported_internet_services', None)
        connectivity_details_data = specs_data.pop('productconnectivity_set', None)
        images_data = specs_data.pop('images', None)
        videos_data = specs_data.pop('videos', None)
        electrical_specs_data = specs_data.pop('electrical_specs', None)

        # 1. Update ProductSpecification fields
        for attr, value in specs_data.items():
            setattr(specs_instance, attr, value)
        specs_instance.save()

        # 2. Update M2M fields
        if internet_services_data is not None:
            specs_instance.supported_internet_services.set(internet_services_data)

        # 3. Handle complex nested updates (Connectivity/Media)
        # For simplicity, we implement a 'replace-all' strategy for nested lists if data is provided.
        if connectivity_details_data is not None:
            specs_instance.productconnectivity_set.all().delete()
            for conn_data in connectivity_details_data:
                ProductConnectivity.objects.create(product=specs_instance, **conn_data)

        # NOTE: Media (Images/Videos) updates should be handled more carefully by the client
        # providing IDs for deletion/update, but here we assume a 'replace-all' strategy for creation.
        # This is simplified; a real-world app needs logic to handle updates on existing images/videos via ID.
        if images_data is not None:
            specs_instance.productimage_set.all().delete()
            for img_data in images_data:
                ProductImage.objects.create(product=specs_instance, **img_data)

        if videos_data is not None:
            specs_instance.productvideo_set.all().delete()
            for vid_data in videos_data:
                ProductVideo.objects.create(product=specs_instance, **vid_data)


        # 4. Handle Electrical Specs (OneToOne update or create)
        if electrical_specs_data is not None:
            ElectricalSpecification.objects.update_or_create(
                product=specs_instance,
                defaults=electrical_specs_data
            )

        return specs_instance

    def handle_digital_details(self, product, digital_details_data, update_instance=None):
        """Helper to create or update DigitalProduct details and its videos."""
        videos_data = digital_details_data.pop('videos', [])

        # Create or Update the DigitalProduct instance
        digital_instance, created = DigitalProduct.objects.update_or_create(
            product=product,
            defaults=digital_details_data
        )

        if videos_data is not None:
            # Simple approach for videos: clear and re-create all DigitalProductVideo entries
            digital_instance.digitalproductvideo_set.all().delete()
            for vid_data in videos_data:
                DigitalProductVideo.objects.create(product=digital_instance, **vid_data)

        return digital_instance


    @transaction.atomic
    def create(self, validated_data):
        # Pop the list of specifications
        product_specs_data = validated_data.pop('product_specs', [])
        digital_details_data = validated_data.pop('digital_details', None)

        # 1. Create the main Product instance
        product = Product.objects.create(**validated_data)

        # 2. Create nested Physical Specifications (loop through the list)
        for spec_data in product_specs_data:
            self.create_single_specification(product, spec_data)

        # 3. Create Digital Details (OneToOne)
        if digital_details_data:
            self.handle_digital_details(product, digital_details_data)

        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        # Pop the list of specifications
        product_specs_data = validated_data.pop('product_specs', None)
        digital_details_data = validated_data.pop('digital_details', None)

        # 1. Update the main Product instance fields
        instance = super().update(instance, validated_data)

        # 2. Update nested Physical Specifications (Complex List Logic)
        if product_specs_data is not None:
            # IDs of specifications submitted in the request
            incoming_spec_ids = {spec.get('id') for spec in product_specs_data if spec.get('id') is not None}
            # IDs of specifications currently attached to the product
            existing_spec_ids = set(instance.product_specs.values_list('id', flat=True))

            # Delete specifications that were NOT in the incoming data
            specs_to_delete = existing_spec_ids - incoming_spec_ids
            ProductSpecification.objects.filter(id__in=specs_to_delete).delete()

            for spec_data in product_specs_data:
                spec_id = spec_data.get('id')

                if spec_id:
                    # UPDATE existing specification
                    try:
                        spec_instance = ProductSpecification.objects.get(id=spec_id, product=instance)
                        self.update_single_specification(spec_instance, spec_data)
                    except ProductSpecification.DoesNotExist:
                        # Ignore or raise error if ID is invalid/not attached to this product
                        pass
                else:
                    # CREATE new specification
                    self.create_single_specification(instance, spec_data)


        # 3. Handle Digital Details update or creation
        if digital_details_data is not None:
            self.handle_digital_details(instance, digital_details_data, update_instance=True)

        return instance
