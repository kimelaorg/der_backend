from django.shortcuts import render, get_object_or_404
from rest_framework import generics, status, viewsets, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from .models import Payment, LocalPaymentDetails
from .serializers import ControlNumberRequestSerializer, PaymentStatusSerializer
from sales.models import Order
from rbac.rbac_permissions import get_configured_permission_class

# Create your views here.

# --- Placeholder for External Gateway and Fulfillment Logic ---

def generate_control_number_external(order_id, amount, phone_number):
    """
    Simulates the call to the external local payment gateway (e.g., GePG, MNO API)
    to request a unique control number.
    In a real system, this would involve a POST request to the gateway.
    """
    # Placeholder: Generates a mock control number and sets a 7-day expiry
    mock_control_number = f"CN{timezone.now().strftime('%Y%m%d%H%M%S')}{order_id}"
    expiry_time = timezone.now() + timedelta(days=7) # Common expiry for control numbers

    # NOTE: In a real app, this would handle error states from the gateway
    return {
        'control_number': mock_control_number,
        'expiry_time': expiry_time,
        'success': True
    }

def fulfill_order(order: Order, transaction_id: str):
    """
    Triggers fulfillment logic across other apps upon successful payment.
    This is critical for atomicity of payment completion.
    """
    try:
        # 1. Update Sales Order status
        order.order_status = 'PAID'
        order.save(update_fields=['order_status'])

        # 2. Trigger Digital Licensing (sends keys/grants access)
        # This function would be implemented in the licensing_app
        # licensing_app.tasks.grant_digital_access.delay(order.id)

        # 3. Trigger Stock Movement Finalization (links pending movements to transaction ID)
        # This function would be implemented in the inventory_app
        # inventory_app.tasks.finalize_movements.delay(order.id, transaction_id)

        # 4. Trigger Notification (sends confirmation SMS/Email)
        # This function would be implemented in the notifications_app
        # notifications_app.tasks.send_payment_confirmation.delay(order.customer.user.phone, order.id)

        return True
    except Exception as e:
        # Log the fulfillment failure but return true for the webhook,
        # as the payment itself was successful. Requires manual follow-up.
        print(f"CRITICAL FULFILLMENT ERROR for Order {order.id}: {e}")
        return False

# --- API Views ---

class ControlNumberGenerationView(generics.CreateAPIView):
    """
    Endpoint for a customer to request a Control Number to pay for a PENDING order.
    A new Payment record is created.
    """
    serializer_class = ControlNumberRequestSerializer
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order_id = serializer.validated_data['order_id']

        try:
            order = Order.objects.select_for_update().get(id=order_id, order_status='PENDING')
        except Order.DoesNotExist:
            return Response({"detail": "Order not found or is already paid/cancelled."},
                            status=status.HTTP_404_NOT_FOUND)

        # 1. Create a Payment Attempt record
        payment = Payment.objects.create(
            order=order,
            amount_due=order.total_amount,
            payment_method="Local Gateway (Placeholder)", # Should come from settings_app
            status='PENDING'
        )

        # 2. Request Control Number from External Gateway
        # NOTE: Using phone number associated with the order's customer
        phone_number = order.customer.phone_number
        gateway_response = generate_control_number_external(order.id, order.total_amount, phone_number)

        if not gateway_response.get('success'):
            payment.status = 'FAILED'
            payment.save()
            return Response({"detail": "Failed to generate Control Number from gateway."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # 3. Store Local Payment Details
        local_details = LocalPaymentDetails.objects.create(
            payment=payment,
            control_number=gateway_response['control_number'],
            expiry_time=gateway_response['expiry_time'],
            # gateway_request_data=... (in real system)
            # gateway_response_data=... (in real system)
        )

        # 4. Update Payment status and notify customer
        payment.status = 'WAITING_PAYMENT'
        payment.save(update_fields=['status'])

        # Notification to customer (via notifications_app) with CN and expiry
        # notifications_app.tasks.send_cn_notification.delay(phone_number, local_details.control_number)

        response_data = PaymentStatusSerializer(payment).data
        return Response(response_data, status=status.HTTP_201_CREATED)


class PaymentWebhookView(views.APIView):
    """
    CRITICAL: Unauthenticated endpoint to receive payment confirmation from the local gateway.
    This must be robust, idempotent, and extremely fast.
    """
    permission_classes = [AllowAny] # No authentication for webhooks

    def post(self, request, *args, **kwargs):
        # NOTE: In a real system, we'd validate the request signature/IP to ensure authenticity

        # Placeholder for receiving data from a local gateway
        webhook_data = request.data
        cn = webhook_data.get('control_number')
        transaction_id = webhook_data.get('transaction_id')
        payment_amount = webhook_data.get('amount')

        if not cn or not transaction_id or not payment_amount:
            return Response({"detail": "Invalid webhook data structure."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # 1. Find the local payment details by the control number
                local_details = LocalPaymentDetails.objects.select_for_update().get(control_number=cn)
                payment = local_details.payment
                order = payment.order

                # 2. Idempotency and State Check
                if payment.status == 'SUCCESS':
                    # Already processed, return success to prevent duplicate action
                    return Response({"detail": "Payment already processed."},
                                     status=status.HTTP_200_OK)

                if local_details.is_expired():
                    # Should be handled by gateway, but good to check
                    payment.status = 'EXPIRED'
                    payment.save()
                    return Response({"detail": "Control number expired."},
                                     status=status.HTTP_400_BAD_REQUEST)

                # 3. Final Validation (Amount check)
                if float(payment_amount) != float(payment.amount_due):
                    # Payment amount mismatch. Manual investigation needed.
                    print(f"Payment amount mismatch for CN {cn}. Expected {payment.amount_due}, Got {payment_amount}")
                    # payment.status remains WAITING_PAYMENT or FAILED, but we acknowledge the webhook
                    return Response({"detail": "Amount mismatch acknowledged."},
                                     status=status.HTTP_200_OK)

                # 4. Success: Update Payment Record
                payment.status = 'SUCCESS'
                payment.transaction_id = transaction_id
                payment.updated_at = timezone.now()
                payment.save(update_fields=['status', 'transaction_id', 'updated_at'])

                # 5. Trigger Asynchronous Fulfillment (Non-blocking)
                fulfill_order(order, transaction_id)

                return Response({"detail": "Payment and fulfillment acknowledged."},
                                 status=status.HTTP_200_OK)

        except LocalPaymentDetails.DoesNotExist:
            return Response({"detail": "Control Number not found."},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Catch all unexpected errors and alert administrators
            print(f"Webhook processing error: {e}")
            return Response({"detail": "Internal Server Error during processing."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentStatusViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Allows customers to check the status of their payment attempt.
    """
    serializer_class = PaymentStatusSerializer
    permission_classes = [IsAuthenticated] # Base permissions
    # FIX: Explicitly define the base queryset for drf-spectacular to inspect the model type
    queryset = Payment.objects.all()

    def get_permissions(self):
        """
        Custom permission check based on the action, using the RBAC factory.
        """
        perms = super().get_permissions()
        required_slug = None

        # Staff users need permission to view all payments
        if self.request.user.is_staff:
            if self.action in ['list', 'retrieve']:
                required_slug = 'payments:view_all_payments' # Example staff permission

        # If a staff permission is required, use the factory to create and instantiate it
        if required_slug:
            # Create the specific Permission CLASS
            PermissionClass = get_configured_permission_class(required_slug)

            # Append the INSTANCE of that class
            perms.append(PermissionClass())

        return perms

    def get_queryset(self):
        # Filter payments to only those belonging to the logged-in customer's orders
        if self.request.user.is_staff:
            # Staff can see all payments (assuming they pass the RBAC check)
            return Payment.objects.all().select_related('order', 'local_details')

        # Assuming the customer is linked to a User via phone
        user_orders = SalesOrder.objects.filter(customer__user=self.request.user)
        return Payment.objects.filter(order__in=user_orders).select_related('order', 'local_details')
