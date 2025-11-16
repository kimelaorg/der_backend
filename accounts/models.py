from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import uuid
from django.conf import settings
# from setups.models import Region
from datetime import timedelta
import secrets
import string

# Create your models here.

OTP_CODE_LENGTH = getattr(settings, 'OTP_CODE_LENGTH', 6)
OTP_EXPIRATION_TIME_MINUTES = getattr(settings, 'OTP_EXPIRATION_TIME_MINUTES', 5)


class UserManager(BaseUserManager):
    def create_user(self, phone_number, password = None, **extra_fields):
        if not phone_number:
            raise ValueError("The phone number must be set")
        user = self.model(phone_number = phone_number, **extra_fields)
        user.set_password(password)
        user.save(using = self._db)
        return user

    def create_superuser(self, phone_number, password = None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(phone_number, password, **extra_fields)


# === User Model ===
class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(default = uuid.uuid4, editable = False, primary_key = True, db_index = True)
    phone_number = PhoneNumberField(unique = True, region = 'TZ', db_index = True)
    first_name = models.CharField(max_length = 30)
    middle_name = models.CharField(max_length = 100)
    last_name = models.CharField(max_length = 100)
    email = models.EmailField(unique=True, null=True, blank=True)
    is_active = models.BooleanField(default = True)
    is_staff = models.BooleanField(default = False)
    is_default_password = models.BooleanField(default = False)
    is_verified = models.BooleanField(default = False)  # Flag for phone verification
    date_joined = models.DateTimeField(default = timezone.now())

    objects = UserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'user'
        permissions = [
            ("can_register_staff", "Can register a new staff user"),
            ("can_reset_password_other_user", "Can force reset any user's password"),
            ("can_deactivate_user", "Can deactivate any user account (is_active = False)"),
            ("can_toggle_is_staff", "Can change a user's is_staff status"),
        ]

    def __str__(self):
        name = f'{self.first_name} {self.middle_name} {self.last_name}'
        return name.title()


# OTP model
class Otp(models.Model):

    TOKEN_TYPE_REGISTRATION = 'registration'
    TOKEN_TYPE_LOGIN = 'login'
    TOKEN_TYPE_PASSWORD_RESET = 'password_reset'

    TOKEN_TYPE_CHOICES = [
        (TOKEN_TYPE_REGISTRATION, 'Registration'),
        (TOKEN_TYPE_LOGIN, 'Login'),
        (TOKEN_TYPE_PASSWORD_RESET, 'Password Reset'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone_number = PhoneNumberField(region='TZ', db_index=True)
    code = models.CharField(max_length = OTP_CODE_LENGTH)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    token_type = models.CharField(max_length=20, choices=TOKEN_TYPE_CHOICES)

    @staticmethod
    def _generate_secure_code(length=OTP_CODE_LENGTH):
        """Generates a cryptographically secure random numeric code."""
        return ''.join(secrets.choice(string.digits) for _ in range(length))


    @classmethod
    def generate_new_code(cls, user, phone_number, token_type):
        """Generates a new random code, calculates expiry, and creates a new OTP entry."""

        cls.objects.filter(user=user, token_type=token_type).delete()

        expiry_time = timezone.now() + timedelta(minutes=OTP_EXPIRATION_TIME_MINUTES)

        new_code = cls._generate_secure_code()

        return cls.objects.create(
            user=user,
            phone_number=phone_number,
            code=new_code,
            token_type=token_type,
            expires_at=expiry_time
        )


# class Address(models.Model):
#     region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True)
#     district = models.CharField(max_length=100)
#     ward = models.CharField(max_length=100)
#     street = models.CharField(max_length=100)
#     post_code = models.PositiveIntegerField()
#     street_prominent_name = models.CharField(max_length=100)
#     house_number = models.CharField(max_length=20)
#     plot_number = models.CharField(max_length=20)
#
#     def __str__(self):
#         return f"{self.street}, {self.ward}, {self.district}, {self.region}"
#
#
#
# class UserAddress(models.Model):
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete = models.CASCADE)
#     address = models.ForeignKey(Address, on_delete = models.CASCADE)
#     is_default = models.BooleanField(default=False)
