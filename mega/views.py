from django.shortcuts import render
from .serializers import MegaProductSerializer
from products.models import Product
from rest_framework import viewsets

# Create your views here.
class MegaProductViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for viewing and editing Product instances, including nested
    creation of ProductSpecification and related components.
    """
    queryset = Product.objects.all()
    serializer_class = MegaProductSerializer

    # You may want to restrict access to authenticated users
    # permission_classes = [IsAuthenticated]

    # Optional: Optimize retrieval by selecting related objects in one go
    def get_queryset(self):
        return Product.objects.select_related('category').prefetch_related(
            'product_specs',
            'product_specs__supported_internet_services',
            'product_specs__electrical_specs',
            'product_specs__productimage_set',
            'product_specs__productconnectivity_set',
            # Add other necessary prefetch/select related fields here
        ).all()
