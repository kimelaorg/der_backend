from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, mixins, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import Role, Permission, UserRole, RolePermission
from .serializers import (
    RoleSerializer, RoleDetailSerializer, PermissionSerializer,
    UserRoleSerializer, RolePermissionSerializer, UserPermissionsSerializer
)
# FIX: Corrected import path to use the actual file name 'rbac_permissions'
# Also, we now import the factory function get_configured_permission_class
from .rbac_permissions import IsStaffUser, get_configured_permission_class

# Define common base permissions for all views in this app
BASE_PERMISSIONS = [permissions.IsAuthenticated, IsStaffUser]

# --- Create argument-free PERMISSION CLASSES using the factory ---
# This resolves the DRF-Spectacular errors caused by passing arguments to classes
MANAGE_ROLES_PERM = get_configured_permission_class('rbac:manage_roles')
ASSIGN_ROLES_PERM = get_configured_permission_class('rbac:assign_user_roles')


User = get_user_model()

# --- Core Management ViewSets (Admin/High-Privilege Staff Only) ---

class RoleViewSet(viewsets.ModelViewSet):
    """
    Manages creation, retrieval, update, and deletion of Roles.
    Requires 'rbac:manage_roles' permission.
    """
    queryset = Role.objects.all().order_by('name')
    # Use the static CLASS here (MANAGE_ROLES_PERM), not a function call
    permission_classes = BASE_PERMISSIONS + [MANAGE_ROLES_PERM]

    def get_serializer_class(self):
        # Use detailed serializer for retrieve, simple for list/create
        if self.action in ['retrieve', 'update', 'partial_update']:
            return RoleDetailSerializer
        return RoleSerializer

    # Custom action to manage permissions attached to a specific role
    @action(detail=True, methods=['get', 'post', 'delete'], url_path='permissions',
            permission_classes=BASE_PERMISSIONS + [MANAGE_ROLES_PERM])
    def manage_permissions(self, request, pk=None):
        role = self.get_object()

        if request.method == 'GET':
            # List all permissions for this role
            role_permissions = RolePermission.objects.filter(role=role).select_related('permission')
            permissions = [rp.permission for rp in role_permissions]
            serializer = PermissionSerializer(permissions, many=True)
            return Response(serializer.data)

        permission_id = request.data.get('permission_id')
        if not permission_id:
            return Response({'detail': _('permission_id is required.')}, status=status.HTTP_400_BAD_REQUEST)

        permission = get_object_or_404(Permission, id=permission_id)

        if request.method == 'POST':
            # Assign a permission to the role
            if RolePermission.objects.filter(role=role, permission=permission).exists():
                return Response({'detail': _('Permission already assigned.')}, status=status.HTTP_409_CONFLICT)

            RolePermission.objects.create(role=role, permission=permission)
            return Response({'detail': _('Permission assigned successfully.')}, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            # Remove a permission from the role
            role_permission = get_object_or_404(RolePermission, role=role, permission=permission)
            role_permission.delete()
            return Response({'detail': _('Permission removed successfully.')}, status=status.HTTP_204_NO_CONTENT)

# --- Static Permission ViewSet (Read-Only) ---

class PermissionReadOnlyViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Provides a read-only list of all available permissions for reference.
    Requires 'rbac:manage_roles' permission to view the permission codes.
    """
    queryset = Permission.objects.all().order_by('module', 'code_name')
    serializer_class = PermissionSerializer
    # Use the static CLASS here (MANAGE_ROLES_PERM), not a function call
    permission_classes = BASE_PERMISSIONS + [MANAGE_ROLES_PERM]

# --- User Role Assignment ViewSet ---

class UserRoleViewSet(viewsets.GenericViewSet):
    """
    Handles the assignment and removal of Roles to/from Users.
    Requires 'rbac:assign_user_roles' permission.
    """
    # Use the static CLASS here (ASSIGN_ROLES_PERM), not a function call
    # permission_classes = BASE_PERMISSIONS + [ASSIGN_ROLES_PERM]
    serializer_class = UserRoleSerializer
    queryset = UserRole.objects.all()

    @action(detail=False, methods=['post'], url_path='assign',
            permission_classes=BASE_PERMISSIONS + [ASSIGN_ROLES_PERM])
    def assign_role(self, request):
        """Assigns a role to a user."""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='remove',
            permission_classes=BASE_PERMISSIONS + [ASSIGN_ROLES_PERM])
    def remove_role(self, request):
        """Removes a role assignment from a user."""
        user_id = request.data.get('user')
        role_id = request.data.get('role')

        if not user_id or not role_id:
            return Response({'detail': _('User ID and Role ID are required.')}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the assignment exists
        user_role = get_object_or_404(UserRole, user_id=user_id, role_id=role_id)

        # Delete the assignment
        user_role.delete()
        return Response({'detail': _('Role removed successfully.')}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='roles',
            permission_classes=BASE_PERMISSIONS + [ASSIGN_ROLES_PERM])
    def get_user_roles(self, request, pk=None):
        """Lists all roles assigned to a specific user by ID (pk)."""
        user = get_object_or_404(User, id=pk)
        roles = Role.objects.filter(userrole__user=user)
        serializer = RoleSerializer(roles, many=True)

        return Response({
            'user_phone': str(user.phone_number),
            'user_id': user.id,
            'roles': serializer.data
        })

    @action(detail=False, methods=['get'], url_path='user',
            # This should ONLY require standard authentication, not a specific RBAC permission
            # because every logged-in user needs their own permissions.
            # Assuming BASE_PERMISSIONS includes IsAuthenticated
            permission_classes=[*BASE_PERMISSIONS])
    def get_current_user_roles_and_permissions(self, request):
        """
        Provides the authenticated user's roles and a flattened list of all their permissions.
        This is the CRITICAL endpoint for the Angular RbacGuard (GET /api/rbac/user-roles/user/).
        """
        user = request.user

        # Check if user is authenticated (should be handled by permission_classes, but good check)
        if not user.is_authenticated:
            return Response({'detail': _('Authentication credentials were not provided.')},
                            status=status.HTTP_401_UNAUTHORIZED)

        # We pass the user object directly to the UserPermissionsSerializer
        # The serializer handles fetching the roles and calculating the permissions array.
        serializer = UserPermissionsSerializer(user)

        return Response(serializer.data, status=status.HTTP_200_OK)
