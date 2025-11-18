from django.contrib import admin
from .models import WishList, OrderItemDigital, ShoppingCart, ShoppingCartItem, Promotion, PromotionCategory, Order, OrderItemPhysical
from .sales_models import Sale, SaleItem


# Register your models here.
admin.site.register(WishList)
admin.site.register(ShoppingCart)
admin.site.register(ShoppingCartItem)
admin.site.register(PromotionCategory)
admin.site.register(Order)
admin.site.register(OrderItemPhysical)
admin.site.register(OrderItemDigital)
admin.site.register(Sale)
admin.site.register(SaleItem)
