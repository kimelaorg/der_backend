import africastalking
from django.conf import settings
from decouple import config
from accounts.models import Otp
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone


User = get_user_model()

def send_sms(otp_entry: Otp):
    """
    Sends an SMS message with the OTP code using the Africa's Talking API.

    Args:
        otp_entry (Otp): An instance of the Otp model
                                             that holds the secure secret and phone number.
    """
    try:
        # Initialize the SDK with credentials
        africastalking.initialize(settings.AT_USERNAME, settings.AT_API_KEY)
        sms = africastalking.SMS

        phone_number = str(otp_entry.phone_number)
        otp_code = otp_entry.code
        token_type = otp_entry.token_type
        user = f'{otp_entry.user.first_name} {otp_entry.user.last_name}'

        '''
            Printing test for Otp code if it is succesfully generated, but this will be commented in production
            here it's only a test
        '''
        print(otp_code)

        # A straight foward message
        message = (
            f"Your {token_type} verification code is: {otp_code}. "
            f"It is valid for {settings.OTP_EXPIRATION_TIME // 60} minutes."
        )

        # For More user instance Customization message
        # message = (
        #     f"Dear {user.title()}, Your {token_type} verification code is: {otp_code}. "
        #     f"It is valid for {settings.OTP_EXPIRATION_SECONDS // 60} minutes."
        # )

        # Send the message
        response = sms.send(message, [phone_number])
        print(f"SMS sent successfully to {phone_number}: {response}")
        return True
    except Exception as e:
        print(f"Failed to send SMS to {phone_number}: {e}")
        # In production, you would log this error
        return False


def sms_to_staff(name, phone_number, password):
    """
        Sending sms to a staff User
    """
    try:
        # Initialize the SDK with credentials
        africastalking.initialize(settings.AT_USERNAME, settings.AT_API_KEY)
        sms = africastalking.SMS
        platform_name = 'Daz Electronics Repair'
        url = 'http://127.0.0.1:8000/api/auth/login'

        # Sending an sms to a new registered user
        message = (
            f"Dear {name.title()},\n"
            f"Welcome to {platform_name.upper()}!\n"
            f"Your account has been created successfully, \n"
            f"to login via {url} \n"
            f"Please use your phone number as the username: {phone_number}\n"
            f"and Password: {password}.\n"
        )

        # Send the message
        response = sms.send(message, [str(phone_number)])
        print(f"SMS sent successfully to {phone_number}: {response}")
        return True

    except Exception as e:
        print(f"Failed to send SMS to {phone_number}: {e}")
        # In production, you would log this error
        return False


# def generate_new_otp(phone_number: str, token_type: str):
#     """
#     Generates a OTP for a verified user and sends it via SMS.
#
#     Args:
#         phone_number (str): The user's phone number.
#         token_type (str): The current token_type.
#     """
#     try:
#         # User lookup logic is sound: registration allows unverified users, others require verified.
#         if token_type == Otp.TOKEN_TYPE_REGISTRATION:
#             user = User.objects.get(Q(phone_number = phone_number))
#         else:
#             # We allow login and password_reset only for existing accounts.
#             # NOTE: For password_reset, you may want to allow the lookup even if not verified,
#             # if they are verified by OTP later. Sticking to the original logic here.
#             user = User.objects.get(Q(phone_number = phone_number), Q(is_verified = True))
#
#     except User.DoesNotExist:
#         return Response({'error': 'No active user found with this phone number.'}, status=status.HTTP_404_NOT_FOUND)
#
#     # Otp.generate_new_code will delete existing unused codes and create a new one.
#     otp_entry = Otp.generate_new_code(
#         user, phone_number, token_type
#     )
#
#     send_sms(otp_entry)
#
#     if token_type == Otp.TOKEN_TYPE_REGISTRATION:
#         message = 'OTP for account activation sent.'
#
#     elif token_type == Otp.TOKEN_TYPE_PASSWORD_RESET:
#         message = 'OTP for password reset sent.'
#
#     else:
#         message = 'Login OTP sent.'
#
#     return Response({'message': message}, status=status.HTTP_200_OK)
#
#
# def verify_otp(phone_number: str, code: str, token_type: str):
#     """
#     Verifies OTP for the given phone number using the stored code, expiry, and usage status.
#
#     Args:
#         phone_number (str): The phone number associated with the OTP.
#         code (str): The OTP code to verify.
#         token_type (str): The current token_type being validated.
#
#     Returns:
#         Response: DRF Response object indicating success or failure.
#     """
#
#     try:
#         # Find the most recently created, unused OTP matching phone and type
#         otp_entry = Otp.objects.filter(
#             phone_number=phone_number,
#             token_type=token_type,
#             is_used=False
#         ).latest('created_at')
#
#     except Otp.DoesNotExist:
#
#         return Response({'error': 'Invalid or expired OTP code.'}, status=status.HTTP_400_BAD_REQUEST)
#
#     if otp_entry.code != code:
#         return Response({'error': 'Invalid or expired OTP code.'}, status=status.HTTP_400_BAD_REQUEST)
#
#     if otp_entry.expires_at < timezone.now():
#         otp_entry.is_used = True
#         otp_entry.save()
#         return Response({'error': 'Invalid or expired OTP code.'}, status=status.HTTP_400_BAD_REQUEST)
#
#     user = otp_entry.user
#
#     if token_type == Otp.TOKEN_TYPE_REGISTRATION:
#         user.is_verified = True
#         user.save()
#         message = 'Account activated successfully.'
#
#     elif token_type == Otp.TOKEN_TYPE_PASSWORD_RESET:
#         message = 'OTP verified. Proceed to password change.'
#
#     else:
#         message = 'Login OTP verified.'
#
#     otp_entry.is_used = True
#     otp_entry.save()
#
#     return Response({'message' : message}, status = status.HTTP_200_OK)
