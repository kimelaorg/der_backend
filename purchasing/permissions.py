from rest_framework import permissions

# Define group names (these must match the groups created in your Django Admin)
PURCHASING_GROUP = 'Purchasing'
WAREHOUSE_GROUP = 'Warehouse'

class IsPurchasingManager(permissions.BasePermission):
    """
    Custom permission to only allow Superusers or users in the 'Purchasing' group
    to create, update, or delete Purchase Orders. All authenticated staff can view.
    """
    def has_permission(self, request, view):
        # 1. Allow all authenticated staff users to read (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated and request.user.is_staff

        # 2. Only allow write methods (POST, PUT, PATCH, DELETE) for Purchasing Managers
        return (request.user.is_superuser or
                (request.user.is_staff and request.user.groups.filter(name=PURCHASING_GROUP).exists()))

class IsWarehouseStaff(permissions.BasePermission):
    """
    Custom permission to only allow Superusers or users in the 'Warehouse' group
    to create (record) Stock Receptions. All authenticated staff can view.
    """
    def has_permission(self, request, view):
        # 1. Allow all authenticated staff users to read (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated and request.user.is_staff

        # 2. Only allow POST (creation) for Warehouse Staff
        if view.action == 'create':
            return (request.user.is_superuser or
                    (request.user.is_staff and request.user.groups.filter(name=WAREHOUSE_GROUP).exists()))

        # 3. Deny all other write actions (PUT, PATCH, DELETE) on StockReception records
        return False
