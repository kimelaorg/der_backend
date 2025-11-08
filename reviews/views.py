from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, permissions, serializers
from products.models import Product
from .models import Review
from .serializers import ReviewSerializer

# Create your views here.


class ReviewViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'post']
    serializer_class = ReviewSerializer

    def get_permissions(self):
        # Allow everyone to view (GET), only authenticated users to create (POST)
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        # Filter reviews for the product specified in the URL
        product_pk = self.kwargs.get('product_pk')
        return Review.objects.filter(product=product_pk)

    def perform_create(self, serializer):
        product_pk = self.kwargs.get('product_pk')
        product = get_object_or_404(Product, pk=product_pk)

        # Ensure user hasn't reviewed this product already
        if Review.objects.filter(product=product, user=self.request.user).exists():
            raise serializers.ValidationError({"detail": "You have already reviewed this product."})

        serializer.save(user=self.request.user, product=product)
