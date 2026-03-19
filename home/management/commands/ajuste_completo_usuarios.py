from django.core.management.base import BaseCommand
from home.models import User, Role


class Command(BaseCommand):
    help = 'Ajusta CPF, username e roles dos usuários'

    def handle(self, *args, **kwargs):

        self.stdout.write("🚀 Iniciando ajuste completo de usuários...")

        total = 0

        # 🔹 1. Criar roles baseadas no ROLE_CHOICES
        for codigo, nome in User.ROLE_CHOICES:
            Role.objects.get_or_create(nome=codigo)

        self.stdout.write("✅ Roles garantidas")

        # 🔹 2. Ajustar usuários
        for user in User.objects.all():

            alterado = False

            # 🔸 CPF
            if user.cpf:
                cpf_limpo = user.cpf.replace('.', '').replace('-', '').replace('/', '')

                if user.cpf != cpf_limpo:
                    user.cpf = cpf_limpo
                    alterado = True

                # 🔸 username = cpf
                if user.username != cpf_limpo:
                    user.username = cpf_limpo
                    alterado = True

            # 🔸 roles
            if user.role:
                role_obj = Role.objects.filter(nome=user.role).first()

                if role_obj and role_obj not in user.roles.all():
                    user.roles.add(role_obj)
                    alterado = True

            if alterado:
                user.save()
                total += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Ajuste concluído! {total} usuários atualizados."))