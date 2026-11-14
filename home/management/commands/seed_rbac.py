from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from rbac.models import Role
from rbac.roles import Roles


class Command(BaseCommand):
    help = "Cria os perfis padrão do sistema."

    def handle(self, *args, **options):

        roles = [
            {
                "name": Roles.ADMINISTRADOR,
                "description": "Acesso total ao sistema.",
                "icon": "bi-shield-lock-fill",
                "color": "danger",
                "order": 1,
            },
            {
                "name": Roles.DIRETOR,
                "description": "Gestão pedagógica e administrativa.",
                "icon": "bi-person-workspace",
                "color": "success",
                "order": 2,
            },
            {
                "name": Roles.COORDENADOR,
                "description": "Coordenação pedagógica.",
                "icon": "bi-diagram-3-fill",
                "color": "warning",
                "order": 3,
            },
            {
                "name": Roles.PROFESSOR,
                "description": "Lançamento de chamadas e notas.",
                "icon": "bi-mortarboard-fill",
                "color": "primary",
                "order": 4,
            },
            {
                "name": Roles.SECRETARIA,
                "description": "Cadastros e matrículas.",
                "icon": "bi-folder-fill",
                "color": "secondary",
                "order": 5,
            },
            {
                "name": Roles.FINANCEIRO,
                "description": "Gestão financeira.",
                "icon": "bi-cash-stack",
                "color": "info",
                "order": 6,
            },
            {
                "name": Roles.RESPONSAVEL,
                "description": "Acesso ao portal do responsável.",
                "icon": "bi-person-heart",
                "color": "dark",
                "order": 7,
            },
        ]

        for item in roles:

            group, _ = Group.objects.get_or_create(name=item["name"])

            Role.objects.get_or_create(
                group=group,
                defaults={
                    "description": item["description"],
                    "icon": item["icon"],
                    "color": item["color"],
                    "is_system": True,
                    "display_order": item["order"],
                },
            )

        self.stdout.write(self.style.SUCCESS("Perfis RBAC criados com sucesso!"))
