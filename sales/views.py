from django.shortcuts import render
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny # Added standard DRF permissions
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Order, WishList, ShoppingCart, ShoppingCartItem, Promotion
from .serializers import (
    SalesOrderSerializer,
    CustomerDetailSerializer,
    WishListSerializer,
    ShoppingCartSerializer,
    PromotionSerializer,
    CartItemWriteSerializer,
    CartItemReadSerializer,
)


# Create your views here.

User = get_user_model()

# --- Customer and Staff Tools ---

class CustomerLookupView(generics.GenericAPIView):
    """
    Staff endpoint to lookup customer details by phone number.
    Only authenticated users (staff) should access this.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerDetailSerializer # Assumes this serializes the User model

    def get(self, request, *args, **kwargs):
        phone_number = request.query_params.get('phone_number')

        if not phone_number:
            return Response({"detail": "Phone number query parameter is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            # Find the User by phone number.
            user = User.objects.get(phone_number=phone_number)

            # CustomerSerializer should be defined to serialize the User object directly
            return Response(CustomerSerializer(user).data, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({"detail": f"No user found with phone number: {phone_number}"},
                            status=status.HTTP_404_NOT_FOUND)


# --- Order ViewSets ---

class OrderBaseViewSet(viewsets.ModelViewSet):
    """Base class for shared order retrieval logic, handling common prefetching."""
    queryset = Order.objects.select_related(
        'customer', 'shipping_method', 'shipping_address'
    ).prefetch_related(
        'physical_items__product__product', # Prefetching deep relations for physical items
        'digital_items__product'           # Prefetching digital products
    ).all()

    def get_serializer_class(self):
        # Default to read-only serializer for safety
        if self.action in ['list', 'retrieve']:
            return BaseOrderSerializer
        return SalesOrderSerializer


class OrderViewSet(OrderBaseViewSet):
    """Customer-facing order creation and retrieval endpoint (self-service)."""
    permission_classes = [IsAuthenticated] # Customers must be logged in

    def get_queryset(self):
        """Filters orders to only show those belonging to the authenticated user."""
        if self.request.user.is_authenticated:
            return self.queryset.filter(customer=self.request.user)
        return self.queryset.none()

    def get_serializer_class(self):
        """Uses SalesOrderSerializer for create and BaseOrderSerializer for read."""
        if self.action in ['list', 'retrieve']:
            return BaseOrderSerializer
        return SalesOrderSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Places a new order using the authenticated user as the customer."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # The serializer handles setting the 'customer=request.user'
        order = serializer.save()

        # Return the created order using the read serializer
        return Response(BaseOrderSerializer(order).data, status=status.HTTP_201_CREATED)


class StaffSalesViewSet(OrderBaseViewSet):
    """Staff-facing order creation and management."""
    # Staff must be authenticated to manage all orders
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Uses StaffOrderSerializer for create/update and BaseOrderSerializer for read."""
        if self.action in ['list', 'retrieve', 'update', 'partial_update']:
            return BaseOrderSerializer
        return StaffOrderSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Creates an order on behalf of a customer, setting the requesting user as staff_creator.
        """
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # Explicitly set the staff_creator to the authenticated staff user
        order = serializer.save(staff_creator=request.user)

        return Response(BaseOrderSerializer(order).data, status=status.HTTP_201_CREATED)


# --- Utility/Management ViewSets ---

class WishListViewSet(viewsets.ModelViewSet):
    """Endpoints for managing a user's wishlist."""
    serializer_class = WishListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filters wishlist items to only show those belonging to the authenticated user."""
        return WishList.objects.filter(user=self.request.user).select_related('product__product')

    def perform_create(self, serializer):
        """Automatically sets the user to the authenticated user."""
        serializer.save(user=self.request.user)


class ShoppingCartViewSet(viewsets.GenericViewSet):
    """
    Endpoint for viewing the user's shopping cart.
    The primary cart object is managed via the item viewset's actions.
    """
    serializer_class = ShoppingCartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Returns the authenticated user's cart."""
        return ShoppingCart.objects.filter(user=self.request.user).prefetch_related('items')

    def list(self, request):
        """Retrieves the user's cart (list action used to represent the single user cart)."""
        cart = self.get_queryset().first()
        if not cart:
            return Response({"detail": "Shopping cart not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(cart)
        return Response(serializer.data)


class ShoppingCartItemViewSet(viewsets.ModelViewSet):
    """
    Nested endpoint for managing individual items within a shopping cart.
    Handles add (create), update quantity (update/partial_update), and remove (destroy).
    """
    serializer_class = CartItemWriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filters items based on the authenticated user's cart."""
        try:
            cart = ShoppingCart.objects.get(user=self.request.user)
            # Use the read serializer for list/retrieve actions
            if self.action in ['list', 'retrieve']:
                self.serializer_class = CartItemReadSerializer
            return ShoppingCartItem.objects.filter(cart=cart).select_related('product_variant')
        except ShoppingCart.DoesNotExist:
            return ShoppingCartItem.objects.none()

    @transaction.atomic
    def perform_create(self, serializer):
        """Finds or creates the cart and adds the item, updating quantity if item exists."""
        cart, _ = ShoppingCart.objects.get_or_create(user=self.request.user)

        product_variant = serializer.validated_data.get('product_variant')
        quantity = serializer.validated_data.get('quantity')

        try:
            cart_item = ShoppingCartItem.objects.get(cart=cart, product_variant=product_variant)
            cart_item.quantity += quantity
            cart_item.save()
            serializer.instance = cart_item
        except ShoppingCartItem.DoesNotExist:
            serializer.save(cart=cart)


class PromotionViewSet(viewsets.ReadOnlyModelViewSet):
    """Publicly viewable list of active promotions."""
    serializer_class = PromotionSerializer
    permission_classes = [AllowAny] # Promotions are generally public

    def get_queryset(self):
        """Only show active promotions that haven't expired."""
        now = timezone.now()
        return Promotion.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).prefetch_related('target_categories')
