from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InventoryManagementViewSet


# instantiate a router and register the main ViewSet
router = DefaultRouter()
router.register(r'management', InventoryManagementViewSet, basename='inventory-management')

urlpatterns = [
    # General inventory status and management endpoints
    path('', include(router.urls)),

]
