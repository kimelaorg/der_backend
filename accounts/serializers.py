from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework.exceptions import AuthenticationFailed as af
from django.core.exceptions import ValidationError as ve
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, authenticate
from phonenumber_field.serializerfields import PhoneNumberField
from .models import Otp
from notifications.sms import send_sms, sms_to_staff
import json
import base64
import secrets
import string

User = get_user_model()

# --- UTILITY FUNCTIONS ---
def enforce_password(value):
    """Enforces Django's configured password policy."""
    try:
        validate_password(value)
    except ve as e:
        raise serializers.ValidationError(e.messages)
    return value


def generate_secure_password(length=12):
    """Generates a cryptographically secure, random password for new staff."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"

    # Ensure at least one of each for complexity
    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*")
    ]

    # Fill the rest of the length with random choices
    password += [secrets.choice(chars) for _ in range(length - len(password))]

    secrets.SystemRandom().shuffle(password)

    return "".join(password)


# --- REGISTRATION AND OTP FLOW SERIALIZERS ---

class RegistrationSerializer(serializers.ModelSerializer):
    """Performs user registration (for customers) and generates the initial OTP."""

    class Meta:
        model = User
        fields = ['phone_number', 'email', 'first_name', 'last_name', 'password']
        extra_kwargs = {
            'email': {'required': False, 'allow_null': True, 'allow_blank': True},
            'password' : {'write_only' : True}
        }

    def validate_password(self, value):
        return enforce_password(value)

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)

        # Trigger OTP generation and SMS notification
        token_type = Otp.TOKEN_TYPE_REGISTRATION
        otp_entry = Otp.generate_new_code(user, user.phone_number, token_type)
        send_sms(otp_entry)

        return user


class ConfirmRegistrationSerializer(serializers.Serializer):
    """Validates the registration OTP code and activates the customer account."""
    phone_number = PhoneNumberField()
    OTP = serializers.CharField(max_length=6)


class LoginRequestOTPSerializer(serializers.Serializer):
    """Step 1 of 2FA login: Authenticate user by credentials and send login OTP."""
    phone_number = PhoneNumberField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')

        user = authenticate(phone_number=phone_number, password=password)

        if not user or not user.is_active:
            raise af('No active account found with the given credentials.')

        if not user.is_verified:
            raise af('Account not yet verified. Please verify your phone number.')

        # The user object is needed in the view to generate the OTP
        attrs['user'] = user
        return attrs


class LoginConfirmOTPSerializer(serializers.Serializer):
    """Step 2 of 2FA login: Validates OTP and generates the final JWT token."""
    phone_number = PhoneNumberField()
    OTP = serializers.CharField(max_length=6)


# --- CUSTOM JWT SERIALIZERS ---
class UserDetailsSerializer(serializers.ModelSerializer):
    """Used to safely serialize the user object for the 'user_data' JWT field."""
    class Meta:
        model = User
        fields = ['phone_number', 'first_name', 'last_name', 'email', 'is_verified', 'is_staff']


class UserTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Customized Simple JWT serializer to use 'phone_number' for auth and
    return a custom Base64-encoded 'user_data' payload.
    """

    def get_token(cls, user):
        return RefreshToken.for_user(user)

    def get_user_data(self, user):
        """Generates the Base64-encoded JSON string for user_data."""
        user_data = UserDetailsSerializer(user).data
        user_data_json = json.dumps({'user': user_data})
        # Note: The .encode('utf-8') and .decode('utf-8') are crucial for byte-string conversion
        base64_encoded_data = base64.urlsafe_b64encode(user_data_json.encode('utf-8')).decode('utf-8')
        return base64_encoded_data

    def validate(self, attrs):
        # Authenticate user using phone number and password
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')

        user = authenticate(phone_number=phone_number, password=password)

        if not user or not user.is_active:
            raise af('No active account found with the given credentials.')

        if not user.is_verified:
            raise af('Account not yet verified. Please verify your phone number.')

        # Manually generate tokens
        refresh = self.get_token(user)
        access = refresh.access_token

        # Construct the final response data
        data = {
            'refresh': str(refresh),
            'access': str(access),
            'user_data': self.get_user_data(user)
        }
        return data


# --- STAFF MANAGEMENT SERIALIZERS ---

class NewStaffSerializer(serializers.ModelSerializer):
    """Used by an Admin to create a new staff user with a temporary password."""

    class Meta:
        model = User
        fields = ['phone_number', 'first_name', 'middle_name', 'last_name']

    def create(self, validated_data):
        user = User.objects.create(**validated_data)

        # FIX: Use the secure utility function for staff password
        password = generate_secure_password()

        user.set_password(password)
        user.is_verified = True
        user.is_staff = True
        user.is_default_password = True
        user.save()

        name = f'{user.first_name} {user.last_name}'
        # Send the temporary password via SMS for first-time login
        sms_to_staff(name, user.phone_number, password)
        return user


class UserSerializer(serializers.ModelSerializer):
    """General serializer for reading/updating user profile details."""
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'first_name', 'last_name', 'is_verified', 'is_default_password']


# --- PASSWORD RESET SERIALIZERS ---

class RequestOTPSerializer(serializers.Serializer):
    """Initiates password reset by sending an OTP to the phone number."""
    phone_number = PhoneNumberField()


class ConfirmPasswordResetSerializer(serializers.Serializer):
    """
    Confirms password reset: Validates OTP and sets the new password.
    Requires OTP code and new password.
    """
    phone_number = PhoneNumberField()
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        return enforce_password(value)
