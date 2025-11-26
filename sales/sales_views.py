from rest_framework.response import Response
from rest_framework import viewsets, status, mixins, generics
from django.contrib.auth.models import Group
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .permissions import IsSalesStaffOrAdmin
from .sales_models import Sale, CustomerDetails
from accounts.models import UserProfile
from .sales_serializers import SaleTransactionSerializer, SaleDetailSerializer, CustomerSerializer
from django.contrib.auth import get_user_model


User = get_user_model()

class CustomerGenericView(generics.CreateAPIView):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    queryset = CustomerDetails.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status = status.HTTP_201_CREATED)



class SalesViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    """
    ViewSet for managing Sale transactions, incorporating the RBAC policy.

    Uses SaleTransactionSerializer (write/input for create)
    and SaleDetailSerializer (read/output for list/retrieve).
    """

    permission_classes = [IsAuthenticated]

    serializer_class = SaleTransactionSerializer

    queryset = Sale.objects.all()

    def get_queryset(self):
        """
        Filters the queryset based on user role to meet the viewing requirements.
        - Admin/Staff sees all sales.
        - Regular Sales Staff only sees sales where they are the 'sales_agent'.
        """
        qs = super().get_queryset()

        user = self.request.user

        if user.is_superuser or user.is_staff:
            return qs

        return qs.filter(sales_agent=user)


    def get_serializer_class(self):
        """
        Swaps the serializer based on the action being performed.
        """
        if self.action == 'create':
            return SaleTransactionSerializer

        return SaleDetailSerializer


    def create(self, request, *args, **kwargs):
        """Handles the POST request to record a new sale transaction."""
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        sale_instance = write_serializer.save()
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

    # def get_queryset(self):
    #     # Optional: Add filtering (e.g., filter by date, sales_outlet, or agent)
    #     qs = super().get_queryset()
    #
    #     # Example filter: Only show sales from the last 30 days
    #     # date_limit = timezone.now() - timedelta(days=30)
    #     # qs = qs.filter(sale_date__gte=date_limit)
    #
    #     return qs
