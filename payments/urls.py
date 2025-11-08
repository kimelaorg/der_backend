from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ControlNumberGenerationView, PaymentWebhookView, PaymentStatusViewSet

router = DefaultRouter()
router.register(r'status', PaymentStatusViewSet, basename='payment-status')

urlpatterns = [
    # 1. Authenticated endpoint to request a new Control Number
    path('generate-control-number/', ControlNumberGenerationView.as_view(), name='generate-control-number'),

    # 2. CRITICAL: Unauthenticated Webhook endpoint for the payment gateway
    # This must be a clean, unique path known only to the gateway.
    path('webhook/v1/confirmation/', PaymentWebhookView.as_view(), name='payment-webhook'),

    # 3. ViewSet for checking payment status
    path('', include(router.urls)),
]
