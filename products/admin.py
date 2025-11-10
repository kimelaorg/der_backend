from django.contrib import admin
from .models import (
    Product, ProductSpecification, ProductImage, ProductVideo, ProductConnectivity,
    ElectricalSpecification, DigitalProduct
    )


# Register your models here.
admin.site.register(ProductSpecification)
