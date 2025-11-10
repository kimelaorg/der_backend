from rest_framework import status, viewsets, generics, permissions
from rest_framework.response import Response
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.models import Group
from .models import Otp
from .logics import verify_otp, generate_new_otp
from .permissions import HasRegisterStaffPermission
from django.db.models import Q
from notifications.sms import send_sms, sms_to_staff
from .serializers import (
    RegistrationSerializer, ConfirmRegistrationSerializer, LoginRequestOTPSerializer,
    LoginConfirmOTPSerializer, UserTokenObtainPairSerializer, RequestOTPSerializer,
    NewStaffSerializer, ConfirmPasswordResetSerializer, UserSerializer
    )


User = get_user_model()


# --- REGISTRATION FLOW VIEWS ---
class RegisterUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data = request.data)
        if serializer.is_valid(raise_exception = True):
            user = serializer.save()

            customer_group, created = Group.objects.filter(Q(name='Customer'),).get_or_create(name='Customer')
            user.groups.add(customer_group)

            message = 'Registration success. OTP sent for verification.'
        return Response({'message' : message}, status = status.HTTP_200_OK)


class ConfirmRegistrationView(generics.GenericAPIView):
    serializer_class = ConfirmRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['OTP']
        token_type = Otp.TOKEN_TYPE_REGISTRATION

        return verify_otp(phone_number, code, token_type)


# --- LOGIN FLOW VIEWS ---
class RequestLoginOTPView(generics.GenericAPIView):
    # This view performs credential check AND sends the OTP
    serializer_class = LoginRequestOTPSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data = request.data)
        serializer.is_valid(raise_exception = True)

        # The user object is attached to validated_data in the serializer
        user = User.objects.get(phone_number=serializer.validated_data['phone_number'])

        otp_entry = Otp.generate_new_code(
            user, user.phone_number, Otp.TOKEN_TYPE_LOGIN
        )
        send_sms(otp_entry)

        return Response({'message': 'Login OTP sent.'}, status=status.HTTP_200_OK)


class LoginWithOTPView(generics.GenericAPIView):
    serializer_class = LoginConfirmOTPSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['OTP']

        # Assumption: verify_otp returns a success response if valid
        otp_response = verify_otp(phone_number, code, Otp.TOKEN_TYPE_LOGIN)

        if otp_response.status_code == status.HTTP_200_OK:
            try:
                user = User.objects.get(Q(phone_number=phone_number))
            except User.DoesNotExist:
                return Response({'error': 'No active account found with the given credentials.'}, status=status.HTTP_404_NOT_FOUND)

            # Generate tokens using the custom serializer
            custom_token_serializer = UserTokenObtainPairSerializer(data={
                'phone_number': phone_number,

            })

            # The previous login step already authenticated, so we just generate the tokens.
            refresh_token = custom_token_serializer.get_token(user)
            access_token = refresh_token.access_token
            user_data_encoded = custom_token_serializer.get_user_data(user)

            context = {
                'refresh': str(refresh_token),
                'access': str(access_token),
                'user_data': user_data_encoded,
            }
            return Response(context, status=status.HTTP_200_OK)

        return otp_response


# --- GENERIC OTP REQUEST VIEWS ---
class RequestOTPView(generics.GenericAPIView):
    """Generic base class for requesting various OTP types."""
    serializer_class = RequestOTPSerializer
    token_type = None

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']

        if self.token_type:
            return generate_new_otp(phone_number, self.token_type)
        return Response({'error': 'Token type not specified.'}, status=status.HTTP_400_BAD_REQUEST)


class RequestRegistrationOtpView(RequestOTPView):
    permission_classes = [permissions.AllowAny]
    token_type = Otp.TOKEN_TYPE_REGISTRATION


class RequestLoginOtpView(RequestOTPView):
    permission_classes = [permissions.AllowAny]
    token_type = Otp.TOKEN_TYPE_LOGIN


class RequestPasswordResetOtpView(RequestOTPView):
    # This should probably be AllowAny since user is locked out
    permission_classes = [permissions.AllowAny]
    token_type = Otp.TOKEN_TYPE_PASSWORD_RESET


# --- PASSWORD RESET FLOW VIEW ---
class ConfirmPasswordResetView(generics.GenericAPIView):
    serializer_class = ConfirmPasswordResetSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']
        new_password = serializer.validated_data['new_password']

        # Step 1: Verify OTP
        otp_response = verify_otp(phone_number, code, Otp.TOKEN_TYPE_PASSWORD_RESET)

        # Step 2: If OTP is valid, proceed to reset password
        if otp_response.status_code == status.HTTP_200_OK:
            try:
                user = User.objects.get(phone_number=phone_number)
                user.set_password(new_password)
                user.is_default_password = False
                user.save()
                return Response({'message': 'Password reset successful.'}, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        return otp_response


# --- STAFF MANAGEMENT VIEWS ---
class NewStaffView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = NewStaffSerializer
    # Apply custom permission check for staff registration
    permission_classes = [permissions.IsAuthenticated, HasRegisterStaffPermission]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data = request.data)
        if serializer.is_valid(raise_exception = True):
            serializer.save()
        context = {
            'user' : serializer.data,
            "message" : 'Staff registered successfully with temporary password sent via SMS.'
        }
        return Response(context, status = status.HTTP_200_OK)


class UserView(viewsets.ModelViewSet):
    """
    ViewSet for Admin/Staff to manage other users or for users to manage their own profile.
    Uses DjangoModelPermissions for granular control over view/change/delete actions.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # Use DjangoModelPermissions which maps HTTP methods to built-in permissions
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

    def get_queryset(self):
        # Customers can only see their own profile
        if not self.request.user.is_staff:
            return User.objects.filter(id=self.request.user.id)
        # Staff can see all users
        return User.objects.all()
