from rest_framework import permissions


class HasRegisterStaffPermission(permissions.BasePermission):
    """
    Custom permission to check if the user has the specific accounts.can_register_staff permission.
    This is required for the NewStaffView.
    """
    message = 'Permission denied. You must be an authorized Admin with "can_register_staff" rights.'

    def has_permission(self, request, view):
        # 1. Must be authenticated
        if not request.user.is_authenticated:
            return False

        # 2. Must have the specific custom permission
        return request.user.has_perm('accounts.can_register_staff')
