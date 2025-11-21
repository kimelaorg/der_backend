from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExpenseViewSet, CategoryView, PayeeViewSet


router = DefaultRouter()

router.register(r'categories', CategoryView, basename='category')
router.register(r'payees', PayeeViewSet, basename='payee')
router.register(r'data', ExpenseViewSet, basename='expense')

urlpatterns = [
    path('', include(router.urls)),
]
