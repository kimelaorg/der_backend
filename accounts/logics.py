from .models import Otp
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from notifications.sms import send_sms


User = get_user_model()


def generate_new_otp(phone_number: str, token_type: str):
    """
    Generates a OTP for a verified user and sends it via SMS.

    Args:
        phone_number (str): The user's phone number.
        token_type (str): The current token_type.
    """
    try:
        # User lookup logic is sound: registration allows unverified users, others require verified.
        if token_type == Otp.TOKEN_TYPE_REGISTRATION:
            user = User.objects.get(Q(phone_number = phone_number))
        else:
            # We allow login and password_reset only for existing accounts.
            # NOTE: For password_reset, you may want to allow the lookup even if not verified,
            # if they are verified by OTP later. Sticking to the original logic here.
            user = User.objects.get(Q(phone_number = phone_number), Q(is_verified = True))

    except User.DoesNotExist:
        return Response({'error': 'No active user found with this phone number.'}, status=status.HTTP_404_NOT_FOUND)

    # Otp.generate_new_code will delete existing unused codes and create a new one.
    otp_entry = Otp.generate_new_code(
        user, phone_number, token_type
    )

    send_sms(otp_entry)

    if token_type == Otp.TOKEN_TYPE_REGISTRATION:
        message = 'OTP for account activation sent.'

    elif token_type == Otp.TOKEN_TYPE_PASSWORD_RESET:
        message = 'OTP for password reset sent.'

    else:
        message = 'OTP code sent! Check your phone.'

    return Response({'message': message}, status=status.HTTP_200_OK)


def verify_otp(phone_number: str, code: str, token_type: str):
    """
    Verifies OTP for the given phone number using the stored code, expiry, and usage status.

    Args:
        phone_number (str): The phone number associated with the OTP.
        code (str): The OTP code to verify.
        token_type (str): The current token_type being validated.

    Returns:
        Response: DRF Response object indicating success or failure.
    """

    try:
        # Find the most recently created, unused OTP matching phone and type
        otp_entry = Otp.objects.filter(
            phone_number=phone_number,
            token_type=token_type,
            is_used=False
        ).latest('created_at')

    except Otp.DoesNotExist:

        return Response({'error': 'Invalid or expired OTP code.'}, status=status.HTTP_400_BAD_REQUEST)

    if otp_entry.code != code:
        return Response({'error': 'Invalid or expired OTP code.'}, status=status.HTTP_400_BAD_REQUEST)

    if otp_entry.expires_at < timezone.now():
        otp_entry.is_used = True
        otp_entry.save()
        return Response({'error': 'Invalid or expired OTP code.'}, status=status.HTTP_400_BAD_REQUEST)

    user = otp_entry.user

    if token_type == Otp.TOKEN_TYPE_REGISTRATION:
        user.is_verified = True
        user.save()
        message = 'Account activated successfully.'

    elif token_type == Otp.TOKEN_TYPE_PASSWORD_RESET:
        message = 'OTP verified. Proceed to password change.'

    else:
        message = 'Login OTP verified.'

    otp_entry.is_used = True
    otp_entry.save()

    return Response({'message' : message}, status = status.HTTP_200_OK)
