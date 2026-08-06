"""
Serviços responsáveis pelas regras de negócio do RBAC.
"""

from django.contrib.auth.models import Group


class RBACService:
    """Serviços relacionados ao controle de acesso."""

    @staticmethod
    def has_permission(user, permission):
        """
        Verifica se o usuário possui determinada permissão.
        """
        if not user or not user.is_authenticated:
            return False

        return user.has_perm(permission)

    @staticmethod
    def has_role(user, role):
        """
        Verifica se o usuário pertence a um determinado perfil.
        """
        if not user or not user.is_authenticated:
            return False

        return user.groups.filter(name=role).exists()

    @staticmethod
    def get_roles(user):
        """
        Retorna todos os perfis do usuário.
        """
        if not user or not user.is_authenticated:
            return Group.objects.none()

        return user.groups.all()
