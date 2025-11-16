from django.contrib import admin
from .models import PurchaseOrder, PurchaseOrderItem, StockReception

# Register your models here.
admin.site.register(PurchaseOrder)
admin.site.register(PurchaseOrderItem)
admin.site.register(StockReception)
