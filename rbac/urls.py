from django.urls import path

from . import views

app_name = "rbac"

urlpatterns = [
    # Perfis
    path("roles/", views.role_list, name="role_list"),
    path("roles/create/", views.role_create, name="role_create"),
    path("roles/<int:pk>/edit/", views.role_edit, name="role_edit"),
    path("roles/<int:pk>/delete/", views.role_delete, name="role_delete"),
    # Permissões
    path(
        "roles/<int:pk>/permissions/",
        views.role_permissions,
        name="role_permissions",
    ),
]
