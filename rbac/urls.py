from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .import views as v

# instantiate router to register viewsets
router = DefaultRouter()
router.register(r'roles', v.RoleViewSet, basename='role')
router.register(r'permissions', v.PermissionReadOnlyViewSet, basename='permission')


urlpatterns = [
    # General RBAC management endpoints (Roles and Permissions) from the instantiated router
    path('', include(router.urls)),

    # User role assignment endpoints
    path('user-roles/assign/', v.UserRoleViewSet.as_view({'post': 'assign_role'}), name='user-role-assign'),
    path('user-roles/remove/', v.UserRoleViewSet.as_view({'post': 'remove_role'}), name='user-role-remove'),
    path('user-roles/user/<str:pk>/', v.UserRoleViewSet.as_view({'get': 'get_user_roles'}), name='user-role-list-by-phone'),
    path('user-roles/user/', v.UserRoleViewSet.as_view({'get': 'get_current_user_roles_and_permissions'}), name='user-role-permission'),
]
