from django.db import models
from django.conf import settings
from django.utils import timezone

# Create your models here.


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='reviews')
    comment = models.TextField(verbose_name="Comment/Insight")
    rating = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default = timezone.now())

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'product')

    def __str__(self):
        return f'Review for {self.product.name} by {self.user.username}'
