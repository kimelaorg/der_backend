from rest_framework import permissions

class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow staff users to perform write operations
    (POST, PUT, PATCH, DELETE), but allow anyone to read (GET, HEAD, OPTIONS).
    This is ideal for administrative data like Promotions.
    """
    def has_permission(self, request, view):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to staff users
        return request.user and request.user.is_staff


class IsOwnerOrStaff(permissions.BasePermission):
    """
    Custom permission to ensure an object can only be viewed, edited, or deleted
    by its owner (the user or customer associated with the object) or by a staff member.
    """
    def has_permission(self, request, view):
        # All authenticated users can at least create or list (which will be filtered
        # in the view to show only their own items).
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Staff members always have full access
        if request.user and request.user.is_staff:
            return True

        # Check for 'user' attribute (e.g., WishList, ShoppingCart)
        if hasattr(obj, 'user'):
            return obj.user == request.user

        # Check for 'customer' attribute (e.g., Order)
        elif hasattr(obj, 'customer'):
            return obj.customer == request.user

        # Default to deny if the object doesn't have a recognizable owner field
        return False


class IsSalesStaffOrAdmin(permissions.BasePermission):
    """
    Custom permission that implements the required policy:
    1. Admin/Staff: Full access (create, list, retrieve all).
    2. Sales Staff (Authenticated, but not admin/staff): Can CREATE and
       can LIST/RETRIEVE only their own sales (filtering handled by get_queryset).
    """

    def has_permission(self, request, view):
        # Must be authenticated to interact with this ViewSet
        if not request.user.is_authenticated:
            return False

        # Admins and Staff get full permission immediately
        if request.user.is_superuser or request.user.is_staff:
            return True

        # Non-admin/non-staff users are allowed to perform only
        # create (POST), list (GET), and retrieve (GET detail).
        if view.action in ['create', 'list', 'retrieve']:
             return True

        # Deny all other actions (update, destroy, etc.)
        return False
