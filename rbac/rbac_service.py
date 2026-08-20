from collections import defaultdict

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission


class RBACService:
    """
    Serviços relacionados ao RBAC.
    """

    SYSTEM_APPS = {
        "admin",
        "auth",
        "contenttypes",
        "sessions",
    }

    MODEL_NAMES = {
        "Aluno": "Alunos",
        "Ano Letivo": "Anos Letivos",
        "Auditlog": "Auditoria",
        "Autorizacoess": "Autorizações",
        "Avaliacao": "Avaliações",
        "Avaliacao Categoria": "Categorias de Avaliação",
        "Avaliacao Infantil": "Avaliações Infantis",
        "Boletim": "Boletins",
        "Chamada": "Chamadas",
        "Curso": "Cursos",
        "Disciplina": "Disciplinas",
        "Escola": "Escolas",
        "Funcionario": "Funcionários",
        "Matricula": "Matrículas",
        "Nota": "Notas",
        "Professor": "Professores",
        "Responsavel": "Responsáveis",
        "Sala": "Salas",
        "Turma": "Turmas",
        "Turma Disciplina": "Turmas / Disciplinas",
        "Usuario": "Usuários",
    }

    @staticmethod
    def format_permission_name(permission):
        """
        Converte os nomes padrão do Django para nomes amigáveis.
        """

        codename = permission.codename

        if codename.startswith("view_"):
            return "Visualizar"

        if codename.startswith("add_"):
            return "Cadastrar"

        if codename.startswith("change_"):
            return "Editar"

        if codename.startswith("delete_"):
            return "Excluir"

        return permission.name

    @classmethod
    def format_model_name(cls, content_type):
        """
        Retorna um nome amigável para o modelo.
        """

        model_class = content_type.model_class()

        if model_class:
            verbose_name = model_class._meta.verbose_name_plural.title()

            return cls.MODEL_NAMES.get(
                verbose_name,
                verbose_name,
            )

        fallback = content_type.model.replace("_", " ").title()

        return cls.MODEL_NAMES.get(
            fallback,
            fallback,
        )

    @classmethod
    def get_permissions_by_model(cls, group):
        """
        Retorna todas as permissões agrupadas por modelo.
        """

        grouped_permissions = defaultdict(list)

        selected_permissions = set(
            group.permissions.values_list(
                "id",
                flat=True,
            )
        )

        permissions = Permission.objects.select_related("content_type").order_by(
            "content_type__model",
            "codename",
        )

        for permission in permissions:

            if permission.content_type.app_label in cls.SYSTEM_APPS:
                continue

            model_name = cls.format_model_name(permission.content_type)

            grouped_permissions[model_name].append(
                {
                    "id": permission.id,
                    "name": cls.format_permission_name(permission),
                    "codename": permission.codename,
                    "checked": permission.id in selected_permissions,
                }
            )

        return dict(grouped_permissions)

    @staticmethod
    def update_permissions(group, permission_ids):
        """
        Atualiza as permissões de um grupo.
        """

        permissions = Permission.objects.filter(id__in=permission_ids)

        group.permissions.set(permissions)

    @staticmethod
    def get_users_by_role(group, school):
        """
        Retorna os usuários da escola que pertencem ao grupo.
        """

        User = get_user_model()

        return (
            User.objects.filter(escola=school)
            .filter(groups=group)
            .order_by(
                "first_name",
                "last_name",
                "username",
            )
        )

    @staticmethod
    def get_users_by_school(school):
        """
        Retorna todos os usuários da escola,
        indicando posteriormente quais pertencem ao grupo.
        """

        User = get_user_model()

        return User.objects.filter(escola=school).order_by(
            "first_name",
            "last_name",
            "username",
        )

    @staticmethod
    def update_users(group, school, user_ids):
        """
        Atualiza os usuários pertencentes ao grupo,
        considerando somente usuários da escola informada.
        """

        User = get_user_model()

        users = User.objects.filter(
            escola=school,
            id__in=user_ids,
        )

        group.user_set.remove(*User.objects.filter(escola=school))

        group.user_set.add(*users)
