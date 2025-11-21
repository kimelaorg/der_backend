from django.contrib import admin
from .models import Category, Payee, Expense


# Register your models here.
admin.site.register(Category)
admin.site.register(Payee)
admin.site.register(Expense)
