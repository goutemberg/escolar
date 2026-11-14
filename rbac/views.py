from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RoleForm
from .models import Role
from .rbac_service import RBACService


def role_list(request):
    """
    Lista todos os perfis cadastrados.
    """

    User = get_user_model()

    school = request.user.escola

    roles = Role.objects.select_related("group").order_by("display_order")

    total_users = User.objects.filter(escola=school).count()

    total_permissions = Permission.objects.count()

    context = {
        "roles": roles,
        "total_roles": roles.count(),
        "total_users": total_users,
        "total_permissions": total_permissions,
    }

    return render(
        request,
        "rbac/role_list.html",
        context,
    )


def role_create(request):
    """
    Cadastra um novo perfil.
    """

    if request.method == "POST":

        form = RoleForm(request.POST)

        if form.is_valid():

            group = Group.objects.create(name=form.cleaned_data["name"])

            role = form.save(commit=False)
            role.group = group
            role.save()

            messages.success(
                request,
                "Perfil cadastrado com sucesso.",
            )

            return redirect("rbac:role_list")

    else:

        form = RoleForm()

    context = {
        "titulo": "Novo Perfil",
        "form": form,
    }

    return render(
        request,
        "rbac/role_form.html",
        context,
    )


def role_edit(request, pk):
    """
    Edita um perfil.
    """

    role = get_object_or_404(
        Role,
        pk=pk,
    )

    if request.method == "POST":

        form = RoleForm(
            request.POST,
            instance=role,
        )

        if form.is_valid():

            role.group.name = form.cleaned_data["name"]
            role.group.save()

            form.save()

            messages.success(
                request,
                "Perfil atualizado com sucesso.",
            )

            return redirect("rbac:role_list")

    else:

        form = RoleForm(
            instance=role,
        )

    context = {
        "titulo": "Editar Perfil",
        "form": form,
        "role": role,
    }

    return render(
        request,
        "rbac/role_form.html",
        context,
    )


def role_delete(request, pk):
    """
    Exclui um perfil.
    """

    pass


def role_permissions(request, pk):
    """
    Gerencia as permissões de um perfil.
    """

    role = get_object_or_404(
        Role.objects.select_related("group"),
        pk=pk,
    )

    if request.method == "POST":

        permission_ids = request.POST.getlist("permissions")

        RBACService.update_permissions(
            role.group,
            permission_ids,
        )

        messages.success(
            request,
            "Permissões atualizadas com sucesso.",
        )

        return redirect("rbac:role_list")

    context = {
        "titulo": "Permissões",
        "role": role,
        "permissions_by_app": (RBACService.get_permissions_by_model(role.group)),
    }

    return render(
        request,
        "rbac/role_permissions.html",
        context,
    )


def role_users(request, pk):
    """
    Gerencia os usuários vinculados a um perfil.
    """

    role = get_object_or_404(
        Role.objects.select_related("group"),
        pk=pk,
    )

    school = request.user.escola

    users = RBACService.get_users_by_school(school)

    selected_users = set(
        RBACService.get_users_by_role(
            role.group,
            school,
        ).values_list(
            "id",
            flat=True,
        )
    )

    if request.method == "POST":

        user_ids = request.POST.getlist("users")

        RBACService.update_users(
            role.group,
            school,
            user_ids,
        )

        messages.success(
            request,
            "Usuários do perfil atualizados com sucesso.",
        )

        return redirect("rbac:role_list")

    context = {
        "titulo": "Usuários do Perfil",
        "role": role,
        "users": users,
        "selected_users": selected_users,
    }

    return render(
        request,
        "rbac/role_users.html",
        context,
    )
