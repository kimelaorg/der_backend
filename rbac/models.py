from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils import timezone

# Create your models here.

class Role(models.Model):
    """
    Defines an organizational role (e.g., Admin, Manager, Sales Rep).
    A user can belong to one or more roles.
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    # Flag to easily identify if a role is meant for staff/internal users
    is_staff_role = models.BooleanField(default=True)

    created_at = models.DateTimeField(default = timezone.now())
    updated_at = models.DateTimeField(auto_now = True)

    class Meta:
        verbose_name = _("Role")
        verbose_name_plural = _("Roles")
        ordering = ('name',)

    def customize_role(self):
        if self.name:
            role = self.name
        return role.lower()

    def save(self, *arg, **kwargs):
        if self.name:
            self.name = self.customize_role()
        super().save(*arg, **kwargs)

    def __str__(self):
        return self.name


# --- 2. Permission Model ---
class Permission(models.Model):
    """
    Defines a granular permission (e.g., can_view_invoices, can_edit_products).
    Permissions are assigned to Roles.
    """
    code_name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100)
    module = models.CharField(max_length=50) # e.g., 'invoicing', 'inventory', 'customers'

    created_at = models.DateTimeField(default = timezone.now())
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Permission")
        verbose_name_plural = _("Permissions")
        ordering = ('module', 'display_name')

    def __str__(self):
        return f"{self.module}: {self.display_name} ({self.code_name})"


# --- 3. Linking Table: Role <-> Permission ---
class RolePermission(models.Model):
    """
    Links Roles to Permissions (Many-to-Many relationship).
    """
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Role Permission")
        verbose_name_plural = _("Role Permissions")
        unique_together = ('role', 'permission')

    def __str__(self):
        return f"{self.role.name} -> {self.permission.code_name}"

# --- 4. Linking Table: User <-> Role ---
class UserRole(models.Model):
    """
    Links Users to Roles (Many-to-Many relationship, allowing multiple roles per user).
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("User Role")
        verbose_name_plural = _("User Roles")
        unique_together = ('user', 'role')

    def __str__(self):
        return f"{self.user.phone} is a {self.role.name}"
