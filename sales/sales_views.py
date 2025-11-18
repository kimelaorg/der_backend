from rest_framework.response import Response
from rest_framework import viewsets, status, mixins, generics
from django.contrib.auth.models import Group
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .permissions import IsSalesStaffOrAdmin
from .sales_models import Sale
from .sales_serializers import SaleTransactionSerializer, SaleDetailSerializer, CustomerSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomerGenericView(generics.CreateAPIView):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data.get('phone_number')

        try:
            customer_instance = User.objects.get(phone_number=phone_number)
            created = False

            response_serializer = CustomerSerializer(customer_instance)

            # print(f"Customer retrieved: ID {customer_instance.id}")

        except User.DoesNotExist:
            created = True

            customer_instance = serializer.save()

            try:
                customer_group, created = Group.objects.filter(Q(name='Customer'),).get_or_create(name='Customer')
                customer_instance.groups.add(customer_group)
                # print(f"New Customer ID {customer_instance.id} assigned to group 'Customer'")
            except Group.DoesNotExist:
                print("WARNING: 'Customer' group does not exist.")

            response_serializer = CustomerSerializer(customer_instance)

            # print(f"New Customer created: ID {customer_instance.id}")

        headers = self.get_success_headers(response_serializer.data)

        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK

        return Response(response_serializer.data, status=status_code, headers=headers)



class SalesViewSet(
    mixins.ListModelMixin,         # Enables GET /sales/
    mixins.RetrieveModelMixin,      # Enables GET /sales/{id}/
    viewsets.GenericViewSet         # Provides base functionality
):
    """
    ViewSet for managing Sale transactions, incorporating the RBAC policy.

    Uses SaleTransactionSerializer (write/input for create)
    and SaleDetailSerializer (read/output for list/retrieve).
    """

    permission_classes = [IsSalesStaffOrAdmin]

    # This must be the primary serializer for DRF's default behavior,
    # but we override which one is used in get_serializer_class().
    serializer_class = SaleTransactionSerializer

    # You must define a base queryset for the mixins to work.
    # queryset = Sale.objects.all() # Uncomment and ensure Sale model is imported

    def get_queryset(self):
        """
        Filters the queryset based on user role to meet the viewing requirements.
        - Admin/Staff sees all sales.
        - Regular Sales Staff only sees sales where they are the 'sales_agent'.
        """
        # Assuming the base queryset is defined on the class level (Sale.objects.all())
        # If not defined, you must define the queryset explicitly here:
        # qs = Sale.objects.all().select_related(...)
        qs = super().get_queryset()

        user = self.request.user

        # Admin/Staff users see everything
        if user.is_superuser or user.is_staff:
            return qs

        # Regular authenticated users see only their own sales
        # This assumes the Sale model has a ForeignKey called 'sales_agent' pointing to the User model.
        return qs.filter(sales_agent=user)


    def get_serializer_class(self):
        """
        Swaps the serializer based on the action being performed.
        """
        # Use the transactional/write serializer for input
        if self.action == 'create':
            return SaleTransactionSerializer

        # Use the detail/read serializer for output
        return SaleDetailSerializer


    def create(self, request, *args, **kwargs):
        """Handles the POST request to record a new sale transaction."""

        # 1. Get the write serializer (SaleTransactionSerializer) using the correct method
        write_serializer = self.get_serializer(data=request.data)

        # Validation (includes stock checks and total amount calculation)
        write_serializer.is_valid(raise_exception=True)

        # The .save() method contains the atomic transaction logic
        sale_instance = write_serializer.save()

        # 2. Return the created sale data using the read serializer (SaleDetailSerializer)
        # We explicitly call SaleDetailSerializer here to get the correct output format.
        # NOTE: This line requires SaleDetailSerializer to be imported.
        read_serializer = SaleDetailSerializer(sale_instance)

        return Response(read_serializer.data, status=status.HTTP_201_CREATED)



# --- 2. Audit/Reporting ViewSet ---
class SaleAuditViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    """
    Provides staff access to view the list of all sales and retrieve specific
    sale details for audit and reporting purposes. (Read-Only)
    """
    # Restrict access to staff users
    permission_classes = [IsAuthenticated, IsAdminUser]

    # Pre-fetch related data for efficient retrieval (reduces N+1 queries)
    queryset = Sale.objects.all().select_related(
        'customer',
        'sales_outlet',
        'sales_agent'
    ).prefetch_related(
        'items',
        'items__product_specification',
        'items__product_specification__inventory' # If you want deep nested data
    )

    # Use the Detail serializer for both list and retrieve actions
    serializer_class = SaleDetailSerializer

    def get_queryset(self):
        # Optional: Add filtering (e.g., filter by date, sales_outlet, or agent)
        qs = super().get_queryset()

        # Example filter: Only show sales from the last 30 days
        # date_limit = timezone.now() - timedelta(days=30)
        # qs = qs.filter(sale_date__gte=date_limit)

        return qs
