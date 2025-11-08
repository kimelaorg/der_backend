from django.contrib import admin
from .models import (
    Brand, ProductCategory, Supplier, PaymentMethod, ShippingMethod,
    SupportedInternetService, SupportedResolution, ScreenSize, PanelType,
    Connectivity, LicenceType, SoftwareFulfillmentMethod,
    Region, District, Ward, Street
)

# Register your models here.
admin.site.register(Brand)
admin.site.register(ProductCategory)
admin.site.register(Supplier)
admin.site.register(SupportedInternetService)
admin.site.register(SupportedResolution)
admin.site.register(ScreenSize)
admin.site.register(PanelType)
admin.site.register(Connectivity)
