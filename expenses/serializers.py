from rest_framework import serializers
from .models import Category, Payee, Expense
from accounts.models import Address, Region
from accounts.serializers import UserDetailsSerializer
from setups.serializers import RegionSerializer
from django.contrib.auth import get_user_model


User = get_user_model()


class AddressSerializer(serializers.ModelSerializer):
    """
    Serializes the Address model. The 'region' is mandatory on the model
    (and thus, if an address exists, it should be present). Other fields are included
    but will display null/empty if not present in the database.
    """
    region = RegionSerializer(read_only=True)

    class Meta:
        model = Address
        fields = [
            'id',
            'region',
            'district',
            'ward',
            'street',
            'post_code',
            'street_prominent_name',
            'house_number'
        ]


class PayeeSerializer(serializers.ModelSerializer):
    """Serializes the Payee model, with an optional Address."""
    address = AddressSerializer(read_only=True, required=False, allow_null=True)

    class Meta:
        model = Payee
        fields = ['id', 'payee_name', 'phone_number', 'address']
        read_only_fields = ['id']
        

class CategorySerializer(serializers.ModelSerializer):
    """Serializes the essential fields of the Category model."""
    class Meta:
        model = Category
        fields = ['id', 'category_name']
        read_only_fields = ['id']


class PayeeSerializer(serializers.ModelSerializer):
    """Serializes the Payee model, including nested Address details."""
    address = AddressSerializer(read_only=True)

    class Meta:
        model = Payee
        fields = ['id', 'payee_name', 'phone_number', 'address']


class ExpenseDetailSerializer(serializers.ModelSerializer):
    """
    The main serializer for an Expense record, nesting all related data
    (User, Category, Payee, Address, and Region).
    """
    category = CategorySerializer(read_only=True)
    payee = PayeeSerializer(read_only=True)
    user = UserDetailsSerializer(read_only=True)

    class Meta:
        model = Expense
        fields = [
            'id',
            'user',
            'expense_date',
            'amount',
            'description',
            'payment_method',
            'category',
            'payee',
        ]
        extra_kwargs = {
            'payee': {'required': False, 'allow_null': True}
        }
