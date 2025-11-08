from rest_framework import serializers
from .models import Review

class ReviewSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'user_username', 'rating', 'comment', 'created_at']
        read_only_fields = ['user', 'product', 'created_at']
