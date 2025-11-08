from rest_framework import permissions
from django.contrib.auth import get_user_model
from functools import wraps

User = get_user_model()

# ----------------------------------------------------------------------
# 1. Base Class: Checks if the User has a specific permission slug
# ----------------------------------------------------------------------

class HasPermission(permissions.BasePermission):
    """
    Base class for required permission checks.
    The permission slug must be set on the class by the factory method.
    """
    required_permission_slug = None

    def has_permission(self, request, view):
        # 1. Ensure a slug is set
        if not self.required_permission_slug:
            return False

        user = request.user

        # 2. Check Authentication
        if not user.is_authenticated:
            return False

        # 3. Superuser bypass (if applicable)
        if user.is_superuser:
            return True

        # 4. Actual RBAC Check (IMPLEMENTATION REQUIRED)
        # --- PLACEHOLDER LOGIC ---
        # You MUST replace this line with your actual database lookup logic
        # that checks if the user's assigned roles grant this specific slug.
        # Example: return user.has_permission(self.required_permission_slug)

        # Temporary fallback: Check staff status if no permission logic exists yet
        if user.is_staff:
            return True

        return False


# ----------------------------------------------------------------------
# 2. Factory Function (The new, recommended way)
# ----------------------------------------------------------------------

def get_configured_permission_class(permission_slug: str):
    """
    Factory function that dynamically generates a concrete permission class
    for a given slug. This is the correct method for DRF-Spectacular.
    """
    # Create a new type (class) inheriting from HasPermission
    # Naming convention helps in debugging (e.g., 'HasPerm_inventory_view')
    return type(f'HasPerm_{permission_slug.replace(":", "_").replace("-", "_")}',
                (HasPermission,),
                {'required_permission_slug': permission_slug})


# ----------------------------------------------------------------------
# 3. Backward Compatibility Layer (Fixes the ImportError)
# ----------------------------------------------------------------------

@wraps(get_configured_permission_class)
def required_permission(permission_slug: str):
    """
    DEPRECATED: Use get_configured_permission_class(slug) instead.

    This function is maintained to fix the ImportError in existing code
    by providing a name that returns the dynamically configured permission class.

    It returns a class, not an instance, making it compatible with
    DRF's 'permission_classes' attribute.
    """
    return get_configured_permission_class(permission_slug)


# ----------------------------------------------------------------------
# 4. Utility Class (Checks for staff status)
# ----------------------------------------------------------------------

class IsStaffUser(permissions.BasePermission):
    """
    Allows access only to authenticated staff users.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff
