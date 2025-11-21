from django.shortcuts import render
from rest_framework import viewsets, permissions, generics
from .models import Expense, Category, Payee
from .serializers import ExpenseDetailSerializer, CategorySerializer, PayeeSerializer

# Create your views here.
class IsAuthenticatedForCreateOnly(permissions.BasePermission):
    """
    Custom permission to allow read-only access (GET, HEAD, OPTIONS)
    to all users, but require authentication for write access (POST).
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user and request.user.is_authenticated


class CategoryView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedForCreateOnly]
    serializer_class = CategorySerializer
    queryset = Category.objects.all()


class PayeeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedForCreateOnly]
    serializer_class = PayeeSerializer
    queryset = Payee.objects.all()



class ExpenseViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for managing Expense records.

    - Requires authentication for all actions.
    - Admins see all expenses.
    - Non-admin users only see their own expenses.
    - Automatically assigns the logged-in user to the 'user' field on creation.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ExpenseDetailSerializer
    queryset = Expense.objects.all()

    def get_queryset(self):
        """Filters expenses based on user role."""
        user = self.request.user

        # Admin users see all expenses
        # if user.is_superuser or user.is_staff:
        if user.is_superuser:
            return Expense.objects.all().order_by('-expense_date')

        return Expense.objects.filter(user=user).order_by('-expense_date')

    def create(self, request, *args, **kwargs):
        """Sets the 'user' field to the currently logged-in user before saving."""
        serializer = self.get_serializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        serializer.save(user=self.request.user)
