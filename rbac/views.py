from django.http import HttpResponse


def role_list(request):
    return HttpResponse("Lista de Perfis")


def role_create(request):
    return HttpResponse("Criar Perfil")


def role_edit(request, pk):
    return HttpResponse(f"Editar Perfil {pk}")


def role_delete(request, pk):
    return HttpResponse(f"Excluir Perfil {pk}")


def role_permissions(request, pk):
    return HttpResponse(f"Permissões do Perfil {pk}")
