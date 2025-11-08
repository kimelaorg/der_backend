from rest_framework import serializers
from .models import Role, Permission, UserRole, RolePermission
from django.contrib.auth import get_user_model
from django.db.models import F

User = get_user_model()

# --- Permission Serializers ---

class PermissionSerializer(serializers.ModelSerializer):
    """Serializer for Permission model (used in Role detail)."""
    class Meta:
        model = Permission
        fields = ('id', 'code_name', 'display_name', 'module')
        read_only_fields = ('id',)

# --- Role Serializers ---

class RoleSerializer(serializers.ModelSerializer):
    """Serializer for listing and creating Roles."""
    class Meta:
        model = Role
        fields = ('id', 'name', 'description', 'is_staff_role', 'created_at')
        read_only_fields = ('id', 'created_at')


class RoleDetailSerializer(serializers.ModelSerializer):
    """Serializer for retrieving and updating a single Role, including its Permissions."""
    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Role
        fields = ('id', 'name', 'description', 'is_staff_role', 'permissions', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at', 'permissions') # Permissions are managed via a dedicated view




# --- User Role Assignment Serializers ---
class UserRoleSerializer(serializers.ModelSerializer):
    """Serializer for assigning Roles to a User."""

    # Read-only fields for context
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)

    class Meta:
        model = UserRole
        fields = ('id', 'user', 'role', 'user_phone', 'role_name')
        read_only_fields = ('id', 'user_phone', 'role_name')

    def validate(self, data):
        """Custom validation to ensure the user and role exist."""
        user_id = data.get('user')
        role_id = data.get('role')

        # Check if user exists (already handled by default model validation, but good practice)
        if not User.objects.filter(id = user_id.pk).exists():
             raise serializers.ValidationError({"user": "User not found."})

        # Check if role exists (already handled by default model validation, but good practice)
        if not Role.objects.filter(pk = role_id.pk).exists():
             raise serializers.ValidationError({"role": "Role not found."})

        # Check for unique_together constraint violation (handled implicitly, but explicit check for better error message)
        if self.instance is None and UserRole.objects.filter(user=user_id, role=role_id).exists():
            raise serializers.ValidationError("This role is already assigned to this user.")

        return data


# --- Role Permission Assignment Serializers ---
class RolePermissionSerializer(serializers.ModelSerializer):
    """Serializer for linking Permissions to Roles."""

    role_name = serializers.CharField(source='role.name', read_only=True)
    permission_code_name = serializers.CharField(source='permission.code_name', read_only=True)

    class Meta:
        model = RolePermission
        fields = ('id', 'role', 'permission', 'role_name', 'permission_code_name')
        read_only_fields = ('id', 'role_name', 'permission_code_name')

    def validate(self, data):
        """Custom validation to ensure role and permission exist and the link is unique."""
        role = data.get('role')
        permission = data.get('permission')

        if not Role.objects.filter(pk=role.pk).exists():
            raise serializers.ValidationError({"role": "Role not found."})

        if not Permission.objects.filter(pk=permission.pk).exists():
            raise serializers.ValidationError({"permission": "Permission not found."})

        # Check for unique_together constraint violation
        if self.instance is None and RolePermission.objects.filter(role=role, permission=permission).exists():
            raise serializers.ValidationError("This permission is already assigned to this role.")

        return data


class UserPermissionsSerializer(serializers.Serializer):
    """
    Serializer for the dedicated RBAC endpoint (GET /api/rbac/user-roles/user/).
    It computes the final list of permissions needed by the Angular frontend.
    """
    # These fields are read from the context or the user object directly
    user_phone = serializers.CharField(source='phone_number') # Assumes User model has phone_number
    user_id = serializers.UUIDField(source='id')

    # Nest the RoleSerializer to include role details
    roles = RoleSerializer(many=True, read_only=True)

    # CRITICAL FIELD: Computes the flattened list of permission codes
    permissions = serializers.SerializerMethodField()

    class Meta:
        # Note: This is a base Serializer, not a ModelSerializer, so no 'model' attribute
        fields = ('user_phone', 'user_id', 'roles', 'permissions')

    def get_permissions(self, user: User) -> list[str]:
        """
        Fetches all unique permission code_names associated with all roles assigned to the user.
        """
        # Fetch the IDs of all roles assigned to this user
        user_role_ids = UserRole.objects.filter(user=user).values_list('role_id', flat=True)

        # Fetch all unique permission code_names linked to those roles
        permission_codes = RolePermission.objects.filter(
            role_id__in=user_role_ids
        ).values_list(
            'permission__code_name', flat=True
        ).distinct()

        return list(permission_codes)
