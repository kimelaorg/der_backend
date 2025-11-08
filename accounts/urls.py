from django.urls import path, include
from . import views as v
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'users', v.UserView) # Manages users/profiles (requires DjangoModelPermissions)

urlpatterns = [
    # User management (Retrieve, Update, Delete Profiles)
    path('', include(router.urls)),

    # Registration for both staff and customer
    path('register/', v.RegisterUserView.as_view(), name='register'),
    path('register/staff/', v.NewStaffView.as_view(), name='staff-register'),
    path('confirm-registration/', v.ConfirmRegistrationView.as_view(), name='confirm-registration'),

    # Login and 2FA
    path('login/', v.RequestLoginOTPView.as_view(), name='login'),
    path('login/verify-otp/', v.LoginWithOTPView.as_view(), name='verify-login-otp'),

    # Requesting OTP (Re-send functionality)
    path('request/password-reset-otp/', v.RequestPasswordResetOtpView.as_view(), name='request-password-reset-otp'),
    path('request/registration-otp/', v.RequestRegistrationOtpView.as_view(), name='request-registration-otp'),
    path('request/login-otp/', v.RequestLoginOtpView.as_view(), name='request-login-otp'),

    # Password Reset
    path('password-reset/confirm/', v.ConfirmPasswordResetView.as_view(), name='confirm-password-reset'),
]
