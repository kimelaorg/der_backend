from rest_framework import serializers
from .models import (
    Brand, ProductCategory, Supplier, PaymentMethod, ShippingMethod,
    SupportedInternetService, SupportedResolution, ScreenSize, PanelType,
    Connectivity, LicenceType, SoftwareFulfillmentMethod,
    Region, District, Ward, Street
)
from django.contrib.auth import get_user_model

# Although User is not strictly needed here, it's a good practice if you plan
# to link setup records to the creator/modifier.
User = get_user_model()

# --- Core Setup Models ---

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class ProductCategorySerializer(serializers.ModelSerializer):
    # Display the parent category name for easier reading
    parent_category_name = serializers.CharField(source='parent_category.name', read_only=True)

    class Meta:
        model = ProductCategory
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'parent_category_name')


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class ShippingMethodSerializer(serializers.ModelSerializer):
    # Displays the full name of the service type instead of the short code ('S', 'E', 'P', 'L')
    service_type_display = serializers.CharField(source='get_service_type_display', read_only=True)

    class Meta:
        model = ShippingMethod
        fields = '__all__'
        read_only_fields = ('service_type_display',)


# --- Product Attribute Models (Simple CRUD) ---

class SupportedInternetServiceSerializer(serializers.ModelSerializer):
    name_display = serializers.CharField(source='get_name_display', read_only=True)
    class Meta:
        model = SupportedInternetService
        fields = '__all__'

class SupportedResolutionSerializer(serializers.ModelSerializer):
    name_display = serializers.CharField(source='get_name_display', read_only=True)
    class Meta:
        model = SupportedResolution
        fields = '__all__'

class ScreenSizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScreenSize
        fields = '__all__'

class PanelTypeSerializer(serializers.ModelSerializer):
    name_display = serializers.CharField(source='get_name_display', read_only=True)
    class Meta:
        model = PanelType
        fields = '__all__'

class ConnectivitySerializer(serializers.ModelSerializer):
    name_display = serializers.CharField(source='get_name_display', read_only=True)
    class Meta:
        model = Connectivity
        fields = '__all__'
        read_only_fields = ['id']

class LicenceTypeSerializer(serializers.ModelSerializer):
    name_display = serializers.CharField(source='get_name_display', read_only=True)
    class Meta:
        model = LicenceType
        fields = '__all__'

class SoftwareFulfillmentMethodSerializer(serializers.ModelSerializer):
    name_display = serializers.CharField(source='get_name_display', read_only=True)
    class Meta:
        model = SoftwareFulfillmentMethod
        fields = '__all__'


# --- Geographical Location Models (Nested for Readability) ---

class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = '__all__'

class DistrictSerializer(serializers.ModelSerializer):
    # Display the name of the parent region
    region_name = serializers.CharField(source='region.name', read_only=True)

    class Meta:
        model = District
        fields = '__all__'
        read_only_fields = ('region_name',)

class WardSerializer(serializers.ModelSerializer):
    # Display the name of the parent district
    district_name = serializers.CharField(source='district.name', read_only=True)

    class Meta:
        model = Ward
        fields = '__all__'
        read_only_fields = ('district_name',)

class StreetSerializer(serializers.ModelSerializer):
    # Display the name of the parent ward
    ward_name = serializers.CharField(source='ward.name', read_only=True)

    class Meta:
        model = Street
        fields = '__all__'
        read_only_fields = ('ward_name',)
