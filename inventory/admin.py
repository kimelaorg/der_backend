from django.contrib import admin
from .models import WarehouseLocation, Inventory, StockMovement


# Register your models here.
admin.site.register(WarehouseLocation)
admin.site.register(Inventory)
admin.site.register(StockMovement)
