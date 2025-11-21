from django.db import models
from django.conf import settings
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
from accounts.models import Address


class Category(models.Model):
    category_name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Category Name'
    )

    category_description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Description'
    )

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['category_name']

    def __str__(self):
        return self.category_name


class Payee(models.Model):
    payee_name = models.CharField(
        max_length=150,
        unique=True,
        verbose_name='Payee Name'
    )

    phone_number = PhoneNumberField(region = 'TZ', db_index = True)

    address = models.ForeignKey(Address, on_delete = models.SET_NULL, null = True)

    class Meta:
        verbose_name_plural = "Payees"
        ordering = ['payee_name']

    def __str__(self):
        return self.payee_name



class Expense(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='User'
    )

    expense_date = models.DateField(
        default=timezone.now,
        verbose_name='Date'
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Amount Spent'
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        verbose_name='Category'
    )

    payee = models.ForeignKey(
        Payee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Paid To'
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Details/Notes'
    )

    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('Credit Card', 'Credit Card'),
        ('Debit Card', 'Debit Card'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Online Wallet', 'Online Wallet'),
        ('Mobile Money', 'Mobile Money'),
    ]

    payment_method = models.CharField(
        max_length=50,
        choices=PAYMENT_METHOD_CHOICES,
        default='Cash',
        verbose_name='Payment Method'
    )

    class Meta:
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
        ordering = ['-expense_date', '-id']

    def __str__(self):
        return f"{self.expense_date.strftime('%Y-%m-%d')} - ${self.amount} ({self.category.category_name})"
